"""Thin convenience layer — embedding is already produced by FaceDetector.

This module exists for pipeline clarity (Detection → Embedding → Similarity)
and for callers that already have a ``FaceInfo`` and just want a normalised
vector.
"""

from __future__ import annotations

import numpy as np

from app.face.detector import FaceInfo


def get_normalized_embedding(face: FaceInfo) -> np.ndarray:
    """Return L2-normalised embedding for a single face."""
    return face.normalized_embedding


def normalize(embedding: np.ndarray) -> np.ndarray:
    """L2-normalise any embedding vector."""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm
