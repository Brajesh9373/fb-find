"""Rank candidates — every social platform is treated equally.

Social results still sort above non-social ones, but no platform is
preferred over another: ties (including ties between different social
platforms) break by the search engine's original position, so the final
link is decided by discovery order and face-verification score — never
by which social network it came from.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app import config


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


# Membership set for social platforms. Every member scores the same —
# there is intentionally no per-platform weight (Instagram first was
# removed so all social results compete on equal footing).
SOCIAL_DOMAINS: set[str] = {d.lower() for d in list(config.SOCIAL_DOMAINS)} | {
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "threads.net",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
}


def _social_score(url: str) -> int:
    """1 for any social platform, 0 otherwise — platforms are never ranked against each other."""
    d = _domain(url)
    for domain in SOCIAL_DOMAINS:
        if domain in d:
            return 1
    return 0


def rank_candidates(
    candidates: list[dict], top_n: int | None = None
) -> list[dict]:
    """Sort so exact matches come first, then socials, then discovery order.

    Priority: exact image matches (is_exact) → social platforms (all
    tied) → the search engine's original position. Non-social,
    non-exact results sort last. Returns new list (does not mutate input).
    """
    ranked = sorted(
        candidates,
        key=lambda c: (
            1 if c.get("is_exact") else 0,
            _social_score(c.get("url", "")),
            -c.get("position", 999),
        ),
        reverse=True,
    )
    ranked = sorted(
        candidates,
        key=lambda c: (
            1 if c.get("is_exact") else 0,
            _social_score(c.get("url", "")),
            -c.get("position", 999),
        ),
        reverse=True,
    )
    if top_n is not None:
        return ranked[:top_n]
    return ranked


def is_social(url: str) -> bool:
    return _social_score(url) > 0
