from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Resume, Job
from app.schemas.base import MatchRequest, MatchResponse
from app.services.match_service import match_resume_job


router = APIRouter()


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@router.post("", response_model=MatchResponse)
async def match(req: MatchRequest, db: Session = Depends(get_db)):
	r = db.get(Resume, req.resume_id)
	if not r:
		raise HTTPException(status_code=404, detail="Resume not found")
	j = db.get(Job, req.job_id)
	if not j:
		raise HTTPException(status_code=404, detail="Job not found")
	return match_resume_job(db, r, j)
