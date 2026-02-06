"""Centralized configuration for KrishiSaathi."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # API Keys
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")

    # Model Settings
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # App Settings
    APP_NAME: str = "KrishiSaathi"
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    SUPPORTED_LANGUAGES: dict[str, str] = {
        "en": "English",
        "te": "Telugu",
        "hi": "Hindi",
        "ta": "Tamil",
        "mr": "Marathi",
        "bn": "Bengali",
        "kn": "Kannada",
        "gu": "Gujarati",
        "pa": "Punjabi",
        "or": "Odia",
        "ml": "Malayalam",
        "as": "Assamese",
    }

    # Database
    DB_PATH: str = "data/krishisaathi.db"
    CHROMA_DB_PATH: str = "data/chroma_db"
