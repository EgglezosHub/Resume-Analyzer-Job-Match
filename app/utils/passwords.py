from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return _pwd.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    if not raw or not hashed:
        return False
    return _pwd.verify(raw, hashed)
