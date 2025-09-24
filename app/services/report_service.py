# app/services/report_service.py
from __future__ import annotations
import secrets
import string
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Report

# short slug generator
_ALPH = string.ascii_lowercase + string.digits
def _slug(n: int = 10) -> str:
    return "".join(secrets.choice(_ALPH) for _ in range(n))

def create_report(
    db: Session,
    payload: dict,
    resume_id: int,
    job_id: int,
    match_id: Optional[int] = None,   # kept for API compatibility (unused)
    user_id: Optional[int] = None,
) -> Report:
    slug = _slug(12)
    rpt = Report(
        slug=slug,
        payload=payload or {},
        resume_id=resume_id,
        job_id=job_id,
        user_id=user_id,
    )
    db.add(rpt); db.commit(); db.refresh(rpt)
    return rpt

def get_report(db: Session, slug: str) -> Optional[Report]:
    return db.query(Report).filter(Report.slug == slug).first()

