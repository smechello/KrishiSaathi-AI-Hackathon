"""Chat interface component — clean, modern message rendering."""

from __future__ import annotations

import streamlit as st

from frontend.components.theme import icon, get_theme, get_palette


# ── CSS for chat bubbles (theme-aware) ─────────────────────────────────

def inject_chat_css() -> None:
    """Inject chat-specific CSS. Called once per page load."""
    p = get_palette(get_theme())
    css = f"""
    <style>
    /* --- Chat message overrides ---------------------------------------- */
    [data-testid="stChatMessage"] {{
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.5rem !important;
        background: {p['card']} !important;
        border: 1px solid {p['card_border']} !important;
        box-shadow: 0 1px 3px {p['shadow']};
    }}
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] em,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4 {{
        color: {p['text']} !important;
    }}

    /* --- Source citations ----------------------------------------------- */
    .ks-sources {{
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        color: {p['text_muted']} !important;
        margin-top: 0.4rem;
    }}
    .ks-sources code {{
        background: {p['bg_secondary']} !important;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-size: 0.75rem;
        color: {p['text_muted']} !important;
    }}

    /* --- Input area --------------------------------------------------- */
    .stChatInput > div {{
        border-color: {p['primary']} !important;
        border-radius: 12px !important;
        background: {p['surface']} !important;
    }}
    .stChatInput textarea,
    .stChatInput input {{
        color: {p['text']} !important;
        background: {p['surface']} !important;
    }}
    .stChatInput textarea::placeholder {{
        color: {p['text_muted']} !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_message(
    role: str,
    content: str,
    sources: list[str] | None = None,
    *,
    language: str | None = None,
    tts_key: str | None = None,
) -> None:
    """Render a single chat message.

    Parameters
    ----------
    role     : "user" or "assistant"
    content  : The message text (supports Markdown).
    sources  : Optional list of source labels (only for assistant messages).
    language : App language code — enables a persistent 🔊 Listen button.
    tts_key  : Unique key suffix for the TTS button widget.
    """
    p = get_palette(get_theme())

    if role == "user":
        with st.chat_message("user", avatar="👨‍🌾"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🌾"):
            st.markdown(content)
            if sources:
                src_icon = icon("source", size=13, color=p["text_muted"])
                src_str = " · ".join(f"`{s}`" for s in sources)
                st.markdown(
                    f'<div class="ks-sources">{src_icon} {src_str}</div>',
                    unsafe_allow_html=True,
                )
            # Persistent TTS button (survives page reruns)
            if language and tts_key and content and content.strip():
                from frontend.components.voice_input import render_voice_output
                render_voice_output(
                    text=content, language=language, key_suffix=tts_key,
                )


def render_chat_history(messages: list[dict], *, language: str | None = None) -> None:
    """Render the full chat history from session state."""
    for i, msg in enumerate(messages):
        render_message(
            role=msg["role"],
            content=msg["content"],
            sources=msg.get("sources"),
            language=language,
            tts_key=f"hist_{i}" if language else None,
        )


def show_typing_indicator() -> None:
    """Show a 'KrishiSaathi is thinking…' placeholder."""
    with st.chat_message("assistant", avatar="🌾"):
        st.markdown("_Thinking…_ ⏳")
