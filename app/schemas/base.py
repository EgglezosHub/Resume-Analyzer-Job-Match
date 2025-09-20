from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ResumeCreate(BaseModel):
	text: str
	filename: Optional[str] = None


class JobCreate(BaseModel):
	title: str
	description: str


class AnalyzeResponse(BaseModel):
	resume_id: int
	skills: list[str]
	sections: dict[str, str]
	tokens: int
	runtime_ms: int


class MatchRequest(BaseModel):
	resume_id: int
	job_id: int


class MatchResponse(BaseModel):
	resume_id: int
	job_id: int
	match_score: float
	semantic_similarity: float
	skill_overlap: float
	missing_skills: list[str]
	recommendations: list[str]
	runtime_ms: int
