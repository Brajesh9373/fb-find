#!/usr/bin/env python3
"""Run the Face → Web → Blockchain web application."""

import logging
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from app.web import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print(f"\n{'='*60}")
    print(f"  Face → Web → Blockchain")
    print(f"  Web Interface")
    print(f"{'='*60}")
    print(f"\n  Starting server on http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
