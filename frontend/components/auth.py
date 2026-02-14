"""Authentication UI — themed login / sign-up / password-reset forms.

Usage in any page::

    from frontend.components.auth import require_auth
    user = require_auth()          # blocks with login form if not authed
    # ↓ only reached when user is authenticated
    ...
"""

from __future__ import annotations

import streamlit as st

from backend.services.supabase_service import SupabaseManager
from backend.config import Config
from frontend.components.theme import (
    get_theme,
    get_palette,
    inject_global_css,
    _logo_b64,
    icon,
)


# ═══════════════════════════════════════════════════════════════════════
#  Public helpers
# ═══════════════════════════════════════════════════════════════════════

def is_authenticated() -> bool:
    """Quick boolean check — ``True`` in local mode (no Supabase)."""
    if not SupabaseManager.is_configured():
        return True
    return st.session_state.get("authenticated", False)


def get_current_user() -> dict | None:
    """Return the current user dict or a local-mode stub."""
    if not SupabaseManager.is_configured():
        return {"id": "local", "email": "", "full_name": "Farmer"}
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    """``True`` when the current authenticated user is in the admin list."""
    user = get_current_user()
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    return email in Config.ADMIN_EMAILS


def require_auth() -> dict:
    """Auth gate — returns user dict *or* renders login UI and halts.

    Call at the top of every page/main function **after**
    ``render_sidebar()``.  In local mode (no Supabase) it returns a
    stub user dict and never blocks.
    """
    if not SupabaseManager.is_configured():
        return {"id": "local", "email": "", "full_name": "Farmer"}

    # Attempt to restore a previously-stored session
    if not st.session_state.get("authenticated"):
        SupabaseManager.restore_session()

    if st.session_state.get("authenticated"):
        return st.session_state["auth_user"]

    # ── Not authenticated → show full-page login form  ─────────────
    render_auth_page()
    st.stop()
    return {}   # unreachable, keeps type-checkers happy


# ═══════════════════════════════════════════════════════════════════════
#  Auth page renderer
# ═══════════════════════════════════════════════════════════════════════

