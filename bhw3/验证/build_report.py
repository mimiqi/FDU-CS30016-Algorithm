"""Build the 3-page report only from complete, audited measured data."""
from __future__ import annotations
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, Preformatted, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon, Circle
from reportlab.graphics import renderSVG
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'大作业3_Randomized_LLM_Solver.pdf'
W, H = A4
CONTENT = W-32*mm
NAVY = colors.HexColor('#18334B')
TEAL = colors.HexColor('#167D8D')
INK = colors.HexColor('#243440')
MUTED = colors.HexColor('#5C6A75')
PALE = colors.HexColor('#F0F5F7')
LINE = colors.HexColor('#CED8DF')

REFLECTION = ('二者都通过随机选择改变执行路径，并在有限预算内汇总证据。经典随机化算法通常能明确随机位的分布，'
              '对独立性和误差作假设或证明；大模型采样依赖共享参数、提示与解码机制，重复调用可能沿用同一误解。'
              '新上下文不等于独立正确性事件。关键不是多试几次，而是让随机性改变解题行为，并用复核和停止规则合理分配预算。')

PSEUDOCODE = '''RandomizedSolve(x, B=10):
  C = []; V = []; used = 0
  for m in [3, 5, 7]:
    while len(C) < m:
      if used == B: return FinalVote(C, V)
      C.append(LLM(x, RandomGeneratorStrategy()))
      used += 1
    if used == B: return FinalVote(C, V)
    v = LLM(x, RandomBlindCheckStrategy())
    V.append(v); used += 1
    if used == B: return FinalVote(C, V)
    a = UniquePlurality(C)
    t = 2 if m == 3 else 3
    if a exists and Count(C,a) >= t
       and StrategySupport(C,a) >= 2 and v == a:
      return a
  return FinalVote(C, V)'''

def p(text, key='body'):
    return Paragraph(text, STYLES[key])

