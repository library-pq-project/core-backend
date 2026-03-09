import hashlib
from datetime import datetime, timezone

from slugify import slugify


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_slug(value: str) -> str:
    return slugify(value)


def make_fingerprint(parts: list[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
