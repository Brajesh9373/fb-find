"""Flask routes for the Face → Web → Blockchain web API."""

from __future__ import annotations

import os
import tempfile
import uuid

from flask import Blueprint, jsonify, render_template, request

from app.web.pipeline import run_pipeline

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@main_bp.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "face-detection"})


@main_bp.route("/api/analyze", methods=["POST"])
def analyze():
    """Accept image upload and run the pipeline."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            "success": False,
            "error": f"Invalid file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        }), 400

    # Save to temp file
    upload_dir = tempfile.mkdtemp(prefix="face-detection-")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    try:
        # Get optional parameters
        threshold = request.form.get("threshold")
        if threshold:
            try:
                threshold = float(threshold)
            except ValueError:
                threshold = None

        skip_blockchain = request.form.get("skip_blockchain", "false").lower() == "true"
        tamper_demo = request.form.get("tamper_demo", "true").lower() == "true"

        # Run pipeline
        result = run_pipeline(
            image_path=filepath,
            threshold=threshold,
            skip_blockchain=skip_blockchain,
            tamper_demo=tamper_demo,
        )

        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": f"Pipeline error: {exc}",
        }), 500

    finally:
        # Cleanup temp file
        try:
            os.unlink(filepath)
            os.rmdir(upload_dir)
        except OSError:
            pass
