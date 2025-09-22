# app/services/analyze_service.py
from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import Resume, Analysis
from app.nlp.skills_extractor import extract_skills
from app.utils.timing import timer

def analyze_resume(db: Session, resume: Resume) -> dict:
    with timer() as elapsed:
        text = resume.text or ""
        skills = sorted(list(set(extract_skills(text))))
        tokens = len(text.split())
        runtime = elapsed()

    a = Analysis(resume_id=resume.id, tokens=tokens, skills=skills)
    db.add(a); db.commit(); db.refresh(a)

    return {"resume_id": resume.id, "tokens": tokens, "skills": skills, "runtime_ms": runtime}

