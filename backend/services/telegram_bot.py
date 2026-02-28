"""Telegram Bot Service for KrishiSaathi.

Full-featured Telegram bot that mirrors the web-app experience:
    - Text chat (all agents via SupervisorAgent)
    - Image diagnosis (Crop Doctor — send a photo)
    - Voice messages (STT → process → TTS reply)
    - Translation (10 Indian languages)
    - Memories (per-user, extracted automatically)
    - Language selection (/language command)

Runs as a separate long-polling process alongside the Streamlit app.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
import time
from typing import Any

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

from backend.config import Config
from backend.main import KrishiSaathi
from backend.services.translation_service import translator
from backend.services.supabase_service import SupabaseManager
from backend.services.memory_engine import get_memory_engine
from backend.services.voice_service import voice

logger = logging.getLogger(__name__)

# ── Language labels ────────────────────────────────────────────────────
LANG_NAMES: dict[str, str] = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 हिन्दी",
    "te": "తెలుగు",
    "ta": "தமிழ்",
    "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
    "bn": "বাংলা",
    "mr": "मराठी",
    "gu": "ગુજરાતી",
    "pa": "ਪੰਜਾਬੀ",
}

GREETINGS: dict[str, str] = {
    "en": (
        "🌾 *Welcome to KrishiSaathi!*\n\n"
        "I'm your AI farming companion. I can help you with:\n"
        "🌱 Crop disease diagnosis (send a photo!)\n"
        "💰 Market prices\n"
        "🏛️ Government schemes\n"
        "🌤️ Weather forecasts\n"
        "🧪 Soil health advice\n\n"
        "Just type your question, send a photo, or use a voice message!\n\n"
        "Commands:\n"
        "/start — Start over\n"
        "/language — Change language\n"
        "/help — Show help\n"
        "/clear — Clear chat history"
    ),
    "hi": (
        "🌾 *कृषिसाथी में आपका स्वागत है!*\n\n"
        "मैं आपका AI खेती सहायक हूं। मैं इनमें मदद कर सकता हूं:\n"
        "🌱 फसल रोग निदान (फोटो भेजें!)\n"
        "💰 मंडी भाव\n"
        "🏛️ सरकारी योजनाएं\n"
        "🌤️ मौसम पूर्वानुमान\n"
        "🧪 मिट्टी स्वास्थ्य सलाह\n\n"
        "अपना सवाल टाइप करें, फोटो भेजें, या वॉइस मैसेज भेजें!"
    ),
    "te": (
        "🌾 *కృషిసాథికి స్వాగతం!*\n\n"
        "నేను మీ AI వ్యవసాయ సహచరుడు. నేను ఈ విషయాలలో సహాయపడగలను:\n"
        "🌱 పంట వ్యాధి నిర్ధారణ (ఫోటో పంపండి!)\n"
        "💰 మార్కెట్ ధరలు\n"
        "🏛️ ప్రభుత్వ పథకాలు\n"
        "🌤️ వాతావరణ సూచన\n"
        "🧪 నేల ఆరోగ్య సలహా\n\n"
        "మీ ప్రశ్నను టైప్ చేయండి, ఫోటో పంపండి, లేదా వాయిస్ మెసేజ్ పంపండి!"
    ),
}

# ── Singleton backend ──────────────────────────────────────────────────
_app: KrishiSaathi | None = None


def _get_backend() -> KrishiSaathi:
    global _app
    if _app is None:
        logger.info("Initialising KrishiSaathi backend for Telegram bot…")
        _app = KrishiSaathi()
    return _app


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _get_user_lang(telegram_id: int) -> str:
    """Get preference language for a Telegram user, default 'en'."""
    tg_user = SupabaseManager.tg_get_user(telegram_id)
    if tg_user:
        return tg_user.get("language", "en") or "en"
    return "en"


def _ensure_user(update: Update) -> str:
    """Ensure Telegram user is registered and return the linked profile_id."""
    user = update.effective_user
    if not user:
        return "tg_unknown"

    # Upsert telegram user
    SupabaseManager.tg_upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
    )

    # Get or create linked profile_id
    profile_id = SupabaseManager.tg_get_profile_id(user.id)
    return profile_id or f"tg_{user.id}"


def _escape_md(text: str) -> str:
    """Minimal escape for Telegram MarkdownV2. Falls back to plain send."""
    # We'll use HTML instead of MarkdownV2 for safety
    return text


async def _send_long(update: Update, text: str, reply_to: int | None = None) -> None:
    """Send a long message, splitting at 4096 char limit if needed."""
    MAX = 4000
    if len(text) <= MAX:
        await update.message.reply_text(text, reply_to_message_id=reply_to)
        return

    # Split at paragraph boundaries
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)

    for i, part in enumerate(parts):
        await update.message.reply_text(
            part, reply_to_message_id=reply_to if i == 0 else None
        )


# ═══════════════════════════════════════════════════════════════════════
#  Command Handlers
# ═══════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    profile_id = _ensure_user(update)
    lang = _get_user_lang(update.effective_user.id)
    greeting = GREETINGS.get(lang, GREETINGS["en"])
    await update.message.reply_text(greeting, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    lang = _get_user_lang(update.effective_user.id)

    help_texts = {
        "en": (
            "🌾 *KrishiSaathi Help*\n\n"
            "📝 *Text* — Type any farming question\n"
            "📷 *Photo* — Send a crop/leaf photo for disease diagnosis\n"
            "🎤 *Voice* — Send a voice message in your language\n\n"
            "*Commands:*\n"
            "/start — Start over\n"
            "/language — Change language\n"
            "/clear — Clear your chat history\n"
            "/help — Show this help"
        ),
        "hi": (
            "🌾 *कृषिसाथी सहायता*\n\n"
            "📝 *टेक्स्ट* — कोई भी खेती का सवाल टाइप करें\n"
            "📷 *फोटो* — फसल/पत्ती की फोटो भेजें\n"
            "🎤 *आवाज़* — अपनी भाषा में वॉइस मैसेज भेजें\n\n"
            "*कमांड:*\n"
            "/start — शुरू करें\n"
            "/language — भाषा बदलें\n"
            "/clear — चैट इतिहास मिटाएं\n"
            "/help — यह सहायता दिखाएं"
        ),
    }

    await update.message.reply_text(
        help_texts.get(lang, help_texts["en"]),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command — show inline keyboard for language selection."""
    buttons = []
    row = []
    for code, name in LANG_NAMES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang:{code}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await update.message.reply_text(
        "🌐 Choose your language / अपनी भाषा चुनें:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def callback_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("lang:"):
        return

    lang_code = data.split(":")[1]
    telegram_id = update.effective_user.id

    SupabaseManager.tg_set_language(telegram_id, lang_code)

    confirmations = {
        "en": f"✅ Language set to *{LANG_NAMES.get(lang_code, lang_code)}*",
        "hi": f"✅ भाषा *{LANG_NAMES.get(lang_code, lang_code)}* में बदली गई",
        "te": f"✅ భాష *{LANG_NAMES.get(lang_code, lang_code)}*కు మార్చబడింది",
    }
    confirm = confirmations.get(lang_code, confirmations["en"])
    await query.edit_message_text(confirm, parse_mode=ParseMode.MARKDOWN)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — clear chat history and memories."""
    profile_id = _ensure_user(update)
    lang = _get_user_lang(update.effective_user.id)

    try:
        SupabaseManager.clear_messages(profile_id)
        mem = get_memory_engine(profile_id)
        mem.clear_all()
    except Exception as exc:
        logger.warning("Clear failed: %s", exc)

    msgs = {
        "en": "🗑️ Chat history and memories cleared!",
        "hi": "🗑️ चैट इतिहास और यादें साफ़ की गईं!",
        "te": "🗑️ చాట్ చరిత్ర మరియు జ్ఞాపకాలు తొలగించబడ్డాయి!",
    }
    await update.message.reply_text(msgs.get(lang, msgs["en"]))


# ═══════════════════════════════════════════════════════════════════════
#  Message Handlers
# ═══════════════════════════════════════════════════════════════════════

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages — main AI chat flow."""
    if not update.message or not update.message.text:
        return

    telegram_id = update.effective_user.id
    profile_id = _ensure_user(update)
    lang = _get_user_lang(telegram_id)
    user_text = update.message.text.strip()

    if not user_text:
        return

    # Check if user is blocked
    tg_user = SupabaseManager.tg_get_user(telegram_id)
    if tg_user and tg_user.get("is_blocked"):
        await update.message.reply_text("⛔ Your access has been restricted. Contact admin.")
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Increment message counter
    SupabaseManager.tg_increment_messages(telegram_id)

    try:
        # Translate to English if needed
        if lang != "en":
            query_en = translator.to_english(user_text, src=lang)
        else:
            query_en = user_text

        # Get memory context
        memory_context = ""
        try:
            mem_engine = get_memory_engine(profile_id)
            memory_context = mem_engine.get_memory_context(query_en)
        except Exception as exc:
            logger.warning("Memory retrieval failed: %s", exc)

        # Get AI response
        app = _get_backend()
        result = app.ask(query_en, user_id=profile_id, memory_context=memory_context)
        response_text = result.get("response", "")
        sources = result.get("sources", [])

        # Ensure English, then translate back
        if response_text:
            response_text = translator.ensure_english(response_text)
            if lang != "en":
                response_text = translator.from_english(response_text, dest=lang)

        # Save messages to chat history
        SupabaseManager.save_message(profile_id, "user", user_text)
        SupabaseManager.save_message(profile_id, "assistant", response_text, sources)

        # Extract memories
        try:
            mem_engine = get_memory_engine(profile_id)
            mem_engine.add_from_conversation(query_en, result.get("response", ""))
        except Exception as exc:
            logger.warning("Memory extraction failed: %s", exc)

        # Build reply
        reply = response_text
        if sources:
            src_str = " · ".join(sources[:5])
            reply += f"\n\n📚 _{src_str}_"

        await _send_long(update, reply, reply_to=update.message.message_id)

    except Exception as exc:
        logger.error("Text handler error: %s", exc, exc_info=True)
        error_msgs = {
            "en": "❌ Sorry, something went wrong. Please try again.",
            "hi": "❌ क्षमा करें, कुछ गलत हो गया। कृपया पुनः प्रयास करें।",
            "te": "❌ క్షమించండి, ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        }
        await update.message.reply_text(error_msgs.get(lang, error_msgs["en"]))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages — Crop Doctor image diagnosis."""
    if not update.message or not update.message.photo:
        return

    telegram_id = update.effective_user.id
    profile_id = _ensure_user(update)
    lang = _get_user_lang(telegram_id)

    # Check if blocked
    tg_user = SupabaseManager.tg_get_user(telegram_id)
    if tg_user and tg_user.get("is_blocked"):
        await update.message.reply_text("⛔ Access restricted.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    SupabaseManager.tg_increment_messages(telegram_id)

    processing_msgs = {
        "en": "🔬 Analyzing your crop image… please wait.",
        "hi": "🔬 आपकी फसल की तस्वीर का विश्लेषण हो रहा है… कृपया प्रतीक्षा करें।",
        "te": "🔬 మీ పంట చిత్రం విశ్లేషించబడుతోంది… దయచేసి వేచి ఉండండి.",
    }
    status_msg = await update.message.reply_text(
        processing_msgs.get(lang, processing_msgs["en"])
    )

    try:
        # Download the highest resolution photo
        photo = update.message.photo[-1]  # Largest size
        photo_file = await photo.get_file()

        # Download to memory
        photo_bytes = await photo_file.download_as_bytearray()

        # Open as PIL Image
        from PIL import Image
        pil_image = Image.open(io.BytesIO(bytes(photo_bytes)))

        # Use caption as context if provided
        context_text = update.message.caption or ""
        if context_text and lang != "en":
            context_text = translator.to_english(context_text, src=lang)

        # Get Crop Doctor agent
        from backend.agents.crop_doctor_agent import CropDoctorAgent
        from backend.knowledge_base.rag_engine import RAGEngine

        app = _get_backend()
        try:
            rag = app.rag
        except Exception:
            rag = None
        doctor = CropDoctorAgent(rag_engine=rag)

        result = doctor.diagnose_from_image(
            pil_image=pil_image,
            context=context_text or None,
        )
        diagnosis = result.get("diagnosis", "")
        sources = result.get("sources", [])

        # Translate diagnosis
        if diagnosis:
            diagnosis = translator.ensure_english(diagnosis)
            if lang != "en":
                diagnosis = translator.from_english(diagnosis, dest=lang)

        # Save to chat history
        SupabaseManager.save_message(profile_id, "user", "[📷 Crop image sent]")
        SupabaseManager.save_message(profile_id, "assistant", diagnosis, sources)

        # Build reply
        reply = f"🌱 *Crop Diagnosis*\n\n{diagnosis}"
        if sources:
            src_str = " · ".join(sources[:5])
            reply += f"\n\n📚 _{src_str}_"

        # Delete the processing message
        try:
            await status_msg.delete()
        except Exception:
            pass

        await _send_long(update, reply, reply_to=update.message.message_id)

    except Exception as exc:
        logger.error("Photo handler error: %s", exc, exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        error_msgs = {
            "en": "❌ Could not analyze the image. Please try again with a clearer photo.",
            "hi": "❌ तस्वीर का विश्लेषण नहीं हो सका। कृपया स्पष्ट फोटो भेजें।",
            "te": "❌ చిత్రం విశ్లేషించలేకపోయింది. దయచేసి స్పష్టమైన ఫోటో పంపండి.",
        }
        await update.message.reply_text(error_msgs.get(lang, error_msgs["en"]))


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages — STT → AI → TTS response."""
    if not update.message or not update.message.voice:
        return

    telegram_id = update.effective_user.id
    profile_id = _ensure_user(update)
    lang = _get_user_lang(telegram_id)

    # Check if blocked
    tg_user = SupabaseManager.tg_get_user(telegram_id)
    if tg_user and tg_user.get("is_blocked"):
        await update.message.reply_text("⛔ Access restricted.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    SupabaseManager.tg_increment_messages(telegram_id)

    try:
        # Download voice file
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()

        # Telegram voice messages are in OGG format
        # Transcribe using Amazon Transcribe
        transcribing_msgs = {
            "en": "🎤 Transcribing your voice message…",
            "hi": "🎤 आपका वॉइस मैसेज लिखा जा रहा है…",
            "te": "🎤 మీ వాయిస్ మెసేజ్ వ్రాయబడుతోంది…",
        }
        status_msg = await update.message.reply_text(
            transcribing_msgs.get(lang, transcribing_msgs["en"])
        )

        transcript = voice.speech_to_text(
            audio_bytes=bytes(voice_bytes),
            language=lang,
            audio_format="ogg",
        )

        if not transcript or not transcript.strip():
            not_understood = {
                "en": "🎤 Could not understand the voice message. Please try again or type your question.",
                "hi": "🎤 वॉइस मैसेज समझ नहीं आया। दोबारा कोशिश करें या टाइप करें।",
                "te": "🎤 వాయిస్ మెసేజ్ అర్థం కాలేదు. మళ్ళీ ప్రయత్నించండి లేదా టైప్ చేయండి.",
            }
            try:
                await status_msg.delete()
            except Exception:
                pass
            await update.message.reply_text(not_understood.get(lang, not_understood["en"]))
            return

        # Show what we heard
        try:
            await status_msg.edit_text(f"🎤 _\"{transcript}\"_\n⏳ Processing…", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

        # Process as text (same flow)
        if lang != "en":
            query_en = translator.to_english(transcript, src=lang)
        else:
            query_en = transcript

        # Memory
        memory_context = ""
        try:
            mem_engine = get_memory_engine(profile_id)
            memory_context = mem_engine.get_memory_context(query_en)
        except Exception:
            pass

        # AI response
        app = _get_backend()
        result = app.ask(query_en, user_id=profile_id, memory_context=memory_context)
        response_text = result.get("response", "")
        sources = result.get("sources", [])

        if response_text:
            response_text = translator.ensure_english(response_text)
            if lang != "en":
                response_text = translator.from_english(response_text, dest=lang)

        # Save messages
        SupabaseManager.save_message(profile_id, "user", transcript)
        SupabaseManager.save_message(profile_id, "assistant", response_text, sources)

        # Extract memories
        try:
            mem_engine = get_memory_engine(profile_id)
            mem_engine.add_from_conversation(query_en, result.get("response", ""))
        except Exception:
            pass

        # Delete status message
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Send text reply
        reply = response_text
        if sources:
            src_str = " · ".join(sources[:5])
            reply += f"\n\n📚 _{src_str}_"
        await _send_long(update, reply, reply_to=update.message.message_id)

        # Also send voice reply (TTS)
        try:
            audio_bytes = voice.text_to_speech(
                text=response_text,
                language=lang,
                output_format="ogg_vorbis",
            )

            if audio_bytes and len(audio_bytes) > 100:
                # gTTS returns mp3, Polly returns ogg — both playable
                await update.message.reply_voice(
                    voice=io.BytesIO(audio_bytes),
                    reply_to_message_id=update.message.message_id,
                )
        except Exception as exc:
            logger.warning("TTS voice reply failed (non-fatal): %s", exc)

    except Exception as exc:
        logger.error("Voice handler error: %s", exc, exc_info=True)
        error_msgs = {
            "en": "❌ Could not process voice message. Please try again or type your question.",
            "hi": "❌ वॉइस मैसेज प्रोसेस नहीं हो सका। कृपया पुनः प्रयास करें।",
            "te": "❌ వాయిస్ మెసేజ్ ప్రాసెస్ చేయలేకపోయింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        }
        await update.message.reply_text(error_msgs.get(lang, error_msgs["en"]))


# ═══════════════════════════════════════════════════════════════════════
#  Error handler
# ═══════════════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors from the bot."""
    logger.error("Telegram bot error: %s", context.error, exc_info=context.error)


# ═══════════════════════════════════════════════════════════════════════
#  Application builder
# ═══════════════════════════════════════════════════════════════════════

def build_bot() -> Application:
    """Build and configure the Telegram bot application."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("clear", cmd_clear))

    # Callback query handler (language selection buttons)
    app.add_handler(CallbackQueryHandler(callback_language, pattern=r"^lang:"))

    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Error handler
    app.add_error_handler(error_handler)

    return app


async def set_bot_commands(app: Application) -> None:
    """Set the bot's command menu in Telegram."""
    commands = [
        BotCommand("start", "Start KrishiSaathi"),
        BotCommand("help", "Show help"),
        BotCommand("language", "Change language"),
        BotCommand("clear", "Clear chat history"),
    ]
    await app.bot.set_my_commands(commands)


def run_bot() -> None:
    """Entry point — run the bot with long polling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  [TG-Bot]  %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Starting KrishiSaathi Telegram Bot…")

    # Ensure database tables exist (including telegram_users)
    if SupabaseManager.is_configured():
        from backend.services.rds_service import ensure_tables
        ensure_tables()
        logger.info("Database tables ensured ✓")

    app = build_bot()

    # Set bot commands on startup
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )
