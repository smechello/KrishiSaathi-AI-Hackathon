"""Centralized configuration for KrishiSaathi."""

from __future__ import annotations

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

    # Database
    DB_PATH: str = "data/krishisaathi.db"
    CHROMA_DB_PATH: str = "data/chroma_db"
