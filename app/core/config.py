from pydantic import BaseModel
from pydantic import Field
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
	api_key: str = os.getenv("API_KEY", "dev-secret-key")
	api_title: str = os.getenv("API_TITLE", "Resume Match API")
	api_version: str = os.getenv("API_VERSION", "0.1.0")
	database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
	sentence_model: str = os.getenv("SENTENCE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


settings = Settings()
