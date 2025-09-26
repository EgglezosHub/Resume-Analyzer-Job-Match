# app/utils/passwords.py
from passlib.context import CryptContext

# Prefer Argon2, but also recognize older hashes if they exist.
_pwd = CryptContext(
    schemes=["argon2", "bcrypt_sha256", "bcrypt"],
    default="argon2",
    deprecated="auto",
)

def hash_password(raw: str) -> str:
    raw = (raw or "").strip()
    if len(raw) < 8:
        raise ValueError("Password must be at least 8 characters")
    # Cap absurdly long inputs (defense-in-depth)
    if len(raw) > 4096:
        raw = raw[:4096]
    return _pwd.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    raw = (raw or "").strip()
    return _pwd.verify(raw, hashed or "")

