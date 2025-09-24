# app/db/session.py
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings as cfg

def _normalize_url(url: str | None) -> str:
    # Treat None or empty/whitespace as unset and fall back to SQLite in container
    if not url or not url.strip():
        return "sqlite:////app/dev.db"
    return url.strip()

DATABASE_URL = _normalize_url(getattr(cfg, "database_url", None))

# SQLite needs special connect args; Postgres does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# Optional: small startup log to help debugging
print(f"[DB] Using {DATABASE_URL}")

