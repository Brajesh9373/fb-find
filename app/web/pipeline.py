"""Pipeline wrapper for web API — streams structured JSON step-by-step via SSE."""

from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from typing import Any, Generator
from urllib.parse import urlparse

import cv2

from app import config
from app.content.canonicalizer import build_canonical_payload
from app.content.extractor import extract_face_from_candidate
from app.content.hashing import fingerprint_canonical
from app.face.detector import FaceDetector, crop_face
from app.face.embedder import normalize as norm_emb
from app.face.similarity import cosine_similarity
from app.search.lens import GoogleLensSearcher
from app.search.ranking import is_social, rank_candidates

logger = logging.getLogger(__name__)


def _mock_candidates(input_image_path: str = "") -> list[dict]:
    """Synthetic results for offline testing (no network)."""
    return [
        {
            "title": "Technology Conference 2026 — Instagram",
            "url": "https://www.instagram.com/p/mock_tech_conf_2026/",
            "source": "instagram.com",
            "thumbnail": input_image_path,
            "image_url": input_image_path,
            "position": 1,
        },
        {
            "title": "Random blog post about photography",
            "url": "https://example.com/blog/photography-tips",
            "source": "example.com",
            "thumbnail": "https://via.placeholder.com/400",
            "image_url": "https://via.placeholder.com/400",
            "position": 2,
        },
        {
            "title": "LinkedIn — Professional profile",
            "url": "https://www.linkedin.com/in/mock-profile/",
            "source": "linkedin.com",
            "thumbnail": "https://via.placeholder.com/400",
            "image_url": "https://via.placeholder.com/400",
            "position": 3,
        },
    ]


