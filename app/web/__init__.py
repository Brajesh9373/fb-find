"""Flask web application for Face → Web → Blockchain pipeline."""

import os
from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application."""
    web_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(web_dir))
    frontend_dir = os.path.join(project_root, "frontend")
    if os.path.isdir(os.path.join(frontend_dir, "templates")):
        template_dir = os.path.join(frontend_dir, "templates")
        static_dir = os.path.join(frontend_dir, "static")
    else:
        template_dir = os.path.join(web_dir, "templates")
        static_dir = os.path.join(web_dir, "static")
    upload_dir = os.path.join(project_root, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    app.config["UPLOAD_FOLDER"] = upload_dir

    from app.web.routes import main_bp

    app.register_blueprint(main_bp)

    return app
