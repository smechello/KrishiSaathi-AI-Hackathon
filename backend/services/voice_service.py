"""Voice Service — Amazon Polly (TTS) + Amazon Transcribe (STT).

Provides speech-to-text and text-to-speech for KrishiSaathi using
AWS-native services.  Supports 10 major Indian languages for STT
(via Amazon Transcribe) and Hindi + English for TTS (via Amazon Polly).
For languages without native Polly voices, text is translated to Hindi
first and then synthesised.

Required IAM policies on EC2 role:
    AmazonPollyFullAccess
    AmazonTranscribeFullAccess
    AmazonS3FullAccess
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.config import Config


# ── Emoji stripper ─────────────────────────────────────────────────────
# Broad Unicode ranges covering emoji blocks so TTS engines don't
# spell out "smiley face emoji", "star emoji", etc.
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001FA00-\U0001FA6F"  # chess, extended-A
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002702-\U000027B0"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "\U000020E3"             # combining enclosing keycap
    "\U00002600-\U000026FF"  # misc symbols (sun, cloud, etc.)
    "\U00002300-\U000023FF"  # misc technical
    "\U00002B50-\U00002B55"  # stars
    "\U0000203C-\U00003299"  # misc CJK / enclosed
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # extended-A chess
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Remove emoji characters from text so TTS doesn't read them aloud."""
    if not text:
        return text
    cleaned = _EMOJI_RE.sub(" ", text)
    # Collapse multiple spaces
    cleaned = re.sub(r"  +", " ", cleaned).strip()
    return cleaned

logger = logging.getLogger(__name__)

# ── AWS Clients (lazy-initialised) ─────────────────────────────────────
_REGION = getattr(Config, "BEDROCK_REGION", None) or "ap-south-1"
_S3_BUCKET = "krishisaathi-voice-temp-904408286347"

_polly: Any = None
_transcribe: Any = None
_s3: Any = None


def _get_polly():
    global _polly
    if _polly is None:
        _polly = boto3.client("polly", region_name=_REGION)
    return _polly


def _get_transcribe():
    global _transcribe
    if _transcribe is None:
        _transcribe = boto3.client("transcribe", region_name=_REGION)
    return _transcribe


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=_REGION)
    return _s3


# ── Language Mappings ──────────────────────────────────────────────────

# Amazon Transcribe language codes for Indian languages
TRANSCRIBE_LANG_MAP: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "pa": "pa-IN",
}

# Amazon Polly voice configuration
# Kajal (neural) for Hindi & English-IN; Aditi (standard) as fallback
POLLY_VOICES: dict[str, dict[str, str]] = {
    "en": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "en-IN"},
    "hi": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
}

# Languages that don't have native Polly voices — use gTTS (Google TTS)
# as a fallback.  gTTS natively supports all major Indian languages.
POLLY_UNSUPPORTED = {"te", "ta", "kn", "ml", "mr", "bn", "gu", "pa"}

# gTTS language codes (ISO 639-1, same as our app codes)
GTTS_LANG_MAP: dict[str, str] = {
    "te": "te", "ta": "ta", "kn": "kn", "ml": "ml",
    "mr": "mr", "bn": "bn", "gu": "gu", "pa": "pa",
}


# ═══════════════════════════════════════════════════════════════════════
#  Voice Service
# ═══════════════════════════════════════════════════════════════════════

