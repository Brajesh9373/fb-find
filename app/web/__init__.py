"""Flask web application for Face → Web → Blockchain pipeline."""

import os
from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application."""
    # Get the directory containing this file
    web_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(web_dir))
    upload_dir = os.path.join(project_root, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=os.path.join(web_dir, "templates"),
        static_folder=os.path.join(web_dir, "static"),
    )

    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    app.config["UPLOAD_FOLDER"] = upload_dir

    from app.web.routes import main_bp

    app.register_blueprint(main_bp)

    return app
