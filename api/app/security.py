# api/app/security.py
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "CAMBIA_ESTE_SECRETO_LARGO_Y_RANDOM")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "60"))

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _bcrypt_safe_password(p: str) -> str:
    """
    bcrypt solo acepta hasta 72 BYTES.
    - quitamos espacios extremos
    - recortamos a 72 bytes (UTF-8) si es necesario
    """
    p = (p or "").strip()
    b = p.encode("utf-8")
    if len(b) <= 72:
        return p
    return b[:72].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    password = (password or "")[:72]
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    password = (password or "")[:72]
    return pwd.verify(password, hashed)


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    payload = {
        "sub": subject,   # email
        "role": role,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        raise ValueError("Invalid token") from e
