# app/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    text = Column(String, nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    similarity = Column(Float, default=0.0)
    skill_overlap = Column(Float, default=0.0)
    match_score = Column(Float, default=0.0)
    missing_skills = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    runtime_ms = Column(Integer, default=0)

    resume = relationship("Resume")
    job = relationship("Job")

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    tokens = Column(Integer, default=0, nullable=False)
    skills = Column(JSON, default=list, nullable=False)

    resume = relationship("Resume")

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    slug = Column(String(16), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)

    payload = Column(JSON, nullable=False, default={})

