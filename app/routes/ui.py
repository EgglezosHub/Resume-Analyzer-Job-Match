from __future__ import annotations
from io import BytesIO
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Resume, Job, Match
from app.utils.pdf import extract_pdf_text
from app.utils.pdf_report import generate_report_pdf
from app.services.analyze_service import analyze_resume
from app.services.match_service import match_resume_job
from app.services.report_service import create_report, get_report

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

# ---------- Landing + Analyze + Demo ----------

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": None, "read_only": False, "share_url": None})

@router.get("/demo", response_class=HTMLResponse)
async def demo(request: Request, db: Session = Depends(get_db)):
    # Minimal built-in demo (no file upload)
    demo_resume = """
    Projects: Built a FastAPI backend with PostgreSQL and Docker; added Redis cache and GitHub Actions CI.
    Implemented REST APIs (auth, pagination). Deployed to AWS (EC2) via Terraform. Wrote tests with pytest.
    """
    demo_jd = """
    Looking for a backend engineer with Python/FastAPI, PostgreSQL, Redis, Docker, CI/CD and AWS/Terraform experience.
    """

    resume = Resume(filename="demo.txt", text=_clean_text(demo_resume)); db.add(resume); db.commit(); db.refresh(resume)
    job = Job(title="Demo JD", description=_clean_text(demo_jd)); db.add(job); db.commit(); db.refresh(job)

    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)

    ms_label, ms_pct, *_ = _bucket(matched.get("match_score", 0.0))
    ss_label, ss_pct, *_ = _bucket(matched.get("semantic_similarity", 0.0))
    so_label, so_pct, *_ = _bucket(matched.get("skill_overlap", 0.0))

    result = {
        "resume_id": analysis.get("resume_id"),
        "tokens": analysis.get("tokens", 0),
        "skills": analysis.get("skills", []),

        "match_score": float(matched.get("match_score", 0.0)),
        "semantic_similarity": float(matched.get("semantic_similarity", 0.0)),
        "skill_overlap": float(matched.get("skill_overlap", 0.0)),

        "ms": {"label": ms_label, "pct": ms_pct},
        "ss": {"label": ss_label, "pct": ss_pct},
        "so": {"label": so_label, "pct": so_pct},

        "missing_skills": matched.get("missing_skills", []),
        "jd_skills": matched.get("jd_skills", []),
        "resume_skills": matched.get("resume_skills", []),

        "recommendations": matched.get("recommendations", []),
        "parsed_metrics": matched.get("parsed_metrics", []),
        "improvements": matched.get("improvements", []),

        "pages": 1, "chars": len(demo_resume), "runtime_ms": matched.get("runtime_ms", 0),
    }

    # create shareable report immediately
    rpt = create_report(db, payload=result, resume_id=resume.id, job_id=job.id, match_id=None)
    share_url = f"/r/{rpt.slug}"
    return templates.TemplateResponse("index.html", {"request": request, "result": result, "error": None, "read_only": False, "share_url": share_url})

@router.post("/ui-match", response_class=HTMLResponse)
async def ui_match(request: Request,
                   file: UploadFile = File(...),
                   job_description: str = Form(...),
                   db: Session = Depends(get_db)):
    if file.content_type != "application/pdf":
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": "Please upload a PDF file.", "read_only": False, "share_url": None})

    text, pages, chars = extract_pdf_text(file.file)
    text = _clean_text(text); jd_text = _clean_text(job_description)

    if len(text) < 40 or len(jd_text) < 40:
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": "Please provide a valid PDF and a sufficiently detailed JD.", "read_only": False, "share_url": None})

    resume = Resume(filename=file.filename, text=text); db.add(resume); db.commit(); db.refresh(resume)
    job = Job(title="Job Description", description=jd_text); db.add(job); db.commit(); db.refresh(job)

    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)

    ms_label, ms_pct, *_ = _bucket(matched.get("match_score", 0.0))
    ss_label, ss_pct, *_ = _bucket(matched.get("semantic_similarity", 0.0))
    so_label, so_pct, *_ = _bucket(matched.get("skill_overlap", 0.0))

    result = {
        "resume_id": analysis.get("resume_id"),
        "tokens": analysis.get("tokens", 0),
        "skills": analysis.get("skills", []),

        "match_score": float(matched.get("match_score", 0.0)),
        "semantic_similarity": float(matched.get("semantic_similarity", 0.0)),
        "skill_overlap": float(matched.get("skill_overlap", 0.0)),

        "ms": {"label": ms_label, "pct": ms_pct},
        "ss": {"label": ss_label, "pct": ss_pct},
        "so": {"label": so_label, "pct": so_pct},

        "missing_skills": matched.get("missing_skills", []),
        "jd_skills": matched.get("jd_skills", []),
        "resume_skills": matched.get("resume_skills", []),

        "recommendations": matched.get("recommendations", []),
        "parsed_metrics": matched.get("parsed_metrics", []),
        "improvements": matched.get("improvements", []),

        "pages": pages, "chars": chars, "runtime_ms": matched.get("runtime_ms", 0),
    }

    # Save shareable report
    rpt = create_report(db, payload=result, resume_id=resume.id, job_id=job.id, match_id=None)
    share_url = f"/r/{rpt.slug}"

    return templates.TemplateResponse("index.html", {"request": request, "result": result, "error": None, "read_only": False, "share_url": share_url})

# ---------- Public read-only report + PDF ----------

@router.get("/r/{slug}", response_class=HTMLResponse)
async def public_report(slug: str, request: Request, db: Session = Depends(get_db)):
    rpt = get_report(db, slug)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return templates.TemplateResponse("index.html", {"request": request, "result": rpt.payload, "error": None, "read_only": True, "share_url": f"/r/{slug}"})

@router.get("/r/{slug}.pdf")
async def public_report_pdf(slug: str, db: Session = Depends(get_db)):
    rpt = get_report(db, slug)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    buf = BytesIO()
    generate_report_pdf(buf, rpt.payload)
    headers = {"Content-Disposition": f'inline; filename="devmatch-{slug}.pdf"'}
    return StreamingResponse(buf, headers=headers, media_type="application/pdf")

