# app/db/models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.types import JSON  # portable JSON type across dialects
from app.db.session import Base
from sqlalchemy.orm import relationship



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


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(16), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # store references for traceability (optional)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)

    # frozen result payload you render publicly
    payload = Column(JSON, nullable=False, default={})

