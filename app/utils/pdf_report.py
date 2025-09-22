# app/utils/pdf_report.py
from __future__ import annotations
from typing import Iterable, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)

# ---- Theme ----
COL_TEXT   = colors.HexColor("#111827")
COL_MUTED  = colors.HexColor("#6B7280")
COL_ACCENT = colors.HexColor("#4F46E5")
COL_RULE   = colors.HexColor("#E5E7EB")

LEFT = RIGHT = 18 * mm
TOP = 22 * mm
BOTTOM = 18 * mm

def _join_skills(skills: Iterable[str]) -> str:
    items = [s.strip() for s in (skills or []) if str(s).strip()]
    return " • ".join(items) if items else "— None detected —"

def generate_report_pdf(buf, payload: dict) -> None:
    if payload is None:
        payload = {}

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="DevMatch — Report",
        author="DevMatch",
    )

    styles = getSampleStyleSheet()

    Base = styles["Normal"]
    Base.fontName = "Helvetica"
    Base.fontSize = 10.5
    Base.leading  = 15
    Base.textColor = COL_TEXT

    H1 = ParagraphStyle(
        "H1", parent=Base, fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=COL_ACCENT, spaceAfter=4,
    )
    SUB = ParagraphStyle(
        "SUB", parent=Base, fontSize=9.5, leading=12,
        textColor=COL_MUTED, spaceAfter=8,
    )
    SEC = ParagraphStyle(
        "SEC", parent=Base, fontName="Helvetica-Bold",
        fontSize=12.5, leading=16, textColor=COL_ACCENT,
        spaceBefore=10, spaceAfter=4,
    )
    BODY = ParagraphStyle(
        "BODY", parent=Base, fontSize=10.5, leading=15, textColor=COL_TEXT,
    )
    BODY_MUTED = ParagraphStyle(
        "BODY_MUTED", parent=BODY, textColor=COL_MUTED
    )
    METRIC_L = ParagraphStyle(
        "METRIC_L", parent=Base, fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=COL_TEXT,
    )
    METRIC_V = ParagraphStyle(
        "METRIC_V", parent=Base, fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=COL_ACCENT, alignment=2,  # right
    )

    story: List = []

    # Title
    story.append(Paragraph("DevMatch — Tech Resume & JD Analyzer", H1))
    story.append(Paragraph("Shareable report", SUB))
    story.append(_hrule())

    # Scores
    story.append(Spacer(0, 8))
    story.append(Paragraph("Scores", SEC))
    score_data = [
        [Paragraph("Match Score", METRIC_L), Paragraph(f"{float(payload.get('match_score') or 0):.2f}", METRIC_V)],
        [Paragraph("Semantic Similarity", METRIC_L), Paragraph(f"{float(payload.get('semantic_similarity') or 0):.2f}", METRIC_V)],
        [Paragraph("JD Skill Coverage", METRIC_L), Paragraph(f"{float(payload.get('skill_overlap') or 0):.2f}", METRIC_V)],
    ]
    tbl = Table(score_data, colWidths=[None, 30*mm], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("LINEBELOW",     (0,0), (-1,0), 0.4, COL_RULE),
        ("LINEBELOW",     (0,1), (-1,1), 0.4, COL_RULE),
        ("LINEBELOW",     (0,2), (-1,2), 0.4, COL_RULE),
    ]))
    story.append(tbl)

    # JD Skills
    story.append(Spacer(0, 12))
    story.append(Paragraph("JD Skills", SEC))
    jd_line = _join_skills(payload.get("jd_skills"))
    story.append(Paragraph(jd_line, BODY if "— None" not in jd_line else BODY_MUTED))

    # Resume Skills
    story.append(Spacer(0, 8))
    story.append(Paragraph("Resume Skills", SEC))
    rs_line = _join_skills(payload.get("resume_skills"))
    story.append(Paragraph(rs_line, BODY if "— None" not in rs_line else BODY_MUTED))

    # Missing Skills
    story.append(Spacer(0, 8))
    story.append(Paragraph("Missing Skills", SEC))
    miss_line = _join_skills(payload.get("missing_skills"))
    story.append(Paragraph(miss_line, BODY if "— None" not in miss_line else BODY_MUTED))

    # Recommendations
    story.append(Spacer(0, 10))
    story.append(Paragraph("Recommendations", SEC))
    recs = [r for r in (payload.get("recommendations") or []) if str(r).strip()]
    if not recs:
        story.append(Paragraph("No extra recommendations.", BODY_MUTED))
    else:
        items = [ListItem(Paragraph(r, BODY), leftIndent=4) for r in recs]
        story.append(ListFlowable(
            items,
            bulletType="bullet",
            bulletFontName="Helvetica",
            bulletFontSize=8.5,
            bulletColor=COL_ACCENT,
            leftIndent=8,
            bulletOffsetY=1.5,
        ))

    # Footer watermark with link
    def _footer(c, doc):
        text = "DevMatch — https://resume-match-api.onrender.com"
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(COL_MUTED)
        w = c.stringWidth(text, "Helvetica", 8)
        x = doc.pagesize[0] - RIGHT - w
        y = BOTTOM - 6
        c.drawString(x, y, text)
        c.linkURL(
            "https://resume-match-api.onrender.com",
            (x, y - 2, x + w, y + 10),
            relative=0,
        )
        c.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)

def _hrule():
    t = Table([[""]], colWidths=[None], rowHeights=[0.8])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), COL_RULE)]))
    return t

