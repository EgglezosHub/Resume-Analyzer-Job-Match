from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None)):
	if not x_api_key or x_api_key != settings.api_key:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
