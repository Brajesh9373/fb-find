# Face → Web → Blockchain: Complete Project Documentation

> **HH Goa 2026 Shortlisting Task 3** — A pipeline that takes a face scan as input, identifies matching content on the web/social media, and verifies the discovered data using blockchain.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Data Flow](#3-data-flow)
4. [Module-by-Module Breakdown](#4-module-by-module-breakdown)
5. [Configuration & Environment](#5-configuration--environment)
6. [Web Interface](#6-web-interface)
7. [CLI Interface](#7-cli-interface)
8. [Smart Contract](#8-smart-contract)
9. [Testing](#9-testing)
10. [Known Limitations](#10-known-limitations)

---

## 1. Project Overview

### What It Does

The system takes a face image, detects the face, searches the web to find where that face appears on social media or other websites, and then records the discovery on the Polygon blockchain as a tamper-evident fingerprint.

### Pipeline Shape

```
Face Image Input
    → Face Detection (InsightFace/ArcFace)
    → Embedding Generation (512-dim vector)
    → Reverse Image Search (Google Lens via SerpApi)
    → Candidate Verification (download images, re-detect faces, compare similarity)
    → Blockchain Registration (SHA-256 fingerprint on Polygon Amoy)
    → Re-verification (compare local hash vs on-chain hash)
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Face Detection | InsightFace `buffalo_l` + ArcFace | Best open-source face recognition, MIT license, runs on CPU |
| Embedding | ArcFace (512-dim) via InsightFace | State-of-the-art face embeddings |
| Web Search | Google Lens via SerpApi | 100 free searches/month, genuine live search |
| Image Hosting | catbox.moe | Free, no API key needed for temporary image hosting |
| Blockchain | Solidity 0.8.20 + web3.py + Polygon Amoy | Free testnet, public RPC, 2-second blocks |
| Web Framework | Flask | Lightweight, no extra dependencies |
| CLI Output | Rich | Beautiful terminal UI with tables and colors |

### Key Constraints

- **All free-tier only** — no paid APIs, no GPU required
- **CPU-only** face detection (ONNX Runtime)
- **100 SerpApi searches/month** (free tier)
- **Polygon Amoy testnet** (chainId 80002) — free testnet POL via faucet

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Web (Flask)  │  │  CLI (Rich)  │  │  Windows Launcher    │  │
│  │  :5000        │  │  argparse    │  │  start.bat           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼─────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE LAYER                             │
│  app/web/pipeline.py  OR  app/main.py                          │
│  (SSE streaming)        (Rich terminal)                        │
│                                                                 │
│  Step 1: Face Detection    ← app/face/detector.py              │
│  Step 2: Embedding         ← app/face/embedder.py              │
│  Step 3: Web Search        ← app/search/lens.py                │
│  Step 4: Verification      ← app/content/extractor.py          │
│  Step 5: Blockchain        ← app/blockchain/registry.py        │
└─────────────────────────────────────────────────────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ InsightFace  │  │  SerpApi     │  │  Polygon Amoy RPC     │  │
│  │ (local CPU)  │  │  Google Lens │  │  (smart contract)     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐                             │
│  │ catbox.moe   │  │ Candidate    │                             │
│  │ (image host) │  │ websites     │                             │
│  └─────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
hhgoa_t3/
├── app/
│   ├── __init__.py              # Package init, version
│   ├── config.py                # Central configuration (env vars)
│   ├── main.py                  # CLI pipeline entry point
│   │
│   ├── face/                    # FACE MODULE
│   │   ├── __init__.py          # Exports FaceDetector, cosine_similarity
│   │   ├── detector.py          # InsightFace wrapper (singleton)
│   │   ├── embedder.py          # L2 normalization
│   │   └── similarity.py        # Cosine similarity + confidence tiers
│   │
│   ├── search/                  # SEARCH MODULE
│   │   ├── __init__.py          # Exports GoogleLensSearcher, rank_candidates
│   │   ├── lens.py              # SerpApi Google Lens integration
│   │   ├── parser.py            # Parse SerpApi JSON → candidate list
│   │   └── ranking.py           # Social platform priority ranking
│   │
│   ├── content/                 # CONTENT MODULE
│   │   ├── __init__.py
│   │   ├── extractor.py         # Download candidate images, extract faces
│   │   ├── canonicalizer.py     # Deterministic JSON for hashing
│   │   ├── hashing.py           # SHA-256 fingerprinting
│   │   └── perceptual.py        # dHash (perceptual hashing, currently unused)
│   │
│   ├── blockchain/              # BLOCKCHAIN MODULE
│   │   ├── __init__.py
│   │   ├── client.py            # web3.py connection, ABI loading, RPC fallbacks
│   │   ├── registry.py          # ContentRegistry contract interaction
│   │   └── verifier.py          # Local vs on-chain hash comparison
│   │
│   ├── web/                     # WEB MODULE
│   │   ├── __init__.py          # Flask app factory
│   │   ├── routes.py            # API endpoints
│   │   ├── pipeline.py          # SSE streaming pipeline
│   │   ├── templates/
│   │   │   └── index.html       # Frontend SPA
│   │   └── static/
│   │       ├── js/app.js        # Frontend JavaScript (SSE client)
│   │       └── css/style.css    # Dark theme styling
│   │
│   └── cli/
│       ├── __init__.py
│       └── display.py           # Rich terminal display helpers
│
├── contracts/
│   ├── ContentRegistry.sol      # Solidity smart contract
│   ├── abi.json                 # Contract ABI
│   └── bytecode.hex             # Compiled EVM bytecode
│
├── scripts/
│   ├── deploy.py                # Contract deployment script
│   └── test_diagnostics.py      # Full system diagnostic test
│
├── tests/
│   ├── test_hashing.py          # Hashing + canonicalization tests
│   ├── test_face.py             # Face similarity tests
│   ├── test_search.py           # Search parser + ranking tests
│   └── test_blockchain.py       # Blockchain verification tests
│
├── samples/                     # Sample images for testing
├── uploads/                     # Uploaded images (gitignored)
├── run_web.py                   # Flask server entry point
├── start.bat                    # Windows launcher menu
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Template for .env
├── .gitignore
├── LICENSE                      # MIT
├── README.md
└── task #3.md                   # Task specification
```

---

## 3. Data Flow

### End-to-End Data Flow (Web Interface)

```
USER                          SERVER                        EXTERNAL
 │                              │                              │
 │  POST /api/analyze           │                              │
 │  (multipart: image + opts)   │                              │
 │ ───────────────────────────> │                              │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Save image to     │                    │
 │                    │ uploads/ as       │                    │
 │                    │ {uuid}.{ext}      │                    │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ═══ STEP 1: FACE DETECTION ═══          │
 │                    ┌─────────┴─────────┐                    │
 │                    │ InsightFace reads  │                    │
 │                    │ image, detects     │                    │
 │                    │ faces, returns     │                    │
 │                    │ bbox + embedding   │                    │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ═══ STEP 2: EMBEDDING ═══               │
 │                    ┌─────────┴─────────┐                    │
 │                    │ L2-normalize the   │                    │
 │                    │ 512-dim embedding  │                    │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ═══ STEP 3: WEB SEARCH ═══              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Upload image to    │ ── catbox.moe ──> │
 │                    │ catbox.moe for     │ <── public URL ── │
 │                    │ public URL         │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Query SerpApi     │ ── SerpApi ──────> │
 │                    │ Google Lens with   │ <── JSON results ─ │
 │                    │ public image URL   │   (visual_matches) │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Parse results →    │                   │
 │                    │ candidate list     │                   │
 │                    │ Rank by social     │                   │
 │                    │ priority           │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ═══ STEP 4: VERIFICATION ═══            │
 │                    ┌─────────┴─────────┐                    │
 │                    │ For each candidate │                   │
 │                    │ (top 12):          │                   │
 │                    │  1. Download image │ ── candidate ───> │
 │                    │  2. Detect face    │ <── image bytes ──│
 │                    │  3. Compare cosine │                   │
 │                    │     similarity     │                   │
 │                    │  4. If sim >= 0.40 │                   │
 │                    │     → MATCH        │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ═══ STEP 5: BLOCKCHAIN ═══               │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Build canonical    │                   │
 │                    │ payload from match │                   │
 │                    │ data (url, platform│                   │
 │                    │ title, image_url,  │                   │
 │                    │ similarity)        │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ SHA-256 hash the   │                   │
 │                    │ canonical JSON     │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Submit register()  │ ── Polygon ─────> │
 │                    │ transaction to     │ <── tx receipt ── │
 │                    │ ContentRegistry    │                   │
 │                    │ smart contract     │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │                    ┌─────────┴─────────┐                    │
 │                    │ Re-read hash from  │ ── Polygon ─────> │
 │                    │ chain, compare     │ <── on-chain hash │
 │                    │ with local hash    │                   │
 │                    └─────────┬─────────┘                    │
 │                              │                              │
 │  SSE events streamed         │                              │
 │  throughout pipeline         │                              │
 │ <─────────────────────────── │                              │
 │                              │                              │
 │  Final JSON response         │                              │
 │  {success, steps, uploaded_  │                              │
 │   image_url}                 │                              │
 │ <─────────────────────────── │                              │
```

### Data Structures

#### Candidate (from SerpApi parsing)

```python
{
    "title": str,           # Page title or snippet
    "url": str,             # Web page URL where match was found
    "source": str,          # Domain name (e.g., "instagram.com")
    "thumbnail": str,       # Thumbnail URL from Google Lens
    "image_url": str,       # Full-size image URL
    "position": int,        # Rank position (1-indexed)
    "_raw": dict            # Original SerpApi response item (for debugging)
}
```

#### Canonical Payload (for blockchain hashing)

```python
{
    "url": str,             # Matched page URL
    "platform": str,        # Domain name (e.g., "instagram.com")
    "title": str,           # Page title
    "image_url": str,       # Image URL from the match
    "similarity": float     # Face similarity score (rounded to 4 decimals)
}
```

This dict is serialized to deterministic JSON (sorted keys, no whitespace, UTF-8), then SHA-256 hashed to produce a `bytes32` fingerprint for the blockchain.

#### Pipeline Result (API response)

```python
{
    "success": bool,
    "uploaded_image_url": str,    # "/uploads/{uuid}.{ext}"
    "steps": {
        "face_detection": {
            "status": "success" | "error",
            "bbox": [x1, y1, x2, y2],
            "confidence": float,
            "embedding_dim": int,
            "faces_count": int
        },
        "embedding": {
            "status": "success",
            "norm": float           # L2 norm (should be ~1.0)
        },
        "web_search": {
            "status": "success",
            "candidates_count": int,
            "social_count": int,
            "candidates": [...]     # Top 12 ranked candidates
        },
        "verification": {
            "status": "success",
            "matched": bool,
            "platform": str,
            "similarity": float,
            "url": str,
            "title": str,
            "image_url": str
        },
        "blockchain": {
            "status": "success" | "skipped",
            "content_hash": str,    # "0x..." SHA-256
            "tx_hash": str,
            "block_number": int,
            "contract_address": str,
            "network": str,
            "chain_id": int,
            "explorer_url": str,
            "verified": bool,       # Re-verification result
            "local_hash": str,
            "chain_hash": str,
            "tamper_demo": {...}    # Optional tamper demonstration
        }
    },
    "error": str | null
}
```

---

## 4. Module-by-Module Breakdown

### 4.1 Face Module (`app/face/`)

#### `detector.py` — Face Detection & Embedding

- **Class**: `FaceDetector` (singleton pattern — only one instance exists)
- **Model**: InsightFace `buffalo_l` (~300MB, downloaded on first run)
- **Provider**: ONNX Runtime CPU (`CPUExecutionProvider`)
- **Detection size**: 640×640 pixels
- **Output**: `FaceInfo` dataclass per detected face:
  ```python
  @dataclass
  class FaceInfo:
      bbox: list[int]        # [x1, y1, x2, y2] bounding box
      confidence: float      # Detection confidence (det_score)
      embedding: np.ndarray  # 512-dim float32 ArcFace embedding
      kps: np.ndarray | None # 5 facial keypoints (eyes, nose, mouth corners)
      age: int | None        # Estimated age
      gender: int | None     # Estimated gender (0=M, 1=F)
  ```
- **Detection flow**: Read image → resize to 640×640 → InsightFace `get()` → extract bbox, score, embedding → sort by (confidence DESC, bbox_area DESC)
- **Key methods**:
  - `detect(image_path)` — detect faces from file path
  - `detect_bytes(data)` — detect from raw image bytes
  - `detect_array(bgr_ndarray)` — detect from OpenCV BGR array
  - `detect_single(image_path)` — return only the best face
  - `get_largest_face_bytes(image_path)` — return largest face as JPEG bytes

#### `embedder.py` — Embedding Normalization

- `normalize(embedding)` — L2-normalize embedding vector, handle zero-norm edge case
- `get_normalized_embedding(face)` — extract + normalize from FaceInfo
- Used in pipeline: `from app.face.embedder import normalize as norm_emb`

#### `similarity.py` — Cosine Similarity & Confidence Tiers

- `cosine_similarity(a, b)` — standard cosine similarity (float64)
- Confidence tiers:
  - **HIGH**: similarity ≥ 0.40 (configurable via `FACE_MATCH_THRESHOLD`)
  - **PROBABLE**: similarity ≥ 0.30 (configurable via `PROBABLE_MATCH_THRESHOLD`)
  - **UNMATCHED**: similarity < 0.30
- `is_match(similarity)` — boolean for HIGH tier
- `is_probable_match(similarity)` — boolean for PROBABLE tier

### 4.2 Search Module (`app/search/`)

#### `lens.py` — Google Lens Search via SerpApi

- **Class**: `GoogleLensSearcher`
- **Flow**: Image → Upload to catbox.moe → Get public URL → Query SerpApi `google_lens` engine
- **catbox.moe upload**: `POST` to `https://catbox.moe/user/api.php` with `reqtype=fileupload` — returns public URL (e.g., `https://files.catbox.moe/abc123.jpg`)
- **SerpApi query**: `GET https://serpapi.com/search.json?engine=google_lens&url={image_url}&api_key={key}`
- **Retry logic**: 2 attempts, 2-second sleep between retries on timeout/connection errors
- **Rate limit**: HTTP 429 raises RuntimeError with suggestion to use `--mock-search`
- **Also has**: `search_from_url(image_url)` — skip catbox upload when image is already public

#### `parser.py` — SerpApi Response Parser

- Extracts candidates from SerpApi response sections: `visual_matches`, `exact_matches`, `knowledge_graph`
- For each item, extracts:
  - `link` → `url`
  - `title` or `snippet` → `title`
  - `source` → `source`
  - `thumbnail` or `image` → `thumbnail`, `image_url`
- Deduplicates by URL (preserves first occurrence)
- Re-assigns sequential position numbers after dedup

#### `ranking.py` — Social Platform Priority Ranking

- `PRIORITY_MAP`: Instagram=100, Facebook=90, X/Twitter=80, LinkedIn=70, Threads=60, TikTok=50, YouTube=40, Pinterest=30
- `rank_candidates(candidates)` — sort by (social_score DESC, position ASC)
- `is_social(url)` — boolean check if URL matches known social domain
- Social platforms appear first in results, then by original SerpApi ranking

### 4.3 Content Module (`app/content/`)

#### `extractor.py` — Candidate Image Download & Face Extraction

- **`fetch_image_bytes(url, timeout=15)`**:
  - Downloads image with browser-like User-Agent
  - Validates: Content-Type header, minimum 128 bytes, PIL image verification
  - Returns raw bytes or None

- **`fetch_og_image_url(page_url, timeout=6)`**:
  - Fetches first 100KB of candidate page HTML
  - Extracts `og:image` or `twitter:image` meta tags via 5 regex patterns
  - Returns high-resolution image URL if found

- **`try_candidate_images(candidate)`**:
  - Image source priority: `image_url` → `og:image` (if enabled) → `thumbnail`
  - Deduplicates URLs, fetches each, returns list of downloaded byte payloads

- **`extract_face_from_candidate(candidate, detector, query_emb=None)`**:
  - Downloads candidate images
  - If `query_emb` provided: scans ALL faces, returns the one with highest cosine similarity
  - If no `query_emb`: returns the largest detected face
  - Returns `(FaceInfo | None, bytes | None)`

- **`verify_single_candidate(candidate, detector, query_emb, threshold)`**:
  - Extract face → compute similarity → classify tier
  - Returns `(similarity, tier, candidate)`

- **`verify_candidates_concurrent(candidates, detector, query_emb, threshold, max_workers=4)`**:
  - Uses `ThreadPoolExecutor(max_workers=4)` for parallel downloads/verification
  - Results sorted by similarity descending
  - **Note**: This function exists but is currently unused in the pipeline (sequential loop is used instead)

#### `canonicalizer.py` — Deterministic JSON for Hashing

- `canonicalize(data)` — JSON with sorted keys, no whitespace, `ensure_ascii=False`, UTF-8
- `build_canonical_payload(url, platform, title, image_url, similarity, ...)` — builds the dict that will be hashed
- `similarity` rounded to 4 decimal places (prevents floating-point noise from changing hash)

#### `hashing.py` — SHA-256 Fingerprinting

- `sha256_hex(data: bytes) → str` — standard SHA-256
- `fingerprint_canonical(data: dict) → str` — canonical JSON → SHA-256 → `0x`-prefixed hex
- `fingerprint_bytes(data: bytes) → str` — raw bytes → SHA-256 → `0x`-prefixed hex
- `to_bytes32(hex_str) → bytes` — convert `0x...` hex to 32-byte value for Solidity `bytes32`

#### `perceptual.py` — Perceptual Hashing (dHash)

- `dhash(image_bytes, hash_size=8)` — 64-bit difference hash using Pillow + numpy
  - Resizes to `(hash_size+1) × hash_size` grayscale
  - Computes horizontal gradient between adjacent pixels
  - Packs into hex string
- `hamming(a, b)` — Hamming distance between two dHashes
- **Currently unused in the pipeline** — available for future use (e.g., detecting re-uploaded/cropped versions of same image)

### 4.4 Blockchain Module (`app/blockchain/`)

#### `client.py` — Web3 Connection & Utilities

- `load_abi()` — loads ABI from `contracts/abi.json`, falls back to embedded `MINIMAL_ABI`
- `get_w3(rpc_url)` — creates Web3 instance, tries primary RPC + 5 public fallbacks with 10-second timeout
  - Primary: `https://rpc-amoy.polygon.technology`
  - Fallbacks: `polygon-amoy.drpc.org`, `publicnode.com`, etc.
- `get_account(w3, private_key)` — derives account from private key

#### `registry.py` — Smart Contract Interaction

- **Class**: `ContentRegistry`
- **Contract functions used**:
  - `register(bytes32 hash)` — register a content hash on-chain
  - `verify(bytes32 hash) → bool` — check if hash exists on-chain
  - `getRecord(bytes32 hash) → (hash, registrant, timestamp, blockNumber, exists)`
- **Transaction handling**:
  - EIP-1559 transactions (type 2)
  - Gas estimation with 20% buffer
  - `maxFeePerGas`: 50 gwei, `maxPriorityFeePerGas`: 30 gwei
  - Pre-checks for duplicate registration (skips tx if already registered)
  - Waits for receipt with 120-second timeout
- **Returns**: `TxReceipt` dataclass with tx_hash, block_number, contract_address, content_hash, status

#### `verifier.py` — Re-verification Logic

- `verify_local_vs_chain(local_hash, chain_exists, chain_hash)` → `VerificationResult`
  - **Verified**: local hash matches on-chain hash
  - **Tampered**: hashes differ (data has been modified)
  - **Not found**: hash doesn't exist on-chain

### 4.5 Web Module (`app/web/`)

#### `__init__.py` — Flask App Factory

- Creates Flask app with:
  - Templates from `app/web/templates/`
  - Static files from `app/web/static/`
  - Upload directory at project root `/uploads/` (created if missing)
  - Max upload size: 16MB
- Registers `main_bp` blueprint

#### `routes.py` — API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves `index.html` template |
| `/api/health` | GET | Health check: `{"status": "ok"}` |
| `/uploads/<filename>` | GET | Serves uploaded images |
| `/api/analyze` | POST | Main pipeline endpoint |

**`POST /api/analyze`**:
- Accepts `multipart/form-data` with:
  - `image` (file) — required
  - `tamper_demo` (string "true"/"false") — default "true"
  - `skip_blockchain` (string "true"/"false") — default "false"
  - `mock_search` (string "true"/"false") — default "false"
  - `threshold` (string float) — optional override
- Validates file type (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.gif`)
- Saves to `uploads/{uuid}.{ext}`
- Runs pipeline, returns JSON result with `uploaded_image_url`

#### `pipeline.py` — SSE Streaming Pipeline

- `run_pipeline_stream(image_path, ...)` — generator yielding SSE events
- Event types: `step_started`, `step_progress`, `step_done`, `step_error`, `pipeline_done`
- 5-step pipeline matching the CLI version
- Includes mock search support (`_mock_candidates()`)
- Includes tamper demo (modifies title, shows hash differs)

### 4.6 CLI Module (`app/cli/`)

#### `display.py` — Rich Terminal Display

- `banner()` — ASCII art header
- `step(n, total, msg)` — progress indicator
- `success(msg)`, `warning(msg)`, `error(msg)`, `info(msg)` — colored output
- `match_box(...)` — formatted match result box
- `blockchain_box(...)` — blockchain transaction details
- `verification_box(...)` — verification result
- `candidates_table(candidates)` — formatted table of search results
- `top_matches_table(matches)` — similarity scores table

---

## 5. Configuration & Environment

### Environment Variables (`.env`)

```bash
# Required for web search
SERPAPI_KEY=your_serpapi_key_here          # Free: 100 searches/month

# Required for blockchain
PRIVATE_KEY=your_wallet_private_key        # Polygon Amoy wallet
CONTRACT_ADDRESS=0x082F...                 # Deployed ContentRegistry address

# Optional overrides
POLYGON_RPC_URL=https://rpc-amoy.polygon.technology
FACE_MATCH_THRESHOLD=0.40                  # HIGH confidence threshold
FACE_MATCH_THRESHOLD=0.65                  # Default in config.py
PROBABLE_MATCH_THRESHOLD=0.30              # PROBABLE confidence threshold
MAX_CANDIDATES=30                          # Max candidates from search
MAX_CANDIDATES_TO_VERIFY=12                # Max candidates to face-verify
SEARCH_TIMEOUT=30                          # SerpApi timeout (seconds)
CHAIN_ID=80002                             # Polygon Amoy testnet
```

### Config Loading (`app/config.py`)

- Uses `python-dotenv` to load `.env` from project root
- All values accessible as module-level constants: `config.SERPAPI_KEY`, `config.FACE_MATCH_THRESHOLD`, etc.
- Fallbacks provided for optional values

### Dependencies (`requirements.txt`)

```
insightface==0.7.3          # Face detection + ArcFace embeddings
onnxruntime==1.19.2         # ML inference runtime (CPU)
opencv-python==4.10.0.84    # Image processing
numpy<2.0                   # Numerical computing
Pillow>=10.0                # Image I/O (perceptual hashing)
requests>=2.31              # HTTP client
python-dotenv>=1.0          # .env loading
rich>=13.0                  # CLI terminal UI
flask>=3.0                  # Web framework
web3>=7.0                   # Ethereum/Polygon interaction
py-solc-x>=2.0              # Solidity compiler
pytest>=8.0                 # Testing
pytest-cov>=5.0             # Coverage
```

---

## 6. Web Interface

### Frontend Architecture

- **Single-page application** (SPA) — all in `index.html` + `app.js` + `style.css`
- **No build step** — vanilla HTML/CSS/JS, no npm/webpack/vite
- **Dark theme** — CSS variables, cyan primary color, responsive design

### User Flow

1. **Upload**: Drag-drop or click to select image → preview shown via `FileReader` data URL
2. **Options**: Toggle tamper demo, skip blockchain, mock search
3. **Analyze**: Click button → `POST /api/analyze` with multipart form data
4. **Progress**: 5-step progress indicator updated via SSE events
5. **Results**: 5 result cards dynamically populated with pipeline output
6. **Error**: Error card shown if pipeline fails

### SSE Streaming

The frontend uses `fetch()` with streaming response reading:

```javascript
const response = await fetch('/api/analyze', { method: 'POST', body: formData });
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    // Parse SSE events: "event: step_started\ndata: {...}\n\n"
    // Update DOM based on event type
}
```

### Result Cards

Each pipeline step has its own result card:
- **Face Detection**: Faces count, confidence %, bounding box, embedding dimension, uploaded image link
- **Embedding**: L2 norm value, normalization status
- **Web Search**: Candidates count, social media count, candidates table (source, title, type)
- **Verification**: Match/no-match badge, platform, similarity %, matched URL
- **Blockchain**: Network, content hash, tx hash (linked to Polygonscan), block number, contract address, explorer link, tamper demo comparison

---

## 7. CLI Interface

### Usage

```bash
# Basic run
python -m app.main --image samples/test.jpg

# With options
python -m app.main --image samples/test.jpg \
    --threshold 0.60 \
    --skip-blockchain \
    --tamper-demo \
    --verbose

# Offline demo (no SerpApi key needed)
python -m app.main --image samples/test.jpg \
    --mock-search \
    --skip-blockchain \
    --tamper-demo
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--image` | (required) | Input face image path |
| `--threshold` | 0.40 | HIGH confidence threshold |
| `--probable-threshold` | 0.30 | PROBABLE confidence threshold |
| `--strict` | false | Disable probable match fallback |
| `--skip-blockchain` | false | Skip on-chain registration |
| `--tamper-demo` | false | Demonstrate tamper detection |
| `--max-verify` | 12 | Max candidates to verify |
| `--verbose` / `-v` | false | Debug logging |
| `--mock-search` | false | Use mock results (no network) |

### CLI Output Example

```
═══════════════════════════════════════════════════
  🔍 Face → Web → Blockchain
  Face Identification → Web Discovery → On-Chain Verification
═══════════════════════════════════════════════════

[1/5] 👤 Detecting face ...
  ✓ Found 1 face (confidence: 98.2%)

[2/5] 🧬 Computing embedding ...
  ✓ 512-dim ArcFace embedding (norm: 1.0000)

[3/5] 🌐 Searching web (Google Lens via SerpApi) ...
  ✓ Found 15 candidates (5 social)

  ┌─ Top Candidates ─────────────────────────────┐
  │ # │ Source      │ Title                  │ Type│
  │ 1 │ instagram   │ Tech Conference 2026   │Social│
  │ 2 │ linkedin    │ Professional profile   │Social│
  │ 3 │ example.com │ Photography blog       │ Web  │
  └──────────────────────────────────────────────┘

[4/5] ✅ Verifying faces ...
  ✓ MATCH FOUND
    Platform: instagram.com
    Similarity: 87.3%
    URL: https://www.instagram.com/p/...

[5/5] ⛓️ Blockchain registration ...
  ✓ Registered on Polygon Amoy
    TX: 0xabc123...
    Block: 12345
    Explorer: https://amoy.polygonscan.com/tx/0xabc123...

  ✓ Re-verified: Local hash matches on-chain fingerprint
```

---

## 8. Smart Contract

### Solidity Contract (`contracts/ContentRegistry.sol`)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ContentRegistry {
    struct Record {
        bytes32 hash;
        address registrant;
        uint256 timestamp;
        uint256 blockNumber;
        bool exists;
    }

    mapping(bytes32 => Record) private records;
    uint256 public totalRecords;

    event ContentRegistered(bytes32 indexed hash, address registrant, uint256 timestamp);

    function register(bytes32 contentHash) external { ... }
    function verify(bytes32 contentHash) external view returns (bool) { ... }
    function getRecord(bytes32 contentHash) external view returns (bytes32, address, uint256, uint256, bool) { ... }
}
```

### Contract Functions

- **`register(bytes32)`** — stores hash, registrant address, timestamp, block number. Emits `ContentRegistered` event.
- **`verify(bytes32) → bool`** — returns true if hash exists on-chain.
- **`getRecord(bytes32) → (hash, registrant, timestamp, blockNumber, exists)`** — returns full record.
- **`totalRecords()`** — total number of registered records.

### Deployment

```bash
# Deploy to Polygon Amoy
python scripts/deploy.py

# Dry run (no transaction)
python scripts/deploy.py --dry-run

# Custom RPC/key
python scripts/deploy.py --rpc https://custom-rpc.com --private-key 0x...
```

- Uses `py-solc-x` to compile Solidity 0.8.20
- Saves `contracts/deployed.json` with address, tx hash, block number
- Saves `contracts/abi.json` for runtime use

### Contract Address

Deployed on Polygon Amoy testnet:
- Address: `0x082F1e254E3E68fd6b15Df24642607dfCEc47252`
- Explorer: `https://amoy.polygonscan.com/address/0x082F...`

---

## 9. Testing

### Test Files

| File | Tests | What it covers |
|------|-------|---------------|
| `tests/test_hashing.py` | 8 tests | Canonical JSON determinism, SHA-256, bytes32 conversion, local vs chain verification |
| `tests/test_face.py` | 8 tests | Cosine similarity (identical, orthogonal, opposite, zero), threshold checks, confidence tiers |
| `tests/test_search.py` | 4 tests | SerpApi result parsing, URL deduplication, social ranking order |
| `tests/test_blockchain.py` | 4 tests | bytes32 validation, verify_local_vs_chain (verified/tampered/not found) |

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_hashing.py -v
```

### Diagnostic Script

```bash
python scripts/test_diagnostics.py
```

Checks: env vars, SerpApi key validity, RPC endpoints, wallet balance, contract deployment, InsightFace detection + embedding on sample image, hashing + canonicalization.

---

## 10. Known Limitations

### Free Tier Constraints

- **SerpApi**: 100 searches/month free. Each input image = 1 search. 429 errors on rate limit.
- **catbox.moe**: Uploaded images persist publicly (privacy concern). No cleanup mechanism.
- **Polygon Amoy**: Testnet only. Data is not on mainnet. Testnet POL needed from faucet.

### Technical Limitations

- **CPU-only**: Face detection runs on CPU (ONNX Runtime). No GPU acceleration.
- **Single face**: Currently processes only the first (best) face from the input image.
- **Sequential verification**: Candidate verification runs sequentially (not in parallel), even though `verify_candidates_concurrent()` exists.
- **Threshold sensitivity**: `FACE_MATCH_THRESHOLD=0.40` is relatively low — may produce false positives with similar-looking people.
- **Stale User-Agent**: Hardcoded Chrome 122 on Linux for candidate image downloads — will become outdated.
- **No rate limiting**: No outbound request rate limiting to candidate websites.
- **No upload cleanup**: Orphaned files accumulate in `/uploads/` if process crashes.

### Search Limitations

- Google Lens finds **visually similar images**, not necessarily the same person.
- Results depend on what's indexed in Google's database — private/deleted content won't appear.
- Social media platforms may block scrapers — candidate image downloads may fail (403, 404).
- `og:image` extraction limited to first 100KB of HTML and 5 regex patterns.

### Blockchain Limitations

- Stores only a **hash fingerprint**, not the actual image or metadata.
- If the on-chain record is lost (contract upgrade, chain reorg), verification fails.
- Gas costs are minimal on testnet but would matter on mainnet.
- `similarity` rounded to 4 decimal places — same match could produce different hashes if run at different times (if similarity differs by >0.0001).
