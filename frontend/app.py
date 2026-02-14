"""KrishiSaathi — Main Streamlit Chat Application.

Launch with:
    streamlit run frontend/app.py
"""

from __future__ import annotations

import logging
import os
import sys
import time

import streamlit as st

# ── Project root on sys.path ───────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.main import KrishiSaathi  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar, GREETINGS  # noqa: E402
from frontend.components.chat_interface import (  # noqa: E402
    inject_chat_css,
    render_message,
    render_chat_history,
)
from frontend.components.theme import render_page_header, icon, get_theme, get_palette  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402
from backend.services.supabase_service import SupabaseManager  # noqa: E402
from backend.services.memory_engine import get_memory_engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KrishiSaathi — AI Farming Companion",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "KrishiSaathi — AI Agricultural Advisory System for Indian Farmers.",
    },
)


# ── Cached backend init (runs once across reruns) ──────────────────────
@st.cache_resource(show_spinner="Loading KrishiSaathi AI engine …")
def get_backend() -> KrishiSaathi:
    """Initialise the backend once and cache it."""
    return KrishiSaathi()


# ── Session state defaults ─────────────────────────────────────────────
def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE


# ── Localised UI strings ──────────────────────────────────────────────
_UI_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "🌾 KrishiSaathi",
        "subtitle": "AI Agricultural Advisory — Ask anything about farming!",
        "input_placeholder": "Type your farming question here …",
        "thinking": "KrishiSaathi is thinking …",
        "error": "Sorry, something went wrong. Please try again.",
        "welcome_banner": "Welcome to KrishiSaathi!",
    },
    "te": {
        "title": "🌾 కృషిసాథి",
        "subtitle": "AI వ్యవసాయ సలహా — వ్యవసాయం గురించి ఏదైనా అడగండి!",
        "input_placeholder": "మీ వ్యవసాయ ప్రశ్నను ఇక్కడ టైప్ చేయండి …",
        "thinking": "కృషిసాథి ఆలోచిస్తోంది …",
        "error": "క్షమించండి, ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        "welcome_banner": "కృషిసాథికి స్వాగతం!",
    },
    "hi": {
        "title": "🌾 कृषिसाथी",
        "subtitle": "AI कृषि सलाहकार — खेती से जुड़ा कोई भी सवाल पूछें!",
        "input_placeholder": "अपना खेती का सवाल यहाँ टाइप करें …",
        "thinking": "कृषिसाथी सोच रहा है …",
        "error": "क्षमा करें, कुछ गलत हो गया। कृपया पुनः प्रयास करें।",
        "welcome_banner": "कृषिसाथी में आपका स्वागत है!",
    },
    "ta": {
        "title": "🌾 கிருஷிசாத்தி",
        "subtitle": "AI விவசாய ஆலோசனை — விவசாயம் பற்றி எதையும் கேளுங்கள்!",
        "input_placeholder": "உங்கள் விவசாய கேள்வியை இங்கே தட்டச்சு செய்யவும் …",
        "thinking": "கிருஷிசாத்தி யோசித்துக்கொண்டிருக்கிறது …",
        "error": "மன்னிக்கவும், ஏதோ தவறு. மீண்டும் முயற்சிக்கவும்.",
        "welcome_banner": "கிருஷிசாத்திக்கு வரவேற்கிறோம்!",
    },
    "kn": {
        "title": "🌾 ಕೃಷಿಸಾಥಿ",
        "subtitle": "AI ಕೃಷಿ ಸಲಹೆ — ಕೃಷಿಯ ಬಗ್ಗೆ ಏನಾದರೂ ಕೇಳಿ!",
        "input_placeholder": "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ …",
        "thinking": "ಕೃಷಿಸಾಥಿ ಯೋಚಿಸುತ್ತಿದೆ …",
        "error": "ಕ್ಷಮಿಸಿ, ಏನೋ ತಪ್ಪಾಯಿತು. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "welcome_banner": "ಕೃಷಿಸಾಥಿಗೆ ಸ್ವಾಗತ!",
    },
    "ml": {
        "title": "🌾 കൃഷിസാത്തി",
        "subtitle": "AI കാർഷിക ഉപദേശം — കൃഷിയെ കുറിച്ച് എന്തും ചോദിക്കൂ!",
        "input_placeholder": "നിങ്ങളുടെ കൃഷി ചോദ്യം ഇവിടെ ടൈപ്പ് ചെയ്യുക …",
        "thinking": "കൃഷിസാത്തി ചിന്തിക്കുന്നു …",
        "error": "ക്ഷമിക്കണം, എന്തോ കുഴപ്പം. ദയവായി വീണ്ടും ശ്രമിക്കുക.",
        "welcome_banner": "കൃഷിസാത്തിയിലേക്ക് സ്വാഗതം!",
    },
    "bn": {
        "title": "🌾 কৃষিসাথী",
        "subtitle": "AI কৃষি পরামর্শ — চাষাবাদ সম্পর্কে যেকোনো প্রশ্ন করুন!",
        "input_placeholder": "আপনার কৃষি প্রশ্ন এখানে টাইপ করুন …",
        "thinking": "কৃষিসাথী ভাবছে …",
        "error": "দুঃখিত, কিছু ভুল হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        "welcome_banner": "কৃষিসাথীতে স্বাগতম!",
    },
}


