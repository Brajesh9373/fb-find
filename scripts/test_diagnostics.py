import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

print("=" * 60)
print("DIAGNOSTIC TEST: API KEYS & ARCHITECTURE")
print("=" * 60)

# 1. Check loaded config
serpapi_key = os.getenv("SERPAPI_KEY")
private_key = os.getenv("PRIVATE_KEY")
contract_address = os.getenv("CONTRACT_ADDRESS")
rpc_url = os.getenv("POLYGON_RPC_URL", "https://rpc-amoy.polygon.technology")
chain_id = os.getenv("CHAIN_ID", "80002")

print("\n[1] Environment Variables Status:")
print(f"  SERPAPI_KEY: {'[SET] (' + serpapi_key[:6] + '...' + serpapi_key[-4:] + ')' if serpapi_key else '[NOT SET]'}")
print(f"  PRIVATE_KEY: {'[SET] (' + private_key[:6] + '...' + private_key[-4:] + ')' if private_key else '[NOT SET]'}")
print(f"  CONTRACT_ADDRESS: {contract_address if contract_address else '[NOT SET]'}")
print(f"  POLYGON_RPC_URL: {rpc_url}")
print(f"  CHAIN_ID: {chain_id}")

# 2. Test SerpApi Key
print("\n[2] Testing SerpAPI Key ...")
if not serpapi_key:
    print("  ❌ SERPAPI_KEY is not set in .env")
else:
    import requests
    try:
        acc_resp = requests.get(f"https://serpapi.com/account.json?api_key={serpapi_key}", timeout=10)
        if acc_resp.status_code == 200:
            acc_data = acc_resp.json()
            plan = acc_data.get("plan_name", "Unknown")
            searches_left = acc_data.get("total_searches_left", "N/A")
            this_month = acc_data.get("this_month_usage", "N/A")
            account_email = acc_data.get("account_email", "N/A")
            print(f"  ✓ SerpAPI Key is VALID and ACTIVE!")
            print(f"    Account Email: {account_email}")
            print(f"    Plan: {plan}")
            print(f"    Searches Remaining: {searches_left}")
            print(f"    Usage this month: {this_month}")
        else:
            print(f"  ❌ SerpAPI Key check failed (HTTP {acc_resp.status_code}): {acc_resp.text}")
    except Exception as e:
        print(f"  ❌ Error contacting SerpApi: {e}")

# 3. Test Blockchain (Polygon Amoy RPC, Wallet, Contract)
print("\n[3] Testing Blockchain & Polygon Amoy ...")
from web3 import Web3

test_rpcs = [
    rpc_url,
    "https://rpc-amoy.polygon.technology",
    "https://polygon-amoy.drpc.org",
    "https://polygon-amoy-bor-rpc.publicnode.com",
    "https://rpc.ankr.com/polygon_amoy",
    "https://80002.rpc.thirdweb.com"
]
unique_rpcs = []
for r in test_rpcs:
    if r and r not in unique_rpcs:
        unique_rpcs.append(r)

working_w3 = None
working_rpc = None

for r in unique_rpcs:
    try:
        w3_test = Web3(Web3.HTTPProvider(r, request_kwargs={"timeout": 6}))
        if w3_test.is_connected():
            cid = w3_test.eth.chain_id
            blk = w3_test.eth.block_number
            print(f"  [OK] RPC '{r}' CONNECTED (Chain ID: {cid}, Block: {blk})")
            if working_w3 is None:
                working_w3 = w3_test
                working_rpc = r
        else:
            print(f"  [FAIL] RPC '{r}' returned not connected")
    except Exception as e:
        print(f"  [FAIL] RPC '{r}': {e}")

if working_w3:
    w3 = working_w3
    print(f"\n  Using Active RPC: {working_rpc}")
    
    if private_key:
        try:
            from app.blockchain.client import get_account
            acct = get_account(w3, private_key)
            balance_wei = w3.eth.get_balance(acct.address)
            balance_pol = w3.from_wei(balance_wei, "ether")
            print(f"  [OK] Wallet Address: {acct.address}")
            print(f"       POL Balance: {balance_pol} POL")
            if balance_pol == 0:
                print("       [WARN] Wallet has 0 POL balance. (Fund via Amoy faucet: https://faucet.polygon.technology/)")
            else:
                print("       [OK] Wallet has funds for gas fees.")
        except Exception as e:
            print(f"  [FAIL] Account derivation error: {e}")
    else:
        print("  [FAIL] PRIVATE_KEY is not set.")

    if contract_address:
        try:
            checksum_addr = Web3.to_checksum_address(contract_address)
            code = w3.eth.get_code(checksum_addr)
            if code and code != b'' and code != b'\x00':
                print(f"  [OK] Contract Code Exists at {contract_address} (Bytecode size: {len(code)} bytes)")
                try:
                    from app.blockchain.registry import ContentRegistry
                    registry = ContentRegistry(contract_address=contract_address, rpc_url=working_rpc)
                    tot = registry.contract.functions.totalRecords().call()
                    print(f"  [OK] Smart Contract totalRecords() on-chain = {tot}")
                except Exception as e:
                    print(f"  [WARN] Contract method call error: {e}")
            else:
                print(f"  [FAIL] No bytecode deployed at {contract_address} on chain {w3.eth.chain_id}")
        except Exception as e:
            print(f"  [FAIL] Contract check error: {e}")
    else:
        print("  [FAIL] CONTRACT_ADDRESS is not set.")
else:
    print("  [FAIL] Could not connect to any Polygon Amoy RPC endpoint.")

# 4. Test InsightFace (Face Detector & Embedder)
print("\n[4] Testing Face Detection & Embedding (InsightFace / ONNX) ...")
try:
    from app.face.detector import FaceDetector
    from app.face.embedder import normalize as norm_emb
    
    sample_img = project_root / "samples" / "virat-kohli-photo-4k.webp"
    if not sample_img.exists():
        print(f"  ❌ Sample image {sample_img} not found.")
    else:
        detector = FaceDetector()
        faces = detector.detect(str(sample_img))
        if faces:
            best = faces[0]
            emb = norm_emb(best.embedding)
            print(f"  ✓ Face Detection successful! Detected {len(faces)} face(s).")
            print(f"    Bounding Box: {best.bbox}")
            print(f"    Confidence: {best.confidence:.2%}")
            print(f"    Embedding dimension: {emb.shape[0]}, norm: {emb.dot(emb):.4f}")
        else:
            print(f"  ❌ No faces detected in {sample_img}")
except Exception as e:
    print(f"  ❌ Face Detection failed: {e}")

# 5. Test Hashing & Canonicalization
print("\n[5] Testing Content Hashing & Canonicalization ...")
try:
    from app.content.canonicalizer import build_canonical_payload
    from app.content.hashing import fingerprint_canonical
    
    test_payload = build_canonical_payload(
        url="https://www.instagram.com/p/test_sample",
        platform="instagram.com",
        title="Test Sample Title",
        image_url="https://example.com/image.jpg",
        similarity=0.925,
    )
    fp = fingerprint_canonical(test_payload)
    print(f"  ✓ Canonical Payload format: {json.dumps(test_payload)}")
    print(f"  ✓ SHA-256 Digest (bytes32 format): {fp}")
except Exception as e:
    print(f"  ❌ Hashing failed: {e}")

print("\n" + "=" * 60)
