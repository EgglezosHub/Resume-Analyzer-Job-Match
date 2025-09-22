# app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# If DATABASE_URL is not set, default to a file-backed SQLite placed at repo root.
DEFAULT_SQLITE = "sqlite:///./dev.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

# Convert "sqlite:///./dev.db" to an **absolute** path so CWD changes don't create a 2nd DB
if DATABASE_URL.startswith("sqlite:///./"):
    # repo_root = .../resume-match-api
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    abs_db = os.path.abspath(os.path.join(repo_root, DATABASE_URL.replace("sqlite:///./", "")))
    DATABASE_URL = f"sqlite:///{abs_db}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# helpful startup log
print(f"[DB] Using {DATABASE_URL}")