class VoiceService:
    """AWS-native voice service for KrishiSaathi."""

    # ── TTS ────────────────────────────────────────────────────────────

    @staticmethod
    def is_tts_available() -> bool:
        """Check if TTS is available (Polly accessible)."""
        try:
            _get_polly().describe_voices(LanguageCode="en-IN")
            return True
        except Exception:
            return False

    @staticmethod
    def text_to_speech(
        text: str,
        language: str = "en",
        output_format: str = "mp3",
    ) -> bytes | None:
        """Convert text to speech using Amazon Polly.

        Parameters
        ----------
        text : str
            Text to synthesise (max ~3000 chars per call).
        language : str
            Language code (``"en"``, ``"hi"``).  For unsupported languages
            the caller should translate to Hindi/English before calling.
        output_format : str
            ``"mp3"`` (default) or ``"ogg_vorbis"`` or ``"pcm"``.

        Returns
        -------
        bytes | None
            Audio bytes, or None on failure.
        """
        if not text or not text.strip():
            return None

        # Strip emojis so TTS doesn't read "smiley emoji" etc.
        text = strip_emojis(text)
        if not text:
            return None

        # ── gTTS fallback for Polly-unsupported Indian languages ──
        if language in POLLY_UNSUPPORTED:
            return _synthesize_gtts(text, language)

        voice_cfg = POLLY_VOICES.get(language, POLLY_VOICES["hi"])

        # Polly has a 3000-char limit per call; chunk if needed
        MAX_CHARS = 2900
        if len(text) <= MAX_CHARS:
            return _synthesize_chunk(text, voice_cfg, output_format)

        # Chunk by sentences/paragraphs
        chunks = _split_text(text, MAX_CHARS)
        parts: list[bytes] = []
        for chunk in chunks:
            audio = _synthesize_chunk(chunk, voice_cfg, output_format)
            if audio:
                parts.append(audio)

        return b"".join(parts) if parts else None

    # ── STT ────────────────────────────────────────────────────────────

    @staticmethod
    def is_stt_available() -> bool:
        """Check if STT is available (Transcribe + S3 accessible)."""
        try:
            _get_transcribe()
            _get_s3()
            return True
        except Exception:
            return False

    @staticmethod
    def speech_to_text(
        audio_bytes: bytes,
        language: str = "en",
        audio_format: str = "wav",
    ) -> str:
        """Convert speech to text using Amazon Transcribe.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio data (WAV or WebM from browser recorder).
        language : str
            App language code (``"en"``, ``"hi"``, ``"te"``, etc.).
        audio_format : str
            ``"wav"``, ``"mp3"``, ``"ogg"``, ``"webm"``, ``"flac"``.

        Returns
        -------
        str
            Transcribed text, or empty string on failure.
        """
        if not audio_bytes:
            return ""

        s3 = _get_s3()
        tc = _get_transcribe()

        # Map audio format to Transcribe MediaFormat
        fmt_map = {
            "wav": "wav",
            "mp3": "mp3",
            "ogg": "ogg",
            "webm": "webm",
            "flac": "flac",
        }
        media_fmt = fmt_map.get(audio_format, "wav")
        ext = media_fmt

        # Upload audio to S3
        job_id = f"ks-{uuid.uuid4().hex[:12]}"
        s3_key = f"voice-input/{job_id}.{ext}"

        try:
            s3.put_object(
                Bucket=_S3_BUCKET,
                Key=s3_key,
                Body=audio_bytes,
                ContentType=f"audio/{audio_format}",
            )
        except Exception as exc:
            logger.error("S3 upload failed: %s", exc)
            return ""

        # Start transcription job
        lang_code = TRANSCRIBE_LANG_MAP.get(language, "en-IN")

        try:
            tc.start_transcription_job(
                TranscriptionJobName=job_id,
                Media={"MediaFileUri": f"s3://{_S3_BUCKET}/{s3_key}"},
                MediaFormat=media_fmt,
                LanguageCode=lang_code,
                OutputBucketName=_S3_BUCKET,
                OutputKey=f"voice-output/{job_id}.json",
            )
        except Exception as exc:
            logger.error("Transcribe job start failed: %s", exc)
            _cleanup_s3(s3_key)
            return ""

        # Poll for completion (timeout 60s)
        transcript = ""
        try:
            transcript = _poll_transcription(tc, job_id, timeout=60)
        except Exception as exc:
            logger.error("Transcription polling failed: %s", exc)

        # Cleanup S3 artifacts
        _cleanup_s3(s3_key)
        _cleanup_s3(f"voice-output/{job_id}.json")
        _cleanup_transcribe_job(tc, job_id)

        return transcript

    @staticmethod
    def get_tts_language(app_lang: str) -> tuple[str, bool]:
        """Determine TTS language and whether translation is needed.

        Returns
        -------
        tuple[str, bool]
            (tts_lang_code, needs_translation)
            With gTTS fallback, all Indian languages are now natively
            supported so ``needs_translation`` is always ``False``.
        """
        # All languages are now supported natively (Polly or gTTS)
        return app_lang, False


