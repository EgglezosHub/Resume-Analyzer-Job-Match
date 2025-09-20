from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Job
from app.schemas.base import JobCreate


router = APIRouter()


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@router.post("", summary="Create job posting")
async def create_job(payload: JobCreate, db: Session = Depends(get_db)):
	if len(payload.description) < 20:
		raise HTTPException(status_code=400, detail="Job description too short")
	j = Job(title=payload.title, description=payload.description)
	db.add(j); db.commit(); db.refresh(j)
	return {"job_id": j.id}
