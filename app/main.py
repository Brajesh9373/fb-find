"""Main pipeline CLI:  Face → Web Search → Blockchain Verification."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

from rich.console import Console

from app import config
from app.cli import display
from app.content.canonicalizer import build_canonical_payload
from app.content.extractor import extract_face_from_candidate
from app.content.hashing import fingerprint_canonical
from app.face.detector import FaceDetector
from app.face.similarity import cosine_similarity
from app.search.lens import GoogleLensSearcher
from app.search.ranking import is_social, rank_candidates

console = Console()
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Face → Web → Blockchain verifier",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--image", "-i", required=True, help="Path to input face image")
    p.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Face match threshold (default from env FACE_MATCH_THRESHOLD)",
    )
    p.add_argument(
        "--skip-blockchain",
        action="store_true",
        help="Skip on-chain registration (useful for testing face+search only)",
    )
    p.add_argument(
        "--tamper-demo",
        action="store_true",
        help="After verification, demonstrate tamper detection by mutating payload",
    )
    p.add_argument(
        "--max-verify",
        type=int,
        default=None,
        help="Max candidates to run face verification on",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--mock-search",
        action="store_true",
        help="Use mock search results (no SerpApi call) for offline testing",
    )
    return p


def run_pipeline(args: argparse.Namespace) -> int:
    threshold = args.threshold if args.threshold is not None else config.FACE_MATCH_THRESHOLD
    max_verify = args.max_verify or config.MAX_CANDIDATES_TO_VERIFY

    display.banner()
    console.print(f"[dim]Input:[/] [white]{args.image}[/]   [dim]Threshold:[/] {threshold:.0%}")
    console.print()

    # ── [1/5] Detect face ───────────────────────────────────────────
    display.step(1, 5, "Detecting face ...")
    detector = FaceDetector()

    try:
        faces = detector.detect(args.image)
    except FileNotFoundError as exc:
        display.error(str(exc))
        return 1
    except Exception as exc:
        display.error(f"Face detection failed: {exc}")
        if args.verbose:
            traceback.print_exc()
        return 1

    if not faces:
        display.error("No face detected — please provide another image.")
        return 1

    if len(faces) > 1:
        display.warning(f"Multiple faces detected ({len(faces)}) — selecting highest-confidence face.")

    best = faces[0]
    display.success(f"Face detected  bbox={best.bbox}  confidence={best.confidence:.2%}")
    display.info(f"Embedding dim={best.embedding.shape[0]}")

    # ── [2/5] Embedding ─────────────────────────────────────────────
    display.step(2, 5, "Generating face embedding ...")
    # Already produced by detector; just normalise explicitly
    from app.face.embedder import normalize as norm_emb

    query_emb = norm_emb(best.embedding)
    display.success(f"Embedding generated  norm={query_emb.dot(query_emb):.4f} (~1.0)")

    # ── [3/5] Web search ────────────────────────────────────────────
    display.step(3, 5, "Searching web (Google Lens via SerpApi) ...")

    if args.mock_search:
        candidates = _mock_candidates()
        display.info("[yellow]MOCK SEARCH enabled — using synthetic results[/]")
    else:
        searcher = GoogleLensSearcher()
        try:
            candidates = searcher.search(args.image)
        except Exception as exc:
            display.error(f"Search failed: {exc}")
            if args.verbose:
                traceback.print_exc()
            # Non-fatal — allow pipeline to show error gracefully
            candidates = []

    if not candidates:
        display.warning("No candidates returned from search.")
        display.error("Pipeline stopped — no candidates to verify.")
        return 1

    display.success(f"Google Lens search completed — {len(candidates)} candidate(s) found")
    social_count = sum(1 for c in candidates if is_social(c.get("url", "")))
    display.info(f"Social candidates: {social_count}/{len(candidates)}")

    ranked = rank_candidates(candidates)
    display.candidates_table(ranked)

    # ── [4/5] Verify candidates ─────────────────────────────────────
    display.step(4, 5, f"Verifying candidates (top {max_verify}) ...")

    matched: dict | None = None
    matched_face = None
    matched_similarity: float = 0.0

    to_verify = ranked[:max_verify]

    for idx, cand in enumerate(to_verify, 1):
        url = cand.get("url", "")
        source = cand.get("source", "") or url
        console.print(f"\n      [white]Candidate #{idx}[/]  [cyan]{source}[/]  [dim]{url[:60]}[/]")

        face, img_bytes = extract_face_from_candidate(cand, detector)
        if face is None:
            display.info("No face found in candidate image — skipping")
            continue

        sim = cosine_similarity(query_emb, face.embedding)
        console.print(f"      Similarity: [yellow]{sim*100:.1f}%[/]  (threshold {threshold*100:.0f}%)")

        if sim >= threshold:
            display.success(f"MATCH ✓  ({sim*100:.1f}% ≥ {threshold*100:.0f}%)")
            matched = cand
            matched_face = face
            matched_similarity = sim
            break
        else:
            display.info(f"No match ({sim*100:.1f}% < {threshold*100:.0f}%)")

    if matched is None:
        display.error(f"No candidate passed verification at threshold {threshold:.0%}")
        console.print("\n[dim]Tip: try lowering --threshold or use a different image.[/]")
        return 1

    # ── Match confirmed ─────────────────────────────────────────────
    platform = matched.get("source") or matched.get("url", "")
    # Clean platform label
    from urllib.parse import urlparse as _up

    try:
        plat_label = _up(matched["url"]).netloc.removeprefix("www.")
    except Exception:
        plat_label = platform

    display.match_box(plat_label, matched_similarity, matched["url"])

    # ── [5/5] Content fingerprint + blockchain ──────────────────────
    display.step(5, 5, "Generating SHA-256 fingerprint ...")

    payload = build_canonical_payload(
        url=matched["url"],
        platform=plat_label,
        title=matched.get("title", ""),
        image_url=matched.get("image_url", "") or matched.get("thumbnail", ""),
        similarity=matched_similarity,
    )
    content_hash = fingerprint_canonical(payload)
    display.success(f"SHA-256: [yellow]{content_hash}[/]")
    display.info(f"Canonical payload: {payload}")

    if args.skip_blockchain:
        display.warning("Skipping blockchain — --skip-blockchain set")
        # Still do local re-verification demo
        console.print("\n[bold]Re-verification (local only):[/]")
        reh = fingerprint_canonical(payload)
        ok = reh == content_hash
        console.print(f"  Local:  {reh}")
        console.print(f"  Status: {'[green]VERIFIED ✓[/]' if ok else '[red]FAILED[/]'}")
        if args.tamper_demo:
            _tamper_demo(payload)
        return 0

    # Blockchain registration
    console.print(f"\n      [dim]Network:[/] [cyan]{config.CHAIN_NAME}[/] (chainId={config.CHAIN_ID})")
    try:
        from app.blockchain.registry import ContentRegistry
        from app.blockchain.verifier import verify_local_vs_chain

        registry = ContentRegistry()
        console.print(f"      [dim]Contract:[/] {registry.contract_address}")
        console.print("      [dim]Sending register() transaction ...[/]")

        receipt = registry.register(content_hash)
        display.blockchain_box(
            content_hash=receipt.content_hash,
            tx_hash=receipt.tx_hash,
            block_number=receipt.block_number,
            contract=receipt.contract_address,
            network=config.CHAIN_NAME,
        )
        if receipt.tx_hash != "(already registered)":
            console.print(f"      [dim]Explorer:[/] {config.EXPLORER_URL}/tx/{receipt.tx_hash}")

        # ── Re-verification ─────────────────────────────────────────
        console.print("\n[bold]BLOCKCHAIN RE-VERIFICATION[/]")
        recomputed = fingerprint_canonical(payload)
        exists = registry.verify(recomputed)
        chain_hash = recomputed if exists else None
        # Fetch full record if exists for accurate chain hash
        if exists:
            rec = registry.get_record(recomputed)
            if rec:
                chain_hash = rec["hash"]

        from app.blockchain.verifier import verify_local_vs_chain as _verify

        result = _verify(recomputed, exists, chain_hash)
        display.verification_box(result.local_hash, result.chain_hash, result.verified, result.tampered)
        console.print(f"  [dim]{result.message}[/]")

        if args.tamper_demo:
            _tamper_demo(payload, registry)

    except Exception as exc:
        display.error(f"Blockchain step failed: {exc}")
        if args.verbose:
            traceback.print_exc()
        console.print("\n[yellow]Content hash was still generated (see above).[/]")
        console.print("[dim]Set POLYGON_RPC_URL / PRIVATE_KEY / CONTRACT_ADDRESS in .env[/]")
        return 1

    console.print("\n[bold green]Pipeline complete ✓[/]")
    return 0


def _tamper_demo(original_payload: dict, registry=None):
    console.print("\n[bold yellow]── TAMPER DEMO ──[/]")
    import copy
    from app.content.hashing import fingerprint_canonical as _fp

    tampered = copy.deepcopy(original_payload)
    # mutate title
    orig_title = tampered.get("title", "")
    tampered["title"] = (orig_title + " [TAMPERED]") if orig_title else "TAMPERED TITLE"
    # or mutate similarity year-like
    console.print(f"  Original title : [white]{original_payload.get('title','')}[/]")
    console.print(f"  Tampered title : [red]{tampered['title']}[/]")

    orig_hash = _fp(original_payload)
    new_hash = _fp(tampered)
    console.print(f"\n  Original hash : [yellow]{orig_hash}[/]")
    console.print(f"  Tampered hash : [red]{new_hash}[/]")
    console.print(f"  Hashes equal? [red]{orig_hash == new_hash}[/]  (expected: False)")

    if registry is not None:
        exists = registry.verify(new_hash)
        from app.blockchain.verifier import verify_local_vs_chain as _verify
        result = _verify(new_hash, exists, new_hash if exists else None)
        display.verification_box(result.local_hash, result.chain_hash, result.verified, result.tampered)
        if not result.verified:
            console.print("[bold red]Tamper correctly detected — on-chain fingerprint unchanged.[/]")
    else:
        console.print(f"\n  On-chain still holds: [yellow]{orig_hash}[/]")
        console.print("  → [bold red]TAMPER DETECTED ❌  Hashes differ[/]")


def _mock_candidates() -> list[dict]:
    """Synthetic results for offline testing (no network)."""
    return [
        {
            "title": "Technology Conference 2026 — Instagram",
            "url": "https://www.instagram.com/p/mock_tech_conf_2026/",
            "source": "instagram.com",
            "thumbnail": "https://via.placeholder.com/400",
            "image_url": "https://via.placeholder.com/400",
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


def main():
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    sys.exit(run_pipeline(args))


if __name__ == "__main__":
    main()
