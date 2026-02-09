import hashlib
import hmac
import secrets

from app.core.config import get_settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
