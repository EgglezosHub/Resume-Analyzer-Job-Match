# app/services/analyze_service.py
from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import Resume
from app.nlp.skills_extractor import extract_skills
from app.utils.timing import timer

def analyze_resume(db: Session, resume: Resume) -> dict:
    # No Analysis table; return computed metrics only.
    with timer() as elapsed:
        text = resume.text or ""
        skills = sorted(set(extract_skills(text)))
        tokens = len(text.split())
        runtime = elapsed()

    return {
        "resume_id": resume.id,
        "tokens": tokens,
        "skills": skills,
        "runtime_ms": runtime,
    }

