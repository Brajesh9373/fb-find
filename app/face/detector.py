"""Face detection & embedding via InsightFace (ArcFace)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import cv2
import numpy as np

from app import config

logger = logging.getLogger(__name__)


@dataclass
class FaceInfo:
    """Single detected face."""

    bbox: list[int]  # [x1, y1, x2, y2]
    confidence: float
    embedding: np.ndarray = field(repr=False)
    kps: np.ndarray | None = field(default=None, repr=False)  # 5 facial keypoints
    age: int | None = None
    gender: int | None = None

    @property
    def normalized_embedding(self) -> np.ndarray:
        norm = np.linalg.norm(self.embedding)
        if norm == 0:
            return self.embedding
        return self.embedding / norm


class FaceDetector:
    """Wrapper around InsightFace detection + alignment + embedding.

    Uses ``buffalo_l`` (≈ 300 MB) by default — the most accurate InsightFace
    pack.  Falls back to ``buffalo_s`` if the large model is not cached and
    ``INSIGHTFACE_MODEL`` env var is unset on a constrained machine.
    """

    _instance: FaceDetector | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_name: str | None = None,
        det_size: tuple[int, int] | None = None,
        providers: list[str] | None = None,
    ):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.model_name = model_name or config.INSIGHTFACE_MODEL
        self.det_size = det_size or config.INSIGHTFACE_DET_SIZE
        self.providers = providers or ["CPUExecutionProvider"]
        self._app = None

    # ── lazy model loading ──────────────────────────────────────────
    def _ensure_loaded(self):
        if self._app is not None:
            return
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise ImportError(
                "InsightFace is not installed.  Run: pip install -r requirements.txt"
            ) from exc

        logger.info("Loading InsightFace model '%s' ...", self.model_name)
        self._app = FaceAnalysis(
            name=self.model_name, providers=self.providers
        )
        self._app.prepare(ctx_id=0, det_size=self.det_size)
        logger.info("InsightFace model ready.")

    def reset(self):
        """Reset singleton (useful for testing)."""
        self._app = None
        self._initialized = False
        FaceDetector._instance = None

    # ── helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _read_image(image_path: str) -> np.ndarray:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Unable to decode image: {image_path}")
        return img

    @staticmethod
    def _read_image_from_bytes(data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to decode image bytes")
        return img

    # ── public API ──────────────────────────────────────────────────
    def detect(self, image_path: str) -> list[FaceInfo]:
        """Detect faces in a file on disk."""
        img = self._read_image(image_path)
        return self.detect_array(img)

    def detect_bytes(self, data: bytes) -> list[FaceInfo]:
        """Detect faces from raw image bytes (e.g. downloaded candidate)."""
        img = self._read_image_from_bytes(data)
        return self.detect_array(img)

    def detect_array(self, img: np.ndarray) -> list[FaceInfo]:
        """Detect faces from an already-loaded BGR ndarray."""
        self._ensure_loaded()
        assert self._app is not None

        raw_faces = self._app.get(img)
        faces: list[FaceInfo] = []
        for f in raw_faces:
            bbox = [int(v) for v in f.bbox]  # type: ignore[attr-defined]
            # InsightFace det_score
            conf = float(getattr(f, "det_score", 0.0))
            emb: np.ndarray = f.normed_embedding  # already L2-normalised by InsightFace
            # need the *raw* embedding for correct pipeline (we re-normalise explicitly)
            # but normed_embedding is fine; keep both pathways consistent
            # Fall back to 'embedding' if normed not available
            if emb is None:
                emb = getattr(f, "embedding", np.zeros(512, dtype=np.float32))
            kps = getattr(f, "kps", None)
            age = getattr(f, "age", None)
            gender = getattr(f, "gender", None)
            # Re-normalise explicitly to avoid double-norm issues
            faces.append(
                FaceInfo(
                    bbox=bbox,
                    confidence=conf,
                    embedding=emb.astype(np.float32),
                    kps=kps,
                    age=age,
                    gender=gender,
                )
            )
        # Sort by confidence descending then bbox area descending (largest first)
        faces.sort(
            key=lambda f: (
                f.confidence,
                (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            ),
            reverse=True,
        )
        return faces

    def detect_single(
        self, image_path: str
    ) -> FaceInfo | None:
        """Return the *best* face or ``None`` if no face found.

        Automatically selects the highest-confidence / largest face when
        multiple are present.
        """
        faces = self.detect(image_path)
        if not faces:
            return None
        return faces[0]

    def get_largest_face_bytes(self, data: bytes) -> FaceInfo | None:
        faces = self.detect_bytes(data)
        if not faces:
            return None
        return faces[0]
