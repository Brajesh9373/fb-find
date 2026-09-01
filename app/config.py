"""Central configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

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
]
PRIVATE_KEY: str | None = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS: str | None = os.getenv("CONTRACT_ADDRESS")

CHAIN_ID: int = int(os.getenv("CHAIN_ID", "80002"))
CHAIN_NAME: str = os.getenv("CHAIN_NAME", "Polygon Amoy")
CURRENCY: str = os.getenv("CURRENCY", "POL")

# ── Face Matching ─────────────────────────────────────────────────────
FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.65"))

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
INSIGHTFACE_DET_SIZE: tuple[int, int] = (640, 640)

# ── Search ────────────────────────────────────────────────────────────
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "20"))
MAX_CANDIDATES_TO_VERIFY: int = int(os.getenv("MAX_CANDIDATES_TO_VERIFY", "5"))
SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "30"))

# ── Explorer ──────────────────────────────────────────────────────────
EXPLORER_URL: str = "https://amoy.polygonscan.com"
