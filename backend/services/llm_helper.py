"""LLM Helper — dual-backend wrapper (Groq primary, Gemini fallback).

Every agent calls ``llm.generate(...)`` instead of touching API clients directly.
This gives us:
  - **Dual backend**: Groq (fast, generous free tier) → Gemini (fallback)
  - Automatic retry with exponential backoff on transient 429 errors
  - Hard-block detection (``limit: 0``) → instant fallback, no wasted retries
  - Model fallback chains within each backend
  - In-memory LRU response cache
  - Role-based model selection (classifier / agent / synthesis)
  - Multimodal support (images → Gemini only)
  - Single place to swap models for production

Usage:
    from backend.services.llm_helper import llm

    text = llm.generate("Your prompt here", role="agent")
    text = llm.generate("Classify intent", role="classifier")
    text = llm.generate([prompt, pil_image], role="agent", use_cache=False)  # multimodal
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any

from backend.config import Config

logger = logging.getLogger(__name__)

# Conditional imports — neither is strictly required if the other works
_groq_available = False
_gemini_available = False

try:
    from groq import Groq
    _groq_available = True
except ImportError:
    logger.debug("groq package not installed — Groq backend disabled")

try:
    import google.generativeai as genai
    _gemini_available = True
except ImportError:
    logger.debug("google-generativeai not installed — Gemini backend disabled")


class _HardBlock(Exception):
    """Raised when a model returns limit:0 — no point retrying."""
    pass


class _BackendExhausted(Exception):
    """Raised when all models in a backend are exhausted."""
    pass


class LLMHelper:
    """Dual-backend LLM wrapper: Groq (primary) + Gemini (fallback)."""

    def __init__(self) -> None:
        self._backend = Config.LLM_BACKEND  # "groq" or "gemini"

        # ── Groq setup ──
        self._groq_client: Groq | None = None
        if _groq_available and Config.GROQ_API_KEY:
            self._groq_client = Groq(api_key=Config.GROQ_API_KEY)

        # ── Gemini setup ──
        if _gemini_available and Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)

        # Role → model name for each backend
        self._groq_model_map: dict[str, str] = {
            "classifier": Config.GROQ_MODEL_CLASSIFIER,
            "agent": Config.GROQ_MODEL_AGENT,
            "synthesis": Config.GROQ_MODEL_SYNTHESIS,
        }
        self._gemini_model_map: dict[str, str] = {
            "classifier": Config.MODEL_CLASSIFIER,
            "agent": Config.MODEL_AGENT,
            "synthesis": Config.MODEL_SYNTHESIS,
        }

        # Fallback chains per backend
        self._groq_fallback: dict[str, list[str]] = Config.GROQ_FALLBACK_CHAIN
        self._gemini_fallback: dict[str, list[str]] = Config.GEMINI_FALLBACK_CHAIN

        # Track hard-blocked models per session (prefixed by backend)
        self._blocked_models: set[str] = set()

        # Lazy Gemini GenerativeModel cache
        self._gemini_models: dict[str, Any] = {}

        # LRU response cache
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._cache_size = Config.LLM_CACHE_SIZE
        self._max_retries = Config.LLM_MAX_RETRIES
        self._base_delay = Config.LLM_RETRY_BASE_DELAY

        primary_map = self._groq_model_map if self._backend == "groq" else self._gemini_model_map
        logger.info(
            "LLMHelper ready  (backend=%s  classifier=%s  agent=%s  synthesis=%s  cache=%d)",
            self._backend,
            primary_map["classifier"],
            primary_map["agent"],
            primary_map["synthesis"],
            self._cache_size,
        )

    # ── public API ─────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str | list[Any],
        *,
        role: str = "agent",
        use_cache: bool = True,
    ) -> str:
        """Generate a text response.

        Parameters
        ----------
        prompt : str or list
            Text prompt, or a list containing text + PIL Image for multimodal.
            Multimodal prompts always go to Gemini (Groq doesn't support images).
        role : str
            One of ``"classifier"``, ``"agent"``, ``"synthesis"``.
        use_cache : bool
            If True, identical prompts return cached responses.
        """
        cache_key = self._cache_key(prompt, role) if use_cache else None

        # Check cache
        if cache_key and cache_key in self._cache:
            logger.debug("Cache HIT for role=%s", role)
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        # Multimodal → Gemini only (Groq has no image support)
        is_multimodal = isinstance(prompt, list)

        if is_multimodal:
            text = self._generate_gemini(prompt, role)
        elif self._backend == "groq" and self._groq_client:
            try:
                text = self._generate_groq(prompt, role)
            except _BackendExhausted:
                logger.warning("Groq exhausted — falling back to Gemini")
                text = self._generate_gemini(prompt, role)
        else:
            text = self._generate_gemini(prompt, role)

        # Store in cache
        if cache_key and text:
            self._cache[cache_key] = text
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

        return text

    @property
    def model_map(self) -> dict[str, str]:
        """Return current primary role → model name mapping."""
        if self._backend == "groq":
            return dict(self._groq_model_map)
        return dict(self._gemini_model_map)

    def cache_stats(self) -> dict[str, int]:
        return {"cached_entries": len(self._cache), "max_size": self._cache_size}

    def clear_cache(self) -> None:
        self._cache.clear()

    def reload_config(self) -> None:
        """Reload model maps and settings from Config (after admin changes)."""
        self._backend = Config.LLM_BACKEND
        self._groq_model_map = {
            "classifier": Config.GROQ_MODEL_CLASSIFIER,
            "agent": Config.GROQ_MODEL_AGENT,
            "synthesis": Config.GROQ_MODEL_SYNTHESIS,
        }
        self._gemini_model_map = {
            "classifier": Config.MODEL_CLASSIFIER,
            "agent": Config.MODEL_AGENT,
            "synthesis": Config.MODEL_SYNTHESIS,
        }
        self._groq_fallback = Config.GROQ_FALLBACK_CHAIN
        self._gemini_fallback = Config.GEMINI_FALLBACK_CHAIN
        self._max_retries = Config.LLM_MAX_RETRIES
        self._base_delay = Config.LLM_RETRY_BASE_DELAY
        new_size = Config.LLM_CACHE_SIZE
        if new_size != self._cache_size:
            self._cache_size = new_size
            self._cache.clear()
        self._blocked_models.clear()
        self._gemini_models.clear()
        logger.info(
            "LLMHelper reloaded  (backend=%s  agent=%s)",
            self._backend,
            self._groq_model_map["agent"] if self._backend == "groq" else self._gemini_model_map["agent"],
        )

    # ── Groq backend ───────────────────────────────────────────────────

    def _generate_groq(self, prompt: str, role: str) -> str:
        """Try each Groq model in the fallback chain."""
        chain = self._groq_fallback.get(
            role, [self._groq_model_map.get(role, "llama-3.3-70b-versatile")]
        )
        last_error: Exception | None = None

        for model_name in chain:
            key = f"groq:{model_name}"
            if key in self._blocked_models:
                continue

            try:
                return self._call_groq(model_name, prompt, role)
            except _HardBlock:
                self._blocked_models.add(key)
                logger.warning("Groq %s hard-blocked — trying next", model_name)
                continue
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Groq %s failed (role=%s): %s — trying next",
                    model_name, role, str(exc)[:120],
                )
                continue

        raise _BackendExhausted(f"All Groq models exhausted for role={role}") from last_error

    def _call_groq(self, model_name: str, prompt: str, role: str) -> str:
        """Call Groq chat completion with retry on transient errors."""
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2048,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                err = str(exc)

                if "limit: 0" in err or "limit:0" in err:
                    raise _HardBlock(f"groq:{model_name} hard-blocked") from exc

                is_rate_limit = "429" in err or "rate_limit" in err.lower()
                is_server_error = "500" in err or "503" in err

                if (is_rate_limit or is_server_error) and attempt < self._max_retries:
                    delay = self._base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Groq %s (role=%s) — %s — retry %ds (%d/%d)",
                        model_name, role,
                        "rate-limited" if is_rate_limit else "server error",
                        delay, attempt, self._max_retries,
                    )
                    time.sleep(delay)
                else:
                    raise
        return ""

    # ── Gemini backend ─────────────────────────────────────────────────

    def _generate_gemini(self, prompt: str | list[Any], role: str) -> str:
        """Try each Gemini model in the fallback chain."""
        if not _gemini_available or not Config.GEMINI_API_KEY:
            raise RuntimeError("Gemini backend not available (missing API key or package)")

        chain = self._gemini_fallback.get(
            role, [self._gemini_model_map.get(role, "gemini-2.0-flash")]
        )
        last_error: Exception | None = None

        for model_name in chain:
            key = f"gemini:{model_name}"
            if key in self._blocked_models:
                continue

            model = self._get_gemini_model(model_name)
            try:
                return self._call_gemini(model, prompt, role)
            except _HardBlock:
                self._blocked_models.add(key)
                logger.warning("Gemini %s hard-blocked — trying next", model_name)
                continue
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini %s failed (role=%s): %s — trying next",
                    model_name, role, str(exc)[:120],
                )
                continue

        if last_error:
            raise last_error
        raise RuntimeError(
            f"All models exhausted for role={role}. "
            "Both Groq and Gemini quotas are used up. "
            "Wait for daily reset or add a new API key."
        )

    def _get_gemini_model(self, model_name: str) -> Any:
        if model_name not in self._gemini_models:
            self._gemini_models[model_name] = genai.GenerativeModel(model_name)
        return self._gemini_models[model_name]

    def _call_gemini(self, model: Any, prompt: str | list[Any], role: str) -> str:
        """Call Gemini generate_content with retry."""
        for attempt in range(1, self._max_retries + 1):
            try:
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as exc:
                err = str(exc)

                if "limit: 0" in err or "limit:0" in err:
                    raise _HardBlock(f"{model.model_name} hard-blocked") from exc

                is_rate_limit = "429" in err or "ResourceExhausted" in err
                is_server_error = "500" in err or "503" in err

                if (is_rate_limit or is_server_error) and attempt < self._max_retries:
                    delay = self._base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini %s (role=%s) — %s — retry %ds (%d/%d)",
                        model.model_name, role,
                        "rate-limited" if is_rate_limit else "server error",
                        delay, attempt, self._max_retries,
                    )
                    time.sleep(delay)
                else:
                    raise
        return ""

    # ── shared helpers ─────────────────────────────────────────────────

    @staticmethod
    def _cache_key(prompt: str | list[Any], role: str) -> str:
        if isinstance(prompt, str):
            raw = f"{role}::{prompt}"
        else:
            text_parts = [str(p) for p in prompt if isinstance(p, str)]
            raw = f"{role}::{'||'.join(text_parts)}"
        return hashlib.sha256(raw.encode()).hexdigest()


# ── Module-level singleton ─────────────────────────────────────────────
# Import and use:  from backend.services.llm_helper import llm
llm = LLMHelper()
