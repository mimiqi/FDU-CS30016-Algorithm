"""生成任务二 Markdown 与 PDF。正文在本脚本的 build_content 中统一维护。"""
from pathlib import Path
import json
import re
import subprocess
from html import escape, unescape
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[2]
BHW = ROOT / 'bhw1'
OUT = BHW
TMP = ROOT / 'tmp' / 'pdfs' / 'task2'
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
PDF = OUT / '任务二报告_C题_复杂度审计.pdf'
MD = BHW / '任务二报告_C题.md'

pdfmetrics.registerFont(TTFont('Song', 'C:/Windows/Fonts/simsun.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei', 'C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('Roman', 'C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('RomanItalic', 'C:/Windows/Fonts/timesi.ttf'))
pdfmetrics.registerFont(TTFont('Math', 'C:/Windows/Fonts/cambria.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('Mono', 'C:/Windows/Fonts/consola.ttf'))
pdfmetrics.registerFontFamily('Song', normal='Song', bold='Hei', italic='Song', boldItalic='Hei')
pdfmetrics.registerFontFamily('Roman', normal='Roman', bold='Roman', italic='RomanItalic', boldItalic='RomanItalic')
pdfmetrics.registerFontFamily('Math', normal='Math', bold='Math', italic='Math', boldItalic='Math')
INK = colors.HexColor('#172331')
ACCENT = colors.HexColor('#274c67')
GRAY = colors.HexColor('#5d6772')
LIGHT = colors.HexColor('#eef2f5')
styles = {
    'body': ParagraphStyle('body', fontName='Song', fontSize=10.7, leading=17.3,
                           textColor=INK, spaceAfter=7, wordWrap='CJK'),
    'small': ParagraphStyle('small', fontName='Song', fontSize=9, leading=14,
                            textColor=GRAY, spaceAfter=6, wordWrap='CJK'),
    'h1': ParagraphStyle('h1', fontName='Hei', fontSize=16, leading=23,
                         textColor=ACCENT, spaceAfter=14, keepWithNext=True),
    'h2': ParagraphStyle('h2', fontName='Hei', fontSize=11.8, leading=19,
                         textColor=INK, spaceBefore=8, spaceAfter=7, keepWithNext=True),
    'eq': ParagraphStyle('eq', fontName='Math', fontSize=12.2, leading=21,
                         textColor=INK, alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
    'quote': ParagraphStyle('quote', fontName='Song', fontSize=10.4, leading=16.8,
                            textColor=INK, leftIndent=13, rightIndent=13,
                            spaceAfter=7, wordWrap='CJK'),
    'title': ParagraphStyle('title', fontName='Hei', fontSize=22, leading=31,
                            textColor=INK, spaceAfter=7),
    'code': ParagraphStyle('code', fontName='Mono', fontSize=9.4, leading=13),
}
story, markdown = [], []

def safe_markup(text, base):
    """为宋体缺失的数学字符及数学字体中的中文逐字符回退。"""
    result = []
    for part in re.split(r'(<[^>]+>)', text):
        if part.startswith('<'):
            result.append(part)
            continue
        for char in part:
            if char.isspace() or ord(char) in pdfmetrics.getFont(base).face.charToGlyph:
                result.append(char)
                continue
            fallback = next((f for f in ('Math', 'Song') if ord(char) in pdfmetrics.getFont(f).face.charToGlyph), None)
            if fallback is None:
                raise ValueError(f'Missing glyph: {char!r}, U+{ord(char):04X}')
            result.append(f'<font name="{fallback}">{char}</font>')
    return ''.join(result)

def plain(s):
    s = re.sub(r'<super>(.*?)</super>', r'^\1', s)
    s = re.sub(r'<sub>(.*?)</sub>', r'_\1', s)
    s = re.sub(r'<b>(.*?)</b>', r'**\1**', s)
    return unescape(re.sub('<[^>]+>', '', s))

def p(text, style='body'):
    story.append(Paragraph(safe_markup(text, styles[style].fontName), styles[style]))
    markdown.append(('> ' if style == 'quote' else '') + plain(text) + '\n')

def h(text, level=1):
    story.append(Paragraph(text, styles['h1' if level == 1 else 'h2']))
    markdown.append(('#' * (level + 1)) + ' ' + text + '\n')

def eq(tex, visual):
    story.append(Paragraph(safe_markup(visual, 'Math'), styles['eq']))
    markdown.append('$$\n' + tex + '\n$$\n')

def code(text):
    code_style = styles['code']
    if any(ord(c) > 127 for c in text):
        code_style = ParagraphStyle('codeCJK', parent=code_style, fontName='Song')
    block = Preformatted(text, code_style)
    box = Table([[block]], colWidths=[483])
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('LEFTPADDING', (0, 0), (-1, -1), 13),
        ('RIGHTPADDING', (0, 0), (-1, -1), 13),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.extend([box, Spacer(1, 10)])
    markdown.append('```text\n' + text + '\n```\n')

def page():
    story.append(PageBreak())
    markdown.append('\n<!-- pagebreak -->\n')

def build_content(data):
    p('算法设计课程 · 大作业1 · 任务二', 'small')
    story.append(Paragraph('可变比例递归的复杂度审计', styles['title']))
    markdown.append('# 任务二：可变比例递归的复杂度审计\n')
    p('C题｜模型少算一个 log n 因子的实例', 'small')
    p('姓名：________________　学号：________________　实验日期：2026-09-21', 'small')
    h('1　算法与问题定义')
    p('本实验设计一个划分比例随规模变化的递归算法。模型给出了看似完整的势函数论证，却将函数值误当作变化率，得到错误的紧确时间复杂度。本文保留模型原结论，定位错误等式，并给出下界反驳与正确的上下界证明。')
    p('<b>计算约定。</b>输入 n 为正整数。使用单位代价 RAM 模型：整数运算、比较、赋值、floor(log₂ n) 和 work() 均为 O(1)，整数不溢出。每次递归实际执行，没有缓存或记忆化。分析变量是数值 n；若改用输入位数衡量，须另作换元。')
    code('procedure C(n):\n    if n <= 3:\n        work()\n        return\n    k = floor(log2(n))\n    r = floor(n / k)\n    C(r)\n    C(n - r)\n    for i = 1 to n:\n        work()')
    p('<b>终止性。</b>n≥4 时，2≤k≤n，因而 1≤r≤n/2，两个子问题都是小于 n 的正整数。递归最终到达 n≤3 的基例。代码逻辑明确且能够正常执行。')
    p('令 T(n) 表示总时间。非递归部分为 Θ(n)，所以需要求解：')
    eq(r'T(n)=T(r)+T(n-r)+\Theta(n),\quad r=\left\lfloor n/\lfloor\log_2 n\rfloor\right\rfloor.',
       'T(n) = T(r) + T(n − r) + Θ(n),　r = ⌊n / ⌊log<sub>2</sub> n⌋⌋.')
    p('问题要求：给出关于 n 的紧确 Θ 界，并解释取整、基例与不均匀划分对结论的影响。')

    page()
    h('2　实验设置与模型原回答')
    p('2026-09-21，调用 gpt-5.6-luna，显式设置 reasoning_effort=low（轻度思考）、fork_turns=none。实际提示词同时包含 A、B、C 三题，要求独立分析且不得读取工作区或调用其他模型；没有提供正确答案或预期错误。A、B 答对，本报告选用答错的 C。后续消息仅询问进度，没有数学提示。', 'small')
    p('以下为原回答的 <b>C 部分完整摘录</b>，仅转换公式的排版，不改写其结论或推导。完整三题输入输出均已归档。', 'small')
    p('C：Θ(n log n / log log n)。', 'quote')
    p('递推为', 'quote')
    eq(r'T(n)=T(r)+T(n-r)+\Theta(n),\qquad r=\left\lfloor\frac n{\lfloor\log_2 n\rfloor}\right\rfloor.',
       'T(n) = T(r) + T(n − r) + Θ(n),　r = ⌊n / ⌊log<sub>2</sub> n⌋⌋.')
    p('令', 'quote')
    eq(r'F(n)=\frac{n\log n}{\log\log n}.', 'F(n) = n log n / log log n.')
    p('设 p=r/n=Θ(1/log n)。利用熵差：', 'quote')
    eq(r'F(n)-F(r)-F(n-r)=\Theta\!\left(\frac{n\log n}{\log\log n}\left[p\log\frac1p+(1-p)\log\frac1{1-p}\right]\right).',
       'F(n) − F(r) − F(n − r)<br/>= Θ((n log n / log log n) [p log(1/p) + (1 − p) log(1/(1 − p))]).')
    p('由于', 'quote')
    eq(r'p\log\frac1p=\Theta\!\left(\frac{\log\log n}{\log n}\right),',
       'p log(1/p) = Θ(log log n / log n),')
    p('上式为 Θ(n)。因此通过上下界归纳，递推解满足', 'quote')
    eq(r'T(n)=\Theta(F(n))=\Theta\!\left(\frac{n\log n}{\log\log n}\right).',
       'T(n) = Θ(F(n)) = Θ(n log n / log log n).')
    p('取整和停止条件只影响低阶项，不改变该渐近界。', 'quote')
    h('审计对象', 2)
    p('被反驳的是上述明确的 Θ 结论及支撑它的“熵差”等式，不是一个宽松上界。模型正确写出了递推式，错误发生在求解递推式的过程中。')

    page()
    h('3　错误定位与独立反驳')
    h('3.1　函数值不能代替变化率', 2)
    p('以下用自然对数分析同阶候选；保留原文的2底对数也得到相同差分阶。令 x=ln n、p=r/n，写 F(n)=n g(x)，其中 g(x)=x/ln x。实际的单次差分是：')
    eq(r'\Delta_F=r[g(x)-g(\ln r)]+(n-r)[g(x)-g(\ln(n-r))].',
       'Δ<sub>F</sub> = r[g(x) − g(ln r)] + (n − r)[g(x) − g(ln(n − r))].')
    p('因为 p=Θ(1/x)，有 ln r=x−Θ(ln x)、ln(n−r)=x−Θ(1/x)。当 n 足够大时，相关区间内的 u 均与 x 同阶，且 ln u 与 ln x 同阶。')
    eq(r'g\prime(u)=\frac{\ln u-1}{(\ln u)^2}=\Theta(1/\ln x).',
       'g′(u) = (ln u − 1) / (ln u)<super>2</super> = Θ(1 / ln x).')
    p('对两个差值分别应用中值定理。记 H(p)=p ln(1/p)+(1−p)ln(1/(1−p))，则 H(p)=Θ(ln x/x)，因此：')
    eq(r'\Delta_F=\Theta\!\left(\frac{nH(p)}{\ln x}\right)=\Theta(n/x)=\Theta(n/\ln n).',
       'Δ<sub>F</sub> = Θ(nH(p) / ln x) = Θ(n / x) = Θ(n / ln n).')
    p('<b>具体错误：</b>模型将差分写成 Θ(n g(x)H(p))；实际应使用 g 的导数，即 Θ(n g′(x)H(p))。这将势函数的下降量多估了一个 ln n 因子。真实下降量不足以对应节点的 Θ(n) 工作量，所谓“上下界归纳”因此不成立。')
    h('3.2　无需先求精确解，也能证明模型答案错误', 2)
    p('递归树是满二叉树。各叶子的规模在1到3之间，规模之和为 n，所以叶子数 L≥n/3。任意有 L 个叶子的二叉树，至少一半叶子的深度为 Ω(log L)：深度小于 log₂(L/2) 的叶子至多 L/2 个。因此叶子深度之和为 Ω(L log L)。')
    p('每个内部节点执行与其规模相等的 work 次数。将这些工作分摊到后代叶子，总内部工作量恰为各叶子的“规模×深度”之和，至少为叶子深度之和。故：')
    eq(r'T(n)=\Omega(n\log n),\qquad \frac{n\log n}{\log\log n}=o(n\log n).',
       'T(n) = Ω(n log n),　而 n log n / log log n = o(n log n).')
    p('模型的紧确界连这一普适下界都不满足。这证明其结论是实质错误，而不只是证明省略了细节。')

    page()
    h('4　正确复杂度：单次分裂的工作量')
    h('4.1　不均匀划分造成的对数规模下降', 2)
    p('令 x=ln n、p=r/n。由 k=⌊log₂ n⌋=Θ(x)、r=⌊n/k⌋，对充分大的 n 有 p=Θ(1/x)。较小子问题的对数规模下降 Θ(ln x)，较大子问题的下降 Θ(1/x)：')
    eq(r'\ln n-\ln r=\ln(1/p)=\Theta(\ln x),',
       'ln n − ln r = ln(1/p) = Θ(ln x),')
    eq(r'\ln n-\ln(n-r)=-\ln(1-p)=\Theta(1/x).',
       'ln n − ln(n − r) = −ln(1 − p) = Θ(1/x).')
    p('以子问题规模占比为权重，平均对数下降量为 H(p)。这里“平均”只是确定性代数加权，不假设算法包含随机行为。由于 p 趋于0：')
    eq(r'H(p)=p\ln(1/p)+(1-p)\ln(1/(1-p))=\Theta(\ln x/x).',
       'H(p) = p ln(1/p) + (1 − p) ln(1/(1 − p)) = Θ(ln x / x).')
    p('其中第一项为 Θ(ln x/x)，第二项为 Θ(1/x)。因此第一项主导，分母中的 ln ln n 由此出现。')
    h('4.2　构造正确的势函数', 2)
    p('选择对充分大 n 定义的势函数 Φ(n)=n G(ln n)，使其每次分裂的下降量与局部工作 Θ(n) 同阶。取：')
    eq(r'G(x)=\frac{x^2}{\ln x},\qquad \Phi(n)=\frac{n(\ln n)^2}{\ln\ln n}.',
       'G(x) = x<super>2</super> / ln x,　Φ(n) = n(ln n)<super>2</super> / ln ln n.')
    eq(r'G\prime(u)=\frac{u(2\ln u-1)}{(\ln u)^2}=\Theta(x/\ln x).',
       'G′(u) = u(2 ln u − 1) / (ln u)<super>2</super> = Θ(x / ln x).')
    p('上述导数估计在 [ln r, x] 的整个区间内一致成立，因为 ln r=x−Θ(ln x)，故区间内 u=Θ(x)。分别对两个差值应用中值定理，且二者均为非负：')
    eq(r'\Delta_\Phi=\Phi(n)-\Phi(r)-\Phi(n-r)',
       'Δ<sub>Φ</sub> = Φ(n) − Φ(r) − Φ(n − r)')
    eq(r'=\Theta\!\left(\frac{x}{\ln x}\,[r\ln(n/r)+(n-r)\ln(n/(n-r))]\right)',
       '= Θ((x / ln x) [r ln(n/r) + (n − r) ln(n/(n − r))])')
    eq(r'=\Theta\!\left(\frac{x}{\ln x}\,nH(p)\right)=\Theta(n).',
       '= Θ((x / ln x) nH(p)) = Θ(n).')
    p('因此存在与 n 无关的正常数 a、b 和固定阈值 N₀，使所有 n≥N₀ 均满足 a n≤ΔΦ≤b n。这是下一页求全树总成本所需的统一上下界。')

    page()
    h('5　递归树求和、取整与紧确结论')
    h('5.1　势能差沿整棵树相消', 2)
    p('把递归树在子问题规模小于固定阈值 N₀ 时截断，记大规模内部节点集合为 I，边界子问题集合为 B。将 Φ 在有限的小规模输入上任意延拓为正有界值；必要时增大 N₀，不影响上一页的渐近估计。')
    p('每次分裂都保持规模之和，故边界子问题的规模总和为 n。其个数至多 n，每个规模有固定上界，因此边界势能总和、以及继续求解这些边界子问题的实际成本，均为 O(n)。内部势能差求和时，中间项全部相消：')
    eq(r'\sum_{v\in I}\Delta_\Phi(n_v)=\Phi(n)-\sum_{b\in B}\Phi(n_b)=\Phi(n)-O(n).',
       'Σ<sub>v∈I</sub> Δ<sub>Φ</sub>(n<sub>v</sub>) = Φ(n) − Σ<sub>b∈B</sub> Φ(n<sub>b</sub>) = Φ(n) − O(n).')
    p('由于 Φ(n)/n 趋于无穷，上式为 Θ(Φ(n))。再用每个节点的统一估计 a nᵥ≤ΔΦ(nᵥ)≤b nᵥ，得到内部节点规模总和为 Θ(Φ(n))。节点实际成本为 Θ(nᵥ)，加入 O(n) 的边界成本，最终得到：')
    eq(r'\boxed{T(n)=\Theta\!\left(\frac{n(\log n)^2}{\log\log n}\right)}',
       '<b>T(n) = Θ(n (log n)<super>2</super> / log log n)</b>')
    p('这是对全部充分大正整数 n 的上下界证明，不只适用于2的幂。证明比较了每一个实际分裂，不需要把递归树假设为平衡树，也没有使用“最长深度×每层 n”的不紧估计。')
    h('5.2　取整与基例为什么不改变结论', 2)
    p('对足够大的 n，floor(log₂ n) 与 ln n 相差常数倍，且 floor(n/k) 与 n/k 相差不足1。由于 n/k 趋于无穷，实际 p 仍被两个正常数倍的 1/ln n 夹住，前述区间和导数估计全部保留。小规模输入则由固定阈值统一吸收，其总贡献为 O(n)。')
    p('n≤3 的基例是算法定义的一部分，保证递归终止，不能随意改成 n≤2。报告始终分析正式实验中已修正的版本。')
    h('5.3　这个结构为什么容易误判', 2)
    p('① 两个子问题规模之和为 n，外观接近归并排序，但划分比例约为 1/log n，并非常数。普通主定理不能直接套用。')
    p('② “熵”确实能表达一次分裂的加权对数下降量，容易让一个结构相似、却少了导数的等式显得可信。')
    p('③ 模型选择了合理的候选函数并写出“上下界归纳”，但归纳真正需要的是单次差分能抵偿 Θ(n) 成本；这一关键检查没有完成。')

    page()
    h('6　可复核实验与结论')
    p('令 W(n) 仅统计 work() 的执行次数。每个递归节点至少执行一次 work，其他控制开销被 W(n) 的常数倍界定，因此 T(n)=Θ(W(n))。精确计数满足：')
    eq(r'W(n)=1\ (n\le3);\qquad W(n)=W(r)+W(n-r)+n\ (n\ge4).',
       'W(n) = 1　(n ≤ 3);　W(n) = W(r) + W(n − r) + n　(n ≥ 4).')
    p('复核脚本用动态规划计算这些递推值，避免重复计算相同规模。这里的动态规划是<b>审计工具</b>，没有改变被分析算法“不使用记忆化”的约定，也不把计数工具自身的耗时当成原算法复杂度。')
    p('用直接递归逐一复核 n=1…512，结果与动态规划完全一致；另对正式递推计数到 n=2²⁰。下表的对数以2为底，Q(n)=n(log₂ n)²/log₂(log₂ n)。')
    selected = [x for x in data['results'] if x['n'] in [256, 4096, 65536, 1048576]]
    rows = [['n', '精确 work 次数 W(n)', 'W(n) / Q(n)']]
    for item in selected:
        rows.append([f"{item['n']:,}", f"{item['workCalls']:,}", f"{item['dividedByNLogSquaredNOverLogLogN']:.6f}"])
    cells = [[Paragraph(escape(x), styles['small']) for x in row] for row in rows]
    table = Table(cells, colWidths=[125, 190, 168], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT),
        ('LINEBELOW', (0,0), (-1,0), .7, ACCENT),
        ('LINEBELOW', (0,-1), (-1,-1), .5, colors.HexColor('#c6ced5')),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.extend([table, Spacer(1,10)])
    markdown.extend(['| ' + ' | '.join(rows[0]) + ' |\n', '|---|---:|---:|\n'])
    markdown.extend('| ' + ' | '.join(row) + ' |\n' for row in rows[1:])
    p('归一化计数与理论结果相容，但有限规模的数值不能证明渐近阶；紧确界由第4、5节的数学推导保证。')
    h('6.1　材料与复现入口', 2)
    p('实验目录：bhw1/实验原始记录/2026-09-21_03_任务二Luna轻度三题/。其中 00 为实验元数据，01 为完整三题提示词，01b 为仅询问进度的后续消息，02 为未经改写的完整模型回答，04 保存原始记录的 SHA-256 校验值。分析单独写在 03_审计说明.md。', 'small')
    p('这些记录来自独立子代理实验，模型与思考强度依据实际调用参数；未提供公开会话链接或底层消息导出。本 PDF 中只摘录选用的 C 部分，原始三题记录保留完整上下文。', 'small')
    code('node bhw1/验证/task2-candidate-count.cjs\nnode bhw1/验证/task2-report-audit.cjs')
    p('脚本与生成结果均位于 bhw1/验证/。作业要求原文为《大作业1 -- 挑战大模型——算法正确性与复杂度审计.md》，未作修改。', 'small')
    h('6.2　结论', 2)
    p('本题代码简短、运行语义明确。Luna 在本次轻度思考实验中正确建立递推，却在势函数差分中混淆函数值与变化率，从而少算一个 log n 因子。正确复杂度为 Θ(n(log n)²/log log n)。本报告依次给出了伪代码、模型分析、具体错误、正确渐近界和完整推导，覆盖任务二的五项要求。')
    p('这是一次具体实验的结论；其他轮次曾给出正确答案，因此不将本次错误外推为模型在所有设置下的稳定表现。', 'small')

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved = []
    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        count = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self.setStrokeColor(colors.HexColor('#c6ced5'))
            self.setLineWidth(.5)
            self.line(56, 43, A4[0]-56, 43)
            self.setFillColor(GRAY)
            self.setFont('Song', 8)
            self.drawString(56, 29, '算法设计 · 任务二 | 可变比例递归的复杂度审计')
            self.setFont('Roman', 9)
            self.drawRightString(A4[0]-56, 29, f'{self._pageNumber} / {count}')
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

if __name__ == '__main__':
    raw = subprocess.check_output(['node', str(BHW / '验证' / 'task2-candidate-count.cjs')], text=True, encoding='utf-8')
    data = json.loads(raw)
    (BHW / '验证' / '任务二_C题_验证结果.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    build_content(data)
    MD.write_text('\n'.join(markdown), encoding='utf-8')
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, rightMargin=56, leftMargin=56,
                            topMargin=43, bottomMargin=57, title='任务二：可变比例递归的复杂度审计',
                            author='课程实验报告', subject='gpt-5.6-luna / low 的时间复杂度分析错误')
    doc.build(story, canvasmaker=NumberedCanvas)
    print(PDF)
