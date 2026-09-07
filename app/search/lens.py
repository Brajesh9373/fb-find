"""Reverse-image search via Google Lens (SerpApi).

Free tier: SerpApi gives 100 searches/month free — no card required.
Signup: https://serpapi.com/users/sign_up
Reference: https://serpapi.com/search-api/google-lens

Fallback: if SERPAPI_KEY is missing, the pipeline can run with
--mock-search for demos/tests.  No paid service is required.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from app import config
from app.search.parser import parse_lens_results

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class GoogleLensSearcher:
    """Perform a genuine, dynamic reverse-image search every run.

    Uses SerpApi Google Lens.  100 free searches/month, no card needed.
    Retries once on transient 5xx / timeout.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.SERPAPI_KEY

    def search(self, image_path: str) -> list[dict[str, Any]]:
        """Upload *image_path* to SerpApi Google Lens and return candidates.

        Each candidate has keys: ``title``, ``url``, ``source``, ``thumbnail``,
        ``position``.
        """
        if not self.api_key:
            raise RuntimeError(
                "SERPAPI_KEY is not set.\n"
                "  Free setup (30s): https://serpapi.com/users/sign_up → copy API key → add to .env\n"
                "  Or run offline demo:  python -m app.main --image sample/virat-kohli-photo-4k.webp --mock-search --skip-blockchain"
            )
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info("Uploading image to SerpApi Google Lens ...")

        # Retry once on transient failure (free tier can be slow)
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                # SerpApi Google Lens requires a public image URL, not file upload.
                # Upload to 0x0.st (free, no API key) to get a temporary URL.
                image_url = self._upload_image(image_path)
                logger.info("Image uploaded, searching via URL ...")

                params = {
                    "engine": "google_lens",
                    "url": image_url,
                    "api_key": self.api_key,
                }
                resp = requests.get(
                    SERPAPI_ENDPOINT,
                    params=params,
                    timeout=config.SEARCH_TIMEOUT,
                )

                if resp.status_code == 429:
                    raise RuntimeError(
                        "SerpApi rate limit hit (free tier: 100/month). "
                        "Wait a minute or use --mock-search for demos."
                    )
                if resp.status_code != 200:
                    try:
                        detail = resp.json()
                    except Exception:
                        detail = resp.text[:500]
                    raise RuntimeError(
                        f"SerpApi request failed (HTTP {resp.status_code}): {detail}"
                    )

                data = resp.json()
                if "error" in data:
                    err = data["error"]
                    # Common free-tier error: "Invalid API key" or quota
                    raise RuntimeError(f"SerpApi error: {err}")

                candidates = parse_lens_results(data)
                logger.info("SerpApi returned %d candidates", len(candidates))
                return candidates

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                if attempt == 0:
                    logger.warning("Search timeout, retrying in 2s ...")
                    time.sleep(2)
                    continue
                raise RuntimeError(f"SerpApi network error after retry: {exc}") from exc

        # Should not reach here
        if last_exc:
            raise last_exc
        return []

    @staticmethod
    def _upload_image(image_path: str) -> str:
        """Upload image to a public hosting service and return the public URL.
        
        Tries multiple services for reliability.
        """
        import time
        
        logger.info("Uploading image to temporary hosting...")
        
        # Try freeimage.host first (reliable, direct image URLs)
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    "https://freeimage.host/api/1/upload",
                    files={"source": fh},
                    data={
                        "key": "6d207e02198a847aa98d0a2a901485a5",
                        "type": "file",
                        "format": "json",
                    },
                    timeout=30,
                )
            
            if resp.status_code == 200:
                result = resp.json()
                if "image" in result and "url" in result["image"]:
                    url = result["image"]["url"]
                    logger.info("Image uploaded to freeimage.host: %s", url)
                    return url
        except Exception as exc:
            logger.warning("freeimage.host upload failed: %s", exc)
        
        # Fallback: catbox.moe
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": fh},
                    timeout=30,
                )
            
            if resp.status_code == 200:
                url = resp.text.strip()
                if url.startswith("http"):
                    logger.info("Image uploaded to catbox.moe: %s", url)
                    return url
        except Exception as exc:
            logger.warning("catbox.moe upload failed: %s", exc)
        
        raise RuntimeError("All image upload services failed. Check your internet connection.")

    def search_from_url(self, image_url: str) -> list[dict[str, Any]]:
        """Search using a publicly-accessible image URL (no upload)."""
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY is not set.")
        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self.api_key,
        }
        resp = requests.get(
            SERPAPI_ENDPOINT, params=params, timeout=config.SEARCH_TIMEOUT
        )
        if resp.status_code != 200:
            raise RuntimeError(f"SerpApi request failed: {resp.text[:500]}")
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"SerpApi error: {data['error']}")
        return parse_lens_results(data)
