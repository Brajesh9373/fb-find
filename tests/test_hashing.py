import hashlib
import json

from app.content.canonicalizer import canonicalize, build_canonical_payload
from app.content.hashing import fingerprint_canonical, fingerprint_bytes, sha256_hex, to_bytes32
from app.blockchain.verifier import verify_local_vs_chain


def test_canonicalize_deterministic():
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    assert canonicalize(d1) == canonicalize(d2)


def test_canonicalize_no_whitespace():
    data = {"url": "https://example.com", "title": "hello"}
    raw = canonicalize(data).decode()
    # separators=(',', ':') → no space after colon/comma
    assert ": " not in raw
    assert ", " not in raw


def test_same_data_same_hash():
    payload = build_canonical_payload(
        url="https://instagram.com/p/abc/",
        platform="instagram.com",
        title="Technology Conference 2026",
        image_url="https://example.com/img.jpg",
        similarity=0.8723,
    )
    assert fingerprint_canonical(payload) == fingerprint_canonical(payload)


def test_changed_data_different_hash():
    p1 = build_canonical_payload(
        url="https://instagram.com/p/abc/",
        platform="instagram.com",
        title="Technology Conference 2026",
        image_url="https://example.com/img.jpg",
        similarity=0.8723,
    )
    p2 = build_canonical_payload(
        url="https://instagram.com/p/abc/",
        platform="instagram.com",
        title="Technology Conference 2027",  # tampered
        image_url="https://example.com/img.jpg",
        similarity=0.8723,
    )
    assert fingerprint_canonical(p1) != fingerprint_canonical(p2)


def test_sha256_known_vector():
    assert sha256_hex(b"hello") == hashlib.sha256(b"hello").hexdigest()


def test_to_bytes32_roundtrip():
    h = "0x" + "ab" * 32
    b = to_bytes32(h)
    assert len(b) == 32
    assert b.hex() == "ab" * 32


def test_verify_local_vs_chain_verified():
    h = "0x" + "aa" * 32
    r = verify_local_vs_chain(h, True, h)
    assert r.verified is True
    assert r.tampered is False


def test_verify_local_vs_chain_tampered():
    h1 = "0x" + "aa" * 32
    h2 = "0x" + "bb" * 32
    r = verify_local_vs_chain(h1, True, h2)
    assert r.verified is False
    assert r.tampered is True


def test_verify_local_vs_chain_not_found():
    h = "0x" + "aa" * 32
    r = verify_local_vs_chain(h, False, None)
    assert r.verified is False
