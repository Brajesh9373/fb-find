"""Canonical JSON representation for deterministic hashing."""

from __future__ import annotations

import json
from typing import Any


def canonicalize(data: dict[str, Any]) -> bytes:
    """Return canonical UTF-8 bytes for *data*.

    Rules that guarantee determinism:
    * keys sorted alphabetically
    * no whitespace outside string values (separators=(",", ":"))
    * UTF-8 encoding
    * ``ensure_ascii=False`` so unicode is preserved literally
    * ``None`` values are included (not stripped) unless caller removes them
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def build_canonical_payload(
    *,
    url: str,
    platform: str,
    title: str,
    image_url: str,
    similarity: float | None = None,
    description: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the dict that will be canonicalised and hashed.

    Only non-None optional fields are included.  ``similarity`` is rounded to
    4 decimal places so floating noise does not flip the hash.  Callers that
    need integer-percentage semantics can multiply before hashing — but the
    default pipeline stores the rounded raw score.
    """
    payload: dict[str, Any] = {
        "url": url.strip(),
        "platform": platform.strip(),
        "title": title.strip() if title else "",
        "image_url": (image_url or "").strip(),
    }
    if description is not None:
        payload["description"] = description.strip()
    if similarity is not None:
        payload["similarity"] = round(float(similarity), 4)
    if extra:
        for k, v in extra.items():
            if v is not None:
                payload[k] = v
    return payload
