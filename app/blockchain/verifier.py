"""Pure re-verification logic: local hash vs on-chain hash."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    local_hash: str
    chain_hash: str | None
    verified: bool
    tampered: bool = False
    message: str = ""


def verify_local_vs_chain(
    local_hash: str,
    chain_exists: bool,
    chain_hash: str | None = None,
) -> VerificationResult:
    """Compare local fingerprint against what the chain stores.

    * ``local_hash``  – SHA-256 hex (``0x…``)
    * ``chain_exists`` – whether the registry returned a record
    * ``chain_hash``   – on-chain hash if exists (normalise to ``0x``)
    """
    lh = local_hash.lower()
    ch = chain_hash.lower() if chain_hash else None

    if not chain_exists or ch is None:
        return VerificationResult(
            local_hash=lh,
            chain_hash=None,
            verified=False,
            message="Hash not found on-chain.",
        )
    if lh == ch:
        return VerificationResult(
            local_hash=lh,
            chain_hash=ch,
            verified=True,
            message="VERIFIED ✓  Local hash matches on-chain fingerprint.",
        )
    return VerificationResult(
        local_hash=lh,
        chain_hash=ch,
        verified=False,
        tampered=True,
        message="TAMPER DETECTED ❌  Hashes differ — data has changed.",
    )