def init_styles():
    pdfmetrics.registerFont(TTFont('CN', r'C:\Windows\Fonts\msyh.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CNB', r'C:\Windows\Fonts\msyhbd.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('Code', r'C:\Windows\Fonts\consola.ttf'))
    return {
      'title': ParagraphStyle('title',fontName='CNB',fontSize=21,leading=28,textColor=NAVY,spaceAfter=7),
      'sub': ParagraphStyle('sub',fontName='CN',fontSize=8.5,leading=13,textColor=MUTED,spaceAfter=12),
      'h': ParagraphStyle('h',fontName='CNB',fontSize=12,leading=18,textColor=NAVY,spaceBefore=9,spaceAfter=5,keepWithNext=True),
      'body': ParagraphStyle('body',fontName='CN',fontSize=9.2,leading=14.8,textColor=INK,wordWrap='CJK',spaceAfter=6),
      'small': ParagraphStyle('small',fontName='CN',fontSize=8,leading=12.8,textColor=MUTED,wordWrap='CJK',spaceAfter=5),
      'tiny': ParagraphStyle('tiny',fontName='CN',fontSize=7.2,leading=11.2,textColor=INK,wordWrap='CJK'),
      'code': ParagraphStyle('code',fontName='Code',fontSize=8.5,leading=12.8,textColor=INK,leftIndent=8,spaceBefore=4,spaceAfter=5),
      'cell': ParagraphStyle('cell',fontName='CN',fontSize=8.4,leading=12.4,textColor=INK,wordWrap='CJK'),
      'headcell': ParagraphStyle('headcell',fontName='CNB',fontSize=8.4,leading=12.4,textColor=colors.white),
    }

def arrow(d, x1,y1,x2,y2, label=None):
    d.add(Line(x1,y1,x2,y2,strokeColor=MUTED,strokeWidth=1))
    import math
    angle = math.atan2(y2-y1,x2-x1)
    points = [x2,y2, x2-5*math.cos(angle-.5),y2-5*math.sin(angle-.5),
              x2-5*math.cos(angle+.5),y2-5*math.sin(angle+.5)]
    d.add(Polygon(points,fillColor=MUTED,strokeColor=MUTED))
    if label:
        d.add(String((x1+x2)/2+4,(y1+y2)/2+4,label,fontName='CN',fontSize=7.4,fillColor=MUTED))

def flow():
    d = Drawing(CONTENT,180)
    def box(x,y,w,lines,highlight=False):
        d.add(Rect(x,y,w,31,rx=3,fillColor=PALE,strokeColor=LINE))
        for n,t in enumerate(lines):
            d.add(String(x+w/2,y+20-n*11,t,fontName='CNB' if highlight else 'CN',
                         fontSize=8.4,fillColor=TEAL if highlight else INK,textAnchor='middle'))
    box(5,131,100,['原题 x','预算 B ≤ 10'])
    box(145,131,125,['随机生成候选','首轮3次，后续2次'])
    box(325,131,110,['随机盲复核1次','只见原题'])
    box(145,76,125,['输出领先答案','4次或7次停止'],True)
    box(325,76,110,['跨策略支持且','复核与领先者一致？'])
    box(325,15,110,['已达到10次？'])
    box(145,15,125,['合并候选与复核','按票数及平票规则输出'],True)
    arrow(d,105,146,145,146)
    arrow(d,270,146,325,146)
    arrow(d,380,131,380,107)
    arrow(d,325,91,270,91,'是')
    arrow(d,380,76,380,46,'否')
    arrow(d,325,30,270,30,'是')
    d.add(Line(435,30,465,30,strokeColor=MUTED))
    d.add(String(441,37,'否',fontName='CN',fontSize=7.4,fillColor=MUTED))
    d.add(Line(465,30,465,177,strokeColor=MUTED))
    d.add(Line(465,177,207,177,strokeColor=MUTED))
    arrow(d,207,177,207,162)
    return d

def curve(s):
    d = Drawing(CONTENT,145)
    x0,y0,gw,gh = 46,30,CONTENT-72,91
    for val in [0,25,50,75,100]:
        y=y0+gh*val/100
        d.add(Line(x0,y,x0+gw,y,strokeColor=LINE,strokeWidth=.5))
        d.add(String(x0-8,y-3,str(val),fontName='CN',fontSize=7.3,textAnchor='end',fillColor=MUTED))
    d.add(String(3,131,'正确率（%）',fontName='CN',fontSize=8,fillColor=INK))
    prev=None
    for k in [1,3,5,10]:
        x=x0+gw*(k-1)/9
        val=s['fixed'][str(k)]['accuracy']*100
        y=y0+gh*val/100
        if prev:
            d.add(Line(prev[0],prev[1],x,y,strokeColor=TEAL,strokeWidth=1.8))
        d.add(Circle(x,y,3,fillColor=TEAL,strokeColor=TEAL))
        d.add(String(x,y+7,f'{val:.0f}%',fontName='CNB',fontSize=8,fillColor=TEAL,textAnchor='middle'))
        d.add(String(x,y0-13,str(k),fontName='CN',fontSize=8,fillColor=INK,textAnchor='middle'))
        prev=(x,y)
    d.add(String(x0+gw/2,2,'生成采样次数（次/题）',fontName='CN',fontSize=8,fillColor=INK,textAnchor='middle'))
    return d

def table(rows, widths):
    items = [[p(escape(str(x)), 'headcell' if i==0 else 'cell') for x in row] for i,row in enumerate(rows)]
    t=Table(items,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
        ('LINEBELOW',(0,-1),(-1,-1),.5,LINE),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    return t

def short(answer,limit=170):
    if answer is None:
        return '格式失败'
    return answer if len(answer)<=limit else answer[:limit]+'…'

def analysis_text(s):
    vals=[s['fixed'][str(k)]['accuracy']*100 for k in (1,3,5,10)]
    changes=[vals[i+1]-vals[i] for i in range(3)]
    monotone=all(x>=0 for x in changes)
    text=(f'固定采样的正确率为 {vals[0]:.0f}% → {vals[1]:.0f}% → {vals[2]:.0f}% → {vals[3]:.0f}%，'
          f'各段变化为 {changes[0]:+.0f}、{changes[1]:+.0f}、{changes[2]:+.0f} 个百分点。'
          + ('本样本整体未下降，但不能推出任意题目或更大预算都单调改善。' if monotone else '整体曲线并非单调上升，更多调用不保证改善。'))
    improvements=[max(0,x) for x in changes]
    if all(changes[i+1]<=changes[i] for i in range(2)) and any(x>0 for x in changes):
        text+='本样本后段增益不大于前段；20题每题占5个百分点，不能据此估计平滑的收益规律。'
    else:
        text+='本样本未呈现稳定的边际收益递减；题量较小，每题占5个百分点。'
    return text

def evidence(s):
    blocks=[]
    rev=[(key,qid) for key,ids in s['reversals'].items() for qid in ids]
    if rev:
        key,qid=rev[0]
        a,b=key.split('->')
        r=next(x for x in s['rows'] if x['id']==qid)
        blocks.append((f'由对变错：{qid}（{r["topic"]}，{a}次 → {b}次）',
          f'标准输出：{short(r["gold"])}；{a}次结果：{short(r["fixed"][a].get("display_answer",r["fixed"][a]["answer"]))}；'
          f'{b}次结果：{short(r["fixed"][b].get("display_answer",r["fixed"][b]["answer"]))}。新增答案改变了票数排序；随机试验有波动，单题优势会丢失。'))
    else:
        blocks.append(('更多次数是否反而变差？','本次相邻预算中未观察到由对变错。理论上新增的相关错误票可改变领先答案，尤其初始优势很小时；这是假设性说明，不是实测案例。'))
    repeated = sorted(s['rows'],key=lambda r:(r['all_ten_wrong'],r['dominant_wrong_count']),reverse=True)[0]
    if repeated['all_ten_wrong']:
        blocks.append((f'10次仍全错：{repeated["id"]}（{repeated["topic"]}）',
            f'10个生成回答均错误，其中同一错误输出重复{repeated["dominant_wrong_count"]}次。'
            f'标准输出为：{short(repeated["gold"])}。候选池中没有正确答案，投票无法凭空恢复正确解。'))
    elif repeated['dominant_wrong_count']:
        blocks.append((f'重复错误：{repeated["id"]}（{repeated["topic"]}）',
            f'本样本没有10次全错题；但该题同一错误输出重复{repeated["dominant_wrong_count"]}次。'
            '这与共享误解相容，不能据20题和一次采样序列证明统计依赖。'))
    else:
        blocks.append(('重复错误的边界','本样本未观察到可重复的同一错误输出；不能由此证明调用独立。需要更多题目和重复实验估计错误相关性。'))
    return blocks

def footer(c,doc):
    c.saveState()
    c.setStrokeColor(LINE)
    c.line(16*mm,15*mm,W-16*mm,15*mm)
    c.setFont('CN',7.2)
    c.setFillColor(MUTED)
    c.drawString(16*mm,10.5*mm,'算法设计 · 大作业3 · 2026-10-14')
    c.drawRightString(W-16*mm,10.5*mm,f'{doc.page} / 3')
    c.restoreState()

def main():
    global STYLES
    STYLES=init_styles()
    s=json.loads((ROOT/'验证/实验结果.json').read_text(encoding='utf-8'))
    audit=json.loads((ROOT/'验证/完整性审计.json').read_text(encoding='utf-8'))
    assert s['status']=='complete' and s['n']==20 and audit['status']=='passed'
    assert len(REFLECTION)<=200
    (ROOT/'图示').mkdir(exist_ok=True)
    d=flow()
    renderSVG.drawToFile(d,str(ROOT/'图示/随机求解流程图.svg'))
    renderSVG.drawToFile(curve(s),str(ROOT/'图示/采样次数与正确率.svg'))
    story=[]
    story += [p('有限预算下的随机化求解','title'),
              p('Randomized LLM Solver｜程序输出预测实验｜20道固定题｜每次求解至多10次调用','sub')]
    story += [p('1  问题、模型与实验边界','h'),
        p('选择20道Python 3程序输出预测题，组合有限状态更新、列表别名、闭包、生成器、递归与控制流。答案是确定的整数及列表/元组输出，没有浮点误差或随机输入。被测模型请求型号为 <b>gpt-5.6-luna</b>，推理档位 <b>low</b>；不用Deep Research或Extended Thinking。'),
        p('每次调用使用新上下文，只输入题目与策略提示；禁用搜索、代码执行及其他工具。离线解释器事先产生标准答案，实验者据此评分，求解器与复核器都看不到标准答案。3道简单预检全部答对后，固定下列20道组合题，正式采样后不换题。','small')]
    story += [p('2  随机性改变解题行为','h'),
        p('普通推理将提示词分词，根据上下文计算下一token的分布，逐步解码至停止。本实验不声称能控制平台未暴露的temperature/top_p；可控随机性在<b>提示策略选择</b>：逐步跟踪、分段归纳、依赖与别名分析、分支边界审查。以种子20261014每四次无放回洗牌，避免预算集中在一种思路。'),
        p('另从逐行记账、陷阱重推、分段复算中随机选择<b>盲复核</b>提示。复核器只看原题，不看候选或票数。不同策略可能暴露遗漏的状态更新，盲复核可减轻跟随多数答案的锚定；但策略标签不同不保证实际推理不同。')]
    story += [p('3  RandomizedSolve 伪代码','h'),Preformatted(PSEUDOCODE,STYLES['code']),
        p('C为生成答案，V为盲复核答案。FinalVote合并全部合法回答取相对多数；平票先取最早的复核答案，再取最早生成答案。格式失败耗费预算但不投票，全部失败输出FAIL。早停只读当前前缀，不查看后续答案或标准答案。一般预算B≤10时，达到B即按同一决胜规则输出。','small')]
    story += [PageBreak(),p('4  流程与真实实验结果','h'),d]
    rows=[['方案（20题）','正确题数 / 正确率','平均调用次数']]
    for label,k in [('Single Run','1'),('Fixed Sampling-3','3'),('Fixed Sampling-5','5'),('Fixed Sampling-10','10')]:
        m=s['fixed'][k]
        rows.append([label,f'{m["correct"]}/20 · {m["accuracy"]:.0%}',f'{m["mean_calls"]:.2f} 次/题'])
    m=s['method']
    rows.append(['Your Method（随机策略+盲复核）',f'{m["correct"]}/20 · {m["accuracy"]:.0%}',f'{m["mean_calls"]:.2f} 次/题'])
    story += [table(rows,[CONTENT*.45,CONTENT*.30,CONTENT*.25]),Spacer(1,8),
        p('公平比较：各方案共享同一随机策略生成池的前缀；Fixed Sampling也使用该策略池，隔离考察固定投票与“复核+自适应分配”的差别，未额外做同一提示词重问对照。1/3/5/10次投票平票均取先出现者。','small'),
        p(f'正式实验实际采集{audit["physical_model_calls"]}次新上下文单题回答，含200次固定生成和{audit["physical_model_calls"]-200}次盲复核；每方案每题分别计预算。Your Method在4/7/10次停止的题数为 '
          f'{audit["method_call_distribution"]["4"]}/{audit["method_call_distribution"]["7"]}/{audit["method_call_distribution"]["10"]}。不是将整场比较声称为每题总共10次。','small'),
        p('5  1 → 3 → 5 → 10次：收益是否单调？','h'),curve(s),
        p(analysis_text(s)),p('图表来源：2026-10-14冻结的20题正式实验；统计文件为 验证/实验结果.json。曲线仅代表这一题库、模型与提示策略，不是总体正确率保证。','small')]
    story += [PageBreak(),p('6  从逐题结果看成功与失效','h')]
    for title,body in evidence(s):
        story += [p(title,'h'),p(escape(body))]
    single=s['fixed']['1']['correct']; method=s['method']['correct']
    relation='提高' if method>single else '相同' if method==single else '降低'
    early=s.get('false_early_stops',[])
    early_text=(f'本方法在 {"、".join(early)} 出现错误早停，说明跨策略一致并不足以认证答案。' if early else
                '本样本没有错误早停，但早停正确性不能由一致性保证。')
    story += [p(f'本方法与Single Run的比较：{single}/20 → {method}/20，正确题数{relation}；'
                f'改对{len(s.get("method_gains_vs_single",[]))}题、改错{len(s.get("method_losses_vs_single",[]))}题。'+early_text+
                '随机化有用的前提是正确解在候选分布中具有一定质量，不同策略能纠正不同遗漏，且复核的证据与错误生成过程不完全重合。'
                '若所有策略共享错误规则，或复核器同样误解题意，一致性只会增加错误确信；提前停止还可能锁定偶然多数。')]
    story += [p('7  10次调用是否等于10次独立试验？','h'),
        p('新上下文消除了显式对话历史，却仍共享模型参数、训练知识、系统提示与同一题目。生成策略的无放回轮换本身也不是同分布独立采样。重复同错只提供相关错误的线索，不能由此证明不独立；本实验没有估计相关系数或声称显著性。'),
        p('增大差异的方法：随机选择可区分的状态表示和检查顺序，限制连续使用同一策略；复核时隐藏候选，要求从原题独立重算。这里“验证”仍是模型内部交叉核对，并非可靠的外部判定器。调用次数还忽略了token长度和延迟，因此平均调用数不等于完全相同的费用。')]
    story += [p(f'8  最后思考（{len(REFLECTION)}字）','h'),p(REFLECTION),
        p('复现与材料','h'),
        p('题库与原始回答：题库与标准答案.md；实验原始记录/Q01…Q20/。所有输入、回答和JSONL事件有SHA-256校验；每条记录应仅有1个完成轮次、0次工具调用。模型名称是请求标识，平台未返回精确权重快照，未声称可跨版本逐字复现。','small'),
        p('离线复核：python bhw3/验证/experiment.py --analyse --require-complete；python bhw3/验证/audit.py。20题小样本、共享前缀以及单次固定种子的实验只能支持描述性结论；没有按结果调整题目或阈值。','small')]
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,
                          topMargin=13*mm,bottomMargin=20*mm,
                          title='Randomized LLM Solver：有限预算下的随机化求解',author='算法设计课程作业')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(OUT)
    assert len(reader.pages)==3, f'Expected 3 pages, got {len(reader.pages)}'
    text='\n'.join(page.extract_text() or '' for page in reader.pages)
    assert '\ufffd' not in text
    # Editable text is generated from the same metric source as the PDF.
    md=['# 有限预算下的随机化求解','',
        '模型：gpt-5.6-luna / low；20道Python程序输出预测题；2026-10-14。',
        '\n## 实验方法\n',
        '具体模型约束、随机策略、停止规则与预算核算见[冻结实验方案](实验方案.md)。',
        '\n```text\n'+PSEUDOCODE+'\n```',
        '\n![流程图](图示/随机求解流程图.svg)',
        '\n## 实测比较\n',
        '| 方案 | 正确题数 / 正确率 | 平均调用次数 |','|---|---|---|']
    md += ['| '+' | '.join(row)+' |' for row in rows[1:]]
    md += ['\n![采样曲线](图示/采样次数与正确率.svg)','\n'+analysis_text(s)]
    for title,body in evidence(s):
        md += ['\n### '+title,'\n'+body]
    md += ['\n## 独立性与边界\n',
           '新上下文不等于正确性事件独立。共享参数、知识、题目和提示会保留共同偏差；无放回选策略本身亦非IID。重复同错不能单独证明统计依赖。盲复核仅为模型交叉检查，不能保证正确。20题仅支持描述性比较，调用次数没有完全衡量token费用。',
           '\n## 最后思考\n',REFLECTION,
           f'\n正式实验采集{audit["physical_model_calls"]}次单题回答，三方案分别计每题预算；共享生成池前缀不重复收费。',
           '\n完整论证、预算解释和图表见同目录三页PDF；逐题统计见验证/实验结果.json。']
    (ROOT/'大作业3_报告正文.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(f'Created {OUT}; pages=3; reflection={len(REFLECTION)} characters')

if __name__=='__main__':
    main()
