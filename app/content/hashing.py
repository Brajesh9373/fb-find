"""SHA-256 fingerprint helpers."""

from __future__ import annotations

import hashlib
from typing import Any

from app.content.canonicalizer import canonicalize


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint_canonical(data: dict[str, Any]) -> str:
    """Hash the canonical JSON bytes of *data* → ``0x``-prefixed hex."""
    raw = canonicalize(data)
    return "0x" + sha256_hex(raw)


def fingerprint_bytes(data: bytes) -> str:
    return "0x" + sha256_hex(data)


def to_bytes32(hex_str: str) -> bytes:
    """Convert ``0x…`` hex to 32-byte value for Solidity ``bytes32``."""
    h = hex_str.removeprefix("0x").removeprefix("0X")
    if len(h) != 64:
        raise ValueError(f"Expected 64 hex chars (32 bytes), got {len(h)}")
    return bytes.fromhex(h)
