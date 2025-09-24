from fastapi import Header, HTTPException, status
from app.core.config import settings
from passlib.context import CryptContext



async def verify_api_key(x_api_key: str | None = Header(default=None)):
	if not x_api_key or x_api_key != settings.api_key:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return _pwd.hash(pw)

def verify_password(pw: str, h: str) -> bool:
    if not pw or not h:
        return False
    return _pwd.verify(pw, h)

