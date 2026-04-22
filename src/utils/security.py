import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256


SECRET_KEY = os.getenv("SECRET_KEY", "cn-bert-rumor-analysis-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))
PBKDF2_PREFIX = "$pbkdf2-sha256$"
BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def get_password_hash(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def needs_password_upgrade(stored_password: str | None) -> bool:
    if not stored_password:
        return False
    return not stored_password.startswith(PBKDF2_PREFIX)


def verify_password(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False

    try:
        if stored_password.startswith(PBKDF2_PREFIX):
            return pbkdf2_sha256.verify(plain_password, stored_password)

        if stored_password.startswith(BCRYPT_PREFIXES):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_password.encode("utf-8"),
            )
    except Exception:
        return False

    return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
