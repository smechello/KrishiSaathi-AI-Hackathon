"""Sidebar component — branding, language, theme toggle & quick links."""

from __future__ import annotations

import base64
import os

import streamlit as st

from backend.config import Config
from backend.services.supabase_service import SupabaseManager
from backend.services.memory_engine import get_memory_engine
from frontend.components.theme import (
    ICON,
    icon,
    get_theme,
    set_theme,
    get_palette,
    inject_global_css,
    _logo_b64,
)
from frontend.components.auth import is_admin

# ── Language display names in their own script ─────────────────────────
LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "te": "తెలుగు (Telugu)",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "gu": "ગુજરાતી (Gujarati)",
    "pa": "ਪੰਜਾਬੀ (Punjabi)",
    "or": "ଓଡ଼ିଆ (Odia)",
    "as": "অসমীয়া (Assamese)",
}

# ── Greeting per language ──────────────────────────────────────────────
GREETINGS: dict[str, str] = {
    "en": "Hello! I am KrishiSaathi — your AI farming companion. Ask me anything about crops, weather, market prices, government schemes, or soil health!",
    "te": "నమస్కారం! నేను కృషిసాథి — మీ AI వ్యవసాయ సహచరుడు. పంటలు, వాతావరణం, మార్కెట్ ధరలు, ప్రభుత్వ పథకాలు లేదా నేల ఆరోగ్యం గురించి ఏదైనా అడగండి!",
    "hi": "नमस्ते! मैं कृषिसाथी हूं — आपका AI खेती सहायक। फसल, मौसम, बाजार भाव, सरकारी योजनाएं या मिट्टी स्वास्थ्य — कुछ भी पूछें!",
    "ta": "வணக்கம்! நான் கிருஷிசாத்தி — உங்கள் AI விவசாய தோழன். பயிர்கள், வானிலை, சந்தை விலைகள், அரசு திட்டங்கள் அல்லது மண் ஆரோக்கியம் பற்றி எதையும் கேளுங்கள்!",
    "kn": "ನಮಸ್ಕಾರ! ನಾನು ಕೃಷಿಸಾಥಿ — ನಿಮ್ಮ AI ಕೃಷಿ ಸಹಚರ. ಬೆಳೆಗಳು, ಹವಾಮಾನ, ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು, ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಅಥವಾ ಮಣ್ಣಿನ ಆರೋಗ್ಯದ ಬಗ್ಗೆ ಏನನ್ನಾದರೂ ಕೇಳಿ!",
    "ml": "നമസ്കാരം! ഞാൻ കൃഷിസാത്തി — നിങ്ങളുടെ AI കൃഷി സഹായി. വിളകൾ, കാലാവസ്ഥ, വിപണി വിലകൾ, സർക്കാർ പദ്ധതികൾ, മണ്ണ് ആരോഗ്യം — എന്തും ചോദിക്കൂ!",
    "bn": "নমস্কার! আমি কৃষিসাথী — আপনার AI কৃষি সহায়ক। ফসল, আবহাওয়া, বাজার দর, সরকারি প্রকল্প বা মাটি স্বাস্থ্য — যেকোনো প্রশ্ন করুন!",
    "mr": "नमस्कार! मी कृषिसाथी आहे — तुमचा AI शेती सहायक. पिके, हवामान, बाजारभाव, सरकारी योजना किंवा मातीचे आरोग्य — काहीही विचारा!",
    "gu": "નમસ્તે! હું કૃષિસાથી — તમારો AI ખેતી સહાયક. પાક, હવામાન, બજાર ભાવ, સરકારી યોજનાઓ અથવા જમીન આરોગ્ય — કંઈ પણ પૂછો!",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਕ੍ਰਿਸ਼ੀਸਾਥੀ — ਤੁਹਾਡਾ AI ਖੇਤੀ ਸਹਾਇਕ। ਫ਼ਸਲਾਂ, ਮੌਸਮ, ਮੰਡੀ ਭਾਅ, ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਜਾਂ ਮਿੱਟੀ ਸਿਹਤ — ਕੁਝ ਵੀ ਪੁੱਛੋ!",
    "or": "ନମସ୍କାର! ମୁଁ କୃଷିସାଥୀ — ଆପଣଙ୍କ AI ଚାଷ ସହାୟକ। ଫସଲ, ପାଣିପାଗ, ବଜାର ଦର, ସରକାରୀ ଯୋଜନା ବା ମାଟି ସ୍ୱାସ୍ଥ୍ୟ — ଯାହା ବି ପଚାରନ୍ତୁ!",
    "as": "নমস্কাৰ! মই কৃষিসাথী — আপোনাৰ AI কৃষি সহায়ক। শস্য, বতৰ, বজাৰ মূল্য, চৰকাৰী আঁচনি বা মাটিৰ স্বাস্থ্য — যিকোনো কথা সোধক!",
}

