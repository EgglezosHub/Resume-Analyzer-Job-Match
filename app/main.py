# app/main.py
from fastapi import FastAPI, Depends
from app.core.config import settings
from app.core.security import verify_api_key
from app.db.session import Base, engine
from app.routes import health, resumes, jobs, analyze, match
from app.routes import ui  # <-- add this

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.api_title, version=settings.api_version)

# Public UI (no API key required)
app.include_router(ui.router, tags=["ui"])

# Protected JSON APIs
app.include_router(health.router, prefix="", tags=["health"])  # this one is fine public too
app.include_router(resumes.router, prefix="/resumes", tags=["resumes"], dependencies=[Depends(verify_api_key)])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])
app.include_router(analyze.router, prefix="/analyze", tags=["analyze"], dependencies=[Depends(verify_api_key)])
app.include_router(match.router, prefix="/match", tags=["match"], dependencies=[Depends(verify_api_key)])
