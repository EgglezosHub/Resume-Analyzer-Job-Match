# app/core/config.py
from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API
    api_key: str = "dev-secret-key"
    api_title: str = "Resume Match API"
    api_version: str = "0.1.0"

    # DB
    database_url: str = "sqlite:////app/dev.db"

    # NLP
    # IMPORTANT: maps to env var SENTENCE_MODEL
    sentence_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Auth / Sessions
    oauth_secret: str = "change-me"           # env: OAUTH_SECRET
    github_client_id: Optional[str] = None    # env: GITHUB_CLIENT_ID
    github_client_secret: Optional[str] = None# env: GITHUB_CLIENT_SECRET
    enable_email_signup: bool = False         # env: ENABLE_EMAIL_SIGNUP

    # Rate limits
    anon_daily_limit: int = 3                 # env: ANON_DAILY_LIMIT
    free_daily_limit: int = 15                # env: FREE_DAILY_LIMIT
    premium_unlimited: bool = False           # env: PREMIUM_UNLIMITED
    redis_url: Optional[str] = None           # env: REDIS_URL

    # Observability
    sentry_dsn: Optional[str] = None          # env: SENTRY_DSN
    posthog_key: Optional[str] = None         # env: POSTHOG_KEY
    posthog_host: str = "https://app.posthog.com"  # env: POSTHOG_HOST

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
    )

settings = Settings()

