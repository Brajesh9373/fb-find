"""Free perceptual hash (dHash) for image similarity — no extra deps.

Uses only Pillow + numpy (already required).  Complements SHA-256:
- SHA-256: exact byte equality (tamper detection)
- dHash: near-duplicate tolerance (resize/crop/compress)
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image


def dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """Compute 64-bit dHash hex string for image bytes.

    Returns 16 hex chars (8 bytes).  Compare via hamming distance.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    # Resize to (hash_size+1) x hash_size and compute horizontal gradient
    img = img.resize((hash_size + 1, hash_size), Image.BILINEAR)
    pixels = np.asarray(img, dtype=np.uint8)
    diff = pixels[:, 1:] > pixels[:, :-1]
    # Pack bits into hex
    bits = diff.flatten()
    # build hex string
    hex_str = ""
    for i in range(0, len(bits), 8):
        byte = bits[i : i + 8]
        # pad last byte if needed
        if len(byte) < 8:
            byte = np.pad(byte, (0, 8 - len(byte)))
        val = 0
        for b in byte:
            val = (val << 1) | int(b)
        hex_str += f"{val:02x}"
    return hex_str


def hamming(a: str, b: str) -> int:
    """Hamming distance between two hex dHashes."""
    # hex -> int -> xor -> popcount
    return bin(int(a, 16) ^ int(b, 16)).count("1")
