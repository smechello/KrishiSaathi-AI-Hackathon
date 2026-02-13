"""Chat interface component — WhatsApp-style message bubbles."""

from __future__ import annotations

import streamlit as st


# ── CSS for chat bubbles ───────────────────────────────────────────────
CHAT_CSS = """
<style>
/* --- Chat container ------------------------------------------------ */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    padding: 1rem 0;
}

/* --- Message bubbles ----------------------------------------------- */
.msg-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}
.msg-row.user { flex-direction: row-reverse; }
.msg-row.bot  { flex-direction: row; }

.msg-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
}
.msg-avatar.user { background: #e8f5e9; }
.msg-avatar.bot  { background: #fff3e0; }

.msg-bubble {
    max-width: 80%;
    padding: 0.75rem 1rem;
    border-radius: 16px;
    font-size: 0.95rem;
    line-height: 1.5;
    word-wrap: break-word;
}
.msg-bubble.user {
    background: #dcf8c6;
    border-top-right-radius: 4px;
    color: #1b1b1b;
}
.msg-bubble.bot {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-top-left-radius: 4px;
    color: #1b1b1b;
}

/* --- Sources tag --------------------------------------------------- */
.sources-tag {
    font-size: 0.78rem;
    color: #777;
    margin-top: 0.4rem;
    padding-left: 0.5rem;
}

/* --- Typing indicator --------------------------------------------- */
@keyframes blink {
    0%, 80%, 100% { opacity: 0; }
    40% { opacity: 1; }
}
.typing-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #888;
    margin: 0 2px;
    animation: blink 1.4s infinite both;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

/* ---- Input area --------------------------------------------------- */
.stChatInput > div {
    border-color: #2e7d32 !important;
}
</style>
"""


def inject_chat_css() -> None:
    """Inject the chat CSS once per page load."""
    st.markdown(CHAT_CSS, unsafe_allow_html=True)


def render_message(role: str, content: str, sources: list[str] | None = None) -> None:
    """Render a single chat message as a styled bubble.

    Parameters
    ----------
    role    : "user" or "assistant"
    content : The message text (supports Markdown).
    sources : Optional list of source labels (only for assistant messages).
    """
    if role == "user":
        with st.chat_message("user", avatar="👨‍🌾"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🌾"):
            st.markdown(content)
            if sources:
                src_str = " · ".join(f"`{s}`" for s in sources)
                st.caption(f"📚 Sources: {src_str}")


def render_chat_history(messages: list[dict]) -> None:
    """Render the full chat history from session state."""
    for msg in messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            sources=msg.get("sources"),
        )


def show_typing_indicator() -> None:
    """Show a 'KrishiSaathi is thinking…' placeholder."""
    with st.chat_message("assistant", avatar="🌾"):
        st.markdown("_Thinking…_ ⏳")
