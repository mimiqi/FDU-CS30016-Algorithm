from __future__ import annotations

from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "大作业2_多GPU推理方案.pdf"
FLOW_IMAGE = ROOT / "bhw2" / "图示" / "多GPU矩阵乘法流程.png"

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
MARGIN_TOP = 15 * mm
MARGIN_BOTTOM = 15 * mm

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#1976D2")
CYAN = colors.HexColor("#00A6A6")
PALE_BLUE = colors.HexColor("#EAF3FB")
PALE_CYAN = colors.HexColor("#E8F8F6")
PALE_GOLD = colors.HexColor("#FFF6DB")
INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#5B6875")
LINE = colors.HexColor("#CCD7E0")
WHITE = colors.white


def register_fonts() -> None:
    pdfmetrics.registerFont(
        TTFont("YaHei", r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0)
    )
    pdfmetrics.registerFont(
        TTFont("YaHeiBold", r"C:\Windows\Fonts\msyhbd.ttc", subfontIndex=0)
    )


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCN",
            parent=styles["Title"],
            fontName="YaHeiBold",
            fontSize=21,
            leading=27,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCN",
            parent=styles["Normal"],
            fontName="YaHei",
            fontSize=9,
            leading=14,
            textColor=MUTED,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1CN",
            parent=styles["Heading1"],
            fontName="YaHeiBold",
            fontSize=13,
            leading=17,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2CN",
            parent=styles["Heading2"],
            fontName="YaHeiBold",
            fontSize=10.5,
            leading=14,
            textColor=BLUE,
            spaceBefore=4,
            spaceAfter=2,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=8.6,
            leading=13.1,
            textColor=INK,
            wordWrap="CJK",
            spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "SmallCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=7.4,
            leading=10.4,
            textColor=INK,
            wordWrap="CJK",
        ),
        "tiny": ParagraphStyle(
            "TinyCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=6.8,
            leading=9.2,
            textColor=INK,
            wordWrap="CJK",
        ),
        "formula": ParagraphStyle(
            "FormulaCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            textColor=NAVY,
            wordWrap="CJK",
        ),
        "callout": ParagraphStyle(
            "CalloutCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=8.2,
            leading=12.2,
            textColor=INK,
            wordWrap="CJK",
        ),
        "table_head": ParagraphStyle(
            "TableHeadCN",
            parent=styles["BodyText"],
            fontName="YaHeiBold",
            fontSize=7.2,
            leading=9.4,
            alignment=TA_CENTER,
            textColor=WHITE,
            wordWrap="CJK",
        ),
        "table_cell": ParagraphStyle(
            "TableCellCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=7,
            leading=9.2,
            alignment=TA_CENTER,
            textColor=INK,
            wordWrap="CJK",
        ),
        "foot": ParagraphStyle(
            "FootCN",
            parent=styles["BodyText"],
            fontName="YaHei",
            fontSize=6.8,
            leading=9.2,
            textColor=MUTED,
            wordWrap="CJK",
        ),
    }


def p(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def boxed(flowables, background=PALE_BLUE, border=LINE, pad=7):
    table = Table([[flowables]], colWidths=[PAGE_W - 2 * MARGIN_X])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, border),
                ("LEFTPADDING", (0, 0), (-1, -1), pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                ("TOPPADDING", (0, 0), (-1, -1), pad - 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 1),
            ]
        )
    )
    return table


def base_table(data, widths, header=True, row_bgs=True):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ]
        )
    if row_bgs:
        first = 1 if header else 0
        for row in range(first, len(data)):
            if (row - first) % 2 == 1:
                commands.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#F6F8FA")))
    table.setStyle(TableStyle(commands))
    return table


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(CYAN)
    canvas.setLineWidth(2.2)
    canvas.line(MARGIN_X, 10.2 * mm, MARGIN_X + 16 * mm, 10.2 * mm)
    canvas.setFont("YaHei", 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - MARGIN_X, 8 * mm, str(doc.page))
    canvas.restoreState()


