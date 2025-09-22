from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def draw_tag(c, x, y, text, fill=colors.HexColor("#333333")):
    c.setFillColor(fill); c.setStrokeColor(fill)
    c.roundRect(x, y-6, 6+len(text)*3.2+6, 14, 3, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x+6, y, text)

def generate_report_pdf(buf, payload: dict):
    # payload comes from the public result dict
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 18*mm
    y = H - margin

    # Header
    c.setFillColor(colors.HexColor("#111827")); c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "DevMatch — Tech Resume & JD Analyzer")
    y -= 8*mm
    c.setFillColor(colors.HexColor("#6B7280")); c.setFont("Helvetica", 10)
    c.drawString(margin, y, "Shareable report (read-only)")
    y -= 10*mm

    # Scores
    def score_line(label, value):
        nonlocal y
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, label)
        c.setFont("Helvetica", 12)
        c.drawRightString(W-margin, y, f"{value:.2f}")
        y -= 8*mm

    score_line("Match Score", float(payload.get("match_score", 0)))
    score_line("Semantic Similarity", float(payload.get("semantic_similarity", 0)))
    score_line("JD Skill Coverage", float(payload.get("skill_overlap", 0)))

    y -= 2*mm
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.line(margin, y, W-margin, y); y -= 8*mm

    # Skills
    def chips(title, items):
        nonlocal y
        c.setFillColor(colors.HexColor("#111827")); c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, title); y -= 7*mm
        x = margin; row_h = 7*mm
        for s in items[:60]:  # cap
            w = 6 + len(s)*3.2 + 6
            if x + w > W - margin:
                x = margin; y -= row_h
            draw_tag(c, x, y, s, colors.HexColor("#111827"))
            x += w + 4
        y -= 10

    chips("JD Skills", payload.get("jd_skills", []))
    chips("Resume Skills", payload.get("resume_skills", []))
    chips("Missing Skills", payload.get("missing_skills", []))

    # Recommendations
    recs = payload.get("recommendations", [])
    if recs:
        y -= 4*mm
        c.setFillColor(colors.HexColor("#111827")); c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Recommendations"); y -= 6*mm
        c.setFont("Helvetica", 10); c.setFillColor(colors.HexColor("#374151"))
        for tip in recs[:12]:
            c.circle(margin+2, y+3, 1.5, stroke=0, fill=1)
            c.drawString(margin+10, y, tip); y -= 6*mm
            if y < margin+20*mm: break

    c.showPage(); c.save(); buf.seek(0)
