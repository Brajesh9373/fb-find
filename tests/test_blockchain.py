"""Blockchain verifier unit tests — no RPC needed."""

from app.blockchain.verifier import verify_local_vs_chain
from app.content.hashing import to_bytes32
import pytest


def test_to_bytes32_valid():
    h = "0x" + "ff" * 32
    assert to_bytes32(h) == bytes.fromhex("ff" * 32)


def test_to_bytes32_invalid_length():
    with pytest.raises(ValueError):
        to_bytes32("0x1234")


def test_verifier_verified():
    h = "0x" + "ab" * 32
    r = verify_local_vs_chain(h, True, h)
    assert r.verified


def test_verifier_tampered():
    r = verify_local_vs_chain("0x" + "aa" * 32, True, "0x" + "bb" * 32)
    assert r.tampered and not r.verified


def test_verifier_not_found():
    r = verify_local_vs_chain("0x" + "aa" * 32, False, None)
    assert not r.verified and not r.tampered
