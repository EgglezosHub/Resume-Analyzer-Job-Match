# app/routes/ui.py
from __future__ import annotations
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Resume, Job
from app.utils.pdf import extract_pdf_text
from app.services.analyze_service import analyze_resume
from app.services.match_service import match_resume_job

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _clean_text(s: str) -> str:
    return (s or "").encode("utf-8", "ignore").decode("utf-8", "ignore").replace("\r", "")

def _bucket(score: float):
    score = 0.0 if score is None else float(score)
    pct = int(round(max(0.0, min(1.0, score)) * 100))
    if score < 0.4:
        return ("Weak", pct, "bg-rose-500", "text-rose-700", "Needs significant alignment")
    if score < 0.6:
        return ("Medium", pct, "bg-amber-500", "text-amber-700", "Relevant but gaps remain")
    return ("Strong", pct, "bg-emerald-500", "text-emerald-700", "Good alignment")

@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": None})

@router.post("/ui-match", response_class=HTMLResponse)
async def ui_match(request: Request,
                   file: UploadFile = File(...),
                   job_description: str = Form(...),
                   db: Session = Depends(get_db)):
    if file.content_type != "application/pdf":
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": "Please upload a PDF file."})

    text, pages, chars = extract_pdf_text(file.file)
    text = _clean_text(text)
    jd_text = _clean_text(job_description)

    if len(text) < 40:
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": "Could not extract enough text from the PDF."})
    if len(jd_text) < 40:
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": "Job description is too short."})

    resume = Resume(filename=file.filename, text=text); db.add(resume); db.commit(); db.refresh(resume)
    job = Job(title="Job Description", description=jd_text); db.add(job); db.commit(); db.refresh(job)

    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)

    ms_label, ms_pct, ms_bar, ms_text, ms_tip = _bucket(matched.get("match_score", 0.0))
    ss_label, ss_pct, ss_bar, ss_text, ss_tip = _bucket(matched.get("semantic_similarity", 0.0))
    so_label, so_pct, so_bar, so_text, so_tip = _bucket(matched.get("skill_overlap", 0.0))

    result = {
        "resume_id": analysis.get("resume_id"),
        "tokens": analysis.get("tokens", 0),
        "skills": analysis.get("skills", []),

        "match_score": float(matched.get("match_score", 0.0)),
        "semantic_similarity": float(matched.get("semantic_similarity", 0.0)),
        "skill_overlap": float(matched.get("skill_overlap", 0.0)),

        "ms": {"label": ms_label, "pct": ms_pct, "bar": ms_bar, "text": ms_text, "tip": ms_tip},
        "ss": {"label": ss_label, "pct": ss_pct, "bar": ss_bar, "text": ss_text, "tip": ss_tip},
        "so": {"label": so_label, "pct": so_pct, "bar": so_bar, "text": so_text, "tip": so_tip},

        "missing_skills": matched.get("missing_skills", []),
        "jd_skills": matched.get("jd_skills", []),           # <-- NEW
        "resume_skills": matched.get("resume_skills", []),   # optional

        "recommendations": matched.get("recommendations", []),
        "parsed_metrics": matched.get("parsed_metrics", []),
        "improvements": matched.get("improvements", []),

        "pages": pages, "chars": chars, "runtime_ms": matched.get("runtime_ms", 0),
    }

    return templates.TemplateResponse("index.html", {"request": request, "result": result, "error": None})

