# app/routes/ui.py
from __future__ import annotations
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import SessionLocal
from app.db.models import Resume, Job, Report, User
from app.utils.pdf import extract_pdf_text
from app.utils.pdf_report import generate_report_pdf
from app.services.analyze_service import analyze_resume
from app.services.match_service import match_resume_job
from app.services.report_service import create_report, get_report

import posthog
from app.core.config import settings as cfg
if cfg.posthog_key:
    posthog.project_api_key = cfg.posthog_key
    posthog.host = cfg.posthog_host

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
    if score < 0.4: return ("Weak", pct)
    if score < 0.6: return ("Medium", pct)
    return ("Strong", pct)

def _build_result_payload(analysis: dict, matched: dict, pages: int, chars: int) -> dict:
    jd_sk = matched.get("jd_skills") or []
    rs_sk = analysis.get("skills") or matched.get("resume_skills") or []
    overlap = sorted([s for s in rs_sk if s in set(jd_sk)])

    ms_label, ms_pct = _bucket(matched.get("match_score", 0.0))
    ss_label, ss_pct = _bucket(matched.get("semantic_similarity", 0.0))
    so_label, so_pct = _bucket(matched.get("skill_overlap", 0.0))

    return {
        "resume_id": analysis.get("resume_id"),
        "tokens": analysis.get("tokens", 0),
        "skills": rs_sk,
        "match_score": float(matched.get("match_score", 0.0)),
        "semantic_similarity": float(matched.get("semantic_similarity", 0.0)),
        "skill_overlap": float(matched.get("skill_overlap", 0.0)),
        "ms": {"label": ms_label, "pct": ms_pct},
        "ss": {"label": ss_label, "pct": ss_pct},
        "so": {"label": so_label, "pct": so_pct},
        "jd_skills": jd_sk,
        "resume_skills": rs_sk,
        "overlap_skills": overlap,
        "missing_skills": matched.get("missing_skills", []),
        "recommendations": matched.get("recommendations", []),
        "parsed_metrics": matched.get("parsed_metrics", []),
        "improvements": matched.get("improvements", []),
        "pages": pages, "chars": chars, "runtime_ms": matched.get("runtime_ms", 0),
    }

def _abs_url(request: Request, path: str) -> str:
    return f"{request.url.scheme}://{request.url.netloc}{path}"

def _url_with_query(base_path: str, page: int, page_size: int) -> str:
    return f"{base_path}?page={page}&page_size={page_size}"

def track(request: Request, event: str, props: Optional[dict]=None) -> None:
    try:
        if not cfg.posthog_key: return
        uid = request.session.get("user_id") if hasattr(request, "session") else None
        ident = str(uid) if uid else (request.client.host if request.client else "0.0.0.0")
        posthog.capture(ident, event, properties=props or {})
    except Exception:
        pass

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    # capture utm
    utm = {k:v for k in ("utm","utm_source","utm_medium","utm_campaign","utm_term","utm_content")
           if (v:=request.query_params.get(k))}
    if utm and hasattr(request, "session"): request.session["utm"] = utm
    track(request, "pageview", {"path": "/"})
    return templates.TemplateResponse("landing.html", {"request": request})

@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    track(request, "pageview", {"path": "/analyze"})
    return templates.TemplateResponse("index.html",
        {"request": request, "result": None, "error": None, "read_only": False, "share_url": None})

@router.get("/demo", response_class=HTMLResponse)
async def demo(request: Request, db: Session = Depends(get_db)):
    track(request, "analyze_clicked", {"demo": True})
    demo_resume = """
Built a FastAPI backend with PostgreSQL and Docker; added Redis cache and GitHub Actions CI.
Implemented REST APIs (auth, pagination). Deployed to AWS via Terraform. Wrote tests with pytest."""
    demo_jd = "Backend engineer with Python/FastAPI, PostgreSQL, Redis, Docker, CI/CD and AWS/Terraform."

    resume = Resume(filename="demo.txt", text=_clean_text(demo_resume)); db.add(resume); db.commit(); db.refresh(resume)
    job = Job(title="Demo JD", description=_clean_text(demo_jd)); db.add(job); db.commit(); db.refresh(job)

    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)
    result = _build_result_payload(analysis, matched, pages=1, chars=len(demo_resume))

    if hasattr(request, "session") and (utm:=request.session.get("utm")): result["utm"] = utm
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    rpt = create_report(db, payload=result, resume_id=resume.id, job_id=job.id, match_id=None, user_id=user_id)

    share_url = _abs_url(request, f"/r/{rpt.slug}")
    track(request, "analyze_success", {"demo": True, "match_score": result.get("match_score")})
    return templates.TemplateResponse("index.html",
        {"request": request, "result": result, "error": None, "read_only": False, "share_url": share_url})

