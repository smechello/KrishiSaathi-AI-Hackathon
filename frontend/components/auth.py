"""Authentication UI — themed login / sign-up / password-reset forms.

Usage in any page::

    from frontend.components.auth import require_auth
    user = require_auth()          # blocks with login form if not authed
    # ↓ only reached when user is authenticated
    ...
"""

from __future__ import annotations

import re
import time
import string
import secrets
import streamlit as st
import streamlit.components.v1 as components

from backend.services.supabase_service import SupabaseManager
from backend.config import Config
from frontend.components.theme import (
    get_theme,
    get_palette,
    inject_global_css,
    _logo_b64,
    icon,
)

# ── Cookie-based persistent session ───────────────────────────────────
_COOKIE_NAME = "ks_session"
_COOKIE_MAX_AGE = 86400  # 24 hours in seconds


def _set_auth_cookie(token: str, remember: bool = True) -> None:
    """Inject JS to set a session cookie in the browser.

    If *remember* is True, cookie persists for 24 h.
    If False, it's a session cookie (cleared when the browser closes).
    """
    if remember:
        age_part = f"max-age={_COOKIE_MAX_AGE};"
    else:
        age_part = ""  # session cookie — no max-age
    components.html(
        f"""<script>
        document.cookie = "{_COOKIE_NAME}={token}; path=/; {age_part} SameSite=Lax; Secure";
        </script>""",
        height=0, width=0,
    )


def _inject_clear_cookie_js() -> None:
    """Inject JS to delete the session cookie (called on rendered page)."""
    components.html(
        f"""<script>
        document.cookie = "{_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax; Secure";
        </script>""",
        height=0, width=0,
    )


def _get_auth_cookie() -> str | None:
    """Read the session cookie via st.context.cookies."""
    try:
        cookies = st.context.cookies
        return cookies.get(_COOKIE_NAME)
    except Exception:
        return None


def _restore_from_cookie() -> bool:
    """Try to restore session from browser cookie. Returns True on success."""
    # If user just signed out, don't restore from cookie
    if st.session_state.get("_pending_cookie_clear"):
        return False
    token = _get_auth_cookie()
    if not token:
        return False
    # Validate the JWT
    from backend.services.rds_service import _decode_token, _create_tokens, _exec
    payload = _decode_token(token)
    if not payload or payload.get("type") != "access":
        return False
    # Check user still exists
    try:
        row = _exec(
            "SELECT id, full_name, email FROM profiles WHERE id = %s",
            (payload["sub"],), fetch="one",
        )
    except Exception:
        return False
    if not row:
        return False
    user_dict = {"id": row["id"], "email": row["email"], "full_name": row["full_name"]}
    tokens = _create_tokens(row["id"], row["email"])
    st.session_state["auth_tokens"] = tokens
    st.session_state["auth_user"] = user_dict
    st.session_state["authenticated"] = True
    return True


# ── Password generator ─────────────────────────────────────────────
def _generate_strong_password(length: int = 14) -> str:
    """Generate a random password that satisfies all complexity rules."""
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%&*?")
    rest = [secrets.choice(string.ascii_letters + string.digits + "!@#$%&*?")
            for _ in range(length - 4)]
    pwd_chars = list(upper + lower + digit + special) + rest
    secrets.SystemRandom().shuffle(pwd_chars)
    return "".join(pwd_chars)

# ── Rate limiting for login attempts ─────────────────────────────────────
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes

def _check_rate_limit() -> tuple[bool, int]:
    """Return (allowed, seconds_remaining). Uses session state."""
    now = time.time()
    attempts = st.session_state.get("_login_attempts", 0)
    lockout_until = st.session_state.get("_login_lockout_until", 0)
    if now < lockout_until:
        return False, int(lockout_until - now)
    return True, 0

def _record_failed_login():
    attempts = st.session_state.get("_login_attempts", 0) + 1
    st.session_state["_login_attempts"] = attempts
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        st.session_state["_login_lockout_until"] = time.time() + _LOCKOUT_SECONDS
        st.session_state["_login_attempts"] = 0

def _reset_login_attempts():
    st.session_state["_login_attempts"] = 0
    st.session_state.pop("_login_lockout_until", None)

def _validate_password_strength(password: str) -> str | None:
    """Return error message if password is weak, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one special character."
    return None
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
        # First try st.session_state (same tab), then browser cookie (refresh/new tab)
        restored = SupabaseManager.restore_session()
        if not restored:
            _restore_from_cookie()

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

    Also handles email-verification and password-reset links that
    arrive via ``st.query_params``.
    """
    theme = get_theme()
    pal   = get_palette(theme)

    # Global theme + auth-specific CSS
    inject_global_css(theme)
    _inject_auth_css(pal, theme)

    # ── Hide sidebar & page navigation on the login screen ────────
    st.markdown(
        """<style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        </style>""",
        unsafe_allow_html=True,
    )

    # ── Clear cookie if user just signed out (JS runs on THIS render) ──
    if st.session_state.pop("_pending_cookie_clear", False):
        _inject_clear_cookie_js()

    # ── Handle verification / reset links from email ───────────────
    params = st.query_params
    if "verify_token" in params:
        _handle_email_verification(params["verify_token"], pal)
        return
    if "reset_token" in params:
        _handle_password_reset(params["reset_token"], pal)
        return

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
        remember = st.checkbox("🔒 Remember me for 24 hours", value=True,
                               key="login_remember")
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button(
                "Sign In", use_container_width=True, type="primary"
            )

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return
        allowed, wait_secs = _check_rate_limit()
        if not allowed:
            st.error(f"🔒 Too many login attempts. Please wait {wait_secs} seconds.")
            return
        with st.spinner("Signing in …"):
            result = SupabaseManager.sign_in(email.strip(), password)
        if result["success"]:
            _reset_login_attempts()
            _load_user_chat(result["user"]["id"])
            # Persist session in browser cookie
            token = st.session_state.get("auth_tokens", {}).get("access_token")
            if token:
                _set_auth_cookie(token, remember=remember)
            st.rerun()
        else:
            _record_failed_login()
            st.error(result["error"])

    # ── Resend verification button (when email-not-verified error) ──
    resend_email = st.session_state.get("needs_verification")
    if resend_email:
        st.info("📧 Your email is not verified yet.")
        if st.button("Resend Verification Email", key="resend_verify_btn"):
            with st.spinner("Sending …"):
                res = SupabaseManager.resend_verification(resend_email)
            if res.get("success"):
                st.success("Verification email sent! Check your inbox.")
            else:
                st.error("Could not send email. Please try again later.")
            st.session_state.pop("needs_verification", None)


