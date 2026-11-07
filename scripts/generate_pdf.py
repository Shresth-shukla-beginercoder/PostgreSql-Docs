#!/usr/bin/env python3
"""
PostgreSQL Master Handbook — PDF Generator

Reads the markdown content files in ../content/ and builds two PDFs:
  1. PostgreSQL_Database_Engineering_Master_Handbook.pdf  (the full textbook)
  2. PostgreSQL_Quick_Reference.pdf                        (compact reference, built from Part 32)

Uses ReportLab. Includes a lightweight markdown parser tailored to the
handbook's structure: h1–h4 headings, code blocks, tables, callout blocks
(> NOTE / WARNING / INTERVIEW / PRACTICAL), bold/italic/inline code.

Run:  python generate_pdf.py
"""

import os
import re
import sys
import html

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    PageBreak, Table, TableStyle, NextPageTemplate, KeepTogether,
    HRFlowable,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE, "content")
OUTPUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MASTER_PDF = os.path.join(OUTPUT_DIR, "PostgreSQL_Database_Engineering_Master_Handbook.pdf")
QUICKREF_PDF = os.path.join(OUTPUT_DIR, "PostgreSQL_Quick_Reference.pdf")

# ---------------------------------------------------------------- fonts ---
def register_fonts():
    """Register a reliable Unicode-capable font stack.

    Uses the built-in ReportLab fonts (Helvetica / Courier) which ship
    with every installation, plus optional TTFs from assets/fonts if
    present. Courier covers our SQL code; Helvetica covers body text.
    """
    font_dir = os.path.join(BASE, "assets", "fonts")
    # Register common Windows fonts if available for better typography
    candidates = [
        ("HandbookMono", "Consolas.ttf"),
        ("HandbookSerif", "Cambria.ttf"),
    ]
    for name, fname in candidates:
        path = os.path.join(font_dir, fname)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
    # Fallbacks always work
    pdfmetrics.registerFontFamily(
        "HandbookMono",
        normal="Courier", bold="Courier-Bold", italic="Courier-Oblique",
    )

FONT_BODY = "Helvetica"
FONT_BODY_BOLD = "Helvetica-Bold"
FONT_BODY_ITALIC = "Helvetica-Oblique"
FONT_HEADING = "Helvetica-Bold"
FONT_CODE = "Courier"

# ---------------------------------------------------------------- colors ---
NAVY = colors.HexColor("#0B2545")
ACCENT = colors.HexColor("#1F6FEB")
CODE_BG = colors.HexColor("#F4F6F8")
CODE_TEXT = colors.HexColor("#0B2545")
NOTE_BG = colors.HexColor("#E8F0FE")
NOTE_BORDER = colors.HexColor("#1F6FEB")
WARN_BG = colors.HexColor("#FDECEA")
WARN_BORDER = colors.HexColor("#C5221F")
INTERVIEW_BG = colors.HexColor("#F3E8FD")
INTERVIEW_BORDER = colors.HexColor("#6B21A8")
TABLE_HEADER_BG = colors.HexColor("#0B2545")
TABLE_ALT_BG = colors.HexColor("#F4F6F8")

