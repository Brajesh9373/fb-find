"""Candidate page / image retrieval + face extraction.

Gracefully handles: inaccessible pages, login walls, missing images, no face.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import requests
from PIL import Image

from app import config
from app.face.detector import FaceDetector, FaceInfo

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_image_bytes(url: str, timeout: int = 15) -> bytes | None:
    """Download raw bytes for an image URL.  Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        # allow if content-type hints at image, but also accept generic
        data = resp.content
        if len(data) < 128:
            return None
        # quick validation: can PIL open it?
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            logger.debug("URL %s is not a valid image (content-type=%s)", url, ctype)
            return None
        return data
    except Exception as exc:
        logger.debug("Failed to fetch image %s: %s", url, exc)
        return None


def try_candidate_images(
    candidate: dict[str, Any],
    timeout: int = 15,
) -> list[bytes]:
    """Attempt to fetch image bytes for a candidate.

    Tries ``image_url`` first, then ``thumbnail``, in order.
    Returns list of successfully fetched byte payloads (0-2 entries).
    """
    urls: list[str] = []
    for key in ("image_url", "thumbnail"):
        u = candidate.get(key)
        if u and isinstance(u, str) and u.startswith("http"):
            urls.append(u)

    payloads: list[bytes] = []
    seen: set[str] = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        data = fetch_image_bytes(u, timeout=timeout)
        if data:
            payloads.append(data)
    return payloads


def extract_face_from_candidate(
    candidate: dict[str, Any],
    detector: FaceDetector | None = None,
) -> tuple[FaceInfo | None, bytes | None]:
    """Try to find a face in any image belonging to *candidate*.

    Returns ``(FaceInfo | None, image_bytes | None)``.
    """
    if detector is None:
        detector = FaceDetector()

    payloads = try_candidate_images(candidate)
    for data in payloads:
        try:
            face = detector.get_largest_face_bytes(data)
            if face is not None:
                return face, data
        except Exception as exc:
            logger.debug("Face detection failed on candidate image: %s", exc)
            continue
    return None, None