def render_auth_page() -> None:
    """Full-page login / sign-up / password-reset form.

    Injects its own CSS and the global theme CSS so it looks correct
    even when the sidebar hasn't been rendered yet.
    """
    theme = get_theme()
    pal   = get_palette(theme)

    # Global theme + auth-specific CSS
    inject_global_css(theme)
    _inject_auth_css(pal, theme)

    # ── Centered column ────────────────────────────────────────────
    _spacer, col, _spacer2 = st.columns([1, 2, 1])

    with col:
        # Logo + branding
        logo_data = _logo_b64()
        logo_html = (
            f'<img src="data:image/svg+xml;base64,{logo_data}" '
            f'width="72" height="72" alt="KrishiSaathi Logo">'
            if logo_data else ""
        )
        st.markdown(
            f'<div class="ks-auth-header">'
            f'  {logo_html}'
            f'  <h1>KrishiSaathi</h1>'
            f'  <p>AI Agricultural Advisory System</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Tabs ───────────────────────────────────────────────────
        tab_login, tab_signup, tab_reset = st.tabs(
            ["  Sign In  ", "  Create Account  ", "  Reset Password  "]
        )

        with tab_login:
            _render_login_form(pal)

        with tab_signup:
            _render_signup_form(pal)

        with tab_reset:
            _render_reset_form(pal)

        # Footer
        st.markdown(
            f'<p class="ks-auth-footer">'
            f'Built with ❤️ for Indian Farmers &middot; © 2026 KrishiSaathi</p>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════
#  Individual form renderers
# ═══════════════════════════════════════════════════════════════════════

def _render_login_form(pal: dict) -> None:
    st.markdown(
        f'<p class="ks-auth-desc">Welcome back! Sign in to continue.</p>',
        unsafe_allow_html=True,
    )
    with st.form("ks_login_form", clear_on_submit=False):
        email    = st.text_input("Email address", placeholder="you@example.com",
                                 key="login_email")
        password = st.text_input("Password", type="password",
                                 placeholder="Enter your password",
                                 key="login_password")
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button(
                "Sign In", use_container_width=True, type="primary"
            )

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return
        with st.spinner("Signing in …"):
            result = SupabaseManager.sign_in(email.strip(), password)
        if result["success"]:
            _load_user_chat(result["user"]["id"])
            st.rerun()
        else:
            st.error(result["error"])


def _render_signup_form(pal: dict) -> None:
    st.markdown(
        f'<p class="ks-auth-desc">Create a free account to get started.</p>',
        unsafe_allow_html=True,
    )
    with st.form("ks_signup_form", clear_on_submit=False):
        full_name = st.text_input("Full name", placeholder="Your name",
                                  key="signup_name")
        email     = st.text_input("Email address", placeholder="you@example.com",
                                  key="signup_email")
        password  = st.text_input("Password", type="password",
                                  placeholder="Minimum 6 characters",
                                  key="signup_password")
        password2 = st.text_input("Confirm password", type="password",
                                  placeholder="Re-enter password",
                                  key="signup_password2")
        submitted = st.form_submit_button(
            "Create Account", use_container_width=True, type="primary"
        )

    if submitted:
        if not full_name or not email or not password:
            st.error("Please fill in all fields.")
            return
        if password != password2:
            st.error("Passwords do not match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        with st.spinner("Creating your account …"):
            result = SupabaseManager.sign_up(email.strip(), password, full_name.strip())
        if result["success"]:
            if result.get("needs_confirm"):
                st.success(
                    "✅ Account created! Check your email for a confirmation link, "
                    "then come back and sign in."
                )
            else:
                st.success("✅ Account created — you're signed in!")
                _load_user_chat(result["user"]["id"])
                st.rerun()
        else:
            st.error(result["error"])


def _render_reset_form(pal: dict) -> None:
    st.markdown(
        f'<p class="ks-auth-desc">'
        f"Enter your email and we'll send you a password-reset link.</p>",
        unsafe_allow_html=True,
    )
    with st.form("ks_reset_form", clear_on_submit=False):
        email = st.text_input("Email address", placeholder="you@example.com",
                              key="reset_email")
        submitted = st.form_submit_button(
            "Send Reset Link", use_container_width=True
        )

    if submitted:
        if not email:
            st.error("Please enter your email address.")
            return
        with st.spinner("Sending …"):
            result = SupabaseManager.reset_password(email.strip())
        if result["success"]:
            st.success(
                "If an account exists with that email you'll receive a "
                "password-reset link shortly."
            )
        else:
            st.error(result["error"])


# ═══════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════

def _load_user_chat(user_id: str) -> None:
    """Populate ``st.session_state["messages"]`` from Supabase."""
    if SupabaseManager.is_configured():
        msgs = SupabaseManager.load_messages(user_id)
        st.session_state["messages"] = msgs if msgs else []


def _inject_auth_css(pal: dict, theme: str) -> None:
    """Theme-aware CSS for the auth page."""
    shadow = "0 8px 32px rgba(0,0,0,0.28)" if theme == "dark" else "0 4px 24px rgba(0,0,0,0.08)"
    st.markdown(
        f"""<style>
        /* ── Auth header ─────────────────────────────────────────── */
        .ks-auth-header {{
            text-align: center;
            margin: 1.5rem 0 1rem;
        }}
        .ks-auth-header h1 {{
            color: {pal["text"]};
            font-size: 2rem;
            font-weight: 800;
            margin: 0.4rem 0 0.1rem;
            letter-spacing: -0.02em;
        }}
        .ks-auth-header p {{
            color: {pal["text_muted"]};
            font-size: 0.95rem;
            margin: 0;
        }}

        /* ── Tab styling ─────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {{
            justify-content: center;
            gap: 0;
            background: {pal["surface"]};
            border-radius: 12px;
            padding: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            font-size: 0.9rem;
            color: {pal["text_secondary"]};
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background: {pal["primary"]} !important;
            color: #ffffff !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none;
        }}
        .stTabs [data-baseweb="tab-border"] {{
            display: none;
        }}

        /* ── Form descriptions ───────────────────────────────────── */
        .ks-auth-desc {{
            color: {pal["text_secondary"]};
            font-size: 0.92rem;
            margin-bottom: 0.75rem;
        }}

        /* ── Footer ──────────────────────────────────────────────── */
        .ks-auth-footer {{
            text-align: center;
            color: {pal["text_muted"]};
            font-size: 0.78rem;
            margin-top: 1rem;
        }}

        /* ── Form container card effect ──────────────────────────── */
        .stTabs [data-baseweb="tab-panel"] {{
            background: {pal["card"]};
            border-radius: 0 0 16px 16px;
            padding: 1.25rem 1rem;
            border: 1px solid {pal["card_border"]};
            border-top: none;
            box-shadow: {shadow};
        }}
        </style>""",
        unsafe_allow_html=True,
    )
