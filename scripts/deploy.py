#!/usr/bin/env python3
"""Deploy ContentRegistry to Polygon Amoy.

Usage:
    python scripts/deploy.py
    python scripts/deploy.py --rpc https://rpc-amoy.polygon.technology

Requires .env with PRIVATE_KEY and optionally POLYGON_RPC_URL.
Writes deployed address + ABI to contracts/deployed.json and contracts/abi.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SOURCE = ROOT / "contracts" / "ContentRegistry.sol"

# Minimal ABI — kept in sync with contracts/ContentRegistry.sol
ABI = json.loads("""[
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
      {"internalType": "bytes32","name":"hash_","type":"bytes32"},
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
]""")


def compile_contract():
    """Try to compile with py-solc-x; fall back to pre-compiled bytecode."""
    bytecode_file = ROOT / "contracts" / "bytecode.hex"
    if bytecode_file.exists():
        print(f"Using cached bytecode from {bytecode_file}")
        return bytecode_file.read_text().strip()

    try:
        import solcx

        print("Compiling ContentRegistry.sol with solc ...")
        # Install solc 0.8.20 if missing
        try:
            solcx.get_solcs()
        except Exception:
            pass
        installed = solcx.get_installed_solc_versions()
        if "0.8.20" not in [str(v) for v in installed]:
            print("Installing solc 0.8.20 ...")
            solcx.install_solc("0.8.20")
        solcx.set_solc_version("0.8.20")

        source = CONTRACT_SOURCE.read_text()
        compiled = solcx.compile_source(
            source, output_values=["abi", "bin"], solc_version="0.8.20"
        )
        # key is like "<stdin>:ContentRegistry"
        key = next(k for k in compiled if "ContentRegistry" in k)
        abi_out = compiled[key]["abi"]
        bin_out = compiled[key]["bin"]
        # Persist ABI
        (ROOT / "contracts" / "abi.json").write_text(json.dumps(abi_out, indent=2))
        (ROOT / "contracts" / "bytecode.hex").write_text(bin_out)
        print("Compiled & cached ABI + bytecode.")
        return bin_out

    except Exception as exc:
        print(f"Compilation failed: {exc}")
        print("Falling back to embedded bytecode (if available) or manual Hardhat/Foundry deploy.")
        if bytecode_file.exists():
            return bytecode_file.read_text().strip()
        print(
            "\nNo bytecode available.  Options:\n"
            "  1. pip install py-solc-x && python scripts/deploy.py\n"
            "  2. Compile with Hardhat/Foundry and paste bytecode into contracts/bytecode.hex\n"
            "  3. Deploy via Remix (https://remix.ethereum.org) and set CONTRACT_ADDRESS in .env\n"
        )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Deploy ContentRegistry to Polygon Amoy")
    parser.add_argument("--rpc", default=os.getenv("POLYGON_RPC_URL", "https://rpc-amoy.polygon.technology"))
    parser.add_argument("--private-key", default=os.getenv("PRIVATE_KEY"))
    parser.add_argument("--dry-run", action="store_true", help="Compile only, do not send tx")
    args = parser.parse_args()

    bytecode = compile_contract()

    if args.dry_run:
        print("Dry run — bytecode ready, not deploying.")
        return

    pk = args.private_key
    if not pk:
        print("ERROR: PRIVATE_KEY not set (env or --private-key)")
        sys.exit(1)
    pk = pk.strip()
    if not pk.startswith("0x"):
        pk = "0x" + pk

    # Write ABI file if not yet written (compile path already did)
    abi_path = ROOT / "contracts" / "abi.json"
    if not abi_path.exists():
        abi_path.write_text(json.dumps(ABI, indent=2))

    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        print(f"Cannot connect to RPC: {args.rpc}")
        sys.exit(1)

    acct = w3.eth.account.from_key(pk)
    print(f"Deployer: {acct.address}")
    bal = w3.eth.get_balance(acct.address)
    print(f"Balance:  {w3.from_wei(bal, 'ether')} POL  (need ~0.01 for deploy)")

    if bal == 0:
        print("Faucet: https://faucet.polygon.technology/  (Polygon Amoy)")
        sys.exit(1)

    chain_id = w3.eth.chain_id
    print(f"Chain ID: {chain_id}")

    Contract = w3.eth.contract(abi=ABI, bytecode=bytecode)
    print("Deploying ContentRegistry ...")

    tx = Contract.constructor().build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": chain_id,
            "gas": 1_500_000,
            "maxFeePerGas": w3.to_wei("50", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("30", "gwei"),
        }
    )
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx hash: {tx_hash.hex()}")
    print("Waiting for confirmation ...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    addr = receipt.contractAddress
    print(f"\n✅ Deployed at: {addr}")
    print(f"   Block: {receipt.blockNumber}")
    print(f"   Gas used: {receipt.gasUsed}")
    print(f"   Explorer: https://amoy.polygonscan.com/address/{addr}")

    deployed = {
        "address": addr,
        "tx_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "chain_id": chain_id,
        "network": "Polygon Amoy",
        "explorer": f"https://amoy.polygonscan.com/address/{addr}",
    }
    (ROOT / "contracts" / "deployed.json").write_text(json.dumps(deployed, indent=2))
    print(f"\nSaved to contracts/deployed.json")
    print(f"Add to .env:  CONTRACT_ADDRESS={addr}")


if __name__ == "__main__":
    main()