def _render_signup_form(pal: dict) -> None:
    st.markdown(
        f'<p class="ks-auth-desc">Create a free account to get started.</p>',
        unsafe_allow_html=True,
    )

    # ── Password generator ───────────────────────────────────────────
    if st.button("🔐 Suggest Strong Password", key="btn_gen_pw"):
        suggested = _generate_strong_password()
        st.session_state["_suggested_pw"] = suggested
    suggested_pw = st.session_state.get("_suggested_pw")
    if suggested_pw:
        st.code(suggested_pw, language=None)
        st.caption("✅ Copy this password and paste it below. "
                   "It meets all security requirements.")

    with st.form("ks_signup_form", clear_on_submit=False):
        full_name = st.text_input("Full name", placeholder="Your name",
                                  key="signup_name")
        email     = st.text_input("Email address", placeholder="you@example.com",
                                  key="signup_email")
        password  = st.text_input("Password", type="password",
                                  placeholder="Min 8 chars, upper/lower/digit/special",
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
        pw_err = _validate_password_strength(password)
        if pw_err:
            st.error(pw_err)
            return
        with st.spinner("Creating your account …"):
            result = SupabaseManager.sign_up(email.strip(), password, full_name.strip())
        if result["success"]:
            if result.get("needs_confirm"):
                st.success(
                    "✅ Account created! We've sent a verification link "
                    "to your email. Please check your inbox (and spam folder), "
                    "click the link to verify, then come back and sign in."
                )
            else:
                st.success("✅ Account created — you're signed in!")
                _load_user_chat(result["user"]["id"])
                token = st.session_state.get("auth_tokens", {}).get("access_token")
                if token:
                    _set_auth_cookie(token)
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
#  Email verification / password-reset link handlers
# ═══════════════════════════════════════════════════════════════════════

def _handle_email_verification(token: str, pal: dict) -> None:
    """Process an email-verification link (``?verify_token=…``)."""
    _spacer, col, _spacer2 = st.columns([1, 2, 1])
    with col:
        st.markdown(
            '<div class="ks-auth-header">'
            '  <h1>Email Verification</h1>'
            '  <p>KrishiSaathi — AI Agricultural Advisory</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Verifying your email …"):
            result = SupabaseManager.verify_email_token(token)

        if result.get("success"):
            st.success(
                "✅ Your email has been verified successfully! "
                "You can now sign in to your account."
            )
        else:
            st.error(result.get("error", "Verification failed."))

        if st.button("Go to Sign In", type="primary", use_container_width=True):
            st.query_params.clear()
            st.rerun()


def _handle_password_reset(token: str, pal: dict) -> None:
    """Process a password-reset link (``?reset_token=…``)."""
    _spacer, col, _spacer2 = st.columns([1, 2, 1])
    with col:
        st.markdown(
            '<div class="ks-auth-header">'
            '  <h1>Reset Password</h1>'
            '  <p>KrishiSaathi — AI Agricultural Advisory</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Check token validity first
        check = SupabaseManager.check_reset_token(token)
        if not check.get("valid"):
            st.error(
                "This password-reset link is invalid or has expired. "
                "Please request a new one."
            )
            if st.button("Go to Sign In", type="primary", use_container_width=True):
                st.query_params.clear()
                st.rerun()
            return

        st.info(f"Resetting password for **{check.get('email', '')}**")

        with st.form("ks_reset_password_form", clear_on_submit=True):
            new_password  = st.text_input(
                "New password", type="password",
                placeholder="Min 8 chars, upper/lower/digit/special",
            )
            confirm_password = st.text_input(
                "Confirm new password", type="password",
                placeholder="Re-enter password",
            )
            submitted = st.form_submit_button(
                "Reset Password", use_container_width=True, type="primary",
            )

        if submitted:
            if not new_password or not confirm_password:
                st.error("Please fill in both fields.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            pw_err = _validate_password_strength(new_password)
            if pw_err:
                st.error(pw_err)
                return

            with st.spinner("Resetting password …"):
                result = SupabaseManager.complete_password_reset(token, new_password)

            if result.get("success"):
                st.success(
                    "✅ Password reset successfully! You can now sign in "
                    "with your new password."
                )
                st.query_params.clear()
            else:
                st.error(result.get("error", "Password reset failed."))


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
