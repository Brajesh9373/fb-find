"""Candidate page / image retrieval + face extraction.

Gracefully handles: inaccessible pages, login walls, missing images, no face.
Enhanced with og:image extraction and multi-face candidate comparison.
"""

from __future__ import annotations

import concurrent.futures
import io
import logging
import os
import re
from typing import Any
from urllib.parse import urljoin

import numpy as np
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


def fetch_og_image_url(page_url: str, timeout: int = 6) -> str | None:
    """Fetch webpage HTML and extract high-resolution og:image or twitter:image."""
    if not (page_url.startswith("http://") or page_url.startswith("https://")):
        return None
    try:
        resp = requests.get(
            page_url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        text = resp.text[:100000]  # inspect first 100KB (head section)

        patterns = [
            r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']',
            r'<meta\s+content=["\'](.*?)["\']\s+property=["\']og:image["\']',
            r'<meta\s+name=["\']twitter:image["\']\s+content=["\'](.*?)["\']',
            r'<meta\s+content=["\'](.*?)["\']\s+name=["\']twitter:image["\']',
            r'<meta\s+property=["\']og:image:secure_url["\']\s+content=["\'](.*?)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                img_url = m.group(1).strip()
                if img_url:
                    return urljoin(page_url, img_url)
    except Exception as exc:
        logger.debug("Failed to extract og:image from %s: %s", page_url, exc)
    return None


def try_candidate_images(
    candidate: dict[str, Any],
    timeout: int = 15,
) -> list[bytes]:
    """Attempt to fetch image bytes for a candidate.

    Tries ``thumbnail`` first (direct image), then ``image_url``, then ``og:image``.
    Thumbnail is prioritized because it's the actual image, not a page URL.
    Returns list of successfully fetched byte payloads.
    """
    urls: list[str] = []
    # Try thumbnail FIRST - it's usually the direct image URL
    for key in ("thumbnail", "image_url"):
        u = candidate.get(key)
        if u and isinstance(u, str) and u.startswith("http"):
            urls.append(u)

    # Extract high-res og:image from candidate page if enabled
    if getattr(config, "ENABLE_OG_IMAGE_EXTRACTION", True):
        page_url = candidate.get("url")
        if page_url and (page_url.startswith("http://") or page_url.startswith("https://")):
            og_img = fetch_og_image_url(page_url, timeout=min(6, timeout))
            if og_img and og_img not in urls:
                # Insert og_image before thumbnail for higher quality face detection
                urls.insert(1 if len(urls) > 0 else 0, og_img)

    payloads: list[bytes] = []
    seen: set[str] = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        if u.startswith("http://") or u.startswith("https://"):
            data = fetch_image_bytes(u, timeout=timeout)
        elif os.path.exists(u):
            try:
                with open(u, "rb") as f:
                    data = f.read()
            except Exception:
                data = None
        else:
            data = None

        if data:
            payloads.append(data)
    return payloads


def extract_face_from_candidate(
    candidate: dict[str, Any],
    detector: FaceDetector | None = None,
    query_emb: np.ndarray | None = None,
) -> tuple[FaceInfo | None, bytes | None]:
    """Try to find a face in any image belonging to *candidate*.

    If *query_emb* is provided, scans ALL detected faces in each candidate image
    and returns the face with highest cosine similarity (multi-face/group support).
    Otherwise returns the largest detected face.

    Returns ``(FaceInfo | None, image_bytes | None)``.
    """
    if detector is None:
        detector = FaceDetector()

    from app.face.similarity import cosine_similarity

    payloads = try_candidate_images(candidate)
    best_face: FaceInfo | None = None
    best_data: bytes | None = None
    best_similarity: float = -1.0

    for data in payloads:
        try:
            if query_emb is not None:
                # Multi-face scan on candidate image
                faces = detector.detect_bytes(data)
                for f in faces:
                    sim = cosine_similarity(query_emb, f.embedding)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_face = f
                        best_data = data
            else:
                face = detector.get_largest_face_bytes(data)
                if face is not None:
                    return face, data
        except Exception as exc:
            logger.debug("Face detection failed on candidate image: %s", exc)
            continue

    if query_emb is not None and best_face is not None:
        return best_face, best_data

    return None, None


def verify_single_candidate(
    cand: dict[str, Any],
    detector: FaceDetector,
    query_emb: np.ndarray,
    high_threshold: float,
    probable_threshold: float,
) -> dict[str, Any]:
    """Verify a single candidate and return evaluation details."""
    from app.face.similarity import cosine_similarity, get_confidence_tier

    face, img_bytes = extract_face_from_candidate(
        cand, detector=detector, query_emb=query_emb
    )
    if face is None:
        return {
            "candidate": cand,
            "face": None,
            "img_bytes": None,
            "similarity": 0.0,
            "confidence_tier": "UNMATCHED",
            "has_face": False,
        }
    sim = cosine_similarity(query_emb, face.embedding)
    tier = get_confidence_tier(
        sim,
        high_threshold=high_threshold,
        probable_threshold=probable_threshold,
    )
    return {
        "candidate": cand,
        "face": face,
        "img_bytes": img_bytes,
        "similarity": sim,
        "confidence_tier": tier,
        "has_face": True,
    }


def verify_candidates_concurrent(
    candidates: list[dict[str, Any]],
    detector: FaceDetector,
    query_emb: np.ndarray,
    high_threshold: float,
    probable_threshold: float,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    """Download and verify multiple candidates in parallel."""
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cand = {
            executor.submit(
                verify_single_candidate,
                c,
                detector,
                query_emb,
                high_threshold,
                probable_threshold,
            ): c
            for c in candidates
        }
        for future in concurrent.futures.as_completed(future_to_cand):
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                logger.debug("Candidate verification error: %s", exc)
    # Sort results by similarity descending
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results
