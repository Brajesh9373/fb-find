"""Cosine similarity helpers for face embeddings."""

from __future__ import annotations

import numpy as np

from app import config


def is_valid_embedding(emb: np.ndarray) -> bool:
    """Check if embedding is valid (not all zeros, not NaN).
    
    Invalid embeddings will always produce 0% similarity.
    """
    if emb is None:
        return False
    emb = np.asarray(emb, dtype=np.float64)
    if np.any(np.isnan(emb)):
        return False
    norm = np.linalg.norm(emb)
    return norm > 0.01  # Not all zeros


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised (or not) vectors.

    Returns a value in ``[-1, 1]`` (practically ``[0, 1]`` for face
    embeddings from the same model).
    
    Returns 0.0 if either embedding is invalid (zeros/NaN).
    """
    # Validate embeddings first
    if not is_valid_embedding(a) or not is_valid_embedding(b):
        return 0.0
    
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_PROBABLE = "PROBABLE"
CONFIDENCE_UNMATCHED = "UNMATCHED"


def get_confidence_tier(
    similarity: float,
    high_threshold: float | None = None,
    probable_threshold: float | None = None,
) -> str:
    """Classify cosine similarity into confidence bands: HIGH, PROBABLE, or UNMATCHED."""
    high = high_threshold if high_threshold is not None else config.FACE_MATCH_THRESHOLD
    probable = (
        probable_threshold
        if probable_threshold is not None
        else getattr(config, "PROBABLE_MATCH_THRESHOLD", 0.52)
    )
    if similarity >= high:
        return CONFIDENCE_HIGH
    elif similarity >= probable:
        return CONFIDENCE_PROBABLE
    return CONFIDENCE_UNMATCHED


def is_match(
    similarity: float, threshold: float | None = None
) -> bool:
    """Check if similarity meets the given or default threshold."""
    threshold = threshold if threshold is not None else config.FACE_MATCH_THRESHOLD
    return similarity >= threshold


def is_probable_match(
    similarity: float, probable_threshold: float | None = None
) -> bool:
    """Check if similarity falls within the probable match confidence band."""
    probable = (
        probable_threshold
        if probable_threshold is not None
        else getattr(config, "PROBABLE_MATCH_THRESHOLD", 0.52)
    )
    return similarity >= probable
