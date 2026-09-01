"""Normalize SerpApi Google Lens JSON into a uniform candidate list."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def parse_lens_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a flat candidate list from SerpApi Google Lens response.

    SerpApi may return matches under several keys depending on engine version:
    ``visual_matches``, ``exact_matches``, ``related_searches`` etc.
    We consolidate ``visual_matches`` (primary) and ``exact_matches``.
    """
    candidates: list[dict[str, Any]] = []

    # Google Lens via SerpApi typically returns:
    #   data["visual_matches"] = [{title, link, source, thumbnail}, ...]
    for section in ("visual_matches", "exact_matches", "knowledge_graph"):
        raw = data.get(section)
        if raw is None:
            continue
        # knowledge_graph is a dict, skip
        if isinstance(raw, dict):
            continue
        if not isinstance(raw, list):
            continue
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            link = item.get("link") or item.get("url") or item.get("source_link") or ""
            if not link:
                continue
            title = item.get("title") or item.get("snippet") or item.get("source") or ""
            source = item.get("source") or _domain(link)
            thumbnail = item.get("thumbnail") or item.get("image") or item.get("thumbnail_url") or ""
            candidates.append(
                {
                    "title": title.strip(),
                    "url": link.strip(),
                    "source": source.strip(),
                    "thumbnail": thumbnail.strip() if isinstance(thumbnail, str) else "",
                    "image_url": item.get("image") or thumbnail or "",
                    "position": item.get("position", idx + 1),
                    # keep raw for debugging
                    "_raw": item,
                }
            )

    # Deduplicate by URL while preserving order
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for c in candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            deduped.append(c)

    # Re-assign position
    for i, c in enumerate(deduped):
        c["position"] = i + 1

    return deduped
