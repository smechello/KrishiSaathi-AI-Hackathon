"""Supabase service — authentication, profiles & chat-history storage.

When ``SUPABASE_URL`` and ``SUPABASE_KEY`` are *not* set the app silently
falls back to "local mode" (no auth, in-memory chat).  Every public method
is a safe no-op in that case.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import streamlit as st

from backend.config import Config

logger = logging.getLogger(__name__)

# ── Lazy import so the app still loads when supabase isn't installed ───
_supabase_available: bool = False
try:
    from supabase import create_client, Client  # type: ignore
    _supabase_available = True
except ImportError:
    Client = None  # type: ignore


# ═══════════════════════════════════════════════════════════════════════
#  SupabaseManager — singleton-free, every method is @classmethod
# ═══════════════════════════════════════════════════════════════════════

class SupabaseManager:
    """Thin façade over the Supabase Python client.

    * All methods are **class-level** — no instantiation required.
    * If Supabase is not configured every method returns a predictable
      fallback so callers never have to guard with ``if``.
    """

    # ── status ────────────────────────────────────────────────────────

    @classmethod
    def is_configured(cls) -> bool:
        """``True`` when Supabase URL **and** key are present and the
        library is installed."""
        return (
            _supabase_available
            and bool(getattr(Config, "SUPABASE_URL", None))
            and bool(getattr(Config, "SUPABASE_KEY", None))
        )

    # ── internal client helpers ────────────────────────────────────────

    @classmethod
    def _new_client(cls) -> "Client":
        """Fresh Supabase client (no session).  Caller must check
        ``is_configured()`` first."""
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    @classmethod
    def _authed_client(cls) -> "Client":
        """Client with the current user's JWT set so that RLS applies."""
        client = cls._new_client()
        tokens = st.session_state.get("auth_tokens")
        if tokens:
            try:
                client.auth.set_session(
                    tokens["access_token"], tokens["refresh_token"]
                )
            except Exception:
                pass                       # caller will get an RLS / 401
        return client

    # ═══════════════════════════════════════════════════════════════════
    #  Authentication
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def sign_up(
        cls, email: str, password: str, full_name: str = ""
    ) -> dict[str, Any]:
        """Register a new user.

        Returns
        -------
        {"success": True, "user": dict, "needs_confirm": bool}
        {"success": False, "error": str}
        """
        try:
            client = cls._new_client()
            res = client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}},
                }
            )
            user = res.user
            session = res.session

            if session:
                # email-confirmation disabled → logged in immediately
                _store_session(session, user)
                return {
                    "success": True,
                    "user": _user_dict(user),
                    "needs_confirm": False,
                }
            # email-confirmation enabled
            return {
                "success": True,
                "user": _user_dict(user),
                "needs_confirm": True,
            }
        except Exception as exc:
            logger.warning("sign_up failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def sign_in(cls, email: str, password: str) -> dict[str, Any]:
        """Sign in with email + password.

        Returns ``{"success": True, "user": dict}``
        or ``{"success": False, "error": str}``.
        """
        try:
            client = cls._new_client()
            res = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            _store_session(res.session, res.user)
            return {"success": True, "user": _user_dict(res.user)}
        except Exception as exc:
            logger.warning("sign_in failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def sign_out(cls) -> None:
        """Sign out server-side, then wipe local session."""
        try:
            tokens = st.session_state.get("auth_tokens")
            if tokens:
                client = cls._new_client()
                client.auth.set_session(
                    tokens["access_token"], tokens["refresh_token"]
                )
                client.auth.sign_out()
        except Exception as exc:
            logger.warning("sign_out remote call failed (ignored): %s", exc)
        _clear_session()

    @classmethod
    def reset_password(cls, email: str) -> dict[str, Any]:
        """Send a password-reset email."""
        try:
            client = cls._new_client()
            client.auth.reset_password_for_email(email)
            return {"success": True}
        except Exception as exc:
            logger.warning("reset_password failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def restore_session(cls) -> dict | None:
        """Re-validate stored tokens.  Returns user dict or ``None``.

        Called once per page load to see if the user is "still" logged in
        from a previous interaction.
        """
        tokens = st.session_state.get("auth_tokens")
        if not tokens:
            return None
        try:
            client = cls._new_client()
            res = client.auth.set_session(
                tokens["access_token"], tokens["refresh_token"]
            )
            if res and res.session:
                # tokens may have been refreshed — persist the new ones
                _store_session(res.session, res.user)
                return _user_dict(res.user)
        except Exception as exc:
            logger.warning("Session restore failed: %s", exc)
            _clear_session()
        return None

    # ═══════════════════════════════════════════════════════════════════
    #  Profile helpers (uses ``profiles`` table)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def get_profile(cls, user_id: str) -> dict | None:
        """Fetch the profile row for *user_id* (or ``None``)."""
        try:
            client = cls._authed_client()
            res = (
                client.table("profiles")
                .select("*")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            return res.data
        except Exception as exc:
            logger.warning("get_profile failed: %s", exc)
            return None

    @classmethod
    def update_profile(cls, user_id: str, data: dict) -> bool:
        """Update one or more profile columns for *user_id*."""
        try:
            client = cls._authed_client()
            client.table("profiles").update(data).eq("id", user_id).execute()
            return True
        except Exception as exc:
            logger.warning("update_profile failed: %s", exc)
            return False

    # ═══════════════════════════════════════════════════════════════════
    #  Chat history (uses ``chat_history`` table)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def save_message(
        cls,
        user_id: str,
        role: str,
        content: str,
        sources: list | None = None,
    ) -> None:
        """Persist a single chat message to Supabase."""
        try:
            client = cls._authed_client()
            client.table("chat_history").insert(
                {
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "sources": json.dumps(sources) if sources else None,
                }
            ).execute()
        except Exception as exc:
            logger.warning("save_message failed: %s", exc)

    @classmethod
    def load_messages(cls, user_id: str, limit: int = 100) -> list[dict]:
        """Load the most recent chat messages for a user (oldest first)."""
        try:
            client = cls._authed_client()
            res = (
                client.table("chat_history")
                .select("role, content, sources, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            messages: list[dict] = []
            for row in res.data or []:
                sources = row.get("sources")
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except json.JSONDecodeError:
                        sources = None
                messages.append(
                    {
                        "role": row["role"],
                        "content": row["content"],
                        "sources": sources,
                    }
                )
            return messages
        except Exception as exc:
            logger.warning("load_messages failed: %s", exc)
            return []

    @classmethod
    def clear_messages(cls, user_id: str) -> bool:
        """Delete **all** chat messages for a user."""
        try:
            client = cls._authed_client()
            client.table("chat_history").delete().eq(
                "user_id", user_id
            ).execute()
            return True
        except Exception as exc:
            logger.warning("clear_messages failed: %s", exc)
            return False


# ═══════════════════════════════════════════════════════════════════════
#  Module-level helpers
# ═══════════════════════════════════════════════════════════════════════


def _user_dict(user: Any) -> dict:
    """Normalise a Supabase ``User`` object into a plain dict."""
    meta = getattr(user, "user_metadata", None) or {}
    return {
        "id": str(user.id),
        "email": getattr(user, "email", "") or "",
        "full_name": meta.get("full_name", ""),
    }


def _store_session(session: Any, user: Any) -> None:
    """Persist auth tokens + user info into ``st.session_state``."""
    st.session_state["auth_tokens"] = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }
    st.session_state["auth_user"] = _user_dict(user)
    st.session_state["authenticated"] = True


def _clear_session() -> None:
    """Wipe every auth-related key from ``session_state``."""
    for key in ("auth_tokens", "auth_user", "authenticated"):
        st.session_state.pop(key, None)


def _friendly_error(exc: Exception) -> str:
    """Extract a user-friendly message from a Supabase exception."""
    msg = str(exc).lower()
    if "already registered" in msg:
        return "An account with this email already exists."
    if "invalid login" in msg or "invalid credentials" in msg:
        return "Invalid email or password."
    if "password" in msg and ("short" in msg or "least" in msg):
        return "Password must be at least 6 characters."
    if "email" in msg and "valid" in msg:
        return "Please enter a valid email address."
    if "rate" in msg or "too many" in msg:
        return "Too many attempts — please try again later."
    if "user not found" in msg:
        return "No account found with that email."
    if "email not confirmed" in msg:
        return "Please confirm your email before signing in."
    # Generic fallback
    return f"Something went wrong. Please try again."