def _sse(event: str, data: Any) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def run_pipeline_stream(
    image_path: str,
    threshold: float | None = None,
    probable_threshold: float | None = None,
    allow_probable: bool = True,
    skip_blockchain: bool = False,
    tamper_demo: bool = True,
    max_verify: int | None = None,
    mock_search: bool = False,
) -> Generator[str, None, None]:
    """Run the full pipeline, yielding SSE events for each step.

    Events emitted:
      - step_started  { step, message }
      - step_progress { step, message }
      - step_done     { step, data }
      - step_error    { step, error }
      - pipeline_done { success, error, uploaded_image_url }
    """
    high_threshold = threshold or config.FACE_MATCH_THRESHOLD
    prob_threshold = (
        probable_threshold
        if probable_threshold is not None
        else getattr(config, "PROBABLE_MATCH_THRESHOLD", 0.30)
    )
    max_verify = max_verify or config.MAX_CANDIDATES_TO_VERIFY

    logger.info("=" * 50)
    logger.info("Pipeline started — thresholds: High>=%.0f%% Probable>=%.0f%%", high_threshold * 100, prob_threshold * 100)
    logger.info("=" * 50)

    uploaded_image_url = f"/uploads/{os.path.basename(image_path)}"

    # ── Step 1: Face Detection ──────────────────────────────────────
    logger.info("STEP 1/5 — Face Detection: Loading model...")
    yield _sse("step_started", {"step": "face_detection", "message": "Loading face detection model..."})

    try:
        detector = FaceDetector()
        logger.info("STEP 1/5 — Detecting faces...")
        yield _sse("step_progress", {"step": "face_detection", "message": "Detecting faces in image..."})

        faces = detector.detect(image_path)

        if not faces:
            yield _sse("step_error", {"step": "face_detection", "error": "No face detected in the image"})
            yield _sse("pipeline_done", {"success": False, "error": "No face detected in the image", "uploaded_image_url": uploaded_image_url})
            return

        best = faces[0]

        # Crop the face and overwrite the uploaded file so the rest of the
        # pipeline (search, verification, display) works on the face only.
        try:
            img = cv2.imread(image_path)
            if img is not None:
                h, w = img.shape[:2]
                x1, y1, x2, y2 = best.bbox
                bw, bh = x2 - x1, y2 - y1
                # Tight crop: minimal padding so Google Lens sees ONLY the face
                pad_x, pad_y = int(bw * 0.15), int(bh * 0.2)
                cx1, cy1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
                cx2, cy2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
                cropped = img[cy1:cy2, cx1:cx2]
                cv2.imwrite(image_path, cropped)
                logger.info("Cropped face region: (%d,%d)-(%d,%d) → saved to %s", cx1, cy1, cx2, cy2, image_path)
        except Exception as crop_exc:
            logger.warning("Face crop failed, using original image: %s", crop_exc)

        face_data = {
            "status": "success",
            "bbox": [int(v) for v in best.bbox],
            "confidence": round(float(best.confidence), 4),
            "embedding_dim": int(best.embedding.shape[0]),
            "faces_count": len(faces),
        }
        yield _sse("step_done", {"step": "face_detection", "data": face_data})
        logger.info("STEP 1/5 — Done: %d face(s) found, confidence %.1f%%", len(faces), float(best.confidence) * 100)
    except Exception as exc:
        yield _sse("step_error", {"step": "face_detection", "error": f"Face detection failed: {exc}"})
        yield _sse("pipeline_done", {"success": False, "error": f"Face detection failed: {exc}", "uploaded_image_url": uploaded_image_url})
        return

    # ── Step 2: Embedding ───────────────────────────────────────────
    logger.info("STEP 2/5 — Computing face embedding...")
    yield _sse("step_started", {"step": "embedding", "message": "Computing face embedding..."})

    try:
        query_emb = norm_emb(best.embedding)
        embed_data = {
            "status": "success",
            "norm": round(float(query_emb.dot(query_emb)), 4),
        }
        yield _sse("step_done", {"step": "embedding", "data": embed_data})
        logger.info("STEP 2/5 — Done: embedding norm %.4f", embed_data["norm"])
    except Exception as exc:
        yield _sse("step_error", {"step": "embedding", "error": f"Embedding failed: {exc}"})
        yield _sse("pipeline_done", {"success": False, "error": f"Embedding failed: {exc}", "uploaded_image_url": uploaded_image_url})
        return

    # ── Step 3: Web Search ──────────────────────────────────────────
    logger.info("STEP 3/5 — Searching web for matching faces...")
    yield _sse("step_started", {"step": "web_search", "message": "Searching web for matching faces..."})

    try:
        if mock_search:
            yield _sse("step_progress", {"step": "web_search", "message": "Using mock search results (offline mode)..."})
            candidates = _mock_candidates(image_path)
        else:
            yield _sse("step_progress", {"step": "web_search", "message": "Uploading face to search engine..."})
            searcher = GoogleLensSearcher()
            candidates = searcher.search(image_path)

        if not candidates:
            yield _sse("step_error", {"step": "web_search", "error": "No candidates found from web search"})
            yield _sse("pipeline_done", {"success": False, "error": "No candidates found from web search", "uploaded_image_url": uploaded_image_url})
            return

        social_count = sum(1 for c in candidates if is_social(c.get("url", "")))
        ranked = rank_candidates(candidates)

        yield _sse("step_progress", {"step": "web_search", "message": f"Found {len(candidates)} candidates, ranking..."})
        logger.info("STEP 3/5 — Done: %d candidates found (%d social)", len(candidates), social_count)

        web_data = {
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
                for c in ranked[:15]
            ],
        }
        yield _sse("step_done", {"step": "web_search", "data": web_data})
    except Exception as exc:
        yield _sse("step_error", {"step": "web_search", "error": f"Web search failed: {exc}"})
        yield _sse("pipeline_done", {"success": False, "error": f"Web search failed: {exc}", "uploaded_image_url": uploaded_image_url})
        return

    # ── Step 4: Verification ────────────────────────────────────────
    from app.face.similarity import get_confidence_tier

    logger.info("STEP 4/5 — Verifying top %d candidates (High>=%.0f%%, Probable>=%.0f%%)...", max_verify, high_threshold * 100, prob_threshold * 100)
    yield _sse("step_started", {"step": "verification", "message": f"Verifying top {max_verify} candidates..."})

    matched = None
    matched_similarity = 0.0
    matched_tier = "UNMATCHED"
    evaluated_candidates = []
    best_probable = None

    try:
        to_verify = ranked[:max_verify]

        for idx, cand in enumerate(to_verify):
            yield _sse("step_progress", {
                "step": "verification",
                "message": f"Checking candidate {idx + 1}/{len(to_verify)}: {cand.get('source', 'Unknown')}...",
            })

            face, img_bytes = extract_face_from_candidate(cand, detector, query_emb=query_emb)
            if face is None:
                evaluated_candidates.append({
                    "title": cand.get("title", ""),
                    "url": cand.get("url", ""),
                    "source": cand.get("source", ""),
                    "similarity": 0.0,
                    "confidence_tier": "UNMATCHED",
                    "has_face": False,
                })
                yield _sse("step_progress", {"step": "verification", "message": f"  → No face found in candidate image"})
                logger.info("  Candidate %d/%d [%s]: No face found", idx + 1, len(to_verify), cand.get("source", "?"))
                continue

            sim = cosine_similarity(query_emb, face.embedding)
            tier = get_confidence_tier(
                sim, high_threshold=high_threshold, probable_threshold=prob_threshold
            )
            eval_entry = {
                "title": cand.get("title", ""),
                "url": cand.get("url", ""),
                "source": cand.get("source", ""),
                "similarity": round(float(sim), 4),
                "confidence_tier": tier,
                "has_face": True,
            }
            evaluated_candidates.append(eval_entry)

            yield _sse("step_progress", {
                "step": "verification",
                "message": f"  → Similarity: {sim:.1%} ({tier})",
            })
            logger.info("  Candidate %d/%d [%s]: %.1f%% — %s", idx + 1, len(to_verify), cand.get("source", "?"), sim * 100, tier)

            if tier == "HIGH":
                matched = cand
                matched_similarity = sim
                matched_tier = "HIGH"
                break
            elif tier == "PROBABLE":
                if best_probable is None or sim > best_probable["similarity"]:
                    best_probable = {
                        "candidate": cand,
                        "similarity": sim,
                        "tier": "PROBABLE",
                    }

        # If no HIGH match was found, but a PROBABLE match exists and allowed
        if matched is None and allow_probable and best_probable is not None:
            matched = best_probable["candidate"]
            matched_similarity = best_probable["similarity"]
            matched_tier = "PROBABLE"

        if matched is None:
            yield _sse("step_error", {
                "step": "verification",
                "error": f"No candidate passed verification (High: ≥{high_threshold:.0%}, Probable: ≥{prob_threshold:.0%})",
                "evaluated_candidates": evaluated_candidates,
            })
            yield _sse("pipeline_done", {
                "success": False,
                "error": f"No candidate passed verification (High: ≥{high_threshold:.0%}, Probable: ≥{prob_threshold:.0%})",
                "uploaded_image_url": uploaded_image_url,
                "evaluated_candidates": evaluated_candidates,
            })
            return

        try:
            plat_label = urlparse(matched["url"]).netloc.removeprefix("www.")
        except Exception:
            plat_label = matched.get("source", "")

        verification_data = {
            "status": "success",
            "matched": True,
            "platform": plat_label,
            "similarity": round(float(matched_similarity), 4),
            "confidence_tier": matched_tier,
            "url": matched["url"],
            "title": matched.get("title", ""),
            "image_url": matched.get("image_url", "") or matched.get("thumbnail", ""),
            "evaluated_candidates": evaluated_candidates,
        }
        yield _sse("step_done", {"step": "verification", "data": verification_data})
        logger.info("STEP 4/5 — Done: MATCHED [%s] at %.1f%% (%s)", plat_label, matched_similarity * 100, matched_tier)
    except Exception as exc:
        yield _sse("step_error", {"step": "verification", "error": f"Verification failed: {exc}"})
        yield _sse("pipeline_done", {"success": False, "error": f"Verification failed: {exc}", "uploaded_image_url": uploaded_image_url})
        return

    # ── Step 5: Blockchain ──────────────────────────────────────────
    if skip_blockchain:
        logger.info("STEP 5/5 — Skipped (user request)")
        yield _sse("step_done", {"step": "blockchain", "data": {"status": "skipped", "reason": "Blockchain skipped by request"}})
        yield _sse("pipeline_done", {"success": True, "error": None, "uploaded_image_url": uploaded_image_url})
        return

    logger.info("STEP 5/5 — Registering on blockchain...")
    yield _sse("step_started", {"step": "blockchain", "message": "Registering content hash on blockchain..."})

    try:
        payload = build_canonical_payload(
            url=matched["url"],
            platform=plat_label,
            title=matched.get("title", ""),
            image_url=matched.get("image_url", "") or matched.get("thumbnail", ""),
            similarity=matched_similarity,
        )
        content_hash = fingerprint_canonical(payload)

        yield _sse("step_progress", {"step": "blockchain", "message": "Submitting transaction to Polygon Amoy..."})

        from app.blockchain.registry import ContentRegistry

        registry = ContentRegistry()
        receipt = registry.register(content_hash)

        yield _sse("step_progress", {"step": "blockchain", "message": f"Transaction submitted: {receipt.tx_hash[:20]}..."})

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

        yield _sse("step_done", {"step": "blockchain", "data": blockchain_data})
        yield _sse("pipeline_done", {"success": True, "error": None, "uploaded_image_url": uploaded_image_url})
        logger.info("STEP 5/5 — Done: TX %s (block #%s)", receipt.tx_hash[:20], receipt.block_number)
        logger.info("Pipeline completed successfully!")

    except Exception as exc:
        yield _sse("step_error", {"step": "blockchain", "error": f"Blockchain step failed: {exc}"})
        # Still mark success since face+search+verification worked
        yield _sse("pipeline_done", {"success": True, "error": f"Blockchain step failed: {exc}", "uploaded_image_url": uploaded_image_url})
