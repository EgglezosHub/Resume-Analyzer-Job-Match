# app/main.py
from fastapi import FastAPI, Depends
from app.core.config import settings
from app.core.security import verify_api_key

from app.db.session import engine
from app.db import models  # ensures models register on Base BEFORE create_all
models.Base.metadata.create_all(bind=engine)

from app.routes import health, resumes, jobs, analyze, match, ui

app = FastAPI(title=settings.api_title, version=settings.api_version)

# Public UI
app.include_router(ui.router, tags=["ui"])

# Public health
app.include_router(health.router, prefix="", tags=["health"])

# Protected JSON APIs
app.include_router(resumes.router, prefix="/resumes", tags=["resumes"], dependencies=[Depends(verify_api_key)])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])
app.include_router(analyze.router, prefix="/analyze", tags=["analyze"], dependencies=[Depends(verify_api_key)])
app.include_router(match.router, prefix="/match", tags=["match"], dependencies=[Depends(verify_api_key)])

