"""Generate a four-page Chinese report from verified measurements and the same prose as Markdown."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import hashlib, html, json, re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon
from pypdf import PdfReader
from prepare import save,sha

W,H=A4; WIDTH=W-36*mm
NAVY=colors.HexColor('#17374D'); TEAL=colors.HexColor('#087F8C')
INK=colors.HexColor('#253746'); MUTED=colors.HexColor('#5C6F7B')
PALE=colors.HexColor('#EDF5F7'); LINE=colors.HexColor('#CDDBE2')
MI=1024**2
REFLECTION=('好的 Embedding 解决如何表示语义，却不消除搜索成本。单次扫描仍需 O(Nd)，若全部请求两两比较则需 O(N²d)，'
            '数据增长会吞噬算力、内存带宽与响应时间。Hash 的价值既包括精确键的快速查找，更在于按相似性组织候选，'
            '把昂贵精筛集中到更有希望的区域。设计者必须同时控制漏检、候选数量、投影成本和索引空间，并随规模调整参数。'
            '因此语义检索仍是选择数据结构、概率保证与资源预算的算法设计问题。')
CODE='''Build(X, texts, k, L):
  Exact = SHA256(text) -> list of matching IDs
  Sample independent R[t,j] ~ Normal(0, I_d)
  For each i, t: insert i into Bucket[t, H_t(X[i])]

Retrieve(q):
  A = Exact.get(SHA256(q), [])
  A = [i in A where texts[i] == q]   # verify collisions
  if A is not empty: return A      # no embedding needed
  u = Normalize(Embed(q))
  C = empty set
  for t = 1 ... L:
    C = C union Bucket[t, H_t(u)]
  return [i in C where Dot(u, X[i]) >= tau]'''

def init():
    pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
    pdfmetrics.registerFont(TTFont('Code','C:/Windows/Fonts/consola.ttf'))
    return {
      'title':ParagraphStyle('title',fontName='CNB',fontSize=19,leading=26,textColor=NAVY,spaceAfter=7),
      'sub':ParagraphStyle('sub',fontName='CN',fontSize=9,leading=14,textColor=MUTED,spaceAfter=10),
      'h':ParagraphStyle('h',fontName='CNB',fontSize=11.5,leading=17,textColor=NAVY,spaceBefore=8,spaceAfter=5,keepWithNext=True),
      'body':ParagraphStyle('body',fontName='CN',fontSize=10,leading=16.2,textColor=INK,spaceAfter=6,wordWrap='CJK'),
      'small':ParagraphStyle('small',fontName='CN',fontSize=8.7,leading=13.4,textColor=MUTED,spaceAfter=5,wordWrap='CJK'),
      'tiny':ParagraphStyle('tiny',fontName='CN',fontSize=7.4,leading=11,textColor=MUTED,spaceAfter=3,wordWrap='CJK'),
      'cell':ParagraphStyle('cell',fontName='CN',fontSize=8.2,leading=12,textColor=INK,wordWrap='CJK'),
      'head':ParagraphStyle('head',fontName='CNB',fontSize=8.1,leading=12,textColor=colors.white,wordWrap='CJK'),
      'code':ParagraphStyle('code',fontName='Code',fontSize=8.5,leading=11.4,textColor=INK,leftIndent=7,spaceBefore=4,spaceAfter=6),
    }

def flow():
    d=Drawing(WIDTH,95)
    boxes=[(0,48,88,['原始查询 q','SHA-256 + 原文比较']),
           (115,48,98,['Exact 命中','直接返回相等文本 ID']),
           (0,0,88,['Exact 未命中','Embedding + 归一化']),
           (115,0,98,['46 张表查桶','合并并去重候选 C']),
           (245,0,111,['只精筛候选','cos ≥ 0.80 则返回']),
           (383,0,WIDTH-383,['没有结果','交给后续生成流程'])]
    for x,y,w,lines in boxes:
        d.add(Rect(x,y,w,35,rx=3,fillColor=PALE,strokeColor=LINE))
        for j,line in enumerate(lines):
            d.add(String(x+w/2,y+22-j*12,line,fontName='CN',fontSize=7.1,fillColor=INK,textAnchor='middle'))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=TEAL,strokeWidth=1))
        if x2>x1:d.add(Polygon([x2,y2,x2-4,y2+2,x2-4,y2-2],fillColor=TEAL,strokeColor=TEAL))
        else:d.add(Polygon([x2,y2,x2-2,y2+4,x2+2,y2+4],fillColor=TEAL,strokeColor=TEAL))
    arrow(88,65,115,65); arrow(44,48,44,35)
    arrow(88,17,115,17); arrow(213,17,245,17); arrow(356,17,383,17)
    return d

def footer(canvas,doc):
    canvas.setStrokeColor(LINE); canvas.line(18*mm,16*mm,W-18*mm,16*mm)
    canvas.setFont('CN',7.5); canvas.setFillColor(MUTED)
    canvas.drawString(18*mm,11*mm,'算法设计与分析  |  大作业 4  |  可复现实验审阅稿')
    canvas.drawRightString(W-18*mm,11*mm,f'{doc.page} / 4')

def typeset(text):
    """Use supported base glyphs for subscripts and ceilings; reject tofu glyphs."""
    for old,new in {'ᵢ':'<sub>i</sub>','ᵣ':'<sub>r</sub>','₀':'<sub>0</sub>',
                    '₁':'<sub>1</sub>','ₜ':'<sub>t</sub>','∼':'~','⌈':'ceil(','⌉':')'}.items():
        text=text.replace(old,new)
    plain=html.unescape(re.sub('<[^>]+>','',text))
    missing={c for c in plain if ord(c)>32 and ord(c) not in pdfmetrics.getFont('CN').face.charToGlyph}
    assert not missing,repr(missing)
    return text

def build():
    global STYLES
    STYLES=init()
    R=json.loads((ROOT/'验证/实验结果.json').read_text(encoding='utf8'))
    audit=json.loads((ROOT/'验证/审计结果.json').read_text(encoding='utf8'))
    meta=json.loads((ROOT/'验证/向量元数据.json').read_text(encoding='utf8'))
    assert audit['status']=='passed' and audit['experiment_sha256']==sha(ROOT/'验证/实验结果.json')
    main=R['main']; s=main['summary']; n=R['N']; memory=R['memory']; timing=R['semantic_timing']
    lsh_bytes=memory['lsh']['payload_bytes']+memory['lsh']['container_bytes']
    index_bytes=memory['exact_index_bytes']+lsh_bytes
    story=[]; markdown=['# 大作业4 用 Hash 与 LSH 加速大模型语义复用','']
    def p(text,style='body'):
        story.append(Paragraph(typeset(text),STYLES[style]))
        markdown.extend([html.unescape(re.sub('<[^>]+>','',text)),''])
    def h(text):
        story.append(Paragraph(text,STYLES['h'])); markdown.extend(['## '+text,''])
    def table(headers,rows,widths):
        cells=[[Paragraph(typeset(str(x)),STYLES['head']) for x in headers]]+[[Paragraph(typeset(str(x)),STYLES['cell']) for x in row] for row in rows]
        t=Table(cells,colWidths=[WIDTH*w/sum(widths) for w in widths],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
                              ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                              ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                              ('LINEBELOW',(0,-1),(-1,-1),.5,LINE)]))
        story.append(t); story.append(Spacer(1,6))
        clean=lambda v:html.unescape(re.sub('<[^>]+>',' ',str(v)))
        markdown.append('| '+' | '.join(map(clean,headers))+' |')
        markdown.append('| '+' | '.join(['---']*len(headers))+' |')
        markdown.extend('| '+' | '.join(map(clean,row))+' |' for row in rows);markdown.append('')
    def page():story.append(PageBreak());markdown.extend(['---',''])

    p('用 Hash 与 LSH 加速语义复用','title')
    p('大作业 4 · Hash-based Semantic Retrieval · 2026-10-22<br/>姓名：________________　学号：________________','sub')
    h('1  问题与数据集')
    p('历史请求有 N 条、向量维度为 d。逐个查询全部向量需要 O(Nd) 计算。本系统先通过 Exact Hash 判断原文重复，未命中时才由 LSH 生成候选，再计算候选的真实余弦相似度。研究目标是减少检查范围，同时量化遗漏和索引开销。')
    table(['实验项','固定设置'],[
       ['历史库','BANKING77 官方训练集，精确去重后 N=10,003；77 个意图 [1]'],
       ['查询','测试集去除原文重叠并去重，固定种子抽取 300 条；另取 100 条历史原文作 Exact 查询'],
       ['向量','all-MiniLM-L6-v2，384 维；官方 ONNX AVX2 uint8 量化导出，CPU 推理 [2]'],
       ['预处理','最多 256 tokens；掩码均值池化 + L2 归一化；保存 float32 向量'],
       ['相关性','τ=0.80；G(q)={i : u·vᵢ ≥ τ}，离线暴力计算全部 Ground Truth'],
    ],[82,410])
    p('历史顺序及抽样种子为 20261022，不按“能否检索到答案”挑查询。类别标签不参与索引或真值构建。余弦阈值衡量的是本模型下的相关性，不能保证两条请求可直接复用同一个答案；本实验也未生成或验证历史答案。','small')
    h('2  两层 Hash 的分工')
    p('<b>Exact Hash：</b>对原始 UTF-8 字符串计算 SHA-256，用哈希表保存“摘要 → ID 列表”。命中摘要后逐项比较原文，避免摘要碰撞造成错误命中。保留大小写、标点和空白；普通 Hash 希望不同文本均匀分散，碰撞只会增加比较成本。')
    p('<b>Semantic Hash：</b>相近向量有意以较大概率落入同一桶，碰撞成为候选线索。它既可能遗漏相似项，也可能产生无关候选；用多张表减少遗漏，再用真实余弦过滤候选。Exact 命中即可返回相等文本；否则进入语义层。')
    story.append(flow());story.append(Spacer(1,5))
    p('本系统只实现检索层。语义层未命中时返回空集，由后续系统决定是否调用大模型；不偷偷回退到全库扫描。','small')
    page()

    h('3  随机超平面 LSH 与参数依据')
    p('对单位向量 v，独立采样 r∼N(0,I)，定义 hᵣ(v)=1[r·v≥0]。若余弦为 s、夹角为 θ=arccos(s)，随机超平面将两者分开的概率为 θ/π，故同侧概率为 p(s)=1−arccos(s)/π [3]。')
    p('<b>每表 AND：</b>Hₜ(v) 拼接 k 个独立 bit，同桶概率为 p(s)<super>k</super>。<br/><b>跨表 OR：</b>L 张表使用独立超平面，至少相遇一次的概率为<br/><b>P(s)=1−(1−p(s)<super>k</super>)<super>L</super>。</b>')
    p('事先要求：s₁=0.80 处 P(s₁)≥0.95，并将 s≤s₀=0.20 的低相似度元素进入概率控制在 5% 内。对每个整数 k，取 L(k)=⌈ln(0.05)/ln(1−p(0.80)<super>k</super>)⌉，再选首个满足远点约束的 k，以限制表数与投影计算。')
    table(['k','L(k)','P(0.80)','P(0.20)','判断'],[
      ['11','36','95.10%','6.42%','远点约束不满足'],
      ['12','46','95.20%','4.67%','主配置，实验前固定'],
      ['13','58','95.14%','3.34%','可行，但增加表数'],
    ],[35,50,80,80,190])
    p('s₀ 是设计参照，不是全部无关文本的分布假设；0.20&lt;s&lt;0.80 的文本可更频繁碰撞。95.2% 是单对向量对随机索引的进入概率，不保证每次查询找齐全部邻居。真实近邻往往高于阈值，平均实测 Recall 可高于边界概率。','small')
    h('4  核心算法与复杂度')
    story.append(Preformatted(CODE,STYLES['code'])); markdown.extend(['```text',CODE,'```',''])
    p('每表存 uint32 桶偏移及 ID 数组，直接定位桶区间；候选合并后去重，随后只读取 X[C]。不限制候选数量，避免额外截断漏检；不同表重复的 ID 只计算一次余弦。')
    p('Exact 摘要需 O(|q|)，表定位期望 O(1)，碰撞后另需原文核验。LSH 建索引的投影开销为 O(NLkd)，另有按桶号排序和目录初始化成本。除 Embedding 外，查询为 O(kLd+B log B+|C|d)，B 为 L 个桶未去重的 ID 总数，此实现排序去重。主配置每次新增 552 次 d 维投影，不能只数候选余弦。')
    p('当前密集桶目录的空间为 O(Nd+NL+Lkd+L·2<super>k</super>)，另加 Exact 表与原文。增大 k 虽能缩小桶，却可能扩大目录；生产实现可用稀疏桶字典改变这一开销。','small')
    page()

    h('5  三种方法的实测比较')
    p(f'对 300 个非完全重复查询，{s["nonempty_truth"]} 个存在阈值邻居，{s["empty_truth"]} 个 G 为空。Macro Recall 仅对非空 G 平均 |C∩G|/|G|；空 G 单列，不记作 100%。Candidate Ratio 对全部 300 个查询平均 |C|/N。')
    method_rows=[]
    for name in ['Brute-force','Exact Hash Only','Hash + LSH']:
        rec=1 if name=='Brute-force' else 0 if name=='Exact Hash Only' else s['macro_recall']
        count=n if name=='Brute-force' else 0 if name=='Exact Hash Only' else s['mean_candidates']
        tm=timing[name]
        method_rows.append([name,f'{rec*100:.2f}%',f'{count/n*100:.2f}%',f'{count:,.1f}',f'{tm["mean_ms"]:.3f}',f'{tm["p95_ms"]:.3f}'])
    table(['方法','Recall','候选比例','余弦次数/次','均时 ms','P95 ms'],method_rows,[108,62,62,78,62,62])
    p(f'主配置 Micro Recall 为 {s["micro_recall"]*100:.2f}%，候选量 P95 为 {s["p95_candidates"]:,.1f}；全部 {s["nonempty_truth"]} 个非空查询至少找回一个相关项，但不代表找齐。精筛结果恰为 C∩G，相对于余弦阈值无误报；候选中平均约 {s["mean_false_candidates"]:.1f} 个低于阈值。')
    p(f'<b>计算减少不等于同比提速：</b>余弦次数减少 {n/s["mean_candidates"]:.2f} 倍，实测均时加速 {timing["Brute-force"]["mean_ms"]/timing["Hash + LSH"]["mean_ms"]:.2f} 倍。LSH 还需超平面投影、查桶、候选去重和非连续向量读取；优化过的连续暴力扫描也很快，因此应同时报告操作量和实际时间。')
    p('Exact Hash Only 在非重复查询上的 Recall 为 0：速度快，但不能完成语义检索。另取 100 个历史原文查询，两种 Hash 方法均 100/100 命中且进行 0 次余弦计算，可跳过 Embedding。这里只统计精确命中，不将提前返回等同于找回全部语义邻居。')
    h('6  Memory Cost 与计时范围')
    table(['方法','索引 MiB','向量 MiB','合计 MiB'],[
      ['Brute-force','0',f'{memory["vectors_bytes"]/MI:.2f}',f'{memory["vectors_bytes"]/MI:.2f}'],
      ['Exact Hash Only',f'{memory["exact_index_bytes"]/MI:.2f}','0',f'{memory["exact_index_bytes"]/MI:.2f}'],
      ['Hash + LSH',f'{index_bytes/MI:.2f}',f'{memory["vectors_bytes"]/MI:.2f}',f'{(index_bytes+memory["vectors_bytes"])/MI:.2f}'],
    ],[205,90,90,90])
    p(f'LSH 数组负载 {memory["lsh"]["payload_bytes"]/MI:.2f} MiB：超平面 {memory["lsh"]["planes_bytes"]/MI:.2f}、桶偏移 {memory["lsh"]["offsets_bytes"]/MI:.2f}、ID {memory["lsh"]["posting_bytes"]/MI:.2f}；再加 {memory["lsh"]["container_bytes"]:,} 字节容器开销及 {memory["exact_index_bytes"]/MI:.2f} MiB Exact 表。计量使用数组 nbytes 与 Python 对象大小，原文公共存储约 {memory["raw_text_python_bytes"]/MI:.2f} MiB 单列，模型、解释器和构建临时峰值不计入表中。')
    p('<b>结论：</b>LSH 保留全部原向量并增加索引，是用额外空间换取少检查数据。Exact Only 无须向量，但也失去语义检索能力，不能用它的低空间证明 LSH 节省存储。')
    p(f'环境：Windows x86-64，Python 3.12、NumPy {meta["versions"]["numpy"]}、OpenBLAS 单线程；预热后每查询测 5 轮，轮换方法顺序。检索计时包含 SHA-256、查桶、去重和精筛，均使用预计算查询向量。ONNX 编码用 4 线程，10,303 条文本的批量编码共 {meta["encode_seconds"]:.2f} 秒；此数不代表单请求延迟，表中提速也不代表端到端大模型系统提速。','small')
    page()

    h('7  参数与数据规模的关系')
    configs={(v['k'],v['L']):v for v in R['configurations'] if v['seed']==R['seed']}
    table(['k / L','Macro Recall','候选比例','LSH 数组 MiB'],[
       [f'{k} / {L}',f'{configs[k,L]["summary"]["macro_recall"]*100:.2f}%',
        f'{configs[k,L]["summary"]["candidate_ratio"]*100:.2f}%',f'{configs[k,L]["lsh_memory"]["payload_bytes"]/MI:.2f}']
       for k,L in [(8,46),(12,23),(12,46),(12,92),(16,46)]],[85,115,115,150])
    seed_results=[v for v in R['configurations'] if (v['k'],v['L'])==(12,46)]
    recalls=[v['summary']['macro_recall']*100 for v in seed_results]; ratios=[v['summary']['candidate_ratio']*100 for v in seed_results]
    p(f'固定 L，增大 k 会缩小候选但增加漏检；固定 k，增大 L 会提高召回、候选量及存储。k=16 的候选更少，但密集桶目录使空间变大。三个预定随机种子的主配置 Recall 范围为 {min(recalls):.2f}% 至 {max(recalls):.2f}%，候选比例为 {min(ratios):.2f}% 至 {max(ratios):.2f}%；未择优换种子。','small')
    table(['历史条数 N','平均候选数','候选比例','平均无关候选'],[
       [f'{v["N"]:,}',f'{v["summary"]["mean_candidates"]:.1f}',f'{v["summary"]["candidate_ratio"]*100:.2f}%',f'{v["summary"]["mean_false_candidates"]:.1f}'] for v in R['scales']],[110,115,110,130])
    p('规模实验使用同一组超平面、同一批 300 个查询及嵌套随机历史子集，真值随子集重算。固定 k、L 时 E|C(q)|=ΣᵢP(sim(q,xᵢ))。分布稳定时比例近似不变，但候选绝对量随 N 增长；本实验约 7.9% 并不意味着始终只检查数百条。')
    p('若无关项进入概率 α=0.001，N=10⁸ 时仍有约 10⁵ 个无关候选。若将 s≤s₀ 的无关项期望总量限制在 B 内，可由 P(s₀)≤L·p(s₀)<super>k</super> 得到充分条件 k≥ln(NL/B)/ln(1/p(s₀))，并增大 L 维持近点召回；二者须联合求解。对 s&gt;s₀ 的文本该界不适用。随规模增大 k、L 时，投影及 NL 存储也上升。')
    p('可改用稀疏桶降低目录空间，或多探测 LSH 用更多桶访问换较少的表；高密度桶再划分可降候选，却须重新评估边界漏检。上述为规模扩展方案，未作为已验证改进。固定参数仍有 Θ(N) 期望候选成本，极端情况下所有向量同桶仍会扫描全库。','small')
    h('8  最后思考')
    assert len(REFLECTION)<=300
    p(REFLECTION,'small')
    h('参考与复现')
    p('[1] Casanueva et al. Efficient Intent Detection with Dual Sentence Encoders, 2020. 数据：github.com/PolyAI-LDN/task-specific-datasets（CC BY 4.0）。<br/>[2] Sentence Transformers. huggingface.co/sentence-transformers/all-MiniLM-L6-v2（Apache-2.0）。<br/>[3] Charikar. Similarity Estimation Techniques from Rounding Algorithms. STOC 2002, pp. 380-388. DOI:10.1145/509907.509965。','tiny')
    p('复现：bhw4/README.md；完整真值与候选、版本、来源 SHA-256、消融及审计结果保存在 bhw4/数据/ 和 bhw4/验证/。原始题目粘贴缺失的公式由实验方案补足。','tiny')

    output=ROOT/'作业4.pdf'
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
          topMargin=16*mm,bottomMargin=22*mm,title='大作业4 用 Hash 与 LSH 加速大模型语义复用',author='课程作业').build(story,onFirstPage=footer,onLaterPages=footer)
    (ROOT/'大作业4_报告正文.md').write_text('\n'.join(markdown),encoding='utf-8')
    reader=PdfReader(output)
    texts=[page.extract_text() for page in reader.pages]
    assert len(reader.pages)==4,f'Expected four pages, got {len(reader.pages)}'
    assert all(len(t)>400 for t in texts)
    for phrase in ['98.55%','7.90%','10,003','12 / 46','最后思考']:
        assert phrase in '\n'.join(texts),phrase
    check={'pages':len(reader.pages),'page_sizes':[[float(p.mediabox.width),float(p.mediabox.height)] for p in reader.pages],
           'page_text_chars':[len(t) for t in texts],'reflection_chars':len(REFLECTION),
           'pdf_sha256':sha(output),'experiment_sha256':sha(ROOT/'验证/实验结果.json'),
           'source_sha256':sha(__file__),'text_checks':'passed','visual_review':'pending'}
    save(ROOT/'验证/报告检查.json',check)
    print(json.dumps(check,ensure_ascii=False,indent=2))

if __name__=='__main__':build()