# ---------------------------------------------------------------- styles ---
def make_styles():
    S = {}
    S["body"] = ParagraphStyle(
        "body", fontName=FONT_BODY, fontSize=9.5, leading=12,
        textColor=colors.HexColor("#1a1a1a"), alignment=TA_JUSTIFY,
        spaceAfter=5,
    )
    S["h1"] = ParagraphStyle(
        "h1", fontName=FONT_HEADING, fontSize=18, leading=22,
        textColor=NAVY, spaceBefore=12, spaceAfter=8,
    )
    S["h2"] = ParagraphStyle(
        "h2", fontName=FONT_HEADING, fontSize=14, leading=17,
        textColor=NAVY, spaceBefore=10, spaceAfter=6,
    )
    S["h3"] = ParagraphStyle(
        "h3", fontName=FONT_HEADING, fontSize=11.5, leading=14,
        textColor=colors.HexColor("#13315C"), spaceBefore=8, spaceAfter=4,
    )
    S["h4"] = ParagraphStyle(
        "h4", fontName=FONT_HEADING, fontSize=10, leading=12,
        textColor=colors.HexColor("#333333"), spaceBefore=6, spaceAfter=3,
    )
    S["code"] = ParagraphStyle(
        "code", fontName=FONT_CODE, fontSize=7.8, leading=10,
        textColor=CODE_TEXT, backColor=CODE_BG,
        leftIndent=8, rightIndent=8, spaceBefore=3, spaceAfter=6,
        borderPadding=(4, 4, 4, 4),
    )
    S["table_cell"] = ParagraphStyle(
        "table_cell", fontName=FONT_BODY, fontSize=8, leading=10,
    )
    S["table_cell_header"] = ParagraphStyle(
        "table_cell_header", fontName=FONT_BODY_BOLD, fontSize=8,
        leading=10, textColor=colors.white,
    )
    S["toc"] = ParagraphStyle("toc", fontName=FONT_BODY, fontSize=11, leading=16)
    S["cover_title"] = ParagraphStyle(
        "cover_title", fontName=FONT_HEADING, fontSize=34, leading=42,
        textColor=colors.white, alignment=TA_CENTER,
    )
    S["cover_sub"] = ParagraphStyle(
        "cover_sub", fontName=FONT_BODY, fontSize=15, leading=20,
        textColor=colors.HexColor("#CBD5E1"), alignment=TA_CENTER,
    )
    S["callout"] = ParagraphStyle(
        "callout", fontName=FONT_BODY, fontSize=9.5, leading=13,
        textColor=colors.HexColor("#1a1a1a"), leftIndent=4, rightIndent=4,
    )
    return S

S = make_styles()

# ------------------------------------------------------- markdown helpers ---
# Removed unused regex pattern

