"""Centralized configuration for KrishiSaathi."""

from __future__ import annotations

import json
import os
from dotenv import load_dotenv
import streamlit as st



class Config:
    """Application configuration loaded from environment variables."""

    # API Keys
    if os.path.exists(".env"):
        load_dotenv()
        GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
        GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
        OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")
        SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
        SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
    else:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
        OPENWEATHER_API_KEY = st.secrets.get("OPENWEATHER_API_KEY")
        SUPABASE_URL = st.secrets.get("SUPABASE_URL")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
    

    # ── LLM Backend ────────────────────────────────────────────────────
    #  "groq"   → Groq Cloud  (primary, free 30 RPM / up to 14.4K RPD)
    #  "gemini" → Google Gemini (fallback, or production with paid key)
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "groq")

    # ── Groq model mapping ─────────────────────────────────────────────
    #  Free-tier limits (Developer plan, Feb 2026):
    #    llama-3.1-8b-instant             → 30 RPM / 14.4K RPD / 6K TPM
    #    llama-3.3-70b-versatile          → 30 RPM / 1K RPD  / 12K TPM
    #    meta-llama/llama-4-scout-17b-16e → 30 RPM / 1K RPD  / 30K TPM
    # ────────────────────────────────────────────────────────────────────
    GROQ_MODEL_CLASSIFIER: str = os.getenv("GROQ_MODEL_CLASSIFIER", "llama-3.1-8b-instant")
    GROQ_MODEL_AGENT: str = os.getenv("GROQ_MODEL_AGENT", "llama-3.3-70b-versatile")
    GROQ_MODEL_SYNTHESIS: str = os.getenv("GROQ_MODEL_SYNTHESIS", "llama-3.1-8b-instant")

    GROQ_FALLBACK_CHAIN: dict[str, list[str]] = {
        "classifier": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"],
        "agent":      ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.1-8b-instant"],
        "synthesis":  ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"],
    }

    # ── Gemini model mapping (fallback / production) ───────────────────
    MODEL_CLASSIFIER: str = os.getenv("MODEL_CLASSIFIER", "gemini-2.0-flash-lite")
    MODEL_AGENT: str = os.getenv("MODEL_AGENT", "gemini-2.0-flash")
    MODEL_SYNTHESIS: str = os.getenv("MODEL_SYNTHESIS", "gemini-2.0-flash-lite")

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    GEMINI_FALLBACK_CHAIN: dict[str, list[str]] = {
        "classifier": ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"],
        "agent":      ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"],
        "synthesis":  ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"],
    }

    # ── LLM call settings ──────────────────────────────────────────────
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_RETRY_BASE_DELAY: int = int(os.getenv("LLM_RETRY_BASE_DELAY", "10"))
    LLM_CACHE_SIZE: int = int(os.getenv("LLM_CACHE_SIZE", "128"))

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

    # ── Admin ─────────────────────────────────────────────────────────
    _admin_raw: str = (
        os.getenv("ADMIN_EMAILS", os.getenv("ADMIN_MAILS", ""))
        if os.path.exists(".env")
        else st.secrets.get("ADMIN_EMAILS", st.secrets.get("ADMIN_MAILS", ""))
    )
    ADMIN_EMAILS: list[str] = [
        e.strip().lower()
        for e in (json.loads(_admin_raw) if _admin_raw.startswith("[") else _admin_raw.split(","))
        if e.strip()
    ]

    # Database
    DB_PATH: str = "data/krishisaathi.db"
    CHROMA_DB_PATH: str = "data/chroma_db"

    # ── Admin-editable settings ────────────────────────────────────────
    #  Primary store  : Supabase ``admin_settings`` table (cloud-safe)
    #  Fallback/cache : local JSON file (dev convenience)
    ADMIN_SETTINGS_FILE: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "admin_settings.json",
    )

    @classmethod
    def load_admin_settings(cls) -> dict:
        """Load admin settings — Supabase first, then local JSON fallback."""
        # 1. Try Supabase (works on Streamlit Cloud)
        try:
            from backend.services.supabase_service import SupabaseManager
            if SupabaseManager.is_configured():
                data = SupabaseManager.load_admin_settings()
                if data:
                    # Also write to local cache for offline use
                    cls._write_local_cache(data)
                    return data
        except Exception:
            pass

        # 2. Fallback: local JSON (works in dev / offline)
        try:
            if os.path.exists(cls.ADMIN_SETTINGS_FILE):
                with open(cls.ADMIN_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @classmethod
    def save_admin_settings(cls, settings: dict) -> None:
        """Persist admin settings to Supabase + local cache, then apply."""
        # 1. Supabase (primary)
        saved_to_cloud = False
        try:
            from backend.services.supabase_service import SupabaseManager
            if SupabaseManager.is_configured():
                saved_to_cloud = SupabaseManager.save_admin_settings(settings)
        except Exception:
            pass

        # 2. Local JSON (always write as fallback/cache)
        cls._write_local_cache(settings)

        # 3. Apply to runtime
        cls.apply_admin_overrides(settings)

    @classmethod
    def _write_local_cache(cls, settings: dict) -> None:
        """Write settings to local JSON file (best-effort)."""
        try:
            os.makedirs(os.path.dirname(cls.ADMIN_SETTINGS_FILE), exist_ok=True)
            with open(cls.ADMIN_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # read-only filesystem — that's OK

    @classmethod
    def apply_admin_overrides(cls, settings: dict | None = None) -> None:
        """Apply admin settings overrides to Config class attributes."""
        if settings is None:
            settings = cls.load_admin_settings()
        if not settings:
            return
        llm = settings.get("llm", {})
        if "backend" in llm:
            cls.LLM_BACKEND = llm["backend"]
        if "groq_classifier" in llm:
            cls.GROQ_MODEL_CLASSIFIER = llm["groq_classifier"]
        if "groq_agent" in llm:
            cls.GROQ_MODEL_AGENT = llm["groq_agent"]
        if "groq_synthesis" in llm:
            cls.GROQ_MODEL_SYNTHESIS = llm["groq_synthesis"]
        if "gemini_classifier" in llm:
            cls.MODEL_CLASSIFIER = llm["gemini_classifier"]
        if "gemini_agent" in llm:
            cls.MODEL_AGENT = llm["gemini_agent"]
        if "gemini_synthesis" in llm:
            cls.MODEL_SYNTHESIS = llm["gemini_synthesis"]
        if "embedding_model" in llm:
            cls.EMBEDDING_MODEL = llm["embedding_model"]
        if "max_retries" in llm:
            cls.LLM_MAX_RETRIES = int(llm["max_retries"])
        if "retry_delay" in llm:
            cls.LLM_RETRY_BASE_DELAY = int(llm["retry_delay"])
        if "cache_size" in llm:
            cls.LLM_CACHE_SIZE = int(llm["cache_size"])
        app = settings.get("app", {})
        if "default_language" in app:
            cls.DEFAULT_LANGUAGE = app["default_language"]

    @classmethod
    def get_current_admin_settings(cls) -> dict:
        """Return current config values as a serialisable dict."""
        saved = cls.load_admin_settings()
        return {
            "llm": {
                "backend": cls.LLM_BACKEND,
                "groq_classifier": cls.GROQ_MODEL_CLASSIFIER,
                "groq_agent": cls.GROQ_MODEL_AGENT,
                "groq_synthesis": cls.GROQ_MODEL_SYNTHESIS,
                "gemini_classifier": cls.MODEL_CLASSIFIER,
                "gemini_agent": cls.MODEL_AGENT,
                "gemini_synthesis": cls.MODEL_SYNTHESIS,
                "embedding_model": cls.EMBEDDING_MODEL,
                "max_retries": cls.LLM_MAX_RETRIES,
                "retry_delay": cls.LLM_RETRY_BASE_DELAY,
                "cache_size": cls.LLM_CACHE_SIZE,
            },
            "app": {
                "default_language": cls.DEFAULT_LANGUAGE,
            },
            "api_sources": saved.get("api_sources", []),
        }


# ── Apply any saved admin overrides on import ─────────────────────────
try:
    Config.apply_admin_overrides()
except Exception:
    pass
