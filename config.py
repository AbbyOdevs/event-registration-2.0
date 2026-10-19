"""Application configuration read from environment variables."""

import os

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Holds every setting the application needs.

    Environment variables
    ---------------------
    ADMIN_EMAIL     administrator login email
    ADMIN_PASSWORD  administrator password (legacy name ``admin`` is still read)
    SECRET_KEY      Flask session signing key
    COOKIE_SECURE   "true" when served over HTTPS
    DATA_FILE       path of the JSON database
    FLASK_DEBUG     "true" to run the development server in debug mode
    """

    DEV_ADMIN_PASSWORD = "gate2026"
    DEV_SECRET_KEY = "dev-secret-change-me"

    def __init__(self):
        self.data_file = os.environ.get(
            "DATA_FILE", os.path.join(APP_ROOT, "data.json")
        )
        self.admin_email = os.environ.get(
            "ADMIN_EMAIL", "admin@gatehub.local"
        ).strip().lower()

        password = os.environ.get("ADMIN_PASSWORD") or os.environ.get("admin")
        self.using_default_admin_password = not password
        self.admin_password = password or self.DEV_ADMIN_PASSWORD

        secret = os.environ.get("SECRET_KEY")
        self.using_default_secret = not secret
        self.secret_key = secret or self.DEV_SECRET_KEY

        self.cookie_secure = (
            os.environ.get("COOKIE_SECURE", "false").lower() == "true"
        )
        self.debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
