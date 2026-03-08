"""Voice input/output components for KrishiSaathi.

Provides:
    render_voice_input()  — microphone button → STT → returns text
    render_voice_output() — 🔊 button → TTS → plays audio
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

# ── Optional dependency: audio-recorder-streamlit ──────────────────────
try:
    from audio_recorder_streamlit import audio_recorder
    _HAS_RECORDER = True
except ImportError:
    _HAS_RECORDER = False
    logger.warning("audio-recorder-streamlit not installed — mic input disabled")


# ── Localised labels ──────────────────────────────────────────────────
_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "mic_help": "Click to record your question",
        "listen": "🔊 Listen",
        "listening": "Transcribing…",
        "no_speech": "Could not understand. Please try again.",
        "tts_fail": "Audio playback not available.",
        "speak_label": "🎤 Speak",
    },
    "hi": {
        "mic_help": "अपना सवाल रिकॉर्ड करने के लिए क्लिक करें",
        "listen": "🔊 सुनें",
        "listening": "लिख रहा है…",
        "no_speech": "समझ नहीं आया। कृपया पुनः प्रयास करें।",
        "tts_fail": "ऑडियो प्लेबैक उपलब्ध नहीं है।",
        "speak_label": "🎤 बोलें",
    },
    "te": {
        "mic_help": "మీ ప్రశ్నను రికార్డ్ చేయడానికి క్లిక్ చేయండి",
        "listen": "🔊 వినండి",
        "listening": "వ్రాస్తోంది…",
        "no_speech": "అర్థం కాలేదు. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        "tts_fail": "ఆడియో ప్లేబ్యాక్ అందుబాటులో లేదు.",
        "speak_label": "🎤 చెప్పండి",
    },
}


def _label(lang: str, key: str) -> str:
    """Get localised label, translating the English fallback when needed."""
    lang_map = _LABELS.get(lang)
    if lang_map and key in lang_map:
        return lang_map[key]
    base = _LABELS["en"][key]
    if lang == "en":
        return base
    try:
        from backend.services.translation_service import translator
        return translator.from_english(base, dest=lang)
    except Exception:
        return base


# ═══════════════════════════════════════════════════════════════════════
#  Voice Input — Microphone → STT → text
# ═══════════════════════════════════════════════════════════════════════

def render_voice_input(language: str = "en", key_suffix: str = "") -> Optional[str]:
    """Render a microphone recorder and return transcribed text.

    Parameters
    ----------
    language : str
        Current app language code (``"en"``, ``"hi"``, …).
    key_suffix : str
        Optional suffix to make the widget key unique across pages.

    Returns
    -------
    str | None
        Transcribed text if user recorded audio, else None.
    """
    if not _HAS_RECORDER:
        return None

    # Audio recorder widget — returns bytes when recording is done
    try:
        audio_bytes = audio_recorder(
            text=_label(language, "speak_label"),
            recording_color="#e8403a",
            neutral_color="#6aa36f",
            icon_name="microphone",
            icon_size="2x",
            pause_threshold=2.0,
            sample_rate=16000,
            key=f"voice_rec_{key_suffix}",
        )
    except Exception as exc:
        logger.warning("audio_recorder component failed to load: %s", exc)
        return None

    if not audio_bytes:
        return None

    # Avoid re-processing the same recording
    audio_hash = hash(audio_bytes)
    if st.session_state.get(f"_last_audio_hash_{key_suffix}") == audio_hash:
        return None
    st.session_state[f"_last_audio_hash_{key_suffix}"] = audio_hash

    # Transcribe
    with st.spinner(_label(language, "listening")):
        try:
            from backend.services.voice_service import voice
            transcript = voice.speech_to_text(
                audio_bytes=audio_bytes,
                language=language,
                audio_format="wav",
            )
        except Exception as exc:
            logger.error("STT failed: %s", exc)
            transcript = ""

    if not transcript or not transcript.strip():
        st.warning(_label(language, "no_speech"))
        return None

    return transcript.strip()


# ═══════════════════════════════════════════════════════════════════════
#  Voice Output — Text → TTS → audio playback
# ═══════════════════════════════════════════════════════════════════════

def render_voice_output(
    text: str,
    language: str = "en",
    key_suffix: str = "",
) -> None:
    """Render a 🔊 Listen button that plays TTS audio of the given text.

    Parameters
    ----------
    text : str
        The text to convert to speech.
    language : str
        Current app language code.
    key_suffix : str
        Unique suffix for the button key.
    """
    if not text or not text.strip():
        return

    btn_label = _label(language, "listen")
    btn_key = f"tts_btn_{key_suffix}"

    if st.button(btn_label, key=btn_key, help="Listen to this response"):
        _play_tts(text, language)


def _play_tts(text: str, language: str) -> None:
    """Generate TTS audio and play it via st.audio."""
    try:
        from backend.services.voice_service import voice, strip_emojis

        # Strip emojis before TTS so it doesn't read "star emoji" etc.
        clean_text = strip_emojis(text)
        if not clean_text:
            return

        audio_bytes = voice.text_to_speech(
            text=clean_text,
            language=language,
            output_format="mp3",
        )

        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        else:
            st.warning(_label(language, "tts_fail"))

    except Exception as exc:
        logger.error("TTS playback failed: %s", exc)
        st.warning(_label(language, "tts_fail"))