# ── Quick-action labels per language ───────────────────────────────────
QUICK_ACTIONS: dict[str, list[tuple[str, str, str]]] = {
    "en": [
        ("crop", "Crop Disease", "My crop has a disease, help me diagnose it"),
        ("rupee", "Market Prices", "What are today's mandi prices for rice?"),
        ("scheme", "Govt Schemes", "What government schemes am I eligible for?"),
        ("weather", "Weather", "What is the weather forecast for my area?"),
        ("soil", "Soil Health", "Recommend fertilizers for my red soil"),
    ],
    "te": [
        ("crop", "పంట వ్యాధి", "నా పంటకు వ్యాధి వచ్చింది, నిర్ధారణ చేయండి"),
        ("rupee", "మార్కెట్ ధరలు", "ఈ రోజు వరి మండి ధర ఎంత?"),
        ("scheme", "ప్రభుత్వ పథకాలు", "నాకు ఏ ప్రభుత్వ పథకాలు అర్హత ఉన్నాయి?"),
        ("weather", "వాతావరణం", "నా ప్రాంతంలో వాతావరణ సూచన ఏమిటి?"),
        ("soil", "నేల ఆరోగ్యం", "ఎర్ర నేలకు ఎరువులు సిఫార్సు చేయండి"),
    ],
    "hi": [
        ("crop", "फसल रोग", "मेरी फसल में रोग लगा है, पहचान करो"),
        ("rupee", "मंडी भाव", "आज चावल का मंडी भाव क्या है?"),
        ("scheme", "सरकारी योजना", "मुझे कौन सी सरकारी योजनाएं मिल सकती हैं?"),
        ("weather", "मौसम", "मेरे क्षेत्र का मौसम कैसा रहेगा?"),
        ("soil", "मिट्टी स्वास्थ्य", "लाल मिट्टी के लिए खाद सुझाव दें"),
    ],
}


