from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Resume
from app.schemas.base import AnalyzeResponse
from app.services.analyze_service import analyze_resume


router = APIRouter()


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@router.post("", response_model=AnalyzeResponse)
async def analyze(resume_id: int, db: Session = Depends(get_db)):
	r = db.get(Resume, resume_id)
	if not r:
		raise HTTPException(status_code=404, detail="Resume not found")
	return analyze_resume(db, r)
