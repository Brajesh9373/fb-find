"""Pipeline wrapper for web API — returns structured JSON instead of CLI output."""

from __future__ import annotations

import copy
import logging
import os
import tempfile
from typing import Any
from urllib.parse import urlparse

from app import config
from app.content.canonicalizer import build_canonical_payload
from app.content.extractor import extract_face_from_candidate
from app.content.hashing import fingerprint_canonical
from app.face.detector import FaceDetector
from app.face.embedder import normalize as norm_emb
from app.face.similarity import cosine_similarity
from app.search.lens import GoogleLensSearcher
from app.search.ranking import is_social, rank_candidates

logger = logging.getLogger(__name__)


def run_pipeline(
    image_path: str,
    threshold: float | None = None,
    skip_blockchain: bool = False,
    tamper_demo: bool = True,
    max_verify: int | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and return structured results.

    Returns a dict with keys: success, steps (face_detection, embedding,
    web_search, verification, blockchain), error.
    """
    threshold = threshold or config.FACE_MATCH_THRESHOLD
    max_verify = max_verify or config.MAX_CANDIDATES_TO_VERIFY

    result: dict[str, Any] = {
        "success": False,
        "steps": {
            "face_detection": {"status": "pending"},
            "embedding": {"status": "pending"},
            "web_search": {"status": "pending"},
            "verification": {"status": "pending"},
            "blockchain": {"status": "pending"},
        },
        "error": None,
    }

    # ── Step 1: Face Detection ──────────────────────────────────────
    try:
        detector = FaceDetector()
        faces = detector.detect(image_path)

        if not faces:
            result["error"] = "No face detected in the image"
            result["steps"]["face_detection"]["status"] = "error"
            return result

        best = faces[0]
        result["steps"]["face_detection"] = {
            "status": "success",
            "bbox": [int(v) for v in best.bbox],
            "confidence": round(float(best.confidence), 4),
            "embedding_dim": int(best.embedding.shape[0]),
            "faces_count": len(faces),
        }
    except Exception as exc:
        result["error"] = f"Face detection failed: {exc}"
        result["steps"]["face_detection"]["status"] = "error"
        return result

    # ── Step 2: Embedding ───────────────────────────────────────────
    try:
        query_emb = norm_emb(best.embedding)
        result["steps"]["embedding"] = {
            "status": "success",
            "norm": round(float(query_emb.dot(query_emb)), 4),
        }
    except Exception as exc:
        result["error"] = f"Embedding failed: {exc}"
        result["steps"]["embedding"]["status"] = "error"
        return result

    # ── Step 3: Web Search ──────────────────────────────────────────
    try:
        searcher = GoogleLensSearcher()
        candidates = searcher.search(image_path)

        if not candidates:
            result["error"] = "No candidates found from web search"
            result["steps"]["web_search"]["status"] = "error"
            return result

        social_count = sum(1 for c in candidates if is_social(c.get("url", "")))
        ranked = rank_candidates(candidates)

        result["steps"]["web_search"] = {
            "status": "success",
            "candidates_count": len(candidates),
            "social_count": social_count,
            "candidates": [
                {
                    "position": c.get("position"),
                    "source": c.get("source", ""),
                    "title": c.get("title", ""),
                    "url": c.get("url", ""),
                    "thumbnail": c.get("thumbnail", ""),
                    "is_social": is_social(c.get("url", "")),
                }
                for c in ranked[:12]
            ],
        }
    except Exception as exc:
        result["error"] = f"Web search failed: {exc}"
        result["steps"]["web_search"]["status"] = "error"
        return result

    # ── Step 4: Verification ────────────────────────────────────────
    matched = None
    matched_similarity = 0.0

    try:
        to_verify = ranked[:max_verify]

        for cand in to_verify:
            face, img_bytes = extract_face_from_candidate(cand, detector)
            if face is None:
                continue

            sim = cosine_similarity(query_emb, face.embedding)

            if sim >= threshold:
                matched = cand
                matched_similarity = sim
                break

        if matched is None:
            result["error"] = f"No candidate passed verification at {threshold:.0%} threshold"
            result["steps"]["verification"]["status"] = "error"
            return result

        try:
            plat_label = urlparse(matched["url"]).netloc.removeprefix("www.")
        except Exception:
            plat_label = matched.get("source", "")

        result["steps"]["verification"] = {
            "status": "success",
            "matched": True,
            "platform": plat_label,
            "similarity": round(float(matched_similarity), 4),
            "url": matched["url"],
            "title": matched.get("title", ""),
            "image_url": matched.get("image_url", "") or matched.get("thumbnail", ""),
        }
    except Exception as exc:
        result["error"] = f"Verification failed: {exc}"
        result["steps"]["verification"]["status"] = "error"
        return result

    # ── Step 5: Blockchain ──────────────────────────────────────────
    if skip_blockchain:
        result["steps"]["blockchain"] = {
            "status": "skipped",
            "reason": "Blockchain skipped by request",
        }
        result["success"] = True
        return result

    try:
        payload = build_canonical_payload(
            url=matched["url"],
            platform=plat_label,
            title=matched.get("title", ""),
            image_url=matched.get("image_url", "") or matched.get("thumbnail", ""),
            similarity=matched_similarity,
        )
        content_hash = fingerprint_canonical(payload)

        from app.blockchain.registry import ContentRegistry

        registry = ContentRegistry()
        receipt = registry.register(content_hash)

        # Re-verification
        recomputed = fingerprint_canonical(payload)
        exists = registry.verify(recomputed)
        chain_hash = recomputed if exists else None
        if exists:
            rec = registry.get_record(recomputed)
            if rec:
                chain_hash = rec["hash"]

        from app.blockchain.verifier import verify_local_vs_chain

        verify_result = verify_local_vs_chain(recomputed, exists, chain_hash)

        blockchain_data: dict[str, Any] = {
            "status": "success",
            "content_hash": content_hash,
            "tx_hash": receipt.tx_hash,
            "block_number": receipt.block_number,
            "contract_address": receipt.contract_address,
            "network": config.CHAIN_NAME,
            "chain_id": config.CHAIN_ID,
            "explorer_url": f"{config.EXPLORER_URL}/tx/{receipt.tx_hash}",
            "verified": verify_result.verified,
            "local_hash": verify_result.local_hash,
            "chain_hash": verify_result.chain_hash,
            "canonical_payload": payload,
        }

        # Tamper demo
        if tamper_demo:
            tampered = copy.deepcopy(payload)
            orig_title = tampered.get("title", "")
            tampered["title"] = (orig_title + " [TAMPERED]") if orig_title else "TAMPERED TITLE"

            orig_hash = fingerprint_canonical(payload)
            tampered_hash = fingerprint_canonical(tampered)

            tamper_exists = registry.verify(tampered_hash)
            tamper_verify = verify_local_vs_chain(tampered_hash, tamper_exists, tampered_hash if tamper_exists else None)

            blockchain_data["tamper_demo"] = {
                "original_title": payload.get("title", ""),
                "tampered_title": tampered["title"],
                "original_hash": orig_hash,
                "tampered_hash": tampered_hash,
                "hashes_equal": orig_hash == tampered_hash,
                "on_chain_verified": tamper_verify.verified,
            }

        result["steps"]["blockchain"] = blockchain_data
        result["success"] = True

    except Exception as exc:
        result["error"] = f"Blockchain step failed: {exc}"
        result["steps"]["blockchain"]["status"] = "error"
        # Still mark success since face+search+verification worked
        result["success"] = True

    return result