def page_one(S):
    story = [
        Spacer(1, 2 * mm),
        p("一次 FFN 矩阵乘法的多 GPU 划分", S["title"]),
        p("用 8 张 GPU 沿公共维度拆分计算，并以逐元素求和恢复完整输出", S["subtitle"]),
        boxed(
            p(
                "<b>核心结论</b>：每张 GPU 保存 1/8 的权重并计算一个部分乘积；8 份部分结果形状相同，通过逐元素求和得到完整输出。并行执行缩短了计算时间，总乘法次数保持不变。",
                S["callout"],
            ),
            PALE_CYAN,
            CYAN,
        ),
        p("1　计算任务与系统配置", S["h1"]),
        p(
            "Transformer 前馈网络（FFN）通过矩阵乘法变换 token 特征。本方案处理 128 个 token，每个 token 包含 8192 个输入特征，投影后生成 4096 个输出特征：",
            S["body"],
        ),
        boxed(
            p(
                "<b>Y = XW</b>　　X ∈ R<super>128×8192</super>，W ∈ R<super>8192×4096</super>，Y ∈ R<super>128×4096</super>",
                S["formula"],
            ),
            PALE_BLUE,
            colors.HexColor("#B8CFE3"),
            5,
        ),
        p(
            "其中，X 是输入，W 是权重，Y 是输出，一行 X 对应一个 token。模型加载阶段，8 份权重块分别驻留在对应 GPU。GPU 1 分发输入块、汇总部分结果并输出 Y；一次推理依次经历输入分发、并行计算和结果合并。",
            S["body"],
        ),
        p("2　怎么分：沿输入特征维度切成 8 份", S["h1"]),
        p(
            "将 X 按列切分，将 W 按对应行切分：<b>X = [X<sub>1</sub> X<sub>2</sub> … X<sub>8</sub>]</b>，<b>W = [W<sub>1</sub>; W<sub>2</sub>; …; W<sub>8</sub>]</b>。每个 X<sub>i</sub> 为 128×1024，每个 W<sub>i</sub> 为 1024×4096。每张卡独立计算 P<sub>i</sub> = X<sub>i</sub>W<sub>i</sub>，局部计算期间无需交换数据。",
            S["body"],
        ),
    ]

    head = [p("GPU", S["table_head"]), p("X 的列 / W 的行", S["table_head"]), p("局部计算", S["table_head"]), p("局部结果", S["table_head"])]
    rows = [head]
    for i in range(8):
        start = i * 1024 + 1
        end = (i + 1) * 1024
        rows.append(
            [
                p(str(i + 1), S["table_cell"]),
                p(f"{start}–{end}", S["table_cell"]),
                p(f"P<sub>{i + 1}</sub> = X<sub>{i + 1}</sub>W<sub>{i + 1}</sub>", S["table_cell"]),
                p("128×4096", S["table_cell"]),
            ]
        )
    story.extend(
        [
            base_table(rows, [18 * mm, 50 * mm, 50 * mm, 42 * mm]),
            Spacer(1, 2.5 * mm),
            boxed(
                p(
                    "<b>为什么能并行？</b> 各卡读取的输入特征区间互不重叠，权重块也已就位；P<sub>1</sub> 到 P<sub>8</sub> 之间没有前后依赖。均匀划分使每张卡承担相同的乘法工作量。代价是每张卡都会产生一份完整形状的部分结果。",
                    S["callout"],
                ),
                PALE_GOLD,
                colors.HexColor("#E6C65C"),
            ),
            PageBreak(),
        ]
    )
    return story


