# app/routes/ui.py
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
    # tolerate unknown chars/newlines; collapse weird whitespace
    return (s or "").encode("utf-8", "ignore").decode("utf-8", "ignore").replace("\r", "")

@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": None})

@router.post("/ui-match", response_class=HTMLResponse)
async def ui_match(
    request: Request,
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
):
    # Basic file/type checks
    if file.content_type != "application/pdf":
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": "Please upload a PDF file."
        })

    # Extract text from PDF (ignore weird chars)
    text, pages, chars = extract_pdf_text(file.file)
    text = _clean_text(text)
    if len(text) < 20:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": "Could not extract enough text from the PDF."
        })

    # Clean JD text
    jd_text = _clean_text(job_description)
    if len(jd_text) < 20:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "error": "Job description is too short."
        })

    # Persist minimal Resume & Job
    resume = Resume(filename=file.filename, text=text)
    db.add(resume); db.commit(); db.refresh(resume)

    job = Job(title="Job Description", description=jd_text)
    db.add(job); db.commit(); db.refresh(job)

    # Analyze + Match using your existing services
    analysis = analyze_resume(db, resume)
    matched = match_resume_job(db, resume, job)

    # Merge a friendly payload for the template
    result = {
        "resume_id": analysis["resume_id"],
        "tokens": analysis["tokens"],
        "skills": analysis["skills"],
        "semantic_similarity": matched["semantic_similarity"],
        "skill_overlap": matched["skill_overlap"],
        "match_score": matched["match_score"],
        "missing_skills": matched["missing_skills"],
        "recommendations": matched["recommendations"],
        "runtime_ms": matched["runtime_ms"],
        "pages": pages,
        "chars": chars,
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": result,
        "error": None
    })
