from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Resume
from app.schemas.base import ResumeCreate
from app.utils.pdf import extract_pdf_text


router = APIRouter()


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@router.post("", summary="Create resume from raw text")
async def create_resume(payload: ResumeCreate, db: Session = Depends(get_db)):
	if not payload.text or len(payload.text) < 20:
		raise HTTPException(status_code=400, detail="Resume text too short")
	r = Resume(filename=payload.filename, text=payload.text)
	db.add(r); db.commit(); db.refresh(r)
	return {"resume_id": r.id}


@router.post("/upload", summary="Upload PDF resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
	if file.content_type not in {"application/pdf"}:
		raise HTTPException(status_code=415, detail="Only PDF supported")
	text, pages, chars = extract_pdf_text(file.file)
	if len(text) < 20:
		raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF")
	r = Resume(filename=file.filename, text=text)
	db.add(r); db.commit(); db.refresh(r)
	return {"resume_id": r.id, "pages": pages, "extracted_chars": chars}
