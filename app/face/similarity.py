"""Cosine similarity helpers for face embeddings."""

from __future__ import annotations

import numpy as np

from app import config


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised (or not) vectors.

    Returns a value in ``[-1, 1]`` (practically ``[0, 1]`` for face
    embeddings from the same model).
    """
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def is_match(
    similarity: float, threshold: float | None = None
) -> bool:
    threshold = threshold if threshold is not None else config.FACE_MATCH_THRESHOLD
    return similarity >= threshold
