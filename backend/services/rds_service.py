"""RDS PostgreSQL service — drop-in replacement for SupabaseManager.

Provides the **exact same class-method API** so callers (auth.py, app.py,
sidebar.py, Admin.py, config.py) do not need any changes.

Auth is handled with:
  - **bcrypt** for password hashing
  - **PyJWT** for session tokens (HS256, 7-day expiry)
  - Tokens stored in ``st.session_state`` just like the Supabase flow

Tables:
  profiles, chat_history, memories, email_verifications,
  password_resets, admin_settings  (created by ``ensure_tables()``)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from backend.config import Config

logger = logging.getLogger(__name__)

# ── Optional imports ────────────────────────────────────────────────────
_pg_available = False
try:
    import psycopg2
    import psycopg2.extras
    _pg_available = True
except ImportError:
    logger.debug("psycopg2 not installed — RDS backend disabled")

_bcrypt_available = False
try:
    import bcrypt
    _bcrypt_available = True
except ImportError:
    logger.debug("bcrypt not installed — password hashing disabled")

_jwt_available = False
try:
    import jwt as pyjwt
    _jwt_available = True
except ImportError:
    logger.debug("PyJWT not installed — JWT tokens disabled")

# ── Connection pool ─────────────────────────────────────────────────────
_pool: Any = None


def _get_dsn() -> str:
    """Build PostgreSQL DSN from Config."""
    return (
        f"host={Config.RDS_HOST} "
        f"port={Config.RDS_PORT} "
        f"dbname={Config.RDS_DBNAME} "
        f"user={Config.RDS_USER} "
        f"password={Config.RDS_PASSWORD} "
        f"sslmode=require"
    )


def _get_conn():
    """Return a connection from the pool (or create a new one)."""
    global _pool
    if _pool is None:
        from psycopg2 import pool as pg_pool
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1, maxconn=5, dsn=_get_dsn()
        )
    conn = _pool.getconn()
    conn.autocommit = True
    return conn


def _put_conn(conn):
    """Return a connection to the pool."""
    if _pool and conn:
        try:
            _pool.putconn(conn)
        except Exception:
            pass


def _exec(sql: str, params: tuple | None = None, fetch: str = "none") -> Any:
    """Execute SQL with auto-connect and return results.

    fetch: "none" | "one" | "all"
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return None
    finally:
        _put_conn(conn)


def _exec_count(sql: str, params: tuple | None = None) -> int:
    """Execute COUNT query and return integer."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else 0
    finally:
        _put_conn(conn)


# ── JWT helpers ─────────────────────────────────────────────────────────

_JWT_SECRET = os.getenv("JWT_SECRET", Config.RDS_PASSWORD or "kr1sh1-s@@th1-s3cr3t")
_JWT_ALGO = "HS256"
_JWT_EXPIRY_DAYS = 7


def _create_tokens(user_id: str, email: str) -> dict:
    """Create access + refresh JWT tokens."""
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=_JWT_EXPIRY_DAYS),
        "type": "access",
    }
    refresh_payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=_JWT_EXPIRY_DAYS * 4),
        "type": "refresh",
    }
    return {
        "access_token": pyjwt.encode(access_payload, _JWT_SECRET, algorithm=_JWT_ALGO),
        "refresh_token": pyjwt.encode(refresh_payload, _JWT_SECRET, algorithm=_JWT_ALGO),
    }


def _decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        return pyjwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except Exception:
        return None


# ── Table creation ──────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    full_name   TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    preferred_language TEXT DEFAULT 'en',
    location    TEXT DEFAULT '',
    phone       TEXT DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_history (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    sources     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id, created_at);

CREATE TABLE IF NOT EXISTS memories (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'personal',
    importance  INTEGER NOT NULL DEFAULT 5,
    access_count INTEGER NOT NULL DEFAULT 0,
    embedding   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id);

CREATE TABLE IF NOT EXISTS email_verifications (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    email       TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE TABLE IF NOT EXISTS password_resets (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    email       TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    used        BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 hour')
);

CREATE TABLE IF NOT EXISTS admin_settings (
    id          TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}'
);
"""


