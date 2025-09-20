# app/db/models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.types import JSON  # portable JSON type across dialects
from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, nullable=False)
    skills = Column(JSON, nullable=True)       # list[str] or list[{name, weight}]
    sections = Column(JSON, nullable=True)     # dict[str, str]
    tokens = Column(Integer, nullable=True)
    runtime_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    similarity = Column(Float, nullable=True)
    skill_overlap = Column(Float, nullable=True)
    match_score = Column(Float, nullable=True)
    missing_skills = Column(JSON, nullable=True)      # list[str]
    recommendations = Column(JSON, nullable=True)     # list[str]
    runtime_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
