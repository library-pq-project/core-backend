import hashlib
from datetime import UTC, datetime

from slugify import slugify


def now_utc() -> datetime:
    return datetime.now(UTC)


def generate_slug(value: str) -> str:
    return slugify(value)


def make_fingerprint(parts: list[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
