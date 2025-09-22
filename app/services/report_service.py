# app/services/report_service.py
from sqlalchemy.orm import Session
from app.db.models import Report
from app.utils.slug import short_slug

def create_report(db: Session, payload: dict, resume_id=None, job_id=None, match_id=None) -> Report:
    for _ in range(6):
        slug = short_slug(10)
        if not db.query(Report).filter_by(slug=slug).first():
            break
    rpt = Report(slug=slug, payload=payload, resume_id=resume_id, job_id=job_id, match_id=match_id)
    db.add(rpt); db.commit(); db.refresh(rpt)
    print(f"[REPORT] Created slug={rpt.slug} id={rpt.id}")
    return rpt

def get_report(db: Session, slug: str) -> Report | None:
    rpt = db.query(Report).filter_by(slug=slug).first()
    print(f"[REPORT] Fetch slug={slug} -> {bool(rpt)}")
    return rpt

