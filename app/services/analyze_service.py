from app.db.models import Resume, Analysis
from app.nlp.skills_extractor import extract_skills
from app.utils.timing import timer
from sqlalchemy.orm import Session


# Simple section splitter (demo):
SECTIONS = ["summary", "experience", "projects", "education", "skills"]


def split_sections(text: str) -> dict[str, str]:
	lower = text.lower()
	buckets = {k: "" for k in SECTIONS}
	current = "summary"
	for line in lower.splitlines():
		if any(h in line for h in SECTIONS):
			for h in SECTIONS:
				if h in line:
					current = h; break
		buckets[current] += line + "\n"
	return buckets


def analyze_resume(db: Session, resume: Resume) -> dict:
	with timer() as elapsed:
		skills = extract_skills(resume.text)
		sections = split_sections(resume.text)
		tokens = len(resume.text.split())
	analysis = Analysis(
		resume_id=resume.id,
		skills=skills,
		sections=sections,
		tokens=tokens,
		runtime_ms=elapsed(),
	)
	db.add(analysis); db.commit(); db.refresh(analysis)
	return {
		"resume_id": resume.id,
		"skills": skills,
		"sections": sections,
		"tokens": tokens,
		"runtime_ms": analysis.runtime_ms,
	}
