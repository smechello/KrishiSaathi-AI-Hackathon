"""Translation Service — multi-language support using deep-translator.

Uses the free Google Translate API under the hood (via ``deep-translator``).
All 12 Indian languages listed in Config.SUPPORTED_LANGUAGES are supported.

Usage
-----
    from backend.services.translation_service import translator

    # Translate a farmer query to English for the AI pipeline
    en_text = translator.to_english("నా టమాటాలలో ఆకు మచ్చలు ఉన్నాయి", src="te")

    # Translate the AI response back to the farmer's language
    te_text = translator.from_english("Your tomato plants have early blight", dest="te")
"""

from __future__ import annotations

import logging
from functools import lru_cache

from deep_translator import GoogleTranslator

from backend.config import Config

logger = logging.getLogger(__name__)

# ── Language code mapping ──────────────────────────────────────────────
# deep-translator uses ISO 639-1 codes.  Most match Config directly.
# Exceptions: Odia ("or" → "or"), Assamese ("as" → not always supported).
_LANG_MAP: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "te": "te",
    "ta": "ta",
    "kn": "kn",
    "ml": "ml",
    "mr": "mr",
    "bn": "bn",
    "gu": "gu",
    "pa": "pa",
    "or": "or",
    "as": "as",
}


class TranslationService:
    """Thin wrapper around deep-translator for KrishiSaathi."""

    # ── public API ─────────────────────────────────────────────────────

    def translate(self, text: str, source: str, target: str) -> str:
        """Translate *text* from *source* language to *target* language.

        Parameters
        ----------
        text   : The text to translate.
        source : ISO 639-1 language code (e.g. "te", "hi", "en").
        target : ISO 639-1 language code.

        Returns the translated text, or the original text unchanged if:
          • source == target
          • text is empty
          • translation fails (logs the error, returns original)
        """
        if not text or not text.strip():
            return text
        if source == target:
            return text

        src = _LANG_MAP.get(source, source)
        tgt = _LANG_MAP.get(target, target)

        try:
            result = self._do_translate(text.strip(), src, tgt)
            return result or text
        except Exception as exc:
            logger.warning("Translation %s→%s failed: %s", src, tgt, exc)
            return text

    def to_english(self, text: str, src: str) -> str:
        """Shortcut: translate *text* from *src* language → English."""
        return self.translate(text, source=src, target="en")

    def from_english(self, text: str, dest: str) -> str:
        """Shortcut: translate English *text* → *dest* language."""
        return self.translate(text, source="en", target=dest)

    def detect_language(self, text: str) -> str:
        """Best-effort language detection.

        Returns an ISO 639-1 code.  Falls back to ``Config.DEFAULT_LANGUAGE``
        if detection fails.
        """
        if not text or not text.strip():
            return Config.DEFAULT_LANGUAGE
        try:
            detected = GoogleTranslator(source="auto", target="en").translate(text)
            # deep-translator doesn't expose detected lang; check if input ≈ output
            if detected and detected.strip().lower() == text.strip().lower():
                return "en"
            # Heuristic: use Unicode block to detect script
            return self._detect_by_script(text)
        except Exception:
            return Config.DEFAULT_LANGUAGE

    # ── internals ──────────────────────────────────────────────────────

    @staticmethod
    def _do_translate(text: str, src: str, tgt: str) -> str:
        """Call Google Translate via deep-translator.

        Handles long text by chunking (Google limit ≈ 5000 chars).
        """
        MAX_CHUNK = 4500
        if len(text) <= MAX_CHUNK:
            return GoogleTranslator(source=src, target=tgt).translate(text)

        # Chunk by paragraphs
        paragraphs = text.split("\n")
        translated_parts: list[str] = []
        chunk = ""
        for para in paragraphs:
            if len(chunk) + len(para) + 1 > MAX_CHUNK:
                if chunk:
                    translated_parts.append(
                        GoogleTranslator(source=src, target=tgt).translate(chunk)
                    )
                chunk = para
            else:
                chunk = f"{chunk}\n{para}" if chunk else para
        if chunk:
            translated_parts.append(
                GoogleTranslator(source=src, target=tgt).translate(chunk)
            )
        return "\n".join(translated_parts)

    @staticmethod
    def _detect_by_script(text: str) -> str:
        """Detect language from Unicode script of the first non-ASCII char."""
        # Unicode block ranges for Indian scripts
        _SCRIPT_RANGES: list[tuple[int, int, str]] = [
            (0x0900, 0x097F, "hi"),   # Devanagari → Hindi/Marathi
            (0x0980, 0x09FF, "bn"),   # Bengali
            (0x0A00, 0x0A7F, "pa"),   # Gurmukhi → Punjabi
            (0x0A80, 0x0AFF, "gu"),   # Gujarati
            (0x0B00, 0x0B7F, "or"),   # Odia
            (0x0B80, 0x0BFF, "ta"),   # Tamil
            (0x0C00, 0x0C7F, "te"),   # Telugu
            (0x0C80, 0x0CFF, "kn"),   # Kannada
            (0x0D00, 0x0D7F, "ml"),   # Malayalam
            (0x0D80, 0x0DFF, "si"),   # Sinhala
        ]
        for ch in text:
            cp = ord(ch)
            if cp < 128:
                continue
            for lo, hi, lang in _SCRIPT_RANGES:
                if lo <= cp <= hi:
                    return lang
        return "en"


# ── Module-level singleton ─────────────────────────────────────────────
translator = TranslationService()
