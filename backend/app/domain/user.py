import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.exceptions import DomainExceptionError

PASSWORD_MIN_LENGTH = 8
_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    created_at: datetime


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise DomainExceptionError("Password must be at least 8 characters")
    if not _PASSWORD_PATTERN.match(password):
        raise DomainExceptionError("Password must contain at least one letter and one number")