def ensure_tables() -> bool:
    """Create all tables if they don't exist. Returns True on success."""
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA_SQL)
            logger.info("RDS tables ensured")
            return True
        finally:
            _put_conn(conn)
    except Exception as exc:
        logger.error("Failed to create tables: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════════
#  SupabaseManager — same API, backed by RDS + bcrypt + JWT
# ═══════════════════════════════════════════════════════════════════════

class SupabaseManager:
    """Drop-in replacement for the original Supabase-backed manager.

    All methods are @classmethod.  Auth uses bcrypt + JWT instead of
    Supabase GoTrue.  Data uses psycopg2 to RDS PostgreSQL.
    """

    _tables_ensured = False

    @classmethod
    def _ensure(cls):
        """Lazy table creation on first use."""
        if not cls._tables_ensured and cls.is_configured():
            cls._tables_ensured = ensure_tables()

    # ── status ────────────────────────────────────────────────────────

    @classmethod
    def is_configured(cls) -> bool:
        return (
            _pg_available
            and _bcrypt_available
            and _jwt_available
            and bool(getattr(Config, "RDS_HOST", None))
        )

    # ── internal helpers ──────────────────────────────────────────────

    @classmethod
    def _authed_client(cls):
        """For backward-compat with admin page direct-table access.
        
        Returns self (the class) so .table() calls route here.
        """
        return cls

    @classmethod
    def _service_client(cls):
        """For backward-compat.  Returns self."""
        return cls

    # ═══════════════════════════════════════════════════════════════════
    #  Authentication
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def sign_up(
        cls, email: str, password: str, full_name: str = ""
    ) -> dict[str, Any]:
        cls._ensure()
        try:
            email = email.lower().strip()

            # Check if email already exists
            existing = _exec(
                "SELECT id FROM profiles WHERE email = %s", (email,), fetch="one"
            )
            if existing:
                return {"success": False, "error": "An account with this email already exists."}

            user_id = str(uuid.uuid4())
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            from backend.services.email_service import EmailService
            use_custom_email = EmailService.is_configured()

            _exec(
                """INSERT INTO profiles (id, full_name, email, password_hash, email_verified)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, full_name.strip(), email, pw_hash, not use_custom_email),
            )

            user_dict = {"id": user_id, "email": email, "full_name": full_name.strip()}

            if use_custom_email:
                # Send verification email
                token = cls.create_email_verification(user_id, email)
                if token:
                    EmailService.send_verification_email(email, full_name, token)
                return {"success": True, "user": user_dict, "needs_confirm": True}

            # No custom email → auto-verified, create session
            tokens = _create_tokens(user_id, email)
            st.session_state["auth_tokens"] = tokens
            st.session_state["auth_user"] = user_dict
            st.session_state["authenticated"] = True
            return {"success": True, "user": user_dict, "needs_confirm": False}

        except Exception as exc:
            logger.warning("sign_up failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def sign_in(cls, email: str, password: str) -> dict[str, Any]:
        cls._ensure()
        try:
            email = email.lower().strip()
            row = _exec(
                "SELECT id, full_name, email, password_hash, email_verified FROM profiles WHERE email = %s",
                (email,),
                fetch="one",
            )
            if not row:
                return {"success": False, "error": "Invalid email or password."}

            if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
                return {"success": False, "error": "Invalid email or password."}

            # Block unverified accounts
            from backend.services.email_service import EmailService
            if EmailService.is_configured() and not row["email_verified"]:
                st.session_state["needs_verification"] = email
                return {
                    "success": False,
                    "error": (
                        "Please verify your email before signing in. "
                        "Check your inbox for the verification link."
                    ),
                }

            user_dict = {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"],
            }
            tokens = _create_tokens(row["id"], row["email"])
            st.session_state["auth_tokens"] = tokens
            st.session_state["auth_user"] = user_dict
            st.session_state["authenticated"] = True
            return {"success": True, "user": user_dict}

        except Exception as exc:
            logger.warning("sign_in failed: %s", exc)
            return {"success": False, "error": _friendly_error(exc)}

    @classmethod
    def sign_out(cls) -> None:
        for key in ("auth_tokens", "auth_user", "authenticated"):
            st.session_state.pop(key, None)

    @classmethod
    def reset_password(cls, email: str) -> dict[str, Any]:
        from backend.services.email_service import EmailService

        if EmailService.is_configured():
            try:
                result = cls.create_password_reset(email)
                if result.get("token"):
                    EmailService.send_password_reset_email(
                        email, result.get("full_name", ""), result["token"]
                    )
                return {"success": True}
            except Exception as exc:
                logger.warning("Custom password reset failed: %s", exc)
                return {"success": False, "error": "Unable to send reset email. Please try again."}

        return {"success": False, "error": "Email service is not configured."}

    @classmethod
    def restore_session(cls) -> dict | None:
        tokens = st.session_state.get("auth_tokens")
        if not tokens:
            return None
        payload = _decode_token(tokens.get("access_token", ""))
        if not payload:
            # Try refresh token
            rpayload = _decode_token(tokens.get("refresh_token", ""))
            if not rpayload:
                for key in ("auth_tokens", "auth_user", "authenticated"):
                    st.session_state.pop(key, None)
                return None
            # Refresh succeeded — issue new tokens
            new_tokens = _create_tokens(rpayload["sub"], rpayload["email"])
            st.session_state["auth_tokens"] = new_tokens
            payload = rpayload

        user_dict = {
            "id": payload["sub"],
            "email": payload.get("email", ""),
            "full_name": st.session_state.get("auth_user", {}).get("full_name", ""),
        }
        st.session_state["auth_user"] = user_dict
        st.session_state["authenticated"] = True
        return user_dict

    # ═══════════════════════════════════════════════════════════════════
    #  Email verification & password reset
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def create_email_verification(cls, user_id: str, email: str) -> str | None:
        try:
            token = str(uuid.uuid4())
            _exec(
                "INSERT INTO email_verifications (user_id, email, token) VALUES (%s, %s, %s)",
                (user_id, email.lower().strip(), token),
            )
            return token
        except Exception as exc:
            logger.warning("create_email_verification failed: %s", exc)
            return None

    @classmethod
    def verify_email_token(cls, token: str) -> dict[str, Any]:
        try:
            row = _exec(
                "SELECT user_id, email, expires_at FROM email_verifications WHERE token = %s",
                (token,),
                fetch="one",
            )
            if not row:
                return {"success": False, "error": "Invalid verification link."}

            if datetime.now(timezone.utc) > row["expires_at"].replace(tzinfo=timezone.utc):
                return {"success": False, "error": "Verification link has expired. Please sign up again."}

            user_id = row["user_id"]

            _exec("UPDATE profiles SET email_verified = TRUE, updated_at = NOW() WHERE id = %s", (user_id,))
            _exec("DELETE FROM email_verifications WHERE token = %s", (token,))

            # Send welcome email
            try:
                from backend.services.email_service import EmailService
                profile = _exec("SELECT full_name, email FROM profiles WHERE id = %s", (user_id,), fetch="one")
                if profile:
                    EmailService.send_welcome_email(profile["email"], profile["full_name"])
            except Exception:
                pass

            return {"success": True}
        except Exception as exc:
            logger.warning("verify_email_token failed: %s", exc)
            return {"success": False, "error": "Verification failed. Please try again."}

    @classmethod
    def create_password_reset(cls, email: str) -> dict[str, Any]:
        try:
            row = _exec(
                "SELECT id, full_name FROM profiles WHERE email = %s",
                (email.lower().strip(),),
                fetch="one",
            )
            if not row:
                return {"success": True, "token": None}

            token = str(uuid.uuid4())
            _exec(
                "INSERT INTO password_resets (user_id, email, token) VALUES (%s, %s, %s)",
                (row["id"], email.lower().strip(), token),
            )
            return {"success": True, "token": token, "full_name": row.get("full_name", "")}
        except Exception as exc:
            logger.warning("create_password_reset failed: %s", exc)
            return {"success": False, "error": str(exc)}

    @classmethod
    def check_reset_token(cls, token: str) -> dict[str, Any]:
        try:
            row = _exec(
                "SELECT email, expires_at, used FROM password_resets WHERE token = %s",
                (token,),
                fetch="one",
            )
            if not row or row.get("used"):
                return {"valid": False}
            if datetime.now(timezone.utc) > row["expires_at"].replace(tzinfo=timezone.utc):
                return {"valid": False}
            return {"valid": True, "email": row["email"]}
        except Exception:
            return {"valid": False}

    @classmethod
    def complete_password_reset(cls, token: str, new_password: str) -> dict[str, Any]:
        try:
            row = _exec(
                "SELECT user_id, expires_at, used FROM password_resets WHERE token = %s",
                (token,),
                fetch="one",
            )
            if not row or row.get("used"):
                return {"success": False, "error": "Invalid or already-used reset link."}
            if datetime.now(timezone.utc) > row["expires_at"].replace(tzinfo=timezone.utc):
                return {"success": False, "error": "Reset link has expired. Please request a new one."}

            pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            _exec(
                "UPDATE profiles SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                (pw_hash, row["user_id"]),
            )
            _exec("UPDATE password_resets SET used = TRUE WHERE token = %s", (token,))
            return {"success": True}
        except Exception as exc:
            logger.warning("complete_password_reset failed: %s", exc)
            return {"success": False, "error": "Password reset failed. Please try again."}

    @classmethod
    def resend_verification(cls, email: str) -> dict[str, Any]:
        try:
            row = _exec(
                "SELECT id, full_name FROM profiles WHERE email = %s",
                (email.lower().strip(),),
                fetch="one",
            )
            if not row:
                return {"success": False}

            _exec("DELETE FROM email_verifications WHERE user_id = %s", (row["id"],))
            token = cls.create_email_verification(row["id"], email)
            if token:
                from backend.services.email_service import EmailService
                EmailService.send_verification_email(email, row.get("full_name", ""), token)
                return {"success": True}
            return {"success": False}
        except Exception as exc:
            logger.warning("resend_verification failed: %s", exc)
            return {"success": False}

    # ═══════════════════════════════════════════════════════════════════
    #  Profile helpers
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def get_profile(cls, user_id: str) -> dict | None:
        try:
            return _exec(
                """SELECT id, full_name, email, email_verified,
                          preferred_language, location, phone,
                          created_at, updated_at
                   FROM profiles WHERE id = %s""",
                (user_id,),
                fetch="one",
            )
        except Exception as exc:
            logger.warning("get_profile failed: %s", exc)
            return None

    @classmethod
    def update_profile(cls, user_id: str, data: dict) -> bool:
        try:
            # Only allow safe columns
            safe_cols = {"full_name", "preferred_language", "location", "phone"}
            updates = {k: v for k, v in data.items() if k in safe_cols}
            if not updates:
                return True
            set_clause = ", ".join(f"{k} = %s" for k in updates)
            vals = list(updates.values()) + [user_id]
            _exec(
                f"UPDATE profiles SET {set_clause}, updated_at = NOW() WHERE id = %s",
                tuple(vals),
            )
            return True
        except Exception as exc:
            logger.warning("update_profile failed: %s", exc)
            return False

    # ═══════════════════════════════════════════════════════════════════
    #  Chat history
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def save_message(cls, user_id: str, role: str, content: str, sources: list | None = None) -> None:
        try:
            _exec(
                "INSERT INTO chat_history (user_id, role, content, sources) VALUES (%s, %s, %s, %s)",
                (user_id, role, content, json.dumps(sources) if sources else None),
            )
        except Exception as exc:
            logger.warning("save_message failed: %s", exc)

    @classmethod
    def load_messages(cls, user_id: str, limit: int = 100) -> list[dict]:
        try:
            rows = _exec(
                """SELECT role, content, sources, created_at
                   FROM chat_history WHERE user_id = %s
                   ORDER BY created_at ASC LIMIT %s""",
                (user_id, limit),
                fetch="all",
            )
            messages = []
            for row in (rows or []):
                sources = row.get("sources")
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except json.JSONDecodeError:
                        sources = None
                messages.append({
                    "role": row["role"],
                    "content": row["content"],
                    "sources": sources,
                })
            return messages
        except Exception as exc:
            logger.warning("load_messages failed: %s", exc)
            return []

    @classmethod
    def clear_messages(cls, user_id: str) -> bool:
        try:
            _exec("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
            return True
        except Exception as exc:
            logger.warning("clear_messages failed: %s", exc)
            return False

    # ═══════════════════════════════════════════════════════════════════
    #  Admin queries
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def admin_list_users(cls) -> list[dict]:
        try:
            rows = _exec(
                """SELECT id, full_name, preferred_language, location, phone,
                          created_at, updated_at
                   FROM profiles ORDER BY created_at DESC""",
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            logger.warning("admin_list_users failed: %s", exc)
            return []

    @classmethod
    def admin_get_all_chat_history(cls, user_id: str | None = None, limit: int = 500) -> list[dict]:
        try:
            if user_id:
                rows = _exec(
                    """SELECT id, user_id, role, content, sources, created_at
                       FROM chat_history WHERE user_id = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit),
                    fetch="all",
                )
            else:
                rows = _exec(
                    """SELECT id, user_id, role, content, sources, created_at
                       FROM chat_history ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                    fetch="all",
                )
            for row in (rows or []):
                src = row.get("sources")
                if isinstance(src, str):
                    try:
                        row["sources"] = json.loads(src)
                    except json.JSONDecodeError:
                        row["sources"] = None
            return rows or []
        except Exception as exc:
            logger.warning("admin_get_all_chat_history failed: %s", exc)
            return []

    @classmethod
    def admin_get_all_memories(cls, user_id: str | None = None, limit: int = 500) -> list[dict]:
        try:
            if user_id:
                rows = _exec(
                    """SELECT id, user_id, content, category, importance,
                              access_count, created_at, updated_at
                       FROM memories WHERE user_id = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit),
                    fetch="all",
                )
            else:
                rows = _exec(
                    """SELECT id, user_id, content, category, importance,
                              access_count, created_at, updated_at
                       FROM memories ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                    fetch="all",
                )
            return rows or []
        except Exception as exc:
            logger.warning("admin_get_all_memories failed: %s", exc)
            return []

    @classmethod
    def admin_delete_user_data(cls, user_id: str) -> dict:
        results = {"chat_deleted": False, "memories_deleted": False}
        try:
            _exec("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
            results["chat_deleted"] = True
        except Exception as exc:
            logger.warning("admin delete chat failed: %s", exc)
        try:
            _exec("DELETE FROM memories WHERE user_id = %s", (user_id,))
            results["memories_deleted"] = True
        except Exception as exc:
            logger.warning("admin delete memories failed: %s", exc)
        return results

    @classmethod
    def admin_delete_user_chats(cls, user_id: str) -> None:
        """Delete all chat history for a specific user."""
        _exec("DELETE FROM chat_history WHERE user_id = %s", (user_id,))

    @classmethod
    def admin_delete_user_memories(cls, user_id: str) -> None:
        """Delete all memories for a specific user."""
        _exec("DELETE FROM memories WHERE user_id = %s", (user_id,))

    @classmethod
    def admin_clear_all_chats(cls) -> None:
        """Delete ALL chat history across all users."""
        _exec("DELETE FROM chat_history", ())

    @classmethod
    def admin_clear_all_memories(cls) -> None:
        """Delete ALL memories across all users."""
        _exec("DELETE FROM memories", ())

    @classmethod
    def admin_get_counts(cls) -> dict:
        counts = {"users": 0, "messages": 0, "memories": 0}
        try:
            counts["users"] = _exec_count("SELECT COUNT(*) FROM profiles")
        except Exception:
            pass
        try:
            counts["messages"] = _exec_count("SELECT COUNT(*) FROM chat_history")
        except Exception:
            pass
        try:
            counts["memories"] = _exec_count("SELECT COUNT(*) FROM memories")
        except Exception:
            pass
        return counts

    # ═══════════════════════════════════════════════════════════════════
    #  Admin settings
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def load_admin_settings(cls) -> dict | None:
        if not cls.is_configured():
            return None
        try:
            cls._ensure()
            row = _exec(
                "SELECT settings FROM admin_settings WHERE id = 'global'",
                fetch="one",
            )
            if row:
                raw = row["settings"]
                if isinstance(raw, str):
                    return json.loads(raw)
                if isinstance(raw, dict):
                    return raw
        except Exception as exc:
            logger.debug("load_admin_settings: %s", exc)
        return None

    @classmethod
    def save_admin_settings(cls, settings: dict) -> bool:
        if not cls.is_configured():
            return False
        try:
            cls._ensure()
            _exec(
                """INSERT INTO admin_settings (id, settings) VALUES ('global', %s)
                   ON CONFLICT (id) DO UPDATE SET settings = EXCLUDED.settings""",
                (json.dumps(settings, ensure_ascii=False),),
            )
            return True
        except Exception as exc:
            logger.warning("save_admin_settings failed: %s", exc)
            return False

    # ═══════════════════════════════════════════════════════════════════
    #  Memory operations (used by memory_engine.py)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def memory_insert(cls, user_id: str, content: str, category: str,
                      importance: int, embedding: list[float] | None) -> dict | None:
        """Insert a new memory row. Returns the inserted row (without embedding)."""
        try:
            row = _exec(
                """INSERT INTO memories (user_id, content, category, importance, access_count, embedding)
                   VALUES (%s, %s, %s, %s, 0, %s)
                   RETURNING id, user_id, content, category, importance, access_count, created_at, updated_at""",
                (user_id, content, category, importance,
                 json.dumps(embedding) if embedding else None),
                fetch="one",
            )
            return dict(row) if row else None
        except Exception as exc:
            logger.warning("memory_insert failed: %s", exc)
            return None

    @classmethod
    def memory_select_all(cls, user_id: str, with_embedding: bool = False) -> list[dict]:
        """Select all memories for a user."""
        try:
            cols = "id, content, category, importance, access_count, created_at, updated_at"
            if with_embedding:
                cols += ", embedding"
            rows = _exec(
                f"SELECT {cols} FROM memories WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            logger.warning("memory_select_all failed: %s", exc)
            return []

    @classmethod
    def memory_select_with_embeddings(cls, user_id: str) -> list[dict]:
        """Select all memories with embeddings for similarity search."""
        try:
            rows = _exec(
                """SELECT id, content, category, importance, access_count,
                          embedding, created_at, updated_at
                   FROM memories WHERE user_id = %s""",
                (user_id,),
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            logger.warning("memory_select_with_embeddings failed: %s", exc)
            return []

    @classmethod
    def memory_select_by_category(cls, user_id: str, category: str) -> list[dict]:
        try:
            rows = _exec(
                """SELECT id, content, category, importance, access_count, created_at
                   FROM memories WHERE user_id = %s AND category = %s
                   ORDER BY importance DESC""",
                (user_id, category),
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            logger.warning("memory_select_by_category failed: %s", exc)
            return []

    @classmethod
    def memory_keyword_search(cls, user_id: str, query: str, limit: int = 10) -> list[dict]:
        try:
            rows = _exec(
                """SELECT id, content, category, importance, access_count, created_at
                   FROM memories WHERE user_id = %s AND content ILIKE %s
                   LIMIT %s""",
                (user_id, f"%{query[:50]}%", limit),
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            return []

    @classmethod
    def memory_update(cls, memory_id: int, user_id: str, content: str, importance: int) -> None:
        try:
            _exec(
                "UPDATE memories SET content = %s, importance = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
                (content, importance, memory_id, user_id),
            )
        except Exception as exc:
            logger.warning("memory_update failed: %s", exc)

    @classmethod
    def memory_boost(cls, memory_id: int, user_id: str) -> None:
        try:
            _exec(
                "UPDATE memories SET access_count = access_count + 1, updated_at = NOW() WHERE id = %s AND user_id = %s",
                (memory_id, user_id),
            )
        except Exception:
            pass

    @classmethod
    def memory_delete(cls, memory_id: int, user_id: str) -> bool:
        try:
            _exec("DELETE FROM memories WHERE id = %s AND user_id = %s", (memory_id, user_id))
            return True
        except Exception:
            return False

    @classmethod
    def memory_clear_all(cls, user_id: str) -> bool:
        try:
            _exec("DELETE FROM memories WHERE user_id = %s", (user_id,))
            return True
        except Exception:
            return False

    @classmethod
    def memory_stats(cls, user_id: str) -> dict:
        try:
            rows = _exec(
                "SELECT category, COUNT(*) as cnt FROM memories WHERE user_id = %s GROUP BY category",
                (user_id,),
                fetch="all",
            )
            cats = {r["category"]: r["cnt"] for r in (rows or [])}
            return {"total": sum(cats.values()), "categories": cats}
        except Exception:
            return {"total": 0, "categories": {}}


# ═══════════════════════════════════════════════════════════════════════
#  Module-level helpers (same signatures as original)
# ═══════════════════════════════════════════════════════════════════════

def _friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "already exists" in msg or "unique" in msg or "duplicate" in msg:
        return "An account with this email already exists."
    if "invalid" in msg:
        return "Invalid email or password."
    if "password" in msg and ("short" in msg or "least" in msg):
        return "Password must be at least 6 characters."
    if "rate" in msg or "too many" in msg:
        return "Too many attempts — please try again later."
    return "Something went wrong. Please try again."
