"""Event Registration System - application entry point.

Run locally:      python app.py
Run in production: gunicorn app:app
"""

from flask import Flask

from config import Config
from models.person import Admin
from repository import JsonRepository
from routes import create_blueprint
from services import AuthService, EventService, RegistrationService


def create_app(config=None, repository=None):
    """Application factory: wires the repository, services and routes."""
    config = config or Config()
    repository = repository or JsonRepository(config.data_file)

    app = Flask(__name__)
    app.secret_key = config.secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = config.cookie_secure
    app.config["APP_SETTINGS"] = config

    admin = Admin(config.admin_email, config.admin_password)

    app.register_blueprint(
        create_blueprint(
            AuthService(repository, admin),
            EventService(repository),
            RegistrationService(repository),
        )
    )
    return app


app = create_app()


if __name__ == "__main__":
    settings = app.config["APP_SETTINGS"]

    if settings.using_default_admin_password:
        print("WARNING: using the default admin password. "
              "Set ADMIN_PASSWORD before deploying.")
    if settings.using_default_secret:
        print("WARNING: using the default SECRET_KEY. "
              "Set SECRET_KEY before deploying.")

    app.run(debug=settings.debug, use_reloader=False,
            host="0.0.0.0", port=5000)
