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
        # ── Custom email service (Gmail SMTP) ──────────────────────
        EMAIL_ADDRESS: str | None = os.getenv("EMAIL_ADDRESS") or os.getenv("EMAIL_ID")
        EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
        SUPABASE_SERVICE_KEY: str | None = os.getenv("SUPABASE_SERVICE_KEY")
        APP_URL: str = os.getenv("APP_URL", "https://krishisaathi-ai-hackathon.streamlit.app")

    # ── Telegram Bot ───────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    else:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
        OPENWEATHER_API_KEY = st.secrets.get("OPENWEATHER_API_KEY")
        SUPABASE_URL = st.secrets.get("SUPABASE_URL")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
        # ── Custom email service (Gmail SMTP) ──────────────────────
        EMAIL_ADDRESS = st.secrets.get("EMAIL_ADDRESS") or st.secrets.get("EMAIL_ID")  
        EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD")
        SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY")
        APP_URL = st.secrets.get("APP_URL", "https://krishisaathi-ai-hackathon.streamlit.app")
        TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    # ── Database Backend ───────────────────────────────────────────────
    #  "rds"      → Amazon RDS PostgreSQL (AWS-native, recommended)
    #  "supabase" → Supabase (legacy, hosted Postgres + GoTrue auth)
    DB_BACKEND: str = os.getenv("DB_BACKEND", "rds")

    # ── RDS PostgreSQL ─────────────────────────────────────────────────
    RDS_HOST: str = os.getenv("RDS_HOST", "")
    RDS_PORT: str = os.getenv("RDS_PORT", "5432")
    RDS_DBNAME: str = os.getenv("RDS_DBNAME", "krishisaathi")
    RDS_USER: str = os.getenv("RDS_USER", "postgres")
    RDS_PASSWORD: str = os.getenv("RDS_PASSWORD", os.getenv("DB_PASSWORD", ""))
    

    # ── LLM Backend ────────────────────────────────────────────────────
    #  "groq"    → Groq Cloud  (primary, free 30 RPM / up to 14.4K RPD)
    #  "gemini"  → Google Gemini (fallback, or production with paid key)
    #  "bedrock" → Amazon Bedrock (AWS-native, Claude 3.5 Sonnet / Haiku)
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

    # ── Amazon Bedrock model mapping (AWS-native) ──────────────────────
    #  Requires IAM role attached to EC2 or AWS credentials configured.
    #  Region should be ap-south-1 (Mumbai) for lowest latency.
    BEDROCK_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    BEDROCK_MODEL_CLASSIFIER: str = os.getenv(
        "BEDROCK_MODEL_CLASSIFIER", "anthropic.claude-3-haiku-20240307-v1:0"
    )
    BEDROCK_MODEL_AGENT: str = os.getenv(
        "BEDROCK_MODEL_AGENT", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    BEDROCK_MODEL_SYNTHESIS: str = os.getenv(
        "BEDROCK_MODEL_SYNTHESIS", "anthropic.claude-3-haiku-20240307-v1:0"
    )
    BEDROCK_MODEL_VISION: str = os.getenv(
        "BEDROCK_MODEL_VISION", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )

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
    _admin_raw = (
        os.getenv("ADMIN_EMAILS", os.getenv("ADMIN_MAILS", ""))
        if os.path.exists(".env")
        else st.secrets.get("ADMIN_EMAILS", st.secrets.get("ADMIN_MAILS", ""))
    )
    # st.secrets may return a list directly; os.getenv always returns str
    if isinstance(_admin_raw, list):
        ADMIN_EMAILS: list[str] = [e.strip().lower() for e in _admin_raw if isinstance(e, str) and e.strip()]
    elif isinstance(_admin_raw, str) and _admin_raw.strip():
        try:
            ADMIN_EMAILS = [
                e.strip().lower()
                for e in (json.loads(_admin_raw) if _admin_raw.startswith("[") else _admin_raw.split(","))
                if e.strip()
            ]
        except (json.JSONDecodeError, ValueError):
            # Fallback: strip brackets/quotes and split by comma
            ADMIN_EMAILS = [
                e.strip().strip('"').strip("'").lower()
                for e in _admin_raw.strip("[]").split(",")
                if e.strip().strip('"').strip("'")
            ]
    else:
        ADMIN_EMAILS = []

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
        """Load admin settings — DB first, then local JSON fallback."""
        # 1. Try database (RDS or Supabase)
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
        # ── Bedrock overrides ──
        if "bedrock_region" in llm:
            cls.BEDROCK_REGION = llm["bedrock_region"]
        if "bedrock_classifier" in llm:
            cls.BEDROCK_MODEL_CLASSIFIER = llm["bedrock_classifier"]
        if "bedrock_agent" in llm:
            cls.BEDROCK_MODEL_AGENT = llm["bedrock_agent"]
        if "bedrock_synthesis" in llm:
            cls.BEDROCK_MODEL_SYNTHESIS = llm["bedrock_synthesis"]
        if "bedrock_vision" in llm:
            cls.BEDROCK_MODEL_VISION = llm["bedrock_vision"]
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
                "bedrock_region": cls.BEDROCK_REGION,
                "bedrock_classifier": cls.BEDROCK_MODEL_CLASSIFIER,
                "bedrock_agent": cls.BEDROCK_MODEL_AGENT,
                "bedrock_synthesis": cls.BEDROCK_MODEL_SYNTHESIS,
                "bedrock_vision": cls.BEDROCK_MODEL_VISION,
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