@router.post("/ui-match", response_class=HTMLResponse)
async def ui_match(request: Request, file: UploadFile = File(...), job_description: str = Form(...), db: Session = Depends(get_db)):
    track(request, "analyze_clicked", {"demo": False})
    if file.content_type != "application/pdf":
        track(request, "analyze_fail", {"reason": "not_pdf"})
        return templates.TemplateResponse("index.html",
            {"request": request, "result": None, "error": "Please upload a PDF file.", "read_only": False, "share_url": None})

    text, pages, chars = extract_pdf_text(file.file)
    text = _clean_text(text); jd_text = _clean_text(job_description)
    if len(text) < 40 or len(jd_text) < 40:
        track(request, "analyze_fail", {"reason": "short_input"})
        return templates.TemplateResponse("index.html",
            {"request": request, "result": None, "error": "Please provide a valid PDF and a sufficiently detailed JD.", "read_only": False, "share_url": None})

    resume = Resume(filename=file.filename, text=text); db.add(resume); db.commit(); db.refresh(resume)
    job = Job(title="Job Description", description=jd_text); db.add(job); db.commit(); db.refresh(job)

    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)
    result = _build_result_payload(analysis, matched, pages=pages, chars=chars)

    if hasattr(request, "session") and (utm:=request.session.get("utm")): result["utm"] = utm
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    rpt = create_report(db, payload=result, resume_id=resume.id, job_id=job.id, match_id=None, user_id=user_id)

    share_url = _abs_url(request, f"/r/{rpt.slug}")
    track(request, "analyze_success", {"demo": False, "pages": pages, "chars": chars, "match_score": result.get("match_score")})
    return templates.TemplateResponse("index.html",
        {"request": request, "result": result, "error": None, "read_only": False, "share_url": share_url})

@router.get("/r/{slug}.pdf")
async def public_report_pdf(slug: str, request: Request, db: Session = Depends(get_db)):
    rpt = get_report(db, slug)
    if not rpt: raise HTTPException(status_code=404, detail="Report not found")
    buf = BytesIO(); generate_report_pdf(buf, rpt.payload)
    headers = {"Content-Disposition": f'inline; filename="devmatch-{slug}.pdf"'}
    track(request, "download_pdf", {"slug": slug})
    return StreamingResponse(buf, headers=headers, media_type="application/pdf")

@router.get("/r/{slug}", response_class=HTMLResponse)
async def public_report(slug: str, request: Request, db: Session = Depends(get_db)):
    rpt = get_report(db, slug)
    if not rpt: raise HTTPException(status_code=404, detail="Report not found")
    share_url = _abs_url(request, f"/r/{slug}")
    og = {"title": f"DevMatch report • Match {rpt.payload.get('match_score', 0):.2f}",
          "description": "Resume ↔ JD alignment with skills, coverage, and suggestions.",
          "url": share_url}
    track(request, "share_view", {"slug": slug})
    return templates.TemplateResponse("index.html",
        {"request": request, "result": rpt.payload, "error": None, "read_only": True, "share_url": share_url, "og": og})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), page: int = 1, page_size: int = 20):
    uid = request.session.get("user_id") if hasattr(request, "session") else None
    if not uid: return RedirectResponse(url="/?error=login_required")
    user: Optional[User] = db.get(User, uid)
    if not user:
        request.session.clear(); return RedirectResponse(url="/?error=login_required")

    page = max(1, int(page or 1)); page_size = max(5, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    total = db.query(func.count(Report.id)).filter(Report.user_id == uid).scalar() or 0
    pages = max(1, (total + page_size - 1) // page_size)
    reports = (db.query(Report)
                 .filter(Report.user_id == uid)
                 .order_by(Report.created_at.desc().nullslast())
                 .offset(offset).limit(page_size).all())

    cards = [{"slug": r.slug,
              "created_at": getattr(r, "created_at", None),
              "score": (r.payload or {}).get("match_score", 0.0),
              "title": (r.payload or {}).get("job_title") or "Job Match",
              "share_url": _abs_url(request, f"/r/{r.slug}")} for r in reports]

    pagination = {"page": page, "page_size": page_size, "total": total, "pages": pages,
                  "has_prev": page > 1, "has_next": page < pages,
                  "prev_url": _url_with_query("/dashboard", page-1, page_size) if page>1 else None,
                  "next_url": _url_with_query("/dashboard", page+1, page_size) if page<pages else None}

    return templates.TemplateResponse("dashboard.html",
        {"request": request, "user": user, "cards": cards, "pagination": pagination})