def _ui(lang: str, key: str) -> str:
    """Get a localised UI string, fallback to English."""
    return _UI_STRINGS.get(lang, _UI_STRINGS["en"]).get(key, _UI_STRINGS["en"][key])


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    _init_session()
    inject_chat_css()

    # ── Sidebar (returns selected language code) ───────────────────────
    lang = render_sidebar()

    # ── Auth gate (shows login form & stops if not authenticated) ──────
    user = require_auth()

    # ── Header ─────────────────────────────────────────────────────────
    render_page_header(
        title=_ui(lang, "title").replace("🌾 ", ""),
        subtitle=_ui(lang, "subtitle"),
        icon_name="leaf",
    )

    # ── Load persisted chat history for this user (first load) ─────────
    if SupabaseManager.is_configured() and user.get("id") != "local":
        if "_chat_loaded" not in st.session_state:
            saved = SupabaseManager.load_messages(user["id"])
            if saved:
                st.session_state["messages"] = saved
            st.session_state["_chat_loaded"] = True

    # ── Welcome message (only if chat is empty) ────────────────────────
    if not st.session_state["messages"]:
        greeting = GREETINGS.get(lang, GREETINGS["en"])
        st.session_state["messages"].append(
            {"role": "assistant", "content": greeting, "sources": None}
        )

    # ── Render chat history ────────────────────────────────────────────
    render_chat_history(st.session_state["messages"])

    # ── Backend ────────────────────────────────────────────────────────
    app = get_backend()

    # ── Check for pending query from Quick Actions ─────────────────────
    pending = st.session_state.pop("pending_query", None)

    # ── Chat input ─────────────────────────────────────────────────────
    user_input = st.chat_input(
        placeholder=_ui(lang, "input_placeholder"),
        key="chat_input",
    )

    # Use pending quick-action if no direct input
    query = user_input or pending
    if not query:
        return

    # ── Add user message ───────────────────────────────────────────────
    st.session_state["messages"].append(
        {"role": "user", "content": query, "sources": None}
    )
    render_message("user", query)

    # Persist user message to Supabase
    if SupabaseManager.is_configured() and user.get("id") != "local":
        SupabaseManager.save_message(user["id"], "user", query)

    # ── Translate user query to English if needed ──────────────────────
    if lang != "en":
        query_en = translator.to_english(query, src=lang)
    else:
        query_en = query

    # ── Retrieve memory context for this user ──────────────────────────
    memory_context = ""
    user_id = user.get("id", "local")
    if SupabaseManager.is_configured() and user_id != "local":
        try:
            mem_engine = get_memory_engine(user_id)
            memory_context = mem_engine.get_memory_context(query_en)
            if memory_context:
                logger.info("Injecting %d chars of memory context", len(memory_context))
        except Exception as exc:
            logger.warning("Memory retrieval failed (non-fatal): %s", exc)

    # ── Get AI response ────────────────────────────────────────────────
    with st.chat_message("assistant", avatar="🌾"):
        with st.spinner(_ui(lang, "thinking")):
            try:
                start = time.time()
                result = app.ask(query_en, user_id=user_id, memory_context=memory_context)
                elapsed = time.time() - start
                logger.info("Response in %.1fs  intent=%s", elapsed, result.get("intent", {}).get("primary_intent"))

                response_text: str = result.get("response", "")
                sources: list[str] = result.get("sources", [])

                # Translate response back to user's language
                if lang != "en" and response_text:
                    response_text = translator.from_english(response_text, dest=lang)

            except Exception as exc:
                logger.error("Backend error: %s", exc, exc_info=True)
                response_text = _ui(lang, "error")
                sources = []

        # Display the response
        st.markdown(response_text)
        if sources:
            p = get_palette(get_theme())
            src_icon = icon("source", size=13, color=p["text_muted"])
            src_str = " · ".join(f"`{s}`" for s in sources)
            st.markdown(
                f'<div class="ks-sources">{src_icon} {src_str}</div>',
                unsafe_allow_html=True,
            )

    # ── Save assistant message ─────────────────────────────────────────
    st.session_state["messages"].append(
        {"role": "assistant", "content": response_text, "sources": sources}
    )

    # Persist assistant message to Supabase
    if SupabaseManager.is_configured() and user.get("id") != "local":
        SupabaseManager.save_message(user["id"], "assistant", response_text, sources)

    # ── Extract & store memories from this conversation turn ───────────
    if SupabaseManager.is_configured() and user.get("id") != "local":
        try:
            mem_engine = get_memory_engine(user["id"])
            new_memories = mem_engine.add_from_conversation(query_en, response_text)
            if new_memories:
                logger.info("Stored %d new memories from this turn", len(new_memories))
        except Exception as exc:
            logger.warning("Memory extraction failed (non-fatal): %s", exc)


if __name__ == "__main__":
    main()