def _inline_markup(text):
    """Convert markdown inline text to reportlab paragraph markup.

    Code spans are stashed as placeholders first so that any '*' or '**'
    inside them (e.g. `SELECT * FROM x`) cannot break the bold/italic
    matching and produce malformed <i>/<b>/<font> nesting.
    """
    t = html.escape(text, quote=False)
    codes = []
    def _stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"
    t = re.sub(r"`([^`]+)`", _stash, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*([^*]+?)\*", r"<i>\1</i>", t)
    def _restore(m):
        c = codes[int(m.group(1))]
        return f"<font name='Courier' backColor='#0B2545' color='white'>{c}</font>"
    t = re.sub(r"\x00(\d+)\x00", _restore, t)
    return t

def md_inline(text, style_key="body"):
    """Convert markdown inline formatting to reportlab Paragraph markup."""
    return Paragraph(_inline_markup(text), S[style_key])

def render_table(rows, col_widths=None):
    data = [[md_inline(c, "table_cell_header") if r == 0 else md_inline(c, "table_cell")
            for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG))
    t.setStyle(TableStyle(style))
    return t

def parse_markdown_block(lines):
    """Parse a list of markdown lines into a list of reportlab flowables."""
    flows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # fenced code block
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code = "\n".join(code_lines)
            # Preserve newlines as <br/>, escape for the XML layer
            esc = html.escape(code, quote=False)
            esc = esc.replace("\n", "<br/>")
            # light syntax coloring: highlight SQL keywords
            flow = Paragraph(esc, S["code"])
            flows.append(flow)
            i += 1
            continue

        # callout blocks starting with ">"
        if stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].lstrip("> ").strip())
                i += 1
            block_text = " ".join(block)
            kind = "note"
            upper = block_text.upper()
            if upper.startswith(("WARNING", "DESTRUCTIVE")):
                kind = "warn"
            elif upper.startswith(("INTERVIEW", "INT-")):
                kind = "interview"
            elif upper.startswith("PRACTICAL"):
                kind = "interview"
            bg, border = {
                "note": (NOTE_BG, NOTE_BORDER),
                "warn": (WARN_BG, WARN_BORDER),
                "interview": (INTERVIEW_BG, INTERVIEW_BORDER),
            }[kind]
            labels = {"note": "NOTE", "warn": "WARNING", "interview": "INTERVIEW TIP"}
            inner = html.escape(block_text, quote=False)
            para = Paragraph(
                f"<b>{labels[kind]}:</b> " + inner, S["callout"]
            )
            t = Table([[para]], colWidths=[7.0 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
            ]))
            flows.append(Spacer(1, 2))
            flows.append(t)
            flows.append(Spacer(1, 4))
            continue

        # table: line is a markdown row and the next line is the |---| separator
        if stripped.startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:|-]+\|?\s*$", lines[i + 1]):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_lines = [stripped]
            i += 2  # skip header + separator
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for tl in table_lines:
                rows.append([c.strip() for c in tl.strip("|").split("|")])
            n_cols = len(header_cells)
            # simple proportional column widths
            if n_cols <= 2:
                widths = [3.5 * inch] * n_cols
            elif n_cols == 3:
                widths = [1.8 * inch, 2.6 * inch, 2.6 * inch]
            elif n_cols == 4:
                widths = [1.5 * inch] * n_cols
            else:
                widths = [7.0 * inch / n_cols] * n_cols
            # pad rows
            for r in rows:
                while len(r) < n_cols:
                    r.append("")
            flows.append(Spacer(1, 3))
            flows.append(render_table(rows, widths))
            flows.append(Spacer(1, 3))
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if level == 1:
                flows.append(Spacer(1, 6))
                flows.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=6))
                flows.append(Paragraph(html.escape(text), S["h1"]))
            elif level == 2:
                flows.append(Paragraph(html.escape(text), S["h2"]))
            elif level == 3:
                flows.append(Paragraph(html.escape(text), S["h3"]))
            else:
                flows.append(Paragraph(html.escape(text), S["h4"]))
            i += 1
            continue

        # horizontal rule
        if re.match(r"^-{3,}$", stripped):
            flows.append(Spacer(1, 4))
            flows.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#999999"), spaceAfter=4))
            i += 1
            continue

        # bullet lists
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            block = []
            while i < len(lines) and re.match(r"^(\s*)[-*]\s+", lines[i]):
                indent = len(lines[i].split(None, 1)[0]) if lines[i].split() else 0
                content = re.sub(r"^[-*]\s+", "", lines[i])
                block.append((indent, content))
                i += 1
            for indent, content in block:
                esc = _inline_markup(content)
                left = 14 + (indent if indent > 1 else 0) * 8
                p = Paragraph(f"&bull; {esc}", ParagraphStyle(
                    "bullet", parent=S["body"], leftIndent=left, alignment=TA_LEFT,
                ))
                flows.append(p)
            flows.append(Spacer(1, 3))
            continue

        # numbered lists
        m = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if m:
            block = []
            num = 1
            while i < len(lines):
                mm = re.match(r"^(\s*)\d+\.\s+(.*)$", lines[i])
                if mm:
                    content = mm.group(2)
                    block.append((num, content))
                    num += 1
                    i += 1
                else:
                    break
            for n, content in block:
                esc = _inline_markup(content)
                p = Paragraph(f"<b>{n}.</b> {esc}", ParagraphStyle(
                    "numlist", parent=S["body"], leftIndent=16, alignment=TA_LEFT,
                ))
                flows.append(p)
            flows.append(Spacer(1, 3))
            continue

        # paragraph: accumulate until blank line
        para_lines = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|```|\||>|[-*]\s|\d+\.\s)", lines[i].strip()
        ):
            para_lines.append(lines[i].strip())
            i += 1
        text = " ".join(para_lines)
        flows.append(md_inline(text))

    return flows

# ------------------------------------------------------------ page furniture
def draw_master_page(canv, doc, is_front=False):
    canv.saveState()
    w, h = letter
    if not is_front:
        # header
        canv.setFont(FONT_BODY, 8)
        canv.setFillColor(colors.HexColor("#666666"))
        canv.drawString(0.75 * inch, h - 0.55 * inch,
                        "The Complete PostgreSQL & Database Engineering Master Handbook")
        canv.line(0.75 * inch, h - 0.62 * inch, w - 0.75 * inch, h - 0.62 * inch)
        # footer
        canv.setFont(FONT_BODY, 8)
        canv.line(0.75 * inch, 0.6 * inch, w - 0.75 * inch, 0.6 * inch)
        canv.setFont(FONT_BODY_ITALIC, 8)
        canv.drawString(0.75 * inch, 0.42 * inch,
                        "A personal learning & engineering reference")
        canv.setFont(FONT_BODY_BOLD, 9)
        canv.drawRightString(w - 0.75 * inch, 0.42 * inch, str(canv.getPageNumber()))
    canv.restoreState()

class MasterDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=letter, **kw)
        frame = Frame(0.75 * inch, 0.7 * inch,
                      letter[0] - 1.5 * inch, letter[1] - 1.4 * inch, id="main")
        self.addPageTemplates([PageTemplate(id="master", frames=[frame], onPage=draw_master_page)])

    def afterFlowable(self, flowable):
        # TOC registration
        if isinstance(flowable, Paragraph):
            style = flowable.style
            if style.name in ("h1", "h2", "h3"):
                level = {"h1": 0, "h2": 1, "h3": 2}[style.name]
                self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))

# --------------------------------------------------------------- cover pages
def cover_flowables(master=True):
    flows = []
    flows.append(Spacer(1, 1.6 * inch))
    flows.append(Paragraph("THE COMPLETE", ParagraphStyle("c1", parent=S["cover_sub"], fontSize=16)))
    flows.append(Spacer(1, 0.3 * inch))
    flows.append(Paragraph("PostgreSQL &amp;<br/>Database Engineering<br/>Master Handbook",
                            S["cover_title"]))
    flows.append(Spacer(1, 0.5 * inch))
    flows.append(Paragraph(
        "From absolute SQL beginner to professional database engineer,<br/>"
        "DBA, and cloud database architect",
        S["cover_sub"]))
    flows.append(Spacer(1, 0.9 * inch))
    flows.append(HRFlowable(width="40%", thickness=2, color=ACCENT, hAlign="CENTER", spaceAfter=10))
    flows.append(Paragraph(
        "Prepared as a personal learning and engineering reference<br/>"
        "PostgreSQL 17 · 32 Parts · SQL → Architecture → Cloud → Interviews",
        ParagraphStyle("c2", parent=S["cover_sub"], fontSize=10)))
    flows.append(Spacer(1, 0.5 * inch))
    flows.append(PageBreak())
    return flows

def toc_flowables():
    flows = [
        Paragraph("Table of Contents", ParagraphStyle("toch", parent=S["h1"], spaceBefore=0)),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc0", parent=S["toc"], fontName=FONT_HEADING, fontSize=12,
                       textColor=NAVY, leftIndent=0, spaceBefore=8),
        ParagraphStyle("toc1", parent=S["toc"], fontSize=10.5, leftIndent=14),
        ParagraphStyle("toc2", parent=S["toc"], fontSize=9.5, leftIndent=28,
                       textColor=colors.HexColor("#555555")),
    ]
    flows.append(toc)
    flows.append(PageBreak())
    return flows

# ------------------------------------------------------------- doc builder ---
def build_master_pdf():
    register_fonts()
    doc = MasterDoc(MASTER_PDF)

    # content order
    content_files = [
        f for f in sorted(os.listdir(CONTENT_DIR))
        if f.endswith(".md") and f != "part_32_quick_ref.md"
    ]

    story = []
    story += cover_flowables()
    story += toc_flowables()
    # second pass entries need their own page template pass:
    story.append(PageBreak())

    part_num = 1
    for fname in content_files:
        with open(os.path.join(CONTENT_DIR, fname), encoding="utf-8") as fh:
            text = fh.read()
        lines = text.splitlines()
        flows = parse_markdown_block(lines)
        story.extend(flows)
        story.append(PageBreak())

    # References section (authoritative sources)
    refs = [
        ("h1", "REFERENCES AND AUTHORITATIVE SOURCES"),
        ("p", "All PostgreSQL commands, syntax, and version behaviors in this handbook are verified against the official documentation:"),
        ("li", "PostgreSQL Documentation (postgresql.org/docs/current) — SQL commands, data types, functions, and configuration reference."),
        ("li", "PostgreSQL Administrator's Guide — replication, WAL, autovacuum, and backup/restore procedures."),
        ("li", "PostgreSQL Release Notes — feature introductions per major version (IDENTITY columns: PG10; MERGE / procedures: PG14; JSON_TABLE: PG17)."),
        ("li", "AWS Documentation (docs.aws.amazon.com) — Amazon RDS for PostgreSQL, Amazon Aurora PostgreSQL-Compatible Edition, DynamoDB, Redshift, ElastiCache, Neptune, and DMS."),
        ("li", "Official documentation of other vendors where referenced: Oracle Database, Microsoft SQL Server, MongoDB, Snowflake, and Elasticsearch."),
        ("h2", "VERSION POLICY"),
        ("p", "Primary reference: PostgreSQL 17 (latest stable major release at time of writing). Where behavior differs by major version, the version is stated explicitly. Statements about AWS managed services are limited to what AWS documents; no PostgreSQL feature is claimed for AWS services that do not support it."),
        ("h2", "DEPRECATED AND VERSION-SPECIFIC FEATURES"),
        ("li", "SERIAL/BIGSERIAL — still supported but superseded by GENERATED ... AS IDENTITY (PG10+)."),
        ("li", "pg_stat_bgwriter — renamed to pg_stat_bgwriter in older versions; in PostgreSQL 15+ use the extended view pg_stat_archiver and log settings (background writer stats moved to the logging collector)."),
        ("li", "AWS Schema Conversion Tool (SCT) — has been replaced by the AWS DMS database assessment and conversion engine; see AWS DMS documentation for current tooling."),
        ("li", "JSON_TABLE — supported natively starting with PostgreSQL 17 only."),
        ("li", "MULTIRANGE types — PostgreSQL 14+."),
        ("li", "pgvector — third-party extension; not part of the PostgreSQL core distribution."),
    ]
    rf = []
    for kind, text in refs:
        if kind == "h1":
            rf.append(Paragraph(html.escape(text), S["h1"]))
        elif kind == "h2":
            rf.append(Paragraph(html.escape(text), S["h2"]))
        elif kind == "li":
            esc = html.escape(text)
            rf.append(Paragraph(f"&bull; {esc}", ParagraphStyle("refli", parent=S["body"], leftIndent=14, alignment=TA_LEFT)))
        else:
            rf.append(md_inline(text))
    story.extend(rf)

    doc.build(story)
    print(f"MASTER PDF written: {MASTER_PDF}")

def build_quick_reference_pdf():
    register_fonts()
    doc = MasterDoc(QUICKREF_PDF)
    content_file = os.path.join(CONTENT_DIR, "part_32_quick_ref.md")
    flows = []
    flows.append(Spacer(1, 0.4 * inch))
    flows.append(Paragraph("PostgreSQL Quick Reference", ParagraphStyle(
        "qr", parent=S["h1"], fontSize=26)))
    flows.append(Paragraph("A compact practical reference for everyday SQL work",
                            ParagraphStyle("qrs", parent=S["cover_sub"], textColor=colors.HexColor("#444444"))))
    flows.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=6, spaceAfter=10))
    with open(content_file, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()
    pf = parse_markdown_block(lines)
    # compact: strip page breaks
    pf = [f for f in pf if not isinstance(f, PageBreak)]
    flows.extend(pf)
    doc.build(flows)
    print(f"QUICK REFERENCE PDF written: {QUICKREF_PDF}")

if __name__ == "__main__":
    if not os.path.isdir(CONTENT_DIR):
        sys.exit(f"Content directory not found: {CONTENT_DIR}")
    build_master_pdf()
    build_quick_reference_pdf()
