# Face → Web → Blockchain

**Face Identification → Genuine Web Discovery → On-Chain Verification**

Single vertical slice built from scratch. Give it a face image, it finds the same person in a real web/social result, proves the match with face similarity, and anchors the content fingerprint on Polygon Amoy. No paid services, no heavy infra.

```
face.jpg → InsightFace (ArcFace) → Google Lens (SerpApi free) → social ranking
       → face re-check (cosine ≥ 0.65) → canonical JSON → SHA-256 (bytes32)
       → Polygon Amoy (ContentRegistry) → re-verify → tamper demo
```

Built for HH GOA 2026. All three required stages are visible in one CLI run.

---

## Why this stack (all free & reliable)

| Need | Choice | Why free & reliable |
|---|---|---|
| Face detect + embed | **InsightFace `buffalo_l` + ArcFace (ONNX Runtime CPU)** | MIT, runs locally, no API, no GPU, SOTA accuracy |
| Reverse image | **Google Lens via SerpApi** (`engine=google_lens`) | 100 searches/month free, no card, genuine live search every run. Fallback `--mock-search` for offline |
| Similarity | Cosine on L2-normalised embeddings, threshold `FACE_MATCH_THRESHOLD=0.65` (env-tunable) | — |
| Fingerprint | Canonical JSON (`sort_keys`, `separators=(',',':')`, UTF-8) → SHA-256 → `0x…` bytes32 + optional `dHash` (Pillow only) | Deterministic, tiny on-chain cost |
| Blockchain | **Solidity 0.8.20 + web3.py + Polygon Amoy** (chainId 80002) | Free testnet POL via faucet, public RPC with 3 fallbacks, 2-sec blocks |
| CLI | **Rich** | Single terminal, clear 5-step flow for demo recording |

> Removed on purpose: Browser Use cloud sessions, PimEyes paid pools, Convex/MongoDB, Firebase, HuggingFace inference, Express/React/Three.js frontends, local JSON "blockchain". They hide the 3 required stages and need paid keys. This repo keeps only what the spec asks for.

---

## Architecture

```
                         ┌─────────────────────┐
                         │    Input Image      │
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  Face Detection     │  InsightFace buffalo_l
                         │  + ArcFace embed    │  CPU only, ~300MB first run
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Google Lens search  │  SerpApi, live every run
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  Parser + Ranking   │  dedup + social priority
                         │  insta > fb > x >   │  linkedin > threads …
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Candidate download  │  fetch image → InsightFace
                         │ + face verify       │  cosine ≥ threshold ?
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Canonical JSON      │  sorted keys, no ws, UTF-8
                         │ → SHA-256 (0x)      │  + optional dHash
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ ContentRegistry.sol │  register / verify / getRecord
                         │ Polygon Amoy        │  only bytes32 stored
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Re-verify: local == │  VERIFIED ✓ or TAMPER ❌
                         │ chain ?             │
                         └─────────────────────┘
```

---

## Quick start

```bash
git clone <your-repo>
cd face-detection

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — see below
```

> First run downloads InsightFace model to `~/.insightface/` (~300 MB, once).

### 1. Free API keys (1 minute)

**SerpApi (Google Lens)** — free, no card:
- https://serpapi.com/users/sign_up → Dashboard → API Key → paste as `SERPAPI_KEY` in `.env`

**Polygon Amoy POL** — free:
- Create throwaway wallet (e.g. MetaMask) → https://faucet.polygon.technology/ → select **Amoy** → paste address → receive 0.5 POL
- In MetaMask: Account details → Show private key → paste as `PRIVATE_KEY` in `.env` (never commit)

No other keys needed.

### 2. Deploy contract (free)

```bash
python scripts/deploy.py          # compiles + deploys to Amoy
# outputs: contracts/abi.json + contract address
# copy address → .env  CONTRACT_ADDRESS=0x...

# compile only (no deploy):
python scripts/deploy.py --dry-run

# via Remix alternative: https://remix.ethereum.org → paste contracts/ContentRegistry.sol
# → Environment: Injected Provider (MetaMask on Amoy) → Deploy → copy address
```

Explorer: `https://amoy.polygonscan.com/address/<CONTRACT_ADDRESS>`

### 3. Run pipeline

```bash
# Full: face + live web search + on-chain
python -m app.main --image samples/test.jpg

# With tamper demo (shows why blockchain matters)
python -m app.main --image samples/test.jpg --tamper-demo

# Face + search only (no blockchain, good for testing)
python -m app.main --image samples/test.jpg --skip-blockchain

# Fully offline (no keys at all) — uses mock candidates
python -m app.main --image samples/test.jpg --mock-search --skip-blockchain --tamper-demo

# Tune threshold
python -m app.main --image samples/test.jpg --threshold 0.70 --verbose
```

**Expected CLI:**

