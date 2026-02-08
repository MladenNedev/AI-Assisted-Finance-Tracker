import re

from app.core.exceptions import DomainExceptionError

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_category_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise DomainExceptionError("Category name cannot be empty")
    if len(normalized) > 100:
        raise DomainExceptionError("Category name must be 100 characters or fewer")
    return normalized


def normalize_category_color(color: str | None) -> str | None:
    if color is None:
        return None
    normalized = color.strip()
    if not normalized:
        return None
    if not _HEX_COLOR_PATTERN.match(normalized):
        raise DomainExceptionError("Category color must be a hex value like #1A2B3C")
    return normalized.upper()


def normalize_category_icon(icon: str | None) -> str | None:
    if icon is None:
        return None
    normalized = icon.strip()
    if not normalized:
        return None
    if len(normalized) > 50:
        raise DomainExceptionError("Category icon must be 50 characters or fewer")
    return normalized
