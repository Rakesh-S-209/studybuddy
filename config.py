"""
config.py - Application configuration

Loads settings from environment variables (via .env file in development).
Provides a Config base class and environment-specific subclasses.
"""

import os
from dotenv import load_dotenv

# Establish base directory of the project
basedir = os.path.abspath(os.path.dirname(__file__))

# Load variables from .env file into the environment using an absolute path.
# This ensures environment variables load correctly regardless of where app.py is triggered.
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration shared across all environments."""

    # -------------------------------------------------------------------------
    # Flask core
    # -------------------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

    # -------------------------------------------------------------------------
    # Database — defaults to a local SQLite file for development
    # -------------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///studybuddy.db"
    )
    # Disable Flask-SQLAlchemy modification tracking (not needed, wastes memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------------------------------------------------------
    # LLM / AI service (OpenAI-compatible endpoint)
    # Target configurations aligned to OpenRouter parameters.
    # -------------------------------------------------------------------------
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL = os.environ.get(
        "LLM_BASE_URL", "https://openrouter.ai/api/v1"
    )
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "openrouter/free")

    # -------------------------------------------------------------------------
    # File upload limits
    # -------------------------------------------------------------------------
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB hard limit
    ALLOWED_EXTENSIONS = {"pdf", "txt"}


class DevelopmentConfig(Config):
    """Development-specific settings — verbose errors, no HTTPS enforcement."""

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production settings — tighter security, no debug output."""

    DEBUG = False
    TESTING = False

    # Enforce HTTPS cookies in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing settings — in-memory DB, CSRF disabled."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


# Map name → class so the factory can resolve by string
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}