```
╭──────────────────────────────────────────╮
│  FACE → WEB → BLOCKCHAIN · HH GOA 2026   │
╰──────────────────────────────────────────╯

[1/5] Detecting face...          ✓ bbox=[...] 98.2%
[2/5] Generating embedding...    ✓ dim=512
[3/5] Searching web...           ✓ 12 candidates, 4 social
        #  Source         Title
        1  instagram.com  Technology Conference 2026
[4/5] Verifying candidates...
        Candidate #1  87.4%  ✓ MATCH
        ┌─ MATCH DISCOVERED ✓ ─┐  instagram.com  87.4%
[5/5] SHA-256...                 ✓ 0x8f31c9...
        Network: Polygon Amoy  Tx: 0x7a91...  Block: 12345678

        BLOCKCHAIN RE-VERIFICATION
        Local: 0x8f31c9...  Chain: 0x8f31c9...  ✓ VERIFIED

        ── TAMPER DEMO ──  title "2026"→"2027"  0x8f31... != 0x19ab...  ❌ TAMPER DETECTED
```

---

## How verification works

```
canonical payload {url, platform, title, image_url, similarity}
        ↓ sort_keys + separators=(',',':') + UTF-8
     SHA-256 → 0x… (bytes32)
        ↓
  registry.register(bytes32)  — Polygon Amoy
        ↓
  registry.getRecord(bytes32) / verify(bytes32)
        ↓
  recomputed == on-chain ?  →  VERIFIED / TAMPER DETECTED
```

Only the 32-byte hash goes on-chain — never the image.

Optional `app/content/perceptual.py:dhash` gives a 64-bit perceptual hash for near-duplicate tolerance (resize/compress) without extra deps.

---

## Smart contract

`contracts/ContentRegistry.sol` — 65 lines, MIT:

```solidity
register(bytes32 contentHash)                    // write
getRecord(bytes32) → (hash, registrant, timestamp, blockNumber, exists)  // read
verify(bytes32) → bool                           // read
totalRecords() → uint256
event ContentRegistered(bytes32 indexed, address indexed, uint256, uint256)
```

---

## Blockchain

| | |
|---|---|
| Network | Polygon Amoy Testnet |
| Chain ID | 80002 |
| Currency | POL (free via faucet) |
| RPC (primary) | `https://rpc-amoy.polygon.technology` |
| Fallbacks | `polygon-amoy.drpc.org`, `polygon-amoy-bor-rpc.publicnode.com` (auto) |
| Explorer | https://amoy.polygonscan.com |
| Faucet | https://faucet.polygon.technology/ |
| Contract | `contracts/ContentRegistry.sol` |

---

## Project structure

```
face-detection/
├── app/
│   ├── main.py                 # 5-step orchestrator (CLI)
│   ├── config.py               # env + free RPC fallbacks
│   ├── face/detector.py        # InsightFace buffalo_l + bbox/score/kps
│   ├── face/embedder.py        # L2 normalisation
│   ├── face/similarity.py      # cosine + threshold
│   ├── search/lens.py          # SerpApi Google Lens (free 100/mo, retry)
│   ├── search/parser.py        # visual_matches/exact_matches → dedup
│   ├── search/ranking.py       # social priority
│   ├── content/extractor.py    # fetch image → face check (graceful)
│   ├── content/canonicalizer.py# sorted JSON → UTF-8 bytes
│   ├── content/hashing.py      # SHA-256 → 0x bytes32
│   ├── content/perceptual.py   # dHash (Pillow only, no extra dep)
│   ├── blockchain/client.py    # web3.py + ABI + RPC failover
│   ├── blockchain/registry.py  # register / verify / getRecord
│   ├── blockchain/verifier.py  # local vs chain
│   └── cli/display.py          # Rich panels
├── contracts/ContentRegistry.sol
├── scripts/deploy.py            # solc 0.8.20 → Amoy (free)
├── tests/  (pytest, no keys needed)
├── samples/
├── requirements.txt
├── .env.example
└── LICENSE (MIT)
```

---

## Tests

```bash
pytest -v
pytest --cov=app tests/
pytest tests/test_hashing.py -v  # determinism + tamper
pytest tests/test_face.py -v     # cosine
pytest tests/test_search.py -v   # parser + ranking
pytest tests/test_blockchain.py -v
```

All tests run offline — no RPC, no SerpApi key.

---

## Limitations (honest)

- SerpApi free = 100/mo; 429 shows retry hint. Use `--mock-search` for CI.
- Social pages often need login; deleted/private/403/robots → skipped gracefully, next candidate tried.
- Face accuracy depends on image quality/pose/age; threshold is tunable (`FACE_MATCH_THRESHOLD`).
- Public data only; blockchain stores fingerprint, not image.

---

## License

MIT — see `LICENSE`.
