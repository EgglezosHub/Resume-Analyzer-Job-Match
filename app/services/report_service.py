from __future__ import annotations
from sqlalchemy.orm import Session

from app.db.models import Report, Match
from app.utils.slug import short_slug

def create_report(db: Session, payload: dict, resume_id: int | None, job_id: int | None, match_id: int | None) -> Report:
    # generate unique slug
    for _ in range(5):
        slug = short_slug(6)
        if not db.query(Report).filter_by(slug=slug).first():
            break
    rpt = Report(slug=slug, payload=payload, resume_id=resume_id, job_id=job_id, match_id=match_id)
    db.add(rpt); db.commit(); db.refresh(rpt)
    return rpt

def get_report(db: Session, slug: str) -> Report | None:
    return db.query(Report).filter_by(slug=slug).first()
