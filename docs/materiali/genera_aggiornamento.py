"""Genera figure, appendice PDF e copia DOCX; non sovrascrive il report manuale.

Dipendenze nell'ambiente separato dei materiali. Nessuna rete o inferenza.
Il generatore storico genera_materiali.py non viene invocato.
"""

import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
from zipfile import ZipFile

import pymupdf
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from lxml import etree
from markdown_it import MarkdownIt
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
DATE = "29 ottobre 2026"
STAMP = "20261029"
INK, TEAL, MUTED = "#183247", "#008195", "#526577"
DONE, READY, OPEN = "#e5f3f2", "#fff2d5", "#eef1f4"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fonts():
    for name, filename in (
        ("Study", "PT_Sans-Web-Regular.ttf"),
        ("StudyBold", "PT_Sans-Web-Bold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, HERE / "fonts" / filename))


class Figure:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.drawing = Drawing(width, height)
        self.drawing.add(Rect(0, 0, width, height, fillColor=colors.white, strokeColor=None))

    def text(self, x, top, value, *, size=20, bold=False, color=INK, anchor="start"):
        self.drawing.add(
            String(
                x,
                self.height - top,
                value,
                fontName="StudyBold" if bold else "Study",
                fontSize=size,
                fillColor=colors.HexColor(color),
                textAnchor=anchor,
            )
        )

    def rect(self, x, top, width, height, *, fill=DONE, stroke=TEAL):
        self.drawing.add(
            Rect(
                x,
                self.height - top - height,
                width,
                height,
                rx=12,
                ry=12,
                fillColor=colors.HexColor(fill),
                strokeColor=colors.HexColor(stroke),
                strokeWidth=1.6,
            )
        )

    def node(self, x, top, width, title, lines, *, height=110, fill=DONE, stroke=TEAL, size=19):
        self.rect(x, top, width, height, fill=fill, stroke=stroke)
        values = [(title, 22, True), *[(line, size, False) for line in lines]]
        for index, (line, font_size, bold) in enumerate(values):
            font = "StudyBold" if bold else "Study"
            if pdfmetrics.stringWidth(line, font, font_size) > width - 22:
                raise ValueError(f"Figure label exceeds its box: {line}")
            self.text(
                x + width / 2,
                top + 31 + index * 26,
                line,
                size=font_size,
                bold=bold,
                anchor="middle",
            )

    def arrow(self, points, *, dashed=False, color=TEAL):
        coordinates = [(x, self.height - y) for x, y in points]
        self.drawing.add(
            PolyLine(
                [value for pair in coordinates for value in pair],
                strokeColor=colors.HexColor(color),
                strokeWidth=2,
                strokeDashArray=[7, 5] if dashed else None,
            )
        )
        (a, b), (x, y) = coordinates[-2:]
        angle = math.atan2(y - b, x - a)
        left = (x - 10 * math.cos(angle - 0.4), y - 10 * math.sin(angle - 0.4))
        right = (x - 10 * math.cos(angle + 0.4), y - 10 * math.sin(angle + 0.4))
        self.drawing.add(
            Polygon(
                [x, y, *left, *right],
                fillColor=colors.HexColor(color),
                strokeColor=None,
            )
        )

    def export(self, directory, name):
        pdf = directory / f"{name}.pdf"
        renderPDF.drawToFile(self.drawing, str(pdf))
        svg = renderSVG.drawToString(self.drawing)
        faces = []
        for family, filename in (
            ("Study", "PT_Sans-Web-Regular.ttf"),
            ("StudyBold", "PT_Sans-Web-Bold.ttf"),
        ):
            data = base64.b64encode((HERE / "fonts" / filename).read_bytes()).decode()
            faces.append(f"@font-face{{font-family:{family};src:url(data:font/ttf;base64,{data})}}")
        svg = svg.replace(
            "<clipPath", "<defs><style>" + "".join(faces) + "</style></defs><clipPath", 1
        )
        svg = svg.replace("<title>...</title>", f"<title>{name} - {DATE}</title>")
        (directory / f"{name}.svg").write_text(svg)
        with pymupdf.open(pdf) as document:
            document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(directory / f"{name}.png")


def architecture():
    f = Figure(1000, 1260)
    f.text(40, 48, "ARCHITETTURA IMPLEMENTATA", size=29, bold=True, color=TEAL)
    f.text(40, 78, f"Revisione {DATE} - ultimo run Apache: 18 ottobre 2026", size=19)
    for x, fill, label in (
        (40, DONE, "Collaudato: leggere i limiti del backend"),
        (450, READY, "Software predisposto"),
        (730, OPEN, "Integrazione aperta"),
    ):
        f.rect(x, 101, 18, 18, fill=fill, stroke=MUTED)
        f.text(x + 27, 117, label, size=16)

    f.node(
        40,
        155,
        280,
        "OpenTelemetry",
        ["Log registrati / log SDK", "Facts Ubuntu associati"],
        size=19,
    )
    f.node(
        360,
        155,
        280,
        "CTI via MCP",
        ["cve2owl / assessment Ubuntu", "Fonti e snapshot verificati"],
        size=18,
    )
    f.node(
        680, 155, 280, "SBOM / OSV", ["Fonte opzionale HTTP", "Profilo Java, non Apache"], size=19
    )
    f.rect(30, 305, 940, 405, fill="#f8fbfc", stroke="#c7d9df")
    f.text(540, 333, "CAMEL + OLLAMA", size=20)

    # Collegamenti prima dei riquadri: le etichette non vengono attraversate.
    for x in (180, 500):
        f.arrow([(x, 265), (x, 355)])
    f.arrow([(820, 265), (820, 355)], dashed=True, color=MUTED)
    f.arrow([(320, 399), (360, 399)])
    f.arrow([(640, 399), (680, 399)])
    f.arrow([(300, 465), (300, 493), (660, 493), (660, 414), (680, 414)])
    f.arrow([(180, 465), (180, 540), (390, 540), (390, 580)])
    f.arrow([(500, 465), (500, 580)])
    f.arrow([(820, 465), (820, 540), (610, 540), (610, 580)])
    f.node(40, 355, 280, "TelemetryAgent", ["RuntimeEvidence", "Identità e fonti osservate"])
    f.node(360, 355, 280, "VulnerabilityAgent", ["VulnerabilityReport", "Assessment separato"])
    f.node(680, 355, 280, "CountermeasureAgent", ["CandidateStrategies", "+ richieste di verifica"])
    f.node(
        340,
        580,
        320,
        "StrategicAgent",
        ["Legge tre artefatti distinti", "Coordina i tool e la decisione"],
    )
    f.node(
        680,
        590,
        280,
        "ArtifactSession",
        ["Pydantic / cache / get_context", "Pubblicazioni controllate"],
        height=100,
        fill="#f8fbfc",
        stroke="#c7d9df",
        size=17,
    )
    f.text(40, 745, "RAMO APACHE", size=21, bold=True)
    f.text(360, 745, "Collaudato: nessuna candidata confermata", size=21, bold=True)
    f.arrow([(340, 635), (335, 635), (335, 770), (180, 770), (180, 790)])
    f.arrow([(320, 845), (360, 845)])
    f.arrow([(640, 845), (680, 845)])
    f.node(
        40,
        790,
        280,
        "Grafo e ranking vuoti",
        ["Gate MCP di astensione", "BWAF / Tiny-ME non eseguiti"],
        size=18,
    )
    f.node(360, 790, 280, "FinalDecision", ["insufficient_evidence", "4 richieste pendenti"])
    f.node(680, 790, 280, "PROV-O via MCP", ["JSON-LD su file", "Scrittura e rilettura"])

    f.arrow([(340, 650), (15, 650), (15, 1075), (40, 1075)], dashed=True, color=MUTED)
    f.text(40, 925, "Mapping di dominio ancora aperto", size=17, color=MUTED)
    f.arrow(
        [(820, 900), (980, 900), (980, 1180), (265, 1180), (265, 1155)],
        dashed=True,
        color="#ae7d13",
    )
    f.text(580, 929, "Adapter PROV-O implementato", size=17, color="#866011")
    f.text(40, 971, "COLLEGAMENTI NATIVI - COLLAUDO ON-CHAIN DA ESEGUIRE", size=21, bold=True)
    f.arrow([(490, 1070), (590, 1070)], dashed=True, color=MUTED)
    f.node(
        40,
        990,
        450,
        "Gateway MCP nativo",
        [
            "9 tool: grafo, ranking, Tiny-ME e PROV-O",
            "Contratti e adapter di provenienza pronti",
            "Test: Fablo simulato e stub Fabric",
        ],
        height=165,
        fill=READY,
        stroke="#ae7d13",
        size=19,
    )
    f.node(
        590,
        990,
        370,
        "Fablo REST / Fabric",
        [
            "BWAF e Tiny-ME della baseline",
            "Chaincode PROV-O da installare",
            "Nessun run on-chain documentato",
        ],
        height=165,
        fill=OPEN,
        stroke=MUTED,
        size=18,
    )
    f.text(
        40,
        1197,
        "Linee tratteggiate: fonte opzionale o collegamento non collaudato nel run Apache.",
        size=17,
    )
    f.text(
        40,
        1224,
        "Schema dei componenti. Il BWAF del run Apache ha zero nodi e zero archi.",
        size=17,
        color=MUTED,
    )
    return f


def comparison():
    f = Figure(1000, 760)
    f.text(40, 48, "DAL MOCKUP ALL'IMPLEMENTAZIONE ATTUALE", size=27, bold=True, color=TEAL)
    f.text(40, 78, "Stessi quattro agenti; evoluzione di fonti, controlli e provenienza", size=20)
    f.rect(40, 110, 415, 54, fill=OPEN, stroke=MUTED)
    f.rect(525, 110, 435, 54)
    f.text(247, 144, "MOCKUP STORICO", bold=True, anchor="middle")
    f.text(742, 144, "STATO AL 29 OTTOBRE 2026", bold=True, anchor="middle")
    rows = [
        (
            "Telemetria",
            ["JSON statico dimostrativo"],
            ["Gateway OTel HTTP", "Log registrati o emessi dall'SDK"],
        ),
        (
            "Vulnerabilità",
            ["Fixture Log4j, lookup esatto"],
            ["CTI via MCP e assessment Ubuntu", "Revisione del pacchetto e limiti espliciti"],
        ),
        (
            "Countermeasure",
            ["Candidate su finding della fixture"],
            ["Contesto SBOM/OSV opzionale", "Apache: 4 richieste di verifica pendenti"],
        ),
        (
            "Ranking e semantica",
            ["Euristica e controlli mock"],
            ["Mock mantenuti; gate di astensione", "Gateway BWAF/Tiny-ME predisposto"],
        ),
        (
            "Provenienza",
            ["Record JSON applicativo"],
            ["PROV-O, archivio MCP e rilettura", "Adapter e chaincode Fabric predisposti"],
        ),
    ]
    for i, (label, left, right) in enumerate(rows):
        top = 185 + i * 94
        f.rect(40, top, 415, 82, fill="#f6f7f9", stroke="#d9e1e6")
        f.rect(525, top, 435, 82, fill=READY if i == 3 else DONE, stroke="#c7d9df")
        f.text(57, top + 24, label, size=19, bold=True)
        for j, value in enumerate(left):
            f.text(57, top + 52 + j * 21, value, size=18)
        for j, value in enumerate(right):
            f.text(542, top + 31 + j * 24, value, size=18)
        f.arrow([(465, top + 41), (515, top + 41)])
    f.text(
        40,
        700,
        "Rimangono aperti mapping ontologico, collaudo on-chain e prova con candidate reali.",
        size=19,
    )
    f.text(
        40,
        731,
        "Le funzionalità predisposte non sono risultati già ottenuti sul ledger.",
        size=18,
        color=MUTED,
    )
    return f


def blocks(source):
    tokens = MarkdownIt("commonmark").enable("table").parse(source)
    result, i = [], 0
    while i < len(tokens):
        token = tokens[i]
        if token.type in ("heading_open", "paragraph_open"):
            inline = tokens[i + 1]
            images = [child for child in inline.children or [] if child.type == "image"]
            if images:
                result.append(("image", images[0].attrGet("src"), images[0].content))
            else:
                result.append(
                    (
                        "heading" if token.type == "heading_open" else "paragraph",
                        inline.content,
                        int(token.tag[1:]) if token.type == "heading_open" else 0,
                    )
                )
            i += 3
        elif token.type == "table_open":
            rows, row = [], []
            i += 1
            while tokens[i].type != "table_close":
                if tokens[i].type == "tr_open":
                    row = []
                elif tokens[i].type == "inline":
                    row.append(tokens[i].content)
                elif tokens[i].type == "tr_close":
                    rows.append(row)
                i += 1
            result.append(("table", rows, 0))
            i += 1
        else:
            raise ValueError(f"Unsupported report block: {token.type}")
    return result


def plain(value):
    tokens = MarkdownIt().parseInline(value)[0].children or []
    return "".join(
        " " if t.type == "softbreak" else t.content
        for t in tokens
        if t.type in ("text", "code_inline", "softbreak")
    )


def reports(base, directory):
    source = HERE / f"aggiornamento-relazione-{STAMP}.md"
    items = blocks(source.read_text())
    original_hash = sha(base)
    document = Document(base)
    note = document.add_paragraph(
        f"Nota di lettura - aggiornamento al {DATE}. "
        "I capitoli 1-10 descrivono il mockup e i capitoli 11-18 le prime integrazioni. "
        "Lo stato attuale è nei capitoli 19-24 aggiunti in fondo, con le figure aggiornate. "
        "Le conclusioni storiche non attestano funzionalità aggiunte successivamente."
    )
    anchor = next(p for p in document.paragraphs if p.text == "Sintesi")
    anchor._p.addprevious(note._p)
    document.add_page_break()

    styles = {
        "paragraph": ParagraphStyle(
            "Body", fontName="Study", fontSize=10, leading=14, spaceAfter=8
        ),
        "heading": ParagraphStyle(
            "Chapter",
            fontName="StudyBold",
            fontSize=16,
            leading=20,
            spaceBefore=16,
            spaceAfter=10,
            textColor=colors.HexColor(TEAL),
            keepWithNext=True,
        ),
        "subheading": ParagraphStyle(
            "Sub",
            fontName="StudyBold",
            fontSize=12,
            leading=16,
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "title": ParagraphStyle(
            "Title",
            fontName="StudyBold",
            fontSize=22,
            leading=27,
            spaceAfter=18,
            textColor=colors.HexColor(TEAL),
        ),
        "caption": ParagraphStyle(
            "Caption",
            fontName="Study",
            fontSize=9,
            leading=12,
            spaceBefore=8,
            spaceAfter=12,
            textColor=colors.HexColor(MUTED),
        ),
        "cell": ParagraphStyle("Cell", fontName="Study", fontSize=8.4, leading=11),
    }
    story = []
    for kind, value, level in items:
        if kind == "heading":
            style = "title" if level == 1 else "heading" if level == 2 else "subheading"
            story.append(Paragraph(html.escape(plain(value)), styles[style]))
            if level == 1:
                p = document.add_paragraph(value)
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(18)
            else:
                document.add_heading(value, level=level - 1)
        elif kind == "paragraph":
            value = plain(value)
            story.append(Paragraph(html.escape(value), styles["paragraph"]))
            document.add_paragraph(value)
        elif kind == "image":
            image = directory / value
            with pymupdf.open(directory / Path(value).with_suffix(".pdf")) as figure:
                ratio = figure[0].rect.height / figure[0].rect.width
            story.extend(
                [
                    PageBreak(),
                    KeepTogether(
                        [
                            Image(str(image), width=470, height=470 * ratio),
                            Paragraph(html.escape(level), styles["caption"]),
                        ]
                    ),
                ]
            )
            document.add_page_break()
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run().add_picture(str(image), width=Inches(6.3))
            document.add_paragraph(level, style="Caption")
        else:
            word_table = document.add_table(rows=0, cols=len(value[0]))
            word_table.style = "Table Grid"
            for row in value:
                cells = word_table.add_row().cells
                for cell, content in zip(cells, row, strict=True):
                    cell.text = plain(content)
                    for run in cell.paragraphs[0].runs:
                        run.font.size = Pt(9)
            data = [
                [Paragraph(html.escape(plain(cell)), styles["cell"]) for cell in row]
                for row in value
            ]
            widths = [470 / len(value[0])] * len(value[0])
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DONE)),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccd6df")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])

    target = directory / f"relazione-aggiornata-{STAMP}.docx"
    if target.resolve() == base.resolve():
        raise ValueError("The manual report must not be overwritten")
    document.save(target)
    restore_unchanged_parts(base, target)
    pdf = directory / f"aggiornamento-relazione-{STAMP}.pdf"
    SimpleDocTemplate(
        str(pdf),
        pagesize=A4,
        rightMargin=62,
        leftMargin=62,
        topMargin=42,
        bottomMargin=42,
        title=f"Aggiornamento relazione - {DATE}",
        author="Alessandro Costa",
    ).build(story)
    if sha(base) != original_hash:
        raise ValueError("The manual report changed during generation")
    preserved = verify_preservation(base, target)
    return {"base_sha256": original_hash, "updated_sha256": sha(target), **preserved}


def restore_unchanged_parts(base, target):
    """Conserva anche i byte delle parti XML che python-docx ha solo riserializzato."""
    entries = []
    with ZipFile(base) as old, ZipFile(target) as new:
        originals = set(old.namelist())
        for info in new.infolist():
            data = new.read(info.filename)
            if info.filename in originals and info.filename.endswith((".xml", ".rels")):
                before = old.read(info.filename)
                parser = etree.XMLParser(load_dtd=False, no_network=True)
                a, b = etree.fromstring(before, parser), etree.fromstring(data, parser)
                if etree.tostring(a, method="c14n", exclusive=True) == etree.tostring(
                    b, method="c14n", exclusive=True
                ):
                    data = before
            entries.append((info, data))
    temporary = target.with_suffix(".docx.tmp")
    with ZipFile(temporary, "w") as archive:
        for info, data in entries:
            archive.writestr(info, data)
    temporary.replace(target)


def verify_preservation(base, target):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    def children(archive):
        root = etree.fromstring(archive.read("word/document.xml"))
        return [
            etree.tostring(element, method="c14n", exclusive=True)
            for element in root.find("w:body", ns)
        ]

    with ZipFile(base) as old, ZipFile(target) as new:
        previous, current = children(old), children(new)
        position = 0
        for child in previous:
            while position < len(current) and current[position] != child:
                position += 1
            if position == len(current):
                raise ValueError("An original DOCX element changed or was removed")
            position += 1
        media = [name for name in old.namelist() if name.startswith("word/media/")]
        if any(old.read(name) != new.read(name) for name in media):
            raise ValueError("An original report image changed")
    return {
        "original_body_elements_preserved": len(previous),
        "original_media_preserved": len(media),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-docx", type=Path, default=HERE / "relazione.docx")
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fonts()
    architecture().export(args.output_dir, "architettura-aggiornata")
    comparison().export(args.output_dir, "confronto-mockup-attuale")
    report = reports(args.base_docx, args.output_dir)
    report["document_revision"] = DATE
    report["last_experiments"] = "18 ottobre 2026"
    report["new_inference_or_on_chain_run"] = False
    report["generator_sha256"] = sha(Path(__file__))
    report["source_markdown_sha256"] = sha(HERE / f"aggiornamento-relazione-{STAMP}.md")
    report["files"] = {
        path.name: sha(path)
        for path in args.output_dir.iterdir()
        if path.name.startswith(
            (
                "architettura-aggiornata.",
                "confronto-mockup-attuale.",
                f"relazione-aggiornata-{STAMP}.",
                f"aggiornamento-relazione-{STAMP}.pdf",
            )
        )
    }
    (args.output_dir / f"aggiornamento-verifica-{STAMP}.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
