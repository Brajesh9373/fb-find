"""web3.py client for Polygon Amoy."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from web3 import Web3

from app import config

logger = logging.getLogger(__name__)

# ── ABI loading ───────────────────────────────────────────────────────
# After ``python scripts/deploy.py`` the ABI is written to
# ``contracts/abi.json``.  Fall back to the minimal ABI needed for
# verification-only usage.
ABI_PATH = Path(__file__).resolve().parents[2] / "contracts" / "abi.json"

MINIMAL_ABI = json.loads(
    """[
  {
    "inputs": [{"internalType": "bytes32","name": "contentHash","type": "bytes32"}],
    "name": "register",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "bytes32","name": "contentHash","type": "bytes32"}],
    "name": "verify",
    "outputs": [{"internalType": "bool","name":"","type":"bool"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "bytes32","name": "contentHash","type": "bytes32"}],
    "name": "getRecord",
    "outputs": [
      {"internalType": "bytes32","name":"hash","type":"bytes32"},
      {"internalType": "address","name":"registrant","type":"address"},
      {"internalType": "uint256","name":"timestamp","type":"uint256"},
      {"internalType": "uint256","name":"blockNumber","type":"uint256"},
      {"internalType": "bool","name":"exists","type":"bool"}
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "totalRecords",
    "outputs": [{"internalType":"uint256","name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true,"internalType":"bytes32","name":"contentHash","type":"bytes32"},
      {"indexed": true,"internalType":"address","name":"registrant","type":"address"},
      {"indexed": false,"internalType":"uint256","name":"timestamp","type":"uint256"},
      {"indexed": false,"internalType":"uint256","name":"blockNumber","type":"uint256"}
    ],
    "name":"ContentRegistered","type":"event"
  }
]"""
)


def load_abi() -> list:
    if ABI_PATH.exists():
        try:
            with open(ABI_PATH) as fh:
                data = json.load(fh)
                # support both raw ABI list and {"abi": [...]} wrapper
                if isinstance(data, dict) and "abi" in data:
                    return data["abi"]
                return data
        except Exception as exc:
            logger.warning("Failed to load ABI from %s: %s — using minimal ABI", ABI_PATH, exc)
    return MINIMAL_ABI


def get_w3(rpc_url: str | None = None) -> Web3:
    # Try custom/primary, then public fallbacks — all free
    candidates = []
    if rpc_url:
        candidates.append(rpc_url)
    if config.POLYGON_RPC_URL not in candidates:
        candidates.append(config.POLYGON_RPC_URL)
    for fb in config.RPC_FALLBACKS:
        if fb not in candidates:
            candidates.append(fb)

    last_err: Exception | None = None
    for url in candidates:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
            if w3.is_connected():
                if url != config.POLYGON_RPC_URL:
                    logger.info("Connected to fallback RPC: %s", url)
                return w3
        except Exception as exc:
            last_err = exc
            logger.debug("RPC %s failed: %s", url, exc)
            continue
    raise ConnectionError(
        f"Cannot connect to any Polygon Amoy RPC. Tried: {candidates}. Last error: {last_err}"
    )


def get_account(w3: Web3, private_key: str | None = None):
    key = private_key or config.PRIVATE_KEY
    if not key:
        raise RuntimeError("PRIVATE_KEY not set in .env")
    key = key.strip()
    if not key.startswith("0x"):
        key = "0x" + key
    return w3.eth.account.from_key(key)