def page_two(S):
    story = [
        p("3　Divide → Conquer → Combine", S["h1"]),
    ]

    dcc = [
        [
            p("<b>DIVIDE</b><br/>沿 8192 个输入特征连续二分，直到得到 8 个各含 1024 个特征的子任务。GPU 1 保留 X<sub>1</sub>，其余输入块直接发送到对应 GPU。", S["callout"]),
            p("<b>CONQUER</b><br/>第 i 张 GPU 计算 P<sub>i</sub> = X<sub>i</sub>W<sub>i</sub>。原先每个输出元素累加 8192 项，现在每卡只累加自己负责的 1024 项。", S["callout"]),
            p("<b>COMBINE</b><br/>GPU 2–8 将 P<sub>i</sub> 发回 GPU 1，GPU 1 对同一输出位置逐元素累加，得到 Y = P<sub>1</sub> + … + P<sub>8</sub>。", S["callout"]),
        ]
    ]
    dcc_table = Table(dcc, colWidths=[53.3 * mm] * 3, hAlign="LEFT")
    dcc_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), PALE_BLUE),
        ("BACKGROUND", (1, 0), (1, 0), PALE_CYAN),
        ("BACKGROUND", (2, 0), (2, 0), PALE_GOLD),
        ("BOX", (0, 0), (0, 0), 0.7, colors.HexColor("#B8CFE3")),
        ("BOX", (1, 0), (1, 0), 0.7, colors.HexColor("#9EDBD5")),
        ("BOX", (2, 0), (2, 0), 0.7, colors.HexColor("#E6C65C")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend(
        [
            dcc_table,
            p("4　为什么要相加，而不是拼接", S["h1"]),
            p(
                "矩阵乘法的每个输出元素本来就是沿公共维度 k 求和。8 张卡覆盖的 k 区间互不重叠，合起来恰好覆盖 1 到 8192：",
                S["body"],
            ),
            boxed(
                p(
                    "Y[a,b] = Σ<sub>k=1…8192</sub> X[a,k]W[k,b] = Σ<sub>i=1…8</sub> ( Σ<sub>k=1024(i−1)+1…1024i</sub> X[a,k]W[k,b] )",
                    S["formula"],
                ),
                PALE_BLUE,
                colors.HexColor("#B8CFE3"),
                5,
            ),
            p(
                "因此 P<sub>i</sub>[a,b] 都对应输出 Y 中同一个位置，只是包含的乘积项不同。8 份部分结果必须逐元素相加；直接拼接会改变输出的形状和含义。",
                S["body"],
            ),
            p("5　数据流与通信位置", S["h1"]),
        ]
    )

    img = Image(str(FLOW_IMAGE))
    max_w = PAGE_W - 2 * MARGIN_X
    max_h = 103 * mm
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    img.hAlign = "CENTER"
    story.extend(
        [
            img,
            p("图 1　矩阵分块、8 张 GPU 的局部计算与集中汇总流程", S["foot"]),
            boxed(
                p(
                    "<b>数据交换</b>：计算开始时，GPU 1 分发 X<sub>2</sub>–X<sub>8</sub>；局部乘法完成后，GPU 2–8 回传 P<sub>2</sub>–P<sub>8</sub>。W<sub>i</sub> 常驻对应 GPU，局部计算阶段无需交换权重或中间数据。GPU 1 完成集中规约并输出 Y。",
                    S["callout"],
                ),
                colors.HexColor("#F6F8FA"),
                LINE,
            ),
            PageBreak(),
        ]
    )
    return story


FINAL_THOUGHT = (
    "本方案与经典分治一样，把同一问题拆成较小的同类子问题，分别求解后再合并。"
    "分治描述算法结构，多 GPU 描述硬件分工；多卡并行缩短等待时间，不减少乘法总量，同时增加通信与同步。"
    "把互不相关的请求分给不同 GPU，没有拆解同一问题，也不需要合成答案，不属于分治。"
)


def page_three(S):
    assert len(FINAL_THOUGHT) <= 200, f"最后思考超过 200 字：{len(FINAL_THOUGHT)}"

    data = [
        [p("GPU 数量", S["table_head"]), p("每卡输入特征", S["table_head"]), p("每卡乘法工作量", S["table_head"]), p("GPU 1 接收结果", S["table_head"])],
    ]
    for n in [1, 2, 4, 8, 16]:
        data.append(
            [
                p(str(n), S["table_cell"]),
                p(str(8192 // n), S["table_cell"]),
                p("全部" if n == 1 else f"1/{n}", S["table_cell"]),
                p(str(n - 1) + " 份", S["table_cell"]),
            ]
        )

    story = [
        p("6　GPU 越多一定越快吗？", S["h1"]),
        p(
            "在相同的 X、W 尺寸下，GPU 数量从 1 增加到 16。各卡承担的乘法份额随之减小，每份部分结果始终为 128×4096：",
            S["body"],
        ),
        base_table(data, [30 * mm, 45 * mm, 45 * mm, 40 * mm]),
        p("为什么一开始会加速", S["h2"]),
        p(
            "局部矩阵乘法可以同时执行。理想情况下，2 张卡把主要计算时间降至约 1/2，4 张卡降至约 1/4。总乘法次数保持不变，节省的是完成同一批计算所需的时间。",
            S["body"],
        ),
    ]

    reasons = [
        [
            p("<b>① 通信与合并增长</b><br/>集中汇总时，GPU 1 接收的 128×4096 结果从 8 卡的 7 份增至 16 卡的 15 份，还要逐元素求和。输入分发同样占用链路。", S["callout"]),
            p("<b>② 子任务过小</b><br/>矩阵变窄后，GPU 计算单元利用率下降；内核启动、调度等固定开销不会随工作量同比减少，小批量 token 时尤其明显。", S["callout"]),
            p("<b>③ 同步与慢卡效应</b><br/>完整 Y 必须等待全部 P<sub>i</sub>。一张卡计算偏慢或传输延迟，其他卡完成后仍需等待；卡数越多，尾部延迟越容易影响整体时间。", S["callout"]),
        ]
    ]
    reasons_table = Table(reasons, colWidths=[53.3 * mm] * 3, hAlign="LEFT")
    reasons_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), PALE_BLUE),
        ("BACKGROUND", (1, 0), (1, 0), PALE_CYAN),
        ("BACKGROUND", (2, 0), (2, 0), PALE_GOLD),
        ("BOX", (0, 0), (0, 0), 0.7, colors.HexColor("#B8CFE3")),
        ("BOX", (1, 0), (1, 0), 0.7, colors.HexColor("#9EDBD5")),
        ("BOX", (2, 0), (2, 0), 0.7, colors.HexColor("#E6C65C")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend(
        [
            reasons_table,
            p("什么时候会更慢", S["h2"]),
            boxed(
                p(
                    "总耗时由输入分发、最慢卡的局部计算、结果传输和求和共同构成。从 8 卡增至 16 卡，局部计算再节省单卡时间的 1/16；新增的通信、规约和等待一旦超过这部分收益，16 卡就会比 8 卡更慢。树形规约可以缓解集中瓶颈，通信和同步成本仍然存在。",
                    S["callout"],
                ),
                colors.HexColor("#FDECEC"),
                colors.HexColor("#D98C8C"),
            ),
            p("7　与经典分治的联系", S["h1"]),
            boxed(p(FINAL_THOUGHT, S["callout"]), colors.HexColor("#F6F8FA"), LINE),
            p("参考资料", S["h2"]),
            p(
                "NVIDIA Megatron Core, <i>RowParallelLinear</i>：输入与权重沿公共维度分块，局部结果通过规约合并。<br/>https://docs.nvidia.com/megatron-core/developer-guide/latest/apidocs/core/core.tensor_parallel.layers.html",
                S["foot"],
            ),
        ]
    )
    return story


def build() -> None:
    register_fonts()
    styles = make_styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    frame = Frame(
        MARGIN_X,
        MARGIN_BOTTOM,
        PAGE_W - 2 * MARGIN_X,
        PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        title="一次 FFN 矩阵乘法的多 GPU 划分",
        author="mimiqi",
        subject="算法设计与分析大作业 2",
        creator="ReportLab",
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    # Draw furniture after the body so white table/image backgrounds cannot cover it.
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPageEnd=on_page)])

    story = []
    story.extend(page_one(styles))
    story.extend(page_two(styles))
    story.extend(page_three(styles))
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
