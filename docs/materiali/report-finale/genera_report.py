"""Generate a standalone academic report; never modifies the manual documents.

Use the separate document environment described in the accompanying README.
The narrative is maintained in contenuto.json; data are frozen experimental results.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pymupdf
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from tipografia import ACCENT, BADGE, markdown, pdf_markup, runs, semantic_alias_cell

HERE = Path(__file__).resolve().parent
MATERIALS = HERE.parent
ROOT = MATERIALS.parents[1]
DATA = json.loads((HERE / "contenuto.json").read_text())
FONT = "PT Sans"
INK, TEAL, MUTED, LIGHT = "#193044", "#008195", "#526577", "#EAF4F5"
WIDTH, HEIGHT = A4
MARGIN = 55
TEXT_WIDTH = WIDTH - 2 * MARGIN
BODY_SIZE, LEADING = 12, 16.5
FONT_FILES = {
    "Report": "PT_Sans-Web-Regular.ttf",
    "ReportBold": "PT_Sans-Web-Bold.ttf",
    "ReportItalic": "PT_Sans-Web-Italic.ttf",
    "ReportBoldItalic": "PT_Sans-Web-BoldItalic.ttf",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_fonts():
    for name, filename in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(MATERIALS / "fonts" / filename)))
    pdfmetrics.registerFontFamily(
        "Report",
        normal="Report",
        bold="ReportBold",
        italic="ReportItalic",
        boldItalic="ReportBoldItalic",
    )


class Diagram:
    def __init__(self, height):
        self.width, self.height = 960, height
        self.drawing = Drawing(self.width, height)
        self.drawing.add(Rect(0, 0, self.width, height, fillColor=colors.white, strokeColor=None))

    def fragments(self, text, size, bold):
        for value, role in runs(text):
            face = (
                "ReportBoldItalic"
                if role == "alias"
                else "ReportBold"
                if bold or role
                else "Report"
            )
            yield value, role, face, pdfmetrics.stringWidth(value, face, size)

    def label(self, x, top, text, size=19, bold=False, color=INK, anchor="middle"):
        fragments = list(self.fragments(text, size, bold))
        width = sum(part[3] for part in fragments)
        cursor = x - width / 2 if anchor == "middle" else x - width if anchor == "end" else x
        baseline = self.height - top
        for value, role, face, width in fragments:
            if role == "identifier":
                self.drawing.add(
                    Rect(
                        cursor,
                        baseline - size * 0.22,
                        width,
                        size * 1.13,
                        fillColor=colors.HexColor(BADGE),
                        strokeColor=None,
                    )
                )
            self.drawing.add(
                String(
                    cursor,
                    baseline,
                    value,
                    fontName=face,
                    fontSize=size,
                    fillColor=colors.HexColor(ACCENT if role else color),
                )
            )
            cursor += width

    def box(self, x, top, w, h, title, subtitle="", fill=LIGHT, title_size=21):
        self.drawing.add(
            Rect(
                x,
                self.height - top - h,
                w,
                h,
                rx=7,
                ry=7,
                fillColor=colors.HexColor(fill),
                strokeColor=colors.HexColor(TEAL),
                strokeWidth=1.5,
            )
        )
        lines = [title, *subtitle.split("\n")] if subtitle else [title]
        line_height = 23
        y = top + h / 2 - (len(lines) - 1) * line_height / 2 + 7
        for i, text in enumerate(lines):
            size = title_size if i == 0 else 18
            check_width = sum(part[3] for part in self.fragments(text, size, i == 0))
            if check_width > w - 18:
                raise ValueError(f"Diagram label too wide: {text}")
            self.label(x + w / 2, y + i * line_height, text, size=size, bold=i == 0)

    def arrow(self, points, color=TEAL):
        transformed = [(x, self.height - y) for x, y in points]
        self.drawing.add(
            PolyLine(
                [v for p in transformed for v in p],
                strokeColor=colors.HexColor(color),
                strokeWidth=2,
            )
        )
        (x0, y0), (x1, y1) = transformed[-2:]
        angle = math.atan2(y1 - y0, x1 - x0)
        size = 9
        head = [
            x1,
            y1,
            x1 - size * math.cos(angle - 0.42),
            y1 - size * math.sin(angle - 0.42),
            x1 - size * math.cos(angle + 0.42),
            y1 - size * math.sin(angle + 0.42),
        ]
        self.drawing.add(Polygon(head, fillColor=colors.HexColor(color), strokeColor=None))

    def save(self, name):
        path = HERE / (name + ".pdf")
        renderPDF.drawToFile(self.drawing, str(path))
        doc = pymupdf.open(path)
        doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(HERE / (name + ".png"))


def diagrams():
    d = Diagram(430)
    d.box(20, 15, 200, 60, "Ingresso statico", title_size=20)
    d.box(290, 15, 580, 60, "CAMEL + Ollama", "Inferenza locale oppure dati prefissati")
    for x, title in [
        (20, "TelemetryAgent"),
        (260, "VulnerabilityAgent"),
        (500, "CountermeasureAgent"),
        (740, "StrategicAgent"),
    ]:
        d.box(x, 135, 200, 75, title, title_size=18)
    d.arrow([(120, 75), (120, 135)])
    for x in [220, 460, 700]:
        d.arrow([(x, 173), (x + 40, 173)])
    d.arrow([(220, 145), (235, 145), (235, 107), (600, 107), (600, 135)])
    d.label(380, 99, "Evidenza runtime", size=17)
    d.box(
        40,
        258,
        610,
        65,
        "Sessione validata · Pydantic",
        "Evidenza runtime | rapporto CTI | candidate",
    )
    for x in [120, 360, 600]:
        d.arrow([(x, 210), (x, 258)])
    d.arrow([(650, 290), (720, 290), (720, 225), (840, 225), (840, 210)])
    d.box(
        700,
        328,
        240,
        85,
        "Backend mock",
        "Grafo e ranking\nValidazione e provenienza",
        title_size=20,
    )
    d.arrow([(840, 210), (960 - 12, 210), (948, 370), (940, 370)])
    d.box(40, 355, 580, 58, "Decisione motivata e tracciabilità", title_size=22)
    d.arrow([(700, 384), (620, 384)])
    d.save("architettura-mockup")

    d = Diagram(560)
    positions = [20, 345, 670]
    for x, title, sub in [
        (20, "OpenTelemetry", "Gateway HTTP"),
        (345, "CTI Knowledge Graph", "MCP · cve2owl · SQLite"),
        (670, "SBOM + OSV", "Inventario e advisory"),
    ]:
        d.box(x, 15, 270, 72, title, sub)
    for x, title in zip(
        positions, ["TelemetryAgent", "VulnerabilityAgent", "CountermeasureAgent"], strict=True
    ):
        d.box(x, 135, 270, 70, title, title_size=20)
        d.arrow([(x + 135, 87), (x + 135, 135)])
    d.arrow([(290, 170), (345, 170)])
    d.arrow([(615, 170), (670, 170)])
    d.box(20, 250, 580, 65, "Artefatti verificati", "Fonti distinte · identificatori · digest")
    d.box(630, 250, 310, 65, "CAMEL + Ollama", "Contratti Pydantic")
    for x in [155, 480]:
        d.arrow([(x, 205), (x, 250)])
    d.arrow([(805, 205), (805, 225), (570, 225), (570, 250)])
    d.box(20, 360, 285, 75, "Preparazione semantica", "OWL · ALN · grafo per CVE", title_size=20)
    d.box(
        345,
        360,
        270,
        75,
        "StrategicAgent",
        "Ranking · validazione\nSelezione · finalizzazione",
        title_size=20,
    )
    d.box(670, 360, 270, 75, "Bridge MCP", "Trasporto stdio", title_size=21)
    d.arrow([(160, 315), (160, 360)])
    d.arrow([(305, 398), (345, 398)])
    d.arrow([(615, 398), (670, 398)])
    d.box(670, 480, 270, 65, "Backend applicativo", "REST · Node.js · TypeScript")
    d.box(20, 480, 580, 65, "Hyperledger Fabric", "Ranking Go/C++ · Tiny-ME · decisione e PROV-O")
    d.arrow([(805, 435), (805, 480)])
    d.arrow([(670, 513), (600, 513)])
    d.save("architettura-completa")

    d = Diagram(350)
    d.box(340, 15, 280, 70, "Vulnerabilità (CVE)")
    for x, title in [(30, "Strategia A"), (355, "Strategia B"), (680, "Strategia C")]:
        d.box(x, 220, 250, 65, title)
        d.arrow([(480, 85), (x + 125, 220)])
    d.label(695, 130, "Relazioni di rimedio nel KG", size=19)
    d.arrow([(280, 252), (355, 252)])
    d.arrow([(605, 252), (680, 252)])
    d.arrow([(805, 285), (805, 325), (155, 325), (155, 285)])
    d.label(480, 315, "Anello orientato di confronto", size=18)
    d.save("grafo-canonico")

    d = Diagram(320)
    for x, title in [
        (20, "Evidenze e policy"),
        (345, "Ranking e validazioni"),
        (670, "Decisione per CVE"),
    ]:
        d.box(x, 15, 270, 65, title, title_size=20)
    d.box(345, 155, 270, 65, "Documento + PROV-O", title_size=20)
    d.arrow([(155, 80), (390, 155)])
    d.arrow([(480, 80), (480, 155)])
    d.arrow([(805, 80), (570, 155)])
    d.box(670, 155, 270, 65, "Commit Fabric")
    d.arrow([(615, 188), (670, 188)])
    d.box(270, 255, 420, 55, "Rilettura e confronto dei contenuti", title_size=20)
    d.arrow([(805, 220), (805, 282), (690, 282)])
    d.save("provenienza")

    d = Diagram(330)
    for x, title, sub in [
        (20, "Osservazioni SDK", "logback-core 1.5.24"),
        (345, "Finding CTI e KG", "CVE-2026-1225"),
        (670, "SBOM e candidata", "S_UPGRADE"),
    ]:
        d.box(x, 15, 270, 70, title, sub, title_size=20)
    d.box(20, 135, 580, 70, "Preparazione canonica", "ABox(a,p,v) + profili ALN(c,r) + grafo")
    d.arrow([(155, 85), (155, 135)])
    d.arrow([(480, 85), (480, 135)])
    d.arrow([(805, 85), (805, 105), (570, 105), (570, 135)])
    d.box(
        670, 135, 270, 70, "Grafo: due nodi, un arco", "Rango 1, score convenzionale", title_size=19
    )
    d.arrow([(600, 170), (670, 170)])
    d.box(20, 260, 580, 55, "Tiny-ME(a,r): abduzione 38, score 62", title_size=22)
    d.arrow([(300, 205), (300, 260)])
    d.arrow([(805, 205), (805, 235), (570, 235), (570, 260)])
    d.box(670, 260, 270, 55, "Decisione condizionata", "PROV-O e ledger", title_size=19)
    d.arrow([(600, 287), (670, 287)])
    d.save("flusso-semantico-c1")

    d = Diagram(180)
    d.box(20, 35, 350, 80, "c: CVE-2026-1225", "Tipo vulnerability")
    d.box(570, 35, 370, 80, "r: rimedio Solutions", "Tipo strategy; binding S_UPGRADE")
    d.arrow([(370, 75), (570, 75)])
    d.label(470, 57, "Rimedio dal KG", size=18)
    d.label(480, 154, "Nessun anello, peso o segno generato in questa fase", size=21)
    d.save("grafo-c1")


def styles():
    base = dict(
        fontName="Report", fontSize=BODY_SIZE, leading=LEADING, textColor=colors.HexColor(INK)
    )
    return {
        "body": ParagraphStyle("Body", **base, alignment=TA_JUSTIFY, spaceAfter=8),
        "title": ParagraphStyle(
            "Title",
            fontName="ReportBold",
            fontSize=19,
            leading=23,
            textColor=colors.HexColor(TEAL),
            spaceAfter=15,
        ),
        "heading": ParagraphStyle(
            "Heading",
            fontName="ReportBold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor(INK),
            spaceBefore=8,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "caption": ParagraphStyle(
            "Caption",
            fontName="ReportItalic",
            fontSize=9.1,
            leading=12,
            textColor=colors.HexColor(MUTED),
            spaceBefore=5,
            spaceAfter=9,
        ),
        "table": ParagraphStyle(
            "Cell", fontName="Report", fontSize=9.15, leading=11.6, textColor=colors.HexColor(INK)
        ),
        "tablehead": ParagraphStyle(
            "CellHead", fontName="ReportBold", fontSize=9.15, leading=11.6, textColor=colors.white
        ),
        "note": ParagraphStyle(
            "Note",
            fontName="Report",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor(INK),
            spaceBefore=8,
            spaceAfter=12,
            backColor=colors.HexColor(LIGHT),
            borderPadding=9,
        ),
    }


def header(canvas, doc):
    if canvas.getPageNumber() == 1:
        return
    canvas.setFont("Report", 8)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(MARGIN, HEIGHT - 29, "POLITECNICO DI BARI")
    canvas.drawRightString(WIDTH - MARGIN, HEIGHT - 29, "Cyber Threat Intelligence spiegabile")
    canvas.setStrokeColor(colors.HexColor(TEAL))
    canvas.setLineWidth(0.55)
    canvas.line(MARGIN, HEIGHT - 36, WIDTH - MARGIN, HEIGHT - 36)
    canvas.setFont("Report", 8.5)
    canvas.drawCentredString(WIDTH / 2, 27, str(canvas.getPageNumber()))


def table_pdf(block, st):
    rows = [[Paragraph(html.escape(str(x)), st["tablehead"]) for x in block["headers"]]]
    rows += [
        [
            Paragraph(pdf_markup(x, aliases=semantic_alias_cell(block, j)), st["table"])
            for j, x in enumerate(row)
        ]
        for row in block["rows"]
    ]
    weights = block.get("widths") or [1 / len(rows[0])] * len(rows[0])
    total = sum(weights)
    tab = Table(
        rows, colWidths=[TEXT_WIDTH * x / total for x in weights], repeatRows=1, hAlign="LEFT"
    )
    tab.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TEAL)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F2F7F8"), colors.white]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(TEAL)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#CDDADF")),
            ]
        )
    )
    out = []
    if block.get("caption"):
        out.append(Paragraph(pdf_markup(block["caption"], italic=True), st["caption"]))
    out.extend([tab, Spacer(1, 10)])
    return out


def cover_pdf():
    m = DATA["metadata"]

    def center(name, size, leading, color=INK):
        return ParagraphStyle(
            name,
            fontName="Report",
            fontSize=size,
            leading=leading,
            alignment=TA_CENTER,
            textColor=colors.HexColor(color),
        )

    title = ParagraphStyle(
        "CoverTitle",
        fontName="ReportBold",
        fontSize=29,
        leading=34,
        alignment=TA_CENTER,
        textColor=colors.HexColor(TEAL),
    )
    logo = Image(str(MATERIALS / "assets/logo-poliba.png"), width=340, height=340 * 101 / 500)
    logo.hAlign = "CENTER"
    # Preserve the official logo's actual aspect ratio.
    image = pymupdf.Pixmap(str(MATERIALS / "assets/logo-poliba.png"))
    logo.drawHeight = logo.drawWidth * image.height / image.width
    return [
        Spacer(1, 30),
        logo,
        Spacer(1, 65),
        Paragraph("REPORT DI PROGETTO", center("Kind", 11, 15, MUTED)),
        Spacer(1, 16),
        Paragraph(m["title"], title),
        Spacer(1, 20),
        Paragraph(m["subtitle"], center("Subtitle", 15, 21)),
        Spacer(1, 65),
        Paragraph("Insegnamento", center("CourseLabel", 10, 14, MUTED)),
        Paragraph(m["course"], center("Course", 15, 20)),
        Spacer(1, 27),
        Paragraph("Docente: Prof. " + m["professor"], center("Professor", 12, 18)),
        Spacer(1, 10),
        Paragraph("Autore: " + m["author"], center("Author", 12, 18)),
    ]


def make_pdf():
    st = styles()
    story = []
    for idx, page in enumerate(DATA["pages"]):
        if idx:
            story.append(PageBreak())
        if idx == 0:
            story.extend(cover_pdf())
            continue
        story.append(Paragraph(pdf_markup(page["title"]), st["title"]))
        for b in page["blocks"]:
            if b["type"] in ["paragraph", "heading", "note"]:
                story.append(
                    Paragraph(
                        pdf_markup(b["text"]),
                        st[{"paragraph": "body", "heading": "heading", "note": "note"}[b["type"]]],
                    )
                )
            elif b["type"] == "table":
                story.extend(table_pdf(b, st))
            elif b["type"] == "figure":
                # Vector PDF is inserted after layout, preserving text and embedded fonts.
                w, h = (
                    960,
                    {
                        "architettura-mockup": 430,
                        "architettura-completa": 560,
                        "grafo-canonico": 350,
                        "provenienza": 320,
                        "flusso-semantico-c1": 330,
                        "grafo-c1": 180,
                    }[b["name"]],
                )
                use_h = min(b["height"], TEXT_WIDTH * h / w)
                story.append(Spacer(TEXT_WIDTH, use_h))
                story[-1]._report_figure = b["name"]
                story.append(Paragraph(pdf_markup(b["caption"], italic=True), st["caption"]))
    placements = []

    class FigureSpace(Spacer):
        def draw(self):
            x, y = self.canv.absolutePosition(0, 0)
            placements.append(
                (self.canv.getPageNumber() - 1, self.name, x, y, self.width, self.height)
            )

    for i, x in enumerate(story):
        if hasattr(x, "_report_figure"):
            obj = FigureSpace(x.width, x.height)
            obj.name = x._report_figure
            story[i] = obj
    path = HERE / "report.pdf"
    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=54,
        bottomMargin=48,
        title=DATA["metadata"]["title"],
        author=DATA["metadata"]["author"],
        subject=DATA["metadata"]["course"],
    )
    frame = Frame(
        MARGIN,
        48,
        TEXT_WIDTH,
        HEIGHT - 54 - 48,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="Academic", frames=frame, onPage=header))
    doc.build(story)
    pdf = pymupdf.open(path)
    for pageidx, name, x, y, w, h in placements:
        source = pymupdf.open(HERE / (name + ".pdf"))
        rect = pymupdf.Rect(x, HEIGHT - y - h, x + w, HEIGHT - y)
        pdf[pageidx].show_pdf_page(rect, source, 0, keep_proportion=True)
    outline = []
    for index, page in enumerate(DATA["pages"][1:], 2):
        title = page["title"]
        level = 2 if re.match(r"^[3-6]\.\d", title) else 1
        outline.append([level, title, index])
    pdf.set_toc(outline)
    final = pdf.tobytes(garbage=4, deflate=True)
    pdf.close()
    path.write_bytes(final)


def set_font(run, size=None, bold=False, italic=False, color=None):
    run.font.name = FONT
    if size is not None:
        run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    for key in ["ascii", "hAnsi", "eastAsia", "cs"]:
        fonts.set(qn("w:" + key), FONT)


def inline_docx(para, text, size, *, bold=False, italic=False, color=INK, aliases=False):
    for value, role in runs(text, aliases=aliases):
        run = para.add_run(value)
        set_font(
            run,
            size,
            bold=bold or role is not None,
            italic=italic or role == "alias",
            color=ACCENT if role else color,
        )
        if role == "identifier":
            shading = OxmlElement("w:shd")
            shading.set(qn("w:val"), "clear")
            shading.set(qn("w:fill"), BADGE.lstrip("#"))
            run._element.get_or_add_rPr().append(shading)


def shade(cell, fill):
    prop = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:fill"), fill.lstrip("#"))
    prop.append(el)


def paragraph(doc, text, kind="body"):
    item = doc.add_paragraph(style="Heading 2" if kind == "heading" else "Normal")
    fmt = item.paragraph_format
    fmt.space_after = Pt(8)
    fmt.line_spacing = Pt(LEADING)
    fmt.widow_control = True
    if kind == "body":
        item.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif kind == "heading":
        fmt.space_before = Pt(8)
        fmt.space_after = Pt(7)
        fmt.keep_with_next = True
    elif kind == "caption":
        fmt.space_before = Pt(5)
        fmt.space_after = Pt(9)
        fmt.line_spacing = Pt(12)
    elif kind == "note":
        item.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt.space_before = Pt(8)
        fmt.space_after = Pt(12)
    inline_docx(
        item,
        text,
        9.1 if kind == "caption" else 12 if kind == "heading" else BODY_SIZE,
        bold=kind == "heading",
        italic=kind == "caption",
        color=MUTED if kind == "caption" else INK,
    )
    return item


def table_docx(doc, b):
    if b.get("caption"):
        paragraph(doc, b["caption"], "caption")
    rows = [b["headers"], *b["rows"]]
    tab = doc.add_table(rows=len(rows), cols=len(rows[0]))
    tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    tab.autofit = False
    weights = b.get("widths") or [1 / len(rows[0])] * len(rows[0])
    total = sum(weights)
    for c, w in zip(tab.columns, weights, strict=True):
        c.width = Inches(TEXT_WIDTH * w / total / 72)
    for i, row in enumerate(rows):
        trpr = tab.rows[i]._tr.get_or_add_trPr()
        no_split = OxmlElement("w:cantSplit")
        trpr.append(no_split)
        if i == 0:
            trpr.append(OxmlElement("w:tblHeader"))
        for j, value in enumerate(row):
            cell = tab.cell(i, j)
            cell.width = Inches(TEXT_WIDTH * weights[j] / total / 72)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            prop = cell._tc.get_or_add_tcPr()
            margins = OxmlElement("w:tcMar")
            for name in ["top", "left", "bottom", "right"]:
                el = OxmlElement("w:" + name)
                el.set(qn("w:w"), "95")
                el.set(qn("w:type"), "dxa")
                margins.append(el)
            prop.append(margins)
            shade(cell, TEAL if i == 0 else "#F2F7F8" if i % 2 else "#FFFFFF")
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = Pt(11.6)
            if i == 0:
                set_font(para.add_run(str(value)), 9.15, bold=True, color="#FFFFFF")
            else:
                inline_docx(para, value, 9.15, aliases=semantic_alias_cell(b, j))
    end = doc.add_paragraph()
    end.paragraph_format.space_after = Pt(0)
    end.paragraph_format.line_spacing = Pt(3)
    set_font(end.add_run(""), 3)


def embed_docx_fonts(path):
    relns = "http://schemas.openxmlformats.org/package/2006/relationships"
    with ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    tree = etree.fromstring(parts["word/fontTable.xml"])
    for el in list(tree):
        tree.remove(el)
    font = etree.SubElement(tree, qn("w:font"))
    font.set(qn("w:name"), FONT)
    family = etree.SubElement(font, qn("w:family"))
    family.set(qn("w:val"), "swiss")
    rels = etree.Element("{" + relns + "}Relationships", nsmap={None: relns})
    for idx, (tag, filename) in enumerate(
        zip(
            ["embedRegular", "embedBold", "embedItalic", "embedBoldItalic"],
            FONT_FILES.values(),
            strict=True,
        ),
        1,
    ):
        key = uuid4()
        key_bytes = key.bytes[::-1]
        raw = bytearray((MATERIALS / "fonts" / filename).read_bytes())
        for i in range(32):
            raw[i] ^= key_bytes[i % 16]
        target = f"fonts/ptsans-{idx}.odttf"
        parts["word/" + target] = bytes(raw)
        rel = etree.SubElement(rels, "{" + relns + "}Relationship")
        rel.set("Id", f"rIdFont{idx}")
        rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font")
        rel.set("Target", target)
        em = etree.SubElement(font, qn("w:" + tag))
        em.set(qn("r:id"), f"rIdFont{idx}")
        em.set(qn("w:fontKey"), "{" + str(key).upper() + "}")
    parts["word/fontTable.xml"] = etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    parts["word/_rels/fontTable.xml.rels"] = etree.tostring(
        rels, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    types = etree.fromstring(parts["[Content_Types].xml"])
    tns = "http://schemas.openxmlformats.org/package/2006/content-types"
    el = etree.SubElement(types, "{" + tns + "}Default")
    el.set("Extension", "odttf")
    el.set("ContentType", "application/vnd.openxmlformats-officedocument.obfuscatedFont")
    parts["[Content_Types].xml"] = etree.tostring(
        types, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)


def make_docx():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(WIDTH / 72)
    section.page_height = Inches(HEIGHT / 72)
    section.top_margin = Inches(54 / 72)
    section.bottom_margin = Inches(48 / 72)
    section.left_margin = section.right_margin = Inches(MARGIN / 72)
    section.header_distance = Inches(0.28)
    section.footer_distance = Inches(0.24)
    section.different_first_page_header_footer = True
    for style in doc.styles:
        if style.type in [1, 2]:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                rpr.insert(0, rf)
            for k in ["ascii", "hAnsi", "eastAsia", "cs"]:
                rf.set(qn("w:" + k), FONT)
            for k in ["asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"]:
                rf.attrib.pop(qn("w:" + k), None)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(BODY_SIZE)
    normal.paragraph_format.line_spacing = Pt(LEADING)
    normal.paragraph_format.space_after = Pt(8)
    header_p = section.header.paragraphs[0]
    set_font(
        header_p.add_run("POLITECNICO DI BARI  |  Cyber Threat Intelligence spiegabile"),
        8,
        color=MUTED,
    )
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:ascii"), FONT)
    rf.set(qn("w:hAnsi"), FONT)
    rpr.append(rf)
    r.append(rpr)
    text = OxmlElement("w:t")
    text.text = "1"
    r.append(text)
    field.append(r)
    footer._p.append(field)
    m = DATA["metadata"]
    for idx, page in enumerate(DATA["pages"]):
        if idx:
            doc.add_page_break()
        if idx == 0:
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(30)
            para.paragraph_format.line_spacing = 1
            para.add_run().add_picture(
                str(MATERIALS / "assets/logo-poliba.png"), width=Inches(340 / 72)
            )
            for text, size, bold, before, after, color in [
                ("REPORT DI PROGETTO", 11, False, 65, 16, MUTED),
                (m["title"], 29, True, 0, 20, TEAL),
                (m["subtitle"], 15, False, 0, 65, INK),
                ("Insegnamento", 10, False, 0, 3, MUTED),
                (m["course"], 15, False, 0, 27, INK),
                ("Docente: Prof. " + m["professor"], 12, False, 0, 10, INK),
                ("Autore: " + m["author"], 12, False, 0, 0, INK),
            ]:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before = Pt(before)
                para.paragraph_format.space_after = Pt(after)
                para.paragraph_format.line_spacing = 1.15
                set_font(para.add_run(text), size, bold=bold, color=color)
            continue
        title = doc.add_paragraph(style="Heading 1")
        title.paragraph_format.space_after = Pt(15)
        title.paragraph_format.line_spacing = Pt(23)
        title.paragraph_format.keep_with_next = True
        inline_docx(title, page["title"], 19, bold=True, color=TEAL)
        for b in page["blocks"]:
            if b["type"] in ["paragraph", "heading", "note"]:
                paragraph(
                    doc,
                    b["text"],
                    {"paragraph": "body", "heading": "heading", "note": "note"}[b["type"]],
                )
            elif b["type"] == "table":
                table_docx(doc, b)
            elif b["type"] == "figure":
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1
                para.add_run().add_picture(
                    str(HERE / (b["name"] + ".png")), width=Inches(TEXT_WIDTH / 72)
                )
                paragraph(doc, b["caption"], "caption")
    settings = doc.settings.element
    for tag in ["embedTrueTypeFonts", "saveSubsetFonts"]:
        el = OxmlElement("w:" + tag)
        settings.append(el)
    doc.core_properties.title = m["title"]
    doc.core_properties.author = m["author"]
    doc.core_properties.subject = m["course"]
    doc.core_properties.language = "it-IT"
    doc.core_properties.keywords = "Cyber Threat Intelligence, agenti, semantica, Fabric"
    path = HERE / "report.docx"
    doc.save(path)
    # Set all theme font faces consistently, then add embeddable OFL font data.
    with ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    theme = etree.fromstring(parts["word/theme/theme1.xml"])
    ans = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    for el in theme.xpath(
        "//a:fontScheme//a:latin | //a:fontScheme//a:ea | "
        "//a:fontScheme//a:cs | //a:fontScheme//a:font",
        namespaces=ans,
    ):
        el.set("typeface", FONT)
    parts["word/theme/theme1.xml"] = etree.tostring(
        theme, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)
    embed_docx_fonts(path)


def make_markdown():
    m = DATA["metadata"]
    out = [
        f"# {m['title']}",
        "",
        m["subtitle"],
        "",
        m["institution"],
        f"Insegnamento: {m['course']}",
        f"Docente: Prof. {m['professor']}",
        f"Autore: {m['author']}",
        "",
    ]
    for page in DATA["pages"][1:]:
        out.extend(["## " + markdown(page["title"]), ""])
        for b in page["blocks"]:
            if b["type"] in ["paragraph", "note"]:
                out.extend([markdown(b["text"]), ""])
            elif b["type"] == "heading":
                out.extend(["### " + markdown(b["text"]), ""])
            elif b["type"] == "figure":
                out.extend([f"![{b['caption']}]({b['name']}.png)", ""])
            elif b["type"] == "table":
                if b.get("caption"):
                    out.extend([markdown(b["caption"]), ""])
                out.append("| " + " | ".join(b["headers"]) + " |")
                out.append("| " + " | ".join(["---"] * len(b["headers"])) + " |")
                out.extend(
                    "| "
                    + " | ".join(
                        markdown(str(v).replace("|", " / "), aliases=semantic_alias_cell(b, j))
                        for j, v in enumerate(row)
                    )
                    + " |"
                    for row in b["rows"]
                )
                out.append("")
    (HERE / "report.md").write_text("\n".join(out))


def verify():
    pdf = pymupdf.open(HERE / "report.pdf")
    texts = [page.get_text() for page in pdf]
    if len(pdf) != len(DATA["pages"]) or len(pdf) > DATA["metadata"]["max_pages"]:
        raise ValueError(f"Unexpected pagination: {len(pdf)} pages")
    for i, page in enumerate(DATA["pages"][1:], 1):
        if page["title"] not in texts[i]:
            raise ValueError(f"Title on unexpected page: {page['title']}")
    full = "\n".join(texts)
    forbidden = [
        "costa-thesis",
        "agent-based-cti-argumentation-pipeline",
        "semantic-cti-ledger-argumentation",
        "resoconto.md",
        ".json",
        ".py",
        ".docx",
        "202611",
        "novembre",
        "ottobre",
        "settembre",
    ]
    for word in forbidden:
        if word in full:
            raise ValueError("Prohibited operational reference: " + word)
    if "Saverio Ieva" not in full or "Information Systems Design and Big Data" not in full:
        raise ValueError("Cover metadata missing")
    bounds = []
    font_names = set()
    missing_glyphs = []
    pdf_spans = []
    for idx, page in enumerate(pdf):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    pdf_spans.append(span)
                    font_names.add(span["font"])
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < -1 or y0 < -1 or x1 > WIDTH + 1 or y1 > HEIGHT + 1:
                        bounds.append((idx + 1, span["text"]))
                    if "\ufffd" in span["text"] or "\x00" in span["text"]:
                        missing_glyphs.append((idx + 1, span["text"]))
    if bounds or missing_glyphs:
        raise ValueError((bounds, missing_glyphs))
    for name in font_names:
        if "PTSans" not in name.replace(" ", ""):
            raise ValueError("Unexpected PDF font " + name)
    embedded = []
    for page in pdf:
        for font in page.get_fonts(full=True):
            if font[0] and "PTSans" in font[3] and font[3] not in embedded:
                if not pdf.extract_font(font[0])[3]:
                    raise ValueError("Unembedded font")
                embedded.append(font[3])
    with ZipFile(HERE / "report.docx") as z:
        tree = etree.fromstring(z.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        breaks = len(tree.xpath('//w:br[@w:type="page"]', namespaces=ns))
        tables = len(tree.xpath("//w:tbl", namespaces=ns))
        fonts = tree.xpath("//w:rFonts/@w:ascii", namespaces=ns)
        if set(fonts) != {FONT}:
            raise ValueError("Unexpected DOCX font")
        font_parts = [x for x in z.namelist() if x.endswith(".odttf")]
        if len(font_parts) != 4:
            raise ValueError("Missing embedded Word fonts")
    notation_probes = {
        "TelemetryAgent": "term",
        "hasAffectedPackage": "term",
        "S_UPGRADE": "identifier",
        "requires_prerequisites": "identifier",
        "maintenance_window": "identifier",
        "--backend-mode mockup": "identifier",
        "a": "alias",
        "c": "alias",
        "r": "alias",
        "A_prep": "alias",
    }
    for value, role in notation_probes.items():
        face = "BoldItalic" if role == "alias" else "Bold"
        if not any(
            value == span["text"].strip()
            and face in span["font"]
            and span["color"] == int(ACCENT.lstrip("#"), 16)
            for span in pdf_spans
        ):
            raise ValueError("Missing PDF notation style: " + value)
        word_runs = tree.xpath("//w:r[w:t=$value]", namespaces=ns, value=value)
        if not any(
            r.xpath("boolean(w:rPr/w:b[not(@w:val='0')])", namespaces=ns)
            and r.xpath("w:rPr/w:color/@w:val", namespaces=ns) == [ACCENT.lstrip("#")]
            and (role != "alias" or r.xpath("boolean(w:rPr/w:i[not(@w:val='0')])", namespaces=ns))
            and (
                role != "identifier"
                or r.xpath("w:rPr/w:shd/@w:fill", namespaces=ns) == [BADGE.lstrip("#")]
            )
            for r in word_runs
        ):
            raise ValueError("Missing Word notation style: " + value)
    original = json.loads((HERE / "originali-protetti.json").read_text())
    if any(sha(ROOT / p) != v for p, v in original.items()):
        raise ValueError("Manual document altered")
    report = {
        "pdf_pages": len(pdf),
        "page_limit": DATA["metadata"]["max_pages"],
        "word_explicit_page_breaks": breaks,
        "word_native_page_count": None,
        "word_native_render_status": (
            "Not verified natively for this revision; PDF is authoritative for the page limit. "
            "An earlier Microsoft Word check timed out."
        ),
        "word_tables": tables,
        "pdf_font_faces": sorted(font_names),
        "embedded_pdf_fonts": embedded,
        "embedded_word_font_files": 4,
        "manual_originals_unchanged": True,
        "out_of_page_text": bounds,
        "missing_glyphs": missing_glyphs,
        "page_titles_verified": True,
        "forbidden_operational_references": False,
        "technical_notation": {
            "font": FONT,
            "accent": ACCENT,
            "identifier_background": BADGE,
            "terms": "bold",
            "identifiers": "bold with a pale background",
            "aliases": "bold italic; single letters recognised only in semantic contexts",
            "pdf_and_word_style_probes_verified": notation_probes,
        },
        "files_sha256": {
            p.name: sha(p)
            for p in HERE.iterdir()
            if p.is_file() and p.name not in ["verifica.json", "README.md"]
        },
    }
    (HERE / "verifica.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "files_sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    register_fonts()
    diagrams()
    make_pdf()
    make_docx()
    make_markdown()
    verify()
