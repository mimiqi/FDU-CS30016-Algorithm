"""只读用户审阅过的 Markdown，将其转换为 PDF，绝不回写正文。

用法：python render-reviewed-markdown.py [输入.md] [输出.pdf]
已有公式只有在 LaTeX 文本完全匹配（忽略空白）时才复用旧版排版。
未识别的新公式会明确报错，避免静默套用旧内容。
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from html import escape, unescape
import unicodedata

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'bhw1/大作业1_正式审阅稿.md'
OUTPUT = Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'bhw1/大作业1_算法正确性与复杂度审计_正式审阅稿.pdf'
QA = ROOT/'bhw1/审计记录/已审阅Markdown_PDF检查.json'
spec=importlib.util.spec_from_file_location('report_layout',HERE/'build-task2-report.py')
L=importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

def norm_tex(s):
    return re.sub(r'\s+','',s)

def load_formula_layouts():
    result={}
    for name in ('build-task2-report.py','build-formal-report.py'):
        tree=ast.parse((HERE/name).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='eq' and len(node.args)==2:
                tex,visual=(ast.literal_eval(x) for x in node.args)
                result[norm_tex(tex)]=visual
    return result

def inline(text):
    # Preserve words and punctuation; interpret only Markdown's bold and code spans.
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font name="Mono">\1</font>',text)
    return text

expected=[]
counts={'paragraphs':0,'headings':0,'mathBlocks':0,'codeBlocks':0,'tables':0,'pageBreaks':0}

def record(text):
    text=re.sub(r'\*\*(.+?)\*\*',r'\1',text)
    text=re.sub(r'`([^`]+)`',r'\1',text)
    if text.strip():expected.append(text)

def paragraph(text,kind='body'):
    L.story.append(L.Paragraph(L.safe_markup(inline(text),L.styles[kind].fontName),L.styles[kind]))
    counts['paragraphs']+=1
    record(text)

def render_table(lines):
    rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    assert len(rows)>=2
    assert all(re.fullmatch(r':?-+:?',c) for c in rows[1]), 'Invalid Markdown table separator'
    rows.pop(1)
    headers=rows[0]
    assert all(len(r)==len(headers) for r in rows)
    if len(headers)==5:
        widths=[35,116,108,116,108]; size=8.6
    elif headers[0]=='共同属性':
        widths=[120,70,180,113]; size=9.0
    elif headers[0]=='tick':
        widths=[35,138,150,160]; size=9.0
    elif headers[0]=='验证场景':
        widths=[180,101,101,101]; size=9.0
    elif len(headers)==3:
        widths=[135,195,153]; size=9.0
    else:
        widths=[483/len(headers)]*len(headers); size=9.0
    sty=L.ParagraphStyle('sourceTable',parent=L.styles['body'],fontSize=size,leading=size+3,spaceAfter=0)
    cells=[]
    for row in rows:
        current=[]
        for j,c in enumerate(row):
            visual=inline(c)
            if len(headers)==5 and j in (1,3):
                visual=visual.replace('；','；<br/>')
            current.append(L.Paragraph(L.safe_markup(visual,'Song'),sty))
            record(c)
        cells.append(current)
    t=L.Table(cells,colWidths=widths,repeatRows=1)
    t.setStyle(L.TableStyle([
        ('BACKGROUND',(0,0),(-1,0),L.LIGHT),
        ('LINEBELOW',(0,0),(-1,0),.7,L.ACCENT),
        ('LINEBELOW',(0,-1),(-1,-1),.5,L.colors.HexColor('#bfc9d2')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[L.colors.white,L.colors.HexColor('#f7f9fa')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))
    L.story.extend([t,L.Spacer(1,9)])
    counts['tables']+=1

def render(text):
    formulas=load_formula_layouts()
    lines=text.splitlines()
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line=='<!-- pagebreak -->':
            L.story.append(L.PageBreak()); counts['pageBreaks']+=1; i+=1;continue
        if line.startswith('```'):
            block=[];i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i]); i+=1
            if i==len(lines):raise ValueError('Unclosed code block')
            L.code('\n'.join(block));counts['codeBlocks']+=1
            for row in block:record(row)
            i+=1;continue
        if line=='$$':
            block=[];i+=1
            while i<len(lines) and lines[i].strip()!='$$':block.append(lines[i]);i+=1
            if i==len(lines):raise ValueError('Unclosed math block')
            tex='\n'.join(block)
            visual=formulas.get(norm_tex(tex))
            if visual is None:raise ValueError('New formula requires explicit typesetting: '+tex)
            L.eq(tex,visual);counts['mathBlocks']+=1;i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                block.append(lines[i]);i+=1
            render_table(block);continue
        match=re.match(r'^(#{1,6})\s+(.+)$',line)
        if match:
            level=len(match[1]);title=match[2]
            style=L.styles['title' if level==1 else ('h1' if level==2 else 'h2')]
            L.story.append(L.Paragraph(L.safe_markup(inline(title),style.fontName),style))
            record(title);counts['headings']+=1;i+=1;continue
        if line.startswith('<!--'):
            raise ValueError('Unsupported comment; review before dropping content: '+line)
        block=[]
        quote=line.startswith('>')
        while i<len(lines) and lines[i].strip():
            current=lines[i].strip()
            if current=='$$' or current.startswith(('```','<!--','#','|')):break
            if current.startswith('>')!=quote:break
            block.append(re.sub(r'^>\s?','',current) if quote else current);i+=1
        if not block:raise ValueError('Unsupported Markdown at line '+str(i+1))
        text=' '.join(block)
        kind='quote' if quote else 'body'
        if text.startswith(('姓名：','算法设计课程 ·')):kind='small'
        paragraph(text,kind)

class PageCanvas(L.NumberedCanvas):
    def save(self):
        count=len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self.setStrokeColor(L.colors.HexColor('#c6ced5'));self.setLineWidth(.5)
            self.line(56,43,L.A4[0]-56,43)
            self.setFillColor(L.GRAY);self.setFont('Song',8)
            self.drawString(56,29,'大作业1 | 算法正确性与复杂度审计')
            self.setFont('Roman',9);self.drawRightString(L.A4[0]-56,29,f'{self._pageNumber} / {count}')
            L.canvas.Canvas.showPage(self)
        L.canvas.Canvas.save(self)

def norm_text(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s))

if __name__=='__main__':
    raw=SOURCE.read_bytes();source_hash=hashlib.sha256(raw).hexdigest()
    render(raw.decode('utf-8-sig'))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    doc=L.SimpleDocTemplate(str(OUTPUT),pagesize=L.A4,leftMargin=56,rightMargin=56,topMargin=43,bottomMargin=57,
        title='挑战大模型：算法正确性与复杂度审计',author='张祺昀',subject='依据用户审阅后的Markdown导出')
    doc.build(L.story,canvasmaker=PageCanvas)
    assert SOURCE.read_bytes()==raw,'Source Markdown changed unexpectedly'
    from pypdf import PdfReader
    reader=PdfReader(OUTPUT)
    extracted='\n'.join(page.extract_text() for page in reader.pages)
    norm=norm_text(extracted)
    missing=[t for t in expected if norm_text(t) not in norm]
    assert not missing, 'Content missing from PDF: '+repr(missing[:3])
    assert '\x00' not in extracted and '\ufffd' not in extracted
    for index,page in enumerate(reader.pages,1):assert f'{index} / {len(reader.pages)}' in page.extract_text()
    result={'source':str(SOURCE),'sourceSha256':source_hash,'sourceUnchanged':True,'pdf':str(OUTPUT),
        'pdfSha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),'pages':len(reader.pages),
        'blocks':counts,'verifiedTextFragments':len(expected),'contentCoveragePass':True,
        'mathLayoutRule':'Exact LaTeX match to verified layout; whitespace differences ignored.',
        'visualReview':'pending'}
    QA.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