def render_sidebar() -> str:
    """Render the sidebar and return the selected language code."""

    # Ensure theme state exists
    if "ks_theme" not in st.session_state:
        st.session_state["ks_theme"] = "light"

    with st.sidebar:
        theme = get_theme()
        p = get_palette(theme)

        # ── Inject global CSS ──────────────────────────────────────────
        inject_global_css(theme)

        # ── Logo & Branding ────────────────────────────────────────────
        logo_data = _logo_b64()
        logo_html = f'<img src="data:image/svg+xml;base64,{logo_data}" alt="KrishiSaathi Logo">' if logo_data else ""

        st.markdown(
            f"""
            <div class="ks-sidebar-brand">
                {logo_html}
                <h2>KrishiSaathi</h2>
                <p>AI Agricultural Advisory System</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Theme Toggle ───────────────────────────────────────────────
        theme_labels = {"light": "Light Mode", "dark": "Dark Mode"}
        sun_icon = icon("sun", size=16, color=p["accent"])
        moon_icon = icon("moon", size=16, color=p["info"])

        tcol1, tcol2 = st.columns([1, 1])
        with tcol1:
            if st.button(
                "☀️ Light" if theme == "dark" else "☀️ Light",
                key="theme_light",
                use_container_width=True,
                disabled=(theme == "light"),
            ):
                set_theme("light")
                st.rerun()
        with tcol2:
            if st.button(
                "🌙 Dark" if theme == "light" else "🌙 Dark",
                key="theme_dark",
                use_container_width=True,
                disabled=(theme == "dark"),
            ):
                set_theme("dark")
                st.rerun()

        st.divider()

        # ── User Profile (only when authenticated) ─────────────────────
        _is_authed = st.session_state.get("authenticated", False)
        _user = st.session_state.get("auth_user")

        if SupabaseManager.is_configured() and _is_authed and _user:
            user_icon = icon("user", size=18, color=p["primary"]) if "user" in ICON else "👤"
            display_name = _user.get("full_name") or _user.get("email", "User")
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:0.5rem; '
                f'padding:0.6rem 0.75rem; background:{p["surface"]}; '
                f'border-radius:10px; margin-bottom:0.5rem;">'
                f'  <div style="width:36px; height:36px; border-radius:50%; '
                f'background:{p["primary"]}; display:flex; align-items:center; '
                f'justify-content:center; color:#fff; font-weight:700; font-size:1rem;">'
                f'{display_name[0].upper()}</div>'
                f'  <div style="flex:1; min-width:0;">'
                f'    <div style="font-weight:600; font-size:0.9rem; color:{p["text"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>'
                f'    <div style="font-size:0.75rem; color:{p["text_muted"]}; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{_user.get("email","")}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("🚪 Sign Out", use_container_width=True, key="btn_logout"):
                SupabaseManager.sign_out()
                st.session_state["messages"] = []
                st.session_state.pop("_chat_loaded", None)
                st.rerun()

            # ── Admin badge ────────────────────────────────────────────
            if is_admin():
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:0.4rem; '
                    f'padding:0.4rem 0.7rem; background:{p["warning"]}22; '
                    f'border:1px solid {p["warning"]}44; border-radius:8px; margin-top:0.4rem;">'
                    f'🔒 <span style="font-weight:600; font-size:0.85rem; color:{p["warning"]};">Admin</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.divider()

        # ── Language selector ──────────────────────────────────────────
        lang_icon = icon("language", size=18, color=p["primary"])
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.3rem;">'
            f'{lang_icon} <span style="font-weight:600; font-size:0.95rem;">Language / భాష</span></div>',
            unsafe_allow_html=True,
        )

        lang_codes = list(LANGUAGE_LABELS.keys())
        lang_labels = list(LANGUAGE_LABELS.values())

        current_lang = st.session_state.get("language", Config.DEFAULT_LANGUAGE)
        try:
            current_idx = lang_codes.index(current_lang)
        except ValueError:
            current_idx = 0

        selected_label = st.selectbox(
            "Choose your language",
            options=lang_labels,
            index=current_idx,
            key="lang_selector",
            label_visibility="collapsed",
        )
        selected_code = lang_codes[lang_labels.index(selected_label)]

        if selected_code != st.session_state.get("language"):
            st.session_state["language"] = selected_code
            st.session_state["lang_changed"] = True
            st.rerun()
        else:
            st.session_state["lang_changed"] = False

        st.divider()

        # ── Quick Actions ──────────────────────────────────────────────
        lang = st.session_state.get("language", "en")
        actions = QUICK_ACTIONS.get(lang, QUICK_ACTIONS["en"])

        qa_header = {
            "en": "Quick Actions",
            "te": "త్వరిత చర్యలు",
            "hi": "त्वरित कार्य",
        }.get(lang, "Quick Actions")

        zap_icon = icon("zap", size=18, color=p["accent"])
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.5rem;">'
            f'{zap_icon} <span style="font-weight:600; font-size:0.95rem;">{qa_header}</span></div>',
            unsafe_allow_html=True,
        )

        for icon_name, label, query in actions:
            ic = icon(icon_name, size=16, color=p["primary"])
            if st.button(f"{label}", key=f"qa_{label}", use_container_width=True):
                st.session_state["pending_query"] = query

        st.divider()

        # ── Memory Panel (only when authenticated) ─────────────────────
        if SupabaseManager.is_configured() and _is_authed and _user:
            _render_memory_panel(_user, lang, p)
            st.divider()

        # ── Chat controls ──────────────────────────────────────────────
        clear_label = {
            "en": "Clear Chat",
            "te": "చాట్ క్లియర్",
            "hi": "चैट मिटाएं",
        }.get(lang, "Clear Chat")

        if st.button(f"🗑️ {clear_label}", use_container_width=True, key="btn_clear"):
            st.session_state["messages"] = []
            st.session_state.pop("pending_query", None)
            st.session_state.pop("_chat_loaded", None)
            # Also clear from Supabase if authenticated
            if SupabaseManager.is_configured() and _is_authed and _user:
                SupabaseManager.clear_messages(_user["id"])
            st.rerun()

        # ── Footer ─────────────────────────────────────────────────────
        st.divider()
        heart = icon("heart", size=12, color="#e53935")
        st.markdown(
            f"""
            <div class="ks-footer">
                <p>Built with {heart} for Indian Farmers</p>
                <p>Powered by Groq · Gemini · ChromaDB</p>
                <p style="margin-top:0.3rem;">© 2026 KrishiSaathi</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.get("language", Config.DEFAULT_LANGUAGE)


# ═══════════════════════════════════════════════════════════════════════
#  Memory Panel — shows memory stats & management
# ═══════════════════════════════════════════════════════════════════════

CATEGORY_ICONS: dict[str, str] = {
    "personal": "👤",
    "location": "📍",
    "farming": "🌾",
    "crops": "🌿",
    "equipment": "🚜",
    "livestock": "🐄",
    "soil": "🪴",
    "preferences": "⚙️",
    "experience": "📚",
    "financial": "💰",
}

MEMORY_LABELS: dict[str, dict[str, str]] = {
    "en": {"header": "Memory", "count": "memories", "clear": "Clear All Memories", "empty": "No memories yet — start chatting!"},
    "te": {"header": "జ్ఞాపకాలు", "count": "జ్ఞాపకాలు", "clear": "అన్ని జ్ఞాపకాలు తొలగించు", "empty": "ఇంకా జ్ఞాపకాలు లేవు — చాట్ చేయడం ప్రారంభించండి!"},
    "hi": {"header": "स्मृति", "count": "यादें", "clear": "सभी यादें मिटाएं", "empty": "अभी तक कोई याद नहीं — चैट शुरू करें!"},
}


def _render_memory_panel(user: dict, lang: str, p: dict) -> None:
    """Render the memory management panel in the sidebar."""
    labels = MEMORY_LABELS.get(lang, MEMORY_LABELS["en"])
    user_id = user.get("id", "")
    if not user_id:
        return

    brain_icon = icon("brain", size=18, color=p["primary"]) if "brain" in ICON else "🧠"
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.3rem;">'
        f'{brain_icon} <span style="font-weight:600; font-size:0.95rem;">{labels["header"]}</span></div>',
        unsafe_allow_html=True,
    )

    try:
        mem_engine = get_memory_engine(user_id)
        stats = mem_engine.stats()
        total = stats.get("total", 0)
        cats = stats.get("categories", {})
    except Exception:
        total = 0
        cats = {}

    if total == 0:
        st.caption(labels["empty"])
        return

    # Summary badge
    st.markdown(
        f'<div style="background:{p["surface"]}; padding:0.5rem 0.75rem; '
        f'border-radius:10px; margin-bottom:0.4rem;">'
        f'<span style="font-weight:700; color:{p["primary"]}; font-size:1.3rem;">{total}</span> '
        f'<span style="color:{p["text_muted"]}; font-size:0.85rem;">{labels["count"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Category breakdown
    if cats:
        cat_parts = []
        for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            emoji = CATEGORY_ICONS.get(cat, "📌")
            cat_parts.append(f'{emoji} {cat}: **{count}**')
        st.markdown("  \n".join(cat_parts))

    # Expandable: View Memories
    with st.expander("🔍 View Memories", expanded=False):
        try:
            memories = mem_engine.get_all(limit=30)
            for m in memories:
                cat = m.get("category", "")
                emoji = CATEGORY_ICONS.get(cat, "📌")
                imp = m.get("importance", 5)
                imp_bar = "●" * imp + "○" * (10 - imp)
                content = m.get("content", "")
                mid = m.get("id")

                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(
                        f'<div style="font-size:0.82rem; padding:0.3rem 0; '
                        f'border-bottom:1px solid {p["border"]};">'
                        f'{emoji} <b>{cat}</b> — {content}<br>'
                        f'<span style="color:{p["text_muted"]}; font-size:0.72rem;">'
                        f'Importance: {imp_bar}</span></div>',
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("🗑", key=f"del_mem_{mid}", help="Delete this memory"):
                        mem_engine.delete(mid)
                        st.rerun()
        except Exception:
            st.caption("Could not load memories.")

    # Clear all memories button
    if st.button(f"🧹 {labels['clear']}", use_container_width=True, key="btn_clear_memories"):
        try:
            mem_engine = get_memory_engine(user_id)
            mem_engine.clear_all()
            st.toast("All memories cleared!", icon="🧹")
            st.rerun()
        except Exception:
            st.error("Failed to clear memories.")
