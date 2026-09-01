"""High-level registry: register + query on-chain fingerprint."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from web3 import Web3

from app import config
from app.blockchain.client import get_account, get_w3, load_abi
from app.content.hashing import to_bytes32

logger = logging.getLogger(__name__)


@dataclass
class TxReceipt:
    tx_hash: str
    block_number: int
    contract_address: str
    content_hash: str
    status: int


class ContentRegistry:
    def __init__(
        self,
        contract_address: str | None = None,
        rpc_url: str | None = None,
        private_key: str | None = None,
    ):
        self.contract_address = contract_address or config.CONTRACT_ADDRESS
        if not self.contract_address:
            raise RuntimeError(
                "CONTRACT_ADDRESS not set.  Deploy with: python scripts/deploy.py"
            )
        self.w3: Web3 = get_w3(rpc_url)
        self.abi = load_abi()
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address), abi=self.abi
        )
        self._private_key = private_key or config.PRIVATE_KEY

    # ── writes ────────────────────────────────────────────────────────
    def register(self, content_hash_hex: str) -> TxReceipt:
        """Submit ``register(bytes32)`` transaction."""
        if not self._private_key:
            raise RuntimeError("PRIVATE_KEY not set — cannot send transaction")
        acct = get_account(self.w3, self._private_key)
        hash_bytes = to_bytes32(content_hash_hex)

        # Pre-check: already registered?
        if self.verify(content_hash_hex):
            logger.info("Hash %s already registered — skipping tx", content_hash_hex)
            # Still return a synthetic receipt for display consistency
            # Query the record for block info
            rec = self.get_record(content_hash_hex)
            return TxReceipt(
                tx_hash="(already registered)",
                block_number=rec["blockNumber"] if rec else 0,
                contract_address=self.contract_address,  # type: ignore[arg-type]
                content_hash=content_hash_hex,
                status=1,
            )

        tx = self.contract.functions.register(hash_bytes).build_transaction(
            {
                "from": acct.address,
                "nonce": self.w3.eth.get_transaction_count(acct.address),
                "chainId": config.CHAIN_ID,
                "gas": 150_000,
                "maxFeePerGas": self.w3.to_wei("30", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("1", "gwei"),
            }
        )
        signed = acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info("Sent register tx %s", tx_hash.hex())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        logger.info(
            "Tx confirmed in block %d (status=%d)", receipt.blockNumber, receipt.status
        )
        return TxReceipt(
            tx_hash=receipt.transactionHash.hex(),
            block_number=receipt.blockNumber,
            contract_address=self.contract_address,  # type: ignore[arg-type]
            content_hash=content_hash_hex,
            status=receipt.status,
        )

    # ── reads ─────────────────────────────────────────────────────────
    def verify(self, content_hash_hex: str) -> bool:
        hash_bytes = to_bytes32(content_hash_hex)
        return bool(self.contract.functions.verify(hash_bytes).call())

    def get_record(self, content_hash_hex: str) -> dict | None:
        hash_bytes = to_bytes32(content_hash_hex)
        result = self.contract.functions.getRecord(hash_bytes).call()
        # result = (hash, registrant, timestamp, blockNumber, exists)
        if len(result) == 5 and not result[4]:
            return None
        return {
            "hash": "0x" + result[0].hex(),
            "registrant": result[1],
            "timestamp": result[2],
            "blockNumber": result[3],
            "exists": result[4],
        }
