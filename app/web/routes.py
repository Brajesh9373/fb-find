"""Flask routes for the Face → Web → Blockchain web API."""

from __future__ import annotations

import os
import uuid

from flask import Blueprint, Response, current_app, jsonify, render_template, send_from_directory, request

from app.web.pipeline import run_pipeline_stream

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@main_bp.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "face-detection"})


@main_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve an uploaded image."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@main_bp.route("/api/analyze", methods=["POST"])
def analyze():
    """Accept image upload and run the pipeline via SSE streaming."""
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

    # Save to persistent upload directory
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Get optional parameters
    threshold = request.form.get("threshold")
    if threshold:
        try:
            threshold = float(threshold)
        except ValueError:
            threshold = None

    skip_blockchain = request.form.get("skip_blockchain", "false").lower() == "true"
    tamper_demo = request.form.get("tamper_demo", "true").lower() == "true"
    mock_search = request.form.get("mock_search", "false").lower() == "true"

    def generate():
        try:
            yield from run_pipeline_stream(
                image_path=filepath,
                threshold=threshold,
                skip_blockchain=skip_blockchain,
                tamper_demo=tamper_demo,
                mock_search=mock_search,
            )
        finally:
            try:
                os.unlink(filepath)
            except OSError:
                pass

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
