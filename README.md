# Identity Signal — Face → Web → Blockchain

> **AI-powered face discovery with tamper-evident blockchain verification.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?logo=flask&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636?logo=solidity&logoColor=white)
![Polygon](https://img.shields.io/badge/Polygon-Amoy_Testnet-8247E5?logo=polygon&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## What Is This?

**Identity Signal** is a system that:
1. **Detects a face** in an uploaded image
2. **Searches the web** to find matching faces on social media and websites
3. **Verifies the match** using AI face comparison
4. **Anchors the proof** on the blockchain for tamper-evident verification

```
Your Photo → Find Face → Search Web → Verify Match → Blockchain Proof
```

**No paid services. No heavy infrastructure. Just open-source tools.**

---

## Table of Contents

- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [How It Works](#how-it-works)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Pipeline Steps](#pipeline-steps)
- [Search Strategy](#search-strategy)
- [Blockchain Verification](#blockchain-verification)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Security Notes](#security-notes)
- [License](#license)

---

## Quick Start (5 Minutes)

### Prerequisites

- Python 3.8+
- A SerpApi key (free at [serpapi.com](https://serpapi.com/users/sign_up))
- A Polygon Amoy wallet with free POL (from [faucet.polygon.technology](https://faucet.polygon.technology/))

### Installation

```bash
# Clone the repository
git clone https://github.com/Brajesh9373/fb-find.git
cd fb-find

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see below)
```

### Configure .env

```env
# Required: SerpApi key (free at serpapi.com)
SERPAPI_KEY=your_serpapi_key_here

# Required: Polygon Amoy wallet private key
PRIVATE_KEY=0x_your_wallet_private_key

# Optional: Contract address (or deploy your own)
CONTRACT_ADDRESS=0x082F1e254E3E68fd6b15Df24642607dfCEc47252

# Optional: Face matching thresholds
FACE_MATCH_THRESHOLD=0.60
PROBABLE_MATCH_THRESHOLD=0.45
```

### Run the System

```bash
# Start web server
python run_web.py
```

Open http://localhost:5000 in your browser and upload a face image.

---

## How It Works

### The 5-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UPLOAD FACE IMAGE                               │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: FACE DETECTION                                                │
│  • Detects face in image using InsightFace                              │
│  • Extracts bounding box and confidence score                           │
│  • Crops face region for search                                         │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: FACE EMBEDDING                                                │
│  • Converts face to 512-dimensional vector (ArcFace)                    │
│  • L2-normalized for cosine similarity comparison                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: WEB SEARCH                                                    │
│  • Searches BOTH full image AND cropped face                            │
│  • Uses Google Lens + Google Reverse Image + Yandex                     │
│  • Merges and deduplicates results                                      │
│  • Ranks social media platforms higher                                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: FACE VERIFICATION                                             │
│  • Downloads candidate images from search results                       │
│  • Detects faces in each candidate                                      │
│  • Compares embeddings using cosine similarity                          │
│  • Assigns confidence tier: HIGH / PROBABLE / UNMATCHED                 │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: BLOCKCHAIN PROOF                                              │
│  • Creates canonical JSON of matched result                             │
│  • Generates SHA-256 fingerprint                                        │
│  • Registers fingerprint on Polygon Amoy                                │
│  • Re-verifies: local hash == on-chain hash                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Face Detection** | InsightFace with buffalo_l model, 512-dim ArcFace embeddings |
| **Hybrid Search** | Google Lens + Google Reverse Image + Yandex (3 engines) |
| **Dual Search** | Searches both full image AND cropped face for maximum coverage |
| **Face Verification** | Cosine similarity with configurable thresholds |
| **Blockchain Proof** | SHA-256 fingerprint on Polygon Amoy testnet |
| **Tamper Detection** | Demonstrates hash mismatch when data is modified |
| **Live Progress** | SSE streaming shows real-time pipeline status |
| **Web UI** | Drag-and-drop upload with dark theme |
| **CLI Mode** | Rich terminal output for demos |

### Confidence Tiers

| Tier | Threshold | Meaning |
|------|-----------|---------|
| **HIGH** | ≥ 60% | Strong face match - same person |
| **PROBABLE** | 45-59% | Possible match - similar face |
| **UNMATCHED** | < 45% | No match - different person |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │   Flask Web UI      │    │   Rich CLI          │            │
│  │   (SSE Streaming)   │    │   (Terminal)        │            │
│  └─────────┬───────────┘    └─────────┬───────────┘            │
└────────────┼──────────────────────────┼─────────────────────────┘
             │                          │
             └──────────┬───────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE LAYER                              │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Face    │→│ Embedding│→│  Search  │→│ Verify   │        │
│  │  Detect  │  │          │  │          │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │              │             │             │               │
│       ▼              ▼             ▼             ▼               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Blockchain Registration                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
             │                          │
             ▼                          ▼
┌──────────────────────┐    ┌──────────────────────┐
│   InsightFace        │    │   SerpApi            │
│   (Local)            │    │   (Google Lens)      │
└──────────────────────┘    └──────────────────────┘
             │                          │
             ▼                          ▼
┌──────────────────────┐    ┌──────────────────────┐
│   catbox.moe         │    │   Polygon Amoy       │
│   (Image Hosting)    │    │   (Blockchain)       │
└──────────────────────┘    └──────────────────────┘
```

---

## Pipeline Steps

### Stage 1: Face Detection

**What happens:**
- InsightFace `buffalo_l` model detects faces in the image
- Returns bounding box coordinates and confidence score
- Crops the face region with padding for search

**Output:**
```json
{
  "faces_count": 1,
  "confidence": 0.9025,
  "bbox": [146, 88, 356, 368],
  "embedding_dim": 512
}
```

### Stage 2: Face Embedding

**What happens:**
- ArcFace converts the face crop into a 512-dimensional vector
- Vector is L2-normalized for cosine similarity comparison

**Output:**
```json
{
  "status": "success",
  "norm": 1.0000
}
```

### Stage 3: Web Search

**What happens:**
1. Uploads image to catbox.moe for public URL
2. Searches with **cropped face** (finds similar faces)
3. Searches with **full image** (finds similar scenes)
4. Uses 3 search engines: Google Lens, Google Reverse Image, Yandex
5. Merges results and removes duplicates
6. Ranks social platforms higher (Instagram > Facebook > X > ...)

**Output:**
```json
{
  "candidates_count": 67,
  "social_count": 25,
  "face_crop_count": 45,
  "full_image_count": 52,
  "candidates": [...]
}
```

### Stage 4: Face Verification

**What happens:**
- Downloads top candidate images
- Detects faces in each candidate
- Compares embeddings using cosine similarity
- Assigns confidence tier to each match

**Output:**
```json
{
  "matched": true,
  "platform": "instagram.com",
  "similarity": 0.830,
  "confidence_tier": "HIGH",
  "all_matches": [
    {"source": "instagram.com", "similarity": 0.830, "tier": "HIGH"},
    {"source": "facebook.com", "similarity": 0.716, "tier": "HIGH"}
  ]
}
```

### Stage 5: Blockchain Proof

**What happens:**
1. Creates canonical JSON of matched result
2. Generates SHA-256 fingerprint
3. Registers fingerprint on Polygon Amoy smart contract
4. Reads back on-chain record
5. Compares local hash with on-chain hash

**Output:**
```json
{
  "verified": true,
  "content_hash": "0x28bd86ce532835d48650206db095d9227f75da9f6df877d28166679a0105830e",
  "tx_hash": "0x...",
  "block_number": 46802087,
  "tamper_demo": {
    "original_hash": "0x28bd...",
    "tampered_hash": "0x4783...",
    "hashes_equal": false
  }
}
```

---

## Search Strategy

### Multi-Engine Search

The system uses **3 search engines** for maximum coverage:

| Engine | Source | Strength |
|--------|--------|----------|
| Google Lens | SerpApi | Visual similarity |
| Google Reverse Image | SerpApi | Exact matches |
| Yandex Images | SerpApi | Face-focused |

### Dual Search

The system searches with **both**:

1. **Cropped Face** - Finds similar faces (same person, different photos)
2. **Full Image** - Finds similar scenes (same context, background)

Results are merged and deduplicated. Candidates found by **both** searches get higher priority.

### Social Platform Priority

Results are ranked with social platforms first:

```
Instagram > Facebook > X/Twitter > LinkedIn > TikTok > YouTube > Pinterest
```

---

## Blockchain Verification

### Smart Contract

**ContentRegistry.sol** stores fingerprint records on Polygon Amoy:

```solidity
struct Record {
    bytes32 contentHash;    // SHA-256 fingerprint
    address registrant;     // Wallet that registered
    uint256 timestamp;      // Registration time
    uint256 blockNumber;    // Block number
    bool exists;            // Existence flag
}
```

### Contract Functions

| Function | Type | Description |
|----------|------|-------------|
| `register(bytes32)` | Write | Register a new fingerprint |
| `verify(bytes32)` | Read | Check if hash exists |
| `getRecord(bytes32)` | Read | Get full record details |
| `totalRecords()` | Read | Get total registrations |

### Network Details

| Property | Value |
|----------|-------|
| Network | Polygon Amoy Testnet |
| Chain ID | 80002 |
| Currency | POL (free via faucet) |
| Explorer | https://amoy.polygonscan.com |
| Faucet | https://faucet.polygon.technology/ |

### Verification Process

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Matched Post   │────▶│  Canonical JSON │────▶│   SHA-256 Hash  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  VERIFIED ✓     │◀────│  Compare Hashes │◀────│  Register on    │
│  (or TAMPERED)  │     │                 │     │  Polygon Amoy   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERPAPI_KEY` | Yes | - | SerpApi key (free at serpapi.com) |
| `PRIVATE_KEY` | Yes | - | Polygon wallet private key |
| `CONTRACT_ADDRESS` | No | Pre-deployed | Smart contract address |
| `POLYGON_RPC_URL` | No | drpc.org | RPC endpoint |
| `CHAIN_ID` | No | 80002 | Polygon Amoy chain ID |
| `FACE_MATCH_THRESHOLD` | No | 0.60 | HIGH match threshold |
| `PROBABLE_MATCH_THRESHOLD` | No | 0.45 | PROBABLE match threshold |
| `MAX_CANDIDATES` | No | 30 | Max search results |
| `MAX_CANDIDATES_TO_VERIFY` | No | 12 | Max candidates to check |
| `SEARCH_TIMEOUT` | No | 30 | Search timeout (seconds) |
| `INSIGHTFACE_MODEL` | No | buffalo_l | Face model (buffalo_l, buffalo_s) |

### Threshold Tuning

Lower thresholds = more matches (but more false positives)
Higher thresholds = fewer matches (but more accurate)

```env
# Strict (fewer, more accurate matches)
FACE_MATCH_THRESHOLD=0.70
PROBABLE_MATCH_THRESHOLD=0.55

# Balanced (default)
FACE_MATCH_THRESHOLD=0.60
PROBABLE_MATCH_THRESHOLD=0.45

# Lenient (more matches, more false positives)
FACE_MATCH_THRESHOLD=0.50
PROBABLE_MATCH_THRESHOLD=0.35
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface |
| GET | `/api/health` | Health check |
| POST | `/api/analyze` | Run pipeline (SSE stream) |

### POST /api/analyze

**Request (multipart/form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Face image (JPG, PNG, WebP) |
| `threshold` | Float | No | Override match threshold |
| `skip_blockchain` | Boolean | No | Skip blockchain step |
| `tamper_demo` | Boolean | No | Show tamper demo |
| `mock_search` | Boolean | No | Use mock results (offline) |

**Response (SSE stream):**

```
event: step_started
data: {"step": "face_detection", "message": "Loading model..."}

event: step_progress
data: {"step": "face_detection", "message": "Detecting faces..."}

event: step_done
data: {"step": "face_detection", "data": {...}}

...

event: pipeline_done
data: {"success": true, "error": null}
```

---

## Project Structure

```
fb-find/
├── app/
│   ├── face/              # Face detection & embedding
│   │   ├── detector.py    # InsightFace wrapper
│   │   ├── embedder.py    # L2 normalization
│   │   └── similarity.py  # Cosine similarity + tiers
│   │
│   ├── search/            # Web search engines
│   │   ├── engine.py      # Hybrid search engine
│   │   ├── engines/       # Individual engines
│   │   │   ├── google_lens.py
│   │   │   ├── google_reverse_image.py
│   │   │   └── yandex.py
│   │   ├── parser.py      # Result parsing
│   │   ├── ranking.py     # Social priority ranking
│   │   └── merger.py      # Multi-engine merger
│   │
│   ├── content/           # Image processing
│   │   ├── extractor.py   # Download + face check
│   │   ├── canonicalizer.py  # Deterministic JSON
│   │   └── hashing.py     # SHA-256 fingerprint
│   │
│   ├── blockchain/        # Polygon integration
│   │   ├── client.py      # Web3 connection
│   │   ├── registry.py    # Smart contract interface
│   │   └── verifier.py    # Hash comparison
│   │
│   ├── web/               # Flask web app
│   │   ├── routes.py      # API endpoints
│   │   ├── pipeline.py    # Pipeline orchestration
│   │   ├── templates/     # HTML templates
│   │   └── static/        # CSS, JS, media
│   │
│   ├── cli/               # CLI display
│   │   └── display.py     # Rich terminal output
│   │
│   ├── config.py          # Configuration
│   └── main.py            # CLI entry point
│
├── contracts/
│   ├── ContentRegistry.sol  # Smart contract
│   └── abi.json             # Contract ABI
│
├── scripts/
│   └── deploy.py            # Contract deployment
│
├── tests/                   # Pytest tests
├── samples/                 # Sample images
├── uploads/                 # User uploads (gitignored)
│
├── run_web.py              # Web server entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── LICENSE                 # MIT License
```

---

## Limitations

| Limitation | Details |
|------------|---------|
| **SerpApi Free Tier** | 100 searches/month. Use `--mock-search` for offline testing |
| **Social Media** | Instagram/Facebook often block scraping - many candidates show "No face found" |
| **Image Quality** | Accuracy depends on face angle, lighting, occlusion |
| **Single Face** | Only processes the primary (largest) face per image |
| **Temporary Hosting** | Images uploaded to catbox.moe (public, temporary) |
| **Testnet Only** | Polygon Amoy is a testnet - no real monetary value |

---

## Security Notes

- **NEVER** commit `.env` file with real keys
- **NEVER** share your private key
- The wallet key stays only in your local environment
- Blockchain stores only the hash, never the image
- Uploaded images are temporary and auto-deleted

---

## Running Tests

```bash
# All tests
pytest -v

# Specific test files
pytest tests/test_face.py -v      # Face similarity
pytest tests/test_search.py -v    # Search parsing
pytest tests/test_hashing.py -v   # Blockchain hashing
pytest tests/test_blockchain.py -v  # Contract interaction

# With coverage
pytest --cov=app tests/
```

---

## License

MIT License - see [LICENSE](LICENSE) file.

Built with:
- [InsightFace](https://github.com/deepinsight/insightface) - Face detection
- [SerpApi](https://serpapi.com) - Google Lens search
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [web3.py](https://web3py.readthedocs.io/) - Blockchain
- [Polygon Amoy](https://polygon.technology/) - Testnet

---

**Built for the signal, not the noise. Face → Web → Blockchain.**
