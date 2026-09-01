"""Rank candidates by social-media priority + original position."""

from __future__ import annotations

from urllib.parse import urlparse

from app import config


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


PRIORITY_MAP: dict[str, int] = {
    domain: len(config.SOCIAL_DOMAINS) - i
    for i, domain in enumerate(config.SOCIAL_DOMAINS)
}
# extras
PRIORITY_MAP.update(
    {
        "instagram.com": 100,
        "facebook.com": 90,
        "x.com": 80,
        "twitter.com": 80,
        "linkedin.com": 70,
        "threads.net": 60,
        "tiktok.com": 50,
        "youtube.com": 40,
        "pinterest.com": 30,
    }
)


def _social_score(url: str) -> int:
    d = _domain(url)
    for domain, score in PRIORITY_MAP.items():
        if domain in d:
            return score
    return 0


def rank_candidates(
    candidates: list[dict], top_n: int | None = None
) -> list[dict]:
    """Sort so social platforms appear first, then by original position.

    Returns new list (does not mutate input).
    """
    ranked = sorted(
        candidates,
        key=lambda c: (_social_score(c.get("url", "")), -c.get("position", 999)),
        reverse=True,
    )
    if top_n is not None:
        return ranked[:top_n]
    return ranked


def is_social(url: str) -> bool:
    return _social_score(url) > 0
