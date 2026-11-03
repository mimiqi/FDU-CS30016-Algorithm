"""Render the user's Markdown report without regenerating or overwriting its prose."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from pypdf import PdfReader

from build_report import init, typeset, NAVY, PALE, LINE, MUTED

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blocks(source):
    lines = source.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
        elif line.startswith('```'):
            content = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith('```'):
                content.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError('Unclosed Markdown code block')
            yield 'code', '\n'.join(content)
            index += 1
        elif line == '---':
            yield 'break', None
            index += 1
        elif line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                cells = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            if not rows or any(len(row) != len(rows[0]) for row in rows):
                raise ValueError('Invalid table shape')
            yield 'table', rows
        elif line.startswith('# '):
            yield 'title', line[2:]
            index += 1
        elif line.startswith('## '):
            yield 'heading', line[3:]
            index += 1
        else:
            content = [line]
            index += 1
            while index < len(lines) and lines[index].strip():
                next_line = lines[index].strip()
                if next_line.startswith(('# ', '## ', '```', '|')) or next_line == '---':
                    break
                content.append(next_line)
                index += 1
            yield 'paragraph', ' '.join(content)


def restore_math(text):
    # The former HTML-to-Markdown export dropped <super> tags. Restore those
    # specific expressions for PDF typography; retain the source file verbatim.
    for old, new in [
        ('p(s)k', 'p(s)^k'),
        ('(1−p(s)^k)L', '(1−p(s)^k)^L'),
        ('p(0.80)k', 'p(0.80)^k'),
        ('p(s₀)k', 'p(s₀)^k'),
        ('L·2k', 'L·2^k'),
    ]:
        text = text.replace(old, new)
    return text


def formatted(text):
    text = html.escape(restore_math(text), quote=False)
    text = re.sub(r'\^([A-Za-z0-9]+)', r'<super>\1</super>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return typeset(text)


def normalized(text):
    return re.sub(r'\s+', '', text)


def widths(headers, total):
    if len(headers) == 2:
        weights = [82, 410]
    elif len(headers) == 5:
        weights = [35, 50, 80, 80, 190]
    elif len(headers) == 6:
        weights = [108, 62, 62, 78, 62, 62]
    elif headers[0] == '方法':
        weights = [205, 90, 90, 90]
    else:
        weights = [110] * len(headers)
    return [total * weight / sum(weights) for weight in weights]


def build(source_path, output_path):
    source_path = source_path.resolve()
    output_path = output_path.resolve()
    source_sha = digest(source_path)
    source = source_path.read_text(encoding='utf-8')
    content = list(blocks(source))
    page_count = 1 + sum(kind == 'break' for kind, _ in content)
    assert 3 <= page_count <= 4, 'The report requires three or four pages'
    styles = init()
    styles['title'].fontSize = 18
    styles['title'].leading = 25
    styles['body'].fontSize = 9.8
    styles['body'].leading = 15.8
    styles['sub'].spaceAfter = 12
    styles['code'].fontSize = 8.4
    styles['code'].leading = 11.5
    total_width = A4[0] - 36 * mm
    story = []
    expected_text = []
    section = ''
    table_count = 0
    reflection_chars = None
    for kind, value in content:
        if kind == 'break':
            story.append(PageBreak())
            continue
        if kind == 'code':
            story.append(Preformatted(value, styles['code']))
            expected_text.extend(line.strip() for line in value.splitlines() if line.strip())
            continue
        if kind == 'table':
            table_count += 1
            rows = [
                [Paragraph(formatted(cell), styles['head' if i == 0 else 'cell']) for cell in row]
                for i, row in enumerate(value)
            ]
            table = Table(rows, colWidths=widths(value[0], total_width), repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, LINE),
            ]))
            story.extend([table, Spacer(1, 6)])
            expected_text.extend(cell for row in value for cell in row)
            continue
        style = 'body'
        display = value
        if kind == 'title':
            style = 'title'
        elif kind == 'heading':
            style = 'h'
            section = value
        elif value.startswith('大作业 4 ·'):
            style = 'sub'
            display = display.replace('姓名：', '<LINEBREAK>姓名：')
        elif section == '参考与复现':
            style = 'tiny'
            display = re.sub(r'。(?=\[[23]\])', '。<LINEBREAK>', display)
        elif section.startswith('8 '):
            reflection_chars = len(value)
        rendered = formatted(display).replace('&lt;LINEBREAK&gt;', '<br/>')
        story.append(Paragraph(rendered, styles[style]))
        expected_text.append(value)

    def footer(canvas, document):
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
        canvas.setFont('CN', 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 11 * mm, '算法设计与分析  |  大作业 4')
        canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f'{document.page} / {page_count}')

    title = next(value for kind, value in content if kind == 'title')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(output_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=22 * mm, title=title,
    ).build(story, onFirstPage=footer, onLaterPages=footer)

    assert source_sha == digest(source_path), 'Source Markdown was changed during conversion'
    reader = PdfReader(output_path)
    assert len(reader.pages) == page_count, f'Unexpected overflow: {len(reader.pages)} pages'
    extracted = [page.extract_text() for page in reader.pages]
    combined = normalized('\n'.join(extracted))
    # Verify every text paragraph, table cell and nonempty code line survives.
    for item in expected_text:
        expected = html.unescape(re.sub(r'<[^>]+>', '', formatted(item)))
        assert normalized(expected) in combined, f'Missing source content: {item[:80]}'
    assert reflection_chars is not None and reflection_chars <= 300
    assert all(len(text) > 350 for text in extracted)
    check = {
        'pages': len(reader.pages),
        'page_sizes': [[float(page.mediabox.width), float(page.mediabox.height)] for page in reader.pages],
        'page_text_chars': [len(text) for text in extracted],
        'tables': table_count,
        'reflection_chars': reflection_chars,
        'pdf_sha256': digest(output_path),
        'source_markdown': str(source_path),
        'source_markdown_sha256': source_sha,
        'renderer': str(Path(__file__).resolve()),
        'renderer_sha256': digest(__file__),
        'source_markdown_unchanged': True,
        'source_blocks_checked': len(expected_text),
        'formula_typography': 'Restored superscript k/L in known probability and memory formulas',
        'text_checks': 'passed',
        'visual_review': 'pending',
    }
    (ROOT / '验证/报告检查.json').write_text(
        json.dumps(check, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    print(json.dumps(check, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', nargs='?', type=Path, default=ROOT / '大作业4_报告正文.md')
    parser.add_argument('--output', type=Path, default=ROOT / '作业4.pdf')
    args = parser.parse_args()
    build(args.source, args.output)