# ═══════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════

def _synthesize_chunk(
    text: str,
    voice_cfg: dict[str, str],
    output_format: str,
) -> bytes | None:
    """Synthesize a single chunk of text via Polly."""
    try:
        resp = _get_polly().synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            **voice_cfg,
        )
        return resp["AudioStream"].read()
    except ClientError as exc:
        logger.error("Polly synthesis failed: %s", exc)
        return None


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks at sentence or paragraph boundaries."""
    chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        if not line.strip():
            if current:
                chunks.append(current)
                current = ""
            continue

        sentences = line.replace(". ", ".\n").split("\n")
        for sent in sentences:
            if len(current) + len(sent) + 2 > max_chars:
                if current:
                    chunks.append(current)
                current = sent
            else:
                current = f"{current} {sent}".strip() if current else sent

    if current:
        chunks.append(current)
    return chunks


def _poll_transcription(tc, job_id: str, timeout: int = 60) -> str:
    """Poll Transcribe until the job completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        resp = tc.get_transcription_job(TranscriptionJobName=job_id)
        status = resp["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            # Read result from S3
            try:
                s3 = _get_s3()
                obj = s3.get_object(
                    Bucket=_S3_BUCKET,
                    Key=f"voice-output/{job_id}.json",
                )
                result = json.loads(obj["Body"].read())
                transcripts = result.get("results", {}).get("transcripts", [])
                if transcripts:
                    return transcripts[0].get("transcript", "")
            except Exception as exc:
                logger.warning("Failed to read transcript result: %s", exc)
            return ""

        if status == "FAILED":
            reason = resp["TranscriptionJob"].get("FailureReason", "unknown")
            logger.error("Transcription failed: %s", reason)
            return ""

        time.sleep(1.5)

    logger.warning("Transcription timed out after %ds for job %s", timeout, job_id)
    return ""


def _cleanup_s3(*keys: str) -> None:
    """Delete temporary S3 objects (best-effort)."""
    s3 = _get_s3()
    for key in keys:
        try:
            s3.delete_object(Bucket=_S3_BUCKET, Key=key)
        except Exception:
            pass


def _cleanup_transcribe_job(tc, job_id: str) -> None:
    """Delete completed transcription job (best-effort)."""
    try:
        tc.delete_transcription_job(TranscriptionJobName=job_id)
    except Exception:
        pass


def _synthesize_gtts(text: str, language: str) -> bytes | None:
    """Synthesise speech using gTTS for languages without Polly voices.

    gTTS natively supports Telugu, Tamil, Kannada, Malayalam, Marathi,
    Bengali, Gujarati and Punjabi — always returns mp3 bytes.
    """
    try:
        from gtts import gTTS as GoogleTTS
        import io as _io

        gtts_lang = GTTS_LANG_MAP.get(language, language)
        tts = GoogleTTS(text=text, lang=gtts_lang, slow=False)
        buf = _io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.read()
        logger.info("gTTS synthesis OK for lang=%s  %d bytes", language, len(audio_bytes))
        return audio_bytes
    except Exception as exc:
        logger.error("gTTS synthesis failed for lang=%s: %s", language, exc)
        return None


# ── Module-level singleton ─────────────────────────────────────────────
voice = VoiceService()
