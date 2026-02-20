"""Supabase service — authentication, profiles & chat-history storage.

When ``SUPABASE_URL`` and ``SUPABASE_KEY`` are *not* set the app silently
falls back to "local mode" (no auth, in-memory chat).  Every public method
is a safe no-op in that case.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import streamlit as st

from backend.config import Config

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

# ── Lazy import so the app still loads when supabase isn't installed ───
_supabase_available: bool = False
try:
    from supabase import create_client  # type: ignore
    _supabase_available = True
except ImportError:
    pass


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
    def _service_client(cls) -> "Client":
        """Client with the **service-role key** — bypasses RLS.

        Used for server-side operations (verification tokens, password
        reset, etc.).  Raises ``RuntimeError`` when the key is not set.
        """
        key = getattr(Config, "SUPABASE_SERVICE_KEY", None)
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not configured")
        return create_client(Config.SUPABASE_URL, key)

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

        When the custom email service is active (EMAIL_ADDRESS +
        SUPABASE_SERVICE_KEY configured), we send our own verification
        email and do NOT store the Supabase session until the user
        verifies.

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
            user_dict = _user_dict(user)

            # ── Custom-email verification flow ────────────────────
            from backend.services.email_service import EmailService

            if EmailService.is_configured() and getattr(Config, "SUPABASE_SERVICE_KEY", None):
                try:
                    svc = cls._service_client()
                    svc.table("profiles").upsert(
                        {
                            "id": str(user.id),
                            "full_name": full_name,
                            "email": email.lower().strip(),
                            "email_verified": False,
                        },
                        on_conflict="id",
                    ).execute()

                    token = cls.create_email_verification(str(user.id), email)
                    if token:
                        EmailService.send_verification_email(
                            email, full_name, token
                        )
                    # Do NOT store session — user must verify first
                    return {
                        "success": True,
                        "user": user_dict,
                        "needs_confirm": True,
                    }
                except Exception as exc:
                    logger.warning(
                        "Custom email verification setup failed, "
                        "falling back: %s", exc,
                    )
                    # Fall through to default behaviour

            # ── Default flow (no custom email) ────────────────────
            if session:
                _store_session(session, user)
                return {
                    "success": True,
                    "user": user_dict,
                    "needs_confirm": False,
                }
            return {
                "success": True,
                "user": user_dict,
                "needs_confirm": True,
            }
        except Exception as exc:
            logger.warning("sign_up failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def sign_in(cls, email: str, password: str) -> dict[str, Any]:
        """Sign in with email + password.

        When the custom email service is active, this also checks
        ``profiles.email_verified`` and rejects unverified accounts.

        Returns ``{"success": True, "user": dict}``
        or ``{"success": False, "error": str}``.
        """
        try:
            client = cls._new_client()
            res = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            # ── Block unverified accounts (custom email flow) ─────
            from backend.services.email_service import EmailService

            if EmailService.is_configured() and getattr(Config, "SUPABASE_SERVICE_KEY", None):
                try:
                    client.auth.set_session(
                        res.session.access_token, res.session.refresh_token
                    )
                    profile = (
                        client.table("profiles")
                        .select("email_verified")
                        .eq("id", str(res.user.id))
                        .maybe_single()
                        .execute()
                    )
                    if (
                        profile.data
                        and profile.data.get("email_verified") is False
                    ):
                        try:
                            client.auth.sign_out()
                        except Exception:
                            pass
                        st.session_state["needs_verification"] = email
                        return {
                            "success": False,
                            "error": (
                                "Please verify your email before signing in. "
                                "Check your inbox for the verification link."
                            ),
                        }
                except Exception as exc:
                    logger.warning(
                        "email_verified check failed (allowing login): %s",
                        exc,
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
        """Send a password-reset email.

        Uses the custom email service when configured; otherwise falls
        back to Supabase's built-in reset email.
        """
        from backend.services.email_service import EmailService

        if EmailService.is_configured() and getattr(Config, "SUPABASE_SERVICE_KEY", None):
            try:
                result = cls.create_password_reset(email)
                if result.get("token"):
                    EmailService.send_password_reset_email(
                        email, result.get("full_name", ""), result["token"]
                    )
                # Always return success (don't reveal if email exists)
                return {"success": True}
            except Exception as exc:
                logger.warning("Custom password reset failed: %s", exc)
                return {
                    "success": False,
                    "error": "Unable to send reset email. Please try again.",
                }

        # ── Fallback: Supabase built-in ───────────────────────────
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
    #  Email verification & password reset (custom email flow)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def create_email_verification(
        cls, user_id: str, email: str
    ) -> str | None:
        """Create a verification token and store it.

        Returns the UUID token string, or ``None`` on failure.
        """
        try:
            token = str(uuid.uuid4())
            svc = cls._service_client()
            svc.table("email_verifications").insert(
                {"user_id": user_id, "email": email.lower().strip(), "token": token}
            ).execute()
            return token
        except Exception as exc:
            logger.warning("create_email_verification failed: %s", exc)
            return None

    @classmethod
    def verify_email_token(cls, token: str) -> dict[str, Any]:
        """Verify a token, mark the profile as verified.

        Returns ``{"success": True}`` or ``{"success": False, "error": …}``.
        """
        try:
            client = cls._new_client()
            res = (
                client.table("email_verifications")
                .select("*")
                .eq("token", token)
                .maybe_single()
                .execute()
            )
            if not res.data:
                return {"success": False, "error": "Invalid verification link."}

            expires_at = datetime.fromisoformat(
                res.data["expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expires_at:
                return {
                    "success": False,
                    "error": "Verification link has expired. Please sign up again.",
                }

            user_id = res.data["user_id"]

            # Mark profile verified + send welcome email
            svc = cls._service_client()
            svc.table("profiles").update(
                {"email_verified": True}
            ).eq("id", user_id).execute()

            # Delete used token
            svc.table("email_verifications").delete().eq(
                "token", token
            ).execute()

            # Send welcome email (best-effort)
            try:
                from backend.services.email_service import EmailService

                profile = (
                    svc.table("profiles")
                    .select("full_name, email")
                    .eq("id", user_id)
                    .maybe_single()
                    .execute()
                )
                if profile.data:
                    EmailService.send_welcome_email(
                        profile.data.get("email", res.data["email"]),
                        profile.data.get("full_name", ""),
                    )
            except Exception:
                pass

            return {"success": True}
        except Exception as exc:
            logger.warning("verify_email_token failed: %s", exc)
            return {
                "success": False,
                "error": "Verification failed. Please try again.",
            }

    @classmethod
    def create_password_reset(cls, email: str) -> dict[str, Any]:
        """Create a password-reset token for *email*.

        Returns ``{"success": True, "token": str, "full_name": str}``
        or ``{"success": True, "token": None}`` if the email isn't found
        (silent — don't reveal whether the email exists).
        """
        try:
            svc = cls._service_client()
            res = (
                svc.table("profiles")
                .select("id, full_name")
                .eq("email", email.lower().strip())
                .maybe_single()
                .execute()
            )
            if not res.data:
                return {"success": True, "token": None}

            token = str(uuid.uuid4())
            user_id = res.data["id"]
            full_name = res.data.get("full_name", "")

            svc.table("password_resets").insert(
                {
                    "user_id": user_id,
                    "email": email.lower().strip(),
                    "token": token,
                }
            ).execute()

            return {"success": True, "token": token, "full_name": full_name}
        except Exception as exc:
            logger.warning("create_password_reset failed: %s", exc)
            return {"success": False, "error": str(exc)}

    @classmethod
    def check_reset_token(cls, token: str) -> dict[str, Any]:
        """Validate a reset token without consuming it.

        Returns ``{"valid": True, "email": str}`` or ``{"valid": False}``.
        """
        try:
            client = cls._new_client()
            res = (
                client.table("password_resets")
                .select("email, expires_at, used")
                .eq("token", token)
                .maybe_single()
                .execute()
            )
            if not res.data or res.data.get("used"):
                return {"valid": False}

            expires_at = datetime.fromisoformat(
                res.data["expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expires_at:
                return {"valid": False}

            return {"valid": True, "email": res.data["email"]}
        except Exception:
            return {"valid": False}

    @classmethod
    def complete_password_reset(
        cls, token: str, new_password: str
    ) -> dict[str, Any]:
        """Verify a reset token and update the user's password.

        Returns ``{"success": True}`` or ``{"success": False, "error": …}``.
        """
        try:
            svc = cls._service_client()
            res = (
                svc.table("password_resets")
                .select("*")
                .eq("token", token)
                .eq("used", False)
                .maybe_single()
                .execute()
            )
            if not res.data:
                return {
                    "success": False,
                    "error": "Invalid or already-used reset link.",
                }

            expires_at = datetime.fromisoformat(
                res.data["expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expires_at:
                return {
                    "success": False,
                    "error": "Reset link has expired. Please request a new one.",
                }

            user_id = res.data["user_id"]

            # Update password via admin API
            svc.auth.admin.update_user_by_id(
                user_id, {"password": new_password}
            )

            # Mark token as used
            svc.table("password_resets").update(
                {"used": True}
            ).eq("token", token).execute()

            return {"success": True}
        except Exception as exc:
            logger.warning("complete_password_reset failed: %s", exc)
            return {
                "success": False,
                "error": "Password reset failed. Please try again.",
            }

    @classmethod
    def resend_verification(cls, email: str) -> dict[str, Any]:
        """Re-send a verification email for an unverified account.

        Deletes old tokens, creates a fresh one, and emails it.
        Returns ``{"success": True}`` or ``{"success": False}``.
        """
        try:
            svc = cls._service_client()
            profile = (
                svc.table("profiles")
                .select("id, full_name")
                .eq("email", email.lower().strip())
                .maybe_single()
                .execute()
            )
            if not profile.data:
                return {"success": False}

            user_id = profile.data["id"]
            full_name = profile.data.get("full_name", "")

            # Remove stale tokens
            svc.table("email_verifications").delete().eq(
                "user_id", user_id
            ).execute()

            # Create new token
            token = cls.create_email_verification(user_id, email)
            if token:
                from backend.services.email_service import EmailService

                EmailService.send_verification_email(email, full_name, token)
                return {"success": True}
            return {"success": False}
        except Exception as exc:
            logger.warning("resend_verification failed: %s", exc)
            return {"success": False}

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

    # ═══════════════════════════════════════════════════════════════════
    #  Admin queries (uses authed client — admin must be signed in)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def admin_list_users(cls) -> list[dict]:
        """List all users via the profiles table.

        Returns list of dicts with id, full_name, preferred_language,
        location, created_at.  Requires an admin-level RLS policy or
        service_role key.
        """
        try:
            client = cls._authed_client()
            res = (
                client.table("profiles")
                .select("id, full_name, preferred_language, location, phone, created_at, updated_at")
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning("admin_list_users failed: %s", exc)
            return []

    @classmethod
    def admin_get_all_chat_history(cls, user_id: str | None = None, limit: int = 500) -> list[dict]:
        """Fetch chat history for one user or all users.

        Returns list of dicts with id, user_id, role, content, sources,
        created_at.
        """
        try:
            client = cls._authed_client()
            q = (
                client.table("chat_history")
                .select("id, user_id, role, content, sources, created_at")
            )
            if user_id:
                q = q.eq("user_id", user_id)
            res = q.order("created_at", desc=True).limit(limit).execute()
            rows = res.data or []
            for row in rows:
                src = row.get("sources")
                if isinstance(src, str):
                    try:
                        row["sources"] = json.loads(src)
                    except json.JSONDecodeError:
                        row["sources"] = None
            return rows
        except Exception as exc:
            logger.warning("admin_get_all_chat_history failed: %s", exc)
            return []

    @classmethod
    def admin_get_all_memories(cls, user_id: str | None = None, limit: int = 500) -> list[dict]:
        """Fetch memories for one user or all users."""
        try:
            client = cls._authed_client()
            q = (
                client.table("memories")
                .select("id, user_id, content, category, importance, access_count, created_at, updated_at")
            )
            if user_id:
                q = q.eq("user_id", user_id)
            res = q.order("created_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as exc:
            logger.warning("admin_get_all_memories failed: %s", exc)
            return []

    @classmethod
    def admin_delete_user_data(cls, user_id: str) -> dict:
        """Delete all chat history + memories for a user (admin action)."""
        results = {"chat_deleted": False, "memories_deleted": False}
        try:
            client = cls._authed_client()
            client.table("chat_history").delete().eq("user_id", user_id).execute()
            results["chat_deleted"] = True
        except Exception as exc:
            logger.warning("admin_delete_user_data: chat deletion failed: %s", exc)
        try:
            client = cls._authed_client()
            client.table("memories").delete().eq("user_id", user_id).execute()
            results["memories_deleted"] = True
        except Exception as exc:
            logger.warning("admin_delete_user_data: memories deletion failed: %s", exc)
        return results

    @classmethod
    def admin_get_counts(cls) -> dict:
        """Return aggregate counts for the admin dashboard."""
        counts = {"users": 0, "messages": 0, "memories": 0}
        try:
            client = cls._authed_client()
            r = client.table("profiles").select("id", count="exact").execute()
            counts["users"] = r.count if r.count is not None else len(r.data or [])
        except Exception:
            pass
        try:
            client = cls._authed_client()
            r = client.table("chat_history").select("id", count="exact").execute()
            counts["messages"] = r.count if r.count is not None else len(r.data or [])
        except Exception:
            pass
        try:
            client = cls._authed_client()
            r = client.table("memories").select("id", count="exact").execute()
            counts["memories"] = r.count if r.count is not None else len(r.data or [])
        except Exception:
            pass
        return counts

    # ═══════════════════════════════════════════════════════════════════
    #  Admin settings persistence (Supabase → survives deploys)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def load_admin_settings(cls) -> dict | None:
        """Load admin settings from the ``admin_settings`` table.

        Returns the parsed settings dict, or ``None`` if the table
        does not exist or has no rows.
        """
        if not cls.is_configured():
            return None
        try:
            client = cls._authed_client()
            res = (
                client.table("admin_settings")
                .select("settings")
                .eq("id", "global")
                .maybe_single()
                .execute()
            )
            if res.data:
                raw = res.data.get("settings")
                if isinstance(raw, str):
                    return json.loads(raw)
                if isinstance(raw, dict):
                    return raw
        except Exception as exc:
            # Table may not exist yet — that's fine
            logger.debug("load_admin_settings: %s", exc)
        return None

    @classmethod
    def save_admin_settings(cls, settings: dict) -> bool:
        """Upsert admin settings into the ``admin_settings`` table.

        Returns ``True`` on success.
        """
        if not cls.is_configured():
            return False
        try:
            client = cls._authed_client()
            client.table("admin_settings").upsert(
                {"id": "global", "settings": json.dumps(settings, ensure_ascii=False)},
                on_conflict="id",
            ).execute()
            return True
        except Exception as exc:
            logger.warning("save_admin_settings failed: %s", exc)
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
