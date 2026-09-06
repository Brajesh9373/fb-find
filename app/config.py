"""Central configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Always load .env from the project root, regardless of cwd
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# ── API Keys ──────────────────────────────────────────────────────────
SERPAPI_KEY: str | None = os.getenv("SERPAPI_KEY")

# ── Blockchain ────────────────────────────────────────────────────────
# All free — no paid RPC needed.  Primary + fallbacks are public endpoints.
POLYGON_RPC_URL: str = os.getenv(
    "POLYGON_RPC_URL", "https://rpc-amoy.polygon.technology"
)
# Public fallbacks (auto-tried if primary is down)
RPC_FALLBACKS: list[str] = [
    "https://rpc-amoy.polygon.technology",
    "https://polygon-amoy.drpc.org",
    "https://polygon-amoy-bor-rpc.publicnode.com",
    "https://rpc.ankr.com/polygon_amoy",
    "https://80002.rpc.thirdweb.com",
]
PRIVATE_KEY: str | None = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS: str | None = os.getenv("CONTRACT_ADDRESS")

CHAIN_ID: int = int(os.getenv("CHAIN_ID", "80002"))
CHAIN_NAME: str = os.getenv("CHAIN_NAME", "Polygon Amoy")
CURRENCY: str = os.getenv("CURRENCY", "POL")

# ── Face Matching ─────────────────────────────────────────────────────
FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.40"))
PROBABLE_MATCH_THRESHOLD: float = float(os.getenv("PROBABLE_MATCH_THRESHOLD", "0.30"))
ALLOW_PROBABLE_MATCH: bool = os.getenv("ALLOW_PROBABLE_MATCH", "true").lower() == "true"
ENABLE_OG_IMAGE_EXTRACTION: bool = os.getenv("ENABLE_OG_IMAGE_EXTRACTION", "true").lower() == "true"

# Domain priority for ranking social candidates (higher = more priority)
SOCIAL_DOMAINS: list[str] = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "threads.net",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
]

# ── InsightFace ───────────────────────────────────────────────────────
INSIGHTFACE_MODEL: str = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
INSIGHTFACE_DET_SIZE: tuple[int, int] = (320, 320)

# ── Search ────────────────────────────────────────────────────────────
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "30"))
MAX_CANDIDATES_TO_VERIFY: int = int(os.getenv("MAX_CANDIDATES_TO_VERIFY", "12"))
SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "30"))
VERIFY_CONCURRENCY: int = int(os.getenv("VERIFY_CONCURRENCY", "4"))

# ── Explorer ──────────────────────────────────────────────────────────
EXPLORER_URL: str = "https://amoy.polygonscan.com"
