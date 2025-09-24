# app/main.py
from __future__ import annotations
import sentry_sdk
from fastapi import FastAPI, Depends
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.routes import ui, auth

# init DB
Base.metadata.create_all(bind=engine)

# observability
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

app = FastAPI(title=settings.api_title, version=settings.api_version)

# sessions (for OAuth + rate limits)
app.add_middleware(SessionMiddleware, secret_key=settings.oauth_secret, https_only=False)

# routers
app.include_router(ui.router, tags=["ui"])
app.include_router(auth.router, tags=["auth"])

@app.get("/healthz")
def health():
    return {"ok": True, "model": settings.sentence_model}

