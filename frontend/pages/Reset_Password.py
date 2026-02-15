"""Password Reset Page — Handle password reset from email link.

When users click the password reset link in their email, they are redirected
to this page with recovery tokens in the URL. This page allows them to set
a new password.
"""

from __future__ import annotations

import logging
import os
import sys

import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.services.supabase_service import SupabaseManager  # noqa: E402
from frontend.components.theme import (  # noqa: E402
    get_theme,
    get_palette,
    inject_global_css,
    _logo_b64,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KrishiSaathi — Reset Password",
    page_icon="🔐",
    layout="centered",
)


def _inject_reset_css(pal: dict, theme: str) -> None:
    """Theme-aware CSS for the reset password page."""
    shadow = "0 8px 32px rgba(0,0,0,0.28)" if theme == "dark" else "0 4px 24px rgba(0,0,0,0.08)"
    st.markdown(
        f"""<style>
        /* ── Reset password container ─────────────────────────────── */
        .ks-reset-header {{
            text-align: center;
            margin: 2rem 0 1.5rem;
        }}
        .ks-reset-header h1 {{
            color: {pal["text"]};
            font-size: 2rem;
            font-weight: 800;
            margin: 0.4rem 0 0.1rem;
            letter-spacing: -0.02em;
        }}
        .ks-reset-header p {{
            color: {pal["text_muted"]};
            font-size: 0.95rem;
            margin: 0;
        }}
        .ks-reset-card {{
            background: {pal["card"]};
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid {pal["card_border"]};
            box-shadow: {shadow};
            margin: 1rem 0;
        }}
        .ks-reset-desc {{
            color: {pal["text_secondary"]};
            font-size: 0.95rem;
            margin-bottom: 1rem;
            text-align: center;
        }}
        </style>""",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Main password reset page logic."""
    
    # Check if Supabase is configured
    if not SupabaseManager.is_configured():
        st.error("⚠️ Password reset is not available in local mode.")
        st.stop()
        return

    theme = get_theme()
    pal = get_palette(theme)

    # Inject CSS
    inject_global_css(theme)
    _inject_reset_css(pal, theme)

    # ── Header ─────────────────────────────────────────────────────
    logo_data = _logo_b64()
    logo_html = (
        f'<img src="data:image/svg+xml;base64,{logo_data}" '
        f'width="72" height="72" alt="KrishiSaathi Logo">'
        if logo_data else ""
    )
    st.markdown(
        f'<div class="ks-reset-header">'
        f'  {logo_html}'
        f'  <h1>🔐 Reset Your Password</h1>'
        f'  <p>Set a new password for your KrishiSaathi account</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Get query parameters ───────────────────────────────────────
    # When Supabase redirects from email, it includes these parameters:
    # - access_token: JWT token for authentication
    # - refresh_token: Refresh token
    # - type: "recovery" for password reset
    
    query_params = st.query_params
    
    # Check if this is a password recovery request
    recovery_type = query_params.get("type", "")
    access_token = query_params.get("access_token", "")
    refresh_token = query_params.get("refresh_token", "")
    
    if recovery_type != "recovery" or not access_token or not refresh_token:
        # No valid recovery tokens in URL
        st.markdown('<div class="ks-reset-card">', unsafe_allow_html=True)
        st.warning(
            "⚠️ **Invalid or missing recovery link.**\n\n"
            "This page requires a valid password reset link from your email. "
            "Please check your inbox and click the link in the password reset email."
        )
        if st.button("← Back to Login", use_container_width=True):
            st.switch_page("frontend/app.py")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()
        return

    # ── Verify the recovery token and establish session ────────────
    if "recovery_verified" not in st.session_state:
        with st.spinner("Verifying recovery link..."):
            result = SupabaseManager.verify_recovery_token(access_token, refresh_token)
        
        if not result["success"]:
            st.markdown('<div class="ks-reset-card">', unsafe_allow_html=True)
            st.error(
                f"❌ **Recovery link verification failed.**\n\n{result['error']}\n\n"
                "The link may have expired or already been used. "
                "Please request a new password reset."
            )
            if st.button("← Back to Login", use_container_width=True):
                st.switch_page("frontend/app.py")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()
            return
        
        # Mark as verified
        st.session_state["recovery_verified"] = True
        st.session_state["recovery_user"] = result["user"]
        logger.info("Recovery token verified for user: %s", result["user"].get("email"))

    # ── Password reset form ────────────────────────────────────────
    st.markdown('<div class="ks-reset-card">', unsafe_allow_html=True)
    
    user_email = st.session_state["recovery_user"].get("email", "")
    st.markdown(
        f'<p class="ks-reset-desc">Enter a new password for <strong>{user_email}</strong></p>',
        unsafe_allow_html=True,
    )

    with st.form("password_reset_form", clear_on_submit=False):
        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="Enter new password (minimum 6 characters)",
            key="new_password"
        )
        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            placeholder="Re-enter your new password",
            key="confirm_password"
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            submitted = st.form_submit_button(
                "✅ Update Password",
                use_container_width=True,
                type="primary"
            )
        with col2:
            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

    if cancel:
        # Clear session and redirect
        st.session_state.pop("recovery_verified", None)
        st.session_state.pop("recovery_user", None)
        st.switch_page("frontend/app.py")

    if submitted:
        # Validate inputs
        if not new_password:
            st.error("❌ Please enter a new password.")
        elif len(new_password) < 6:
            st.error("❌ Password must be at least 6 characters long.")
        elif new_password != confirm_password:
            st.error("❌ Passwords do not match. Please try again.")
        else:
            # Update password
            with st.spinner("Updating your password..."):
                result = SupabaseManager.update_password(new_password)
            
            if result["success"]:
                st.success(
                    "✅ **Password updated successfully!**\n\n"
                    "You can now sign in with your new password."
                )
                
                # Clear recovery state
                st.session_state.pop("recovery_verified", None)
                st.session_state.pop("recovery_user", None)
                
                # Provide button to go to login
                if st.button("→ Go to Sign In", use_container_width=True, type="primary"):
                    st.switch_page("frontend/app.py")
                
                # Auto-redirect after a few seconds
                st.info("You will be redirected to the sign-in page in a moment...")
                import time
                time.sleep(3)
                st.switch_page("frontend/app.py")
            else:
                st.error(
                    f"❌ **Failed to update password.**\n\n{result['error']}\n\n"
                    "Please try again or request a new password reset link."
                )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Footer ─────────────────────────────────────────────────────
    st.markdown(
        f'<p style="text-align:center; color:{pal["text_muted"]}; font-size:0.78rem; margin-top:1.5rem;">'
        f'Built with ❤️ for Indian Farmers &middot; © 2026 KrishiSaathi</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
