"""Admin Dashboard — Metrics, user activity, chat logs, memory viewer.

Accessible only to users whose email is in ``ADMIN_EMAILS``.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.services.supabase_service import SupabaseManager  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import (  # noqa: E402
    render_page_header,
    get_theme,
    get_palette,
    inject_global_css,
    icon,
)
from frontend.components.auth import require_auth, is_admin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Admin", page_icon="🔒", layout="wide")


# ═══════════════════════════════════════════════════════════════════════
#  Cached data loaders (per session, refresh button clears cache)
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def _load_counts() -> dict:
    return SupabaseManager.admin_get_counts()

@st.cache_data(ttl=120, show_spinner=False)
def _load_users() -> list[dict]:
    return SupabaseManager.admin_list_users()

@st.cache_data(ttl=120, show_spinner=False)
def _load_all_messages(user_id: str | None = None) -> list[dict]:
    return SupabaseManager.admin_get_all_chat_history(user_id=user_id, limit=1000)

@st.cache_data(ttl=120, show_spinner=False)
def _load_all_memories(user_id: str | None = None) -> list[dict]:
    return SupabaseManager.admin_get_all_memories(user_id=user_id, limit=1000)


def _clear_admin_cache() -> None:
    _load_counts.clear()
    _load_users.clear()
    _load_all_messages.clear()
    _load_all_memories.clear()


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _ago(iso_str: str | None) -> str:
    """Convert ISO timestamp to a human-readable 'X ago' string."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.days > 365:
            return f"{delta.days // 365}y ago"
        if delta.days > 30:
            return f"{delta.days // 30}mo ago"
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        return f"{minutes}m ago" if minutes > 0 else "just now"
    except Exception:
        return str(iso_str)[:10]


def _date_str(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso_str)[:16]


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    lang = render_sidebar()
    user = require_auth()
    theme = get_theme()
    p = get_palette(theme)

    # ── Admin gate ─────────────────────────────────────────────────────
    if not is_admin():
        render_page_header(title="Access Denied", subtitle="This page is restricted to administrators.", icon_name="shield")
        st.error("You do not have admin access. If you believe this is an error, contact the system administrator.")
        st.info(f"Your email: **{user.get('email', '—')}**")
        st.stop()

    render_page_header(title="Admin Dashboard", subtitle="System overview, user management & analytics", icon_name="shield")

    # ── Top toolbar ────────────────────────────────────────────────────
    tcol1, tcol2, tcol3 = st.columns([1, 1, 4])
    with tcol1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            _clear_admin_cache()
            st.rerun()
    with tcol2:
        auto_refresh = st.toggle("Auto-refresh (2 min)", value=False)

    st.divider()

    # ── Load data ──────────────────────────────────────────────────────
    with st.spinner("Loading admin data …"):
        counts = _load_counts()
        users = _load_users()
        all_msgs = _load_all_messages()
        all_mems = _load_all_memories()

    # ── Build lookup maps ──────────────────────────────────────────────
    user_map: dict[str, dict] = {u["id"]: u for u in users}
    user_msg_counts: Counter = Counter()
    user_last_active: dict[str, str] = {}
    daily_messages: Counter = Counter()
    role_counts: Counter = Counter()
    intent_counts: Counter = Counter()

    for msg in all_msgs:
        uid = msg.get("user_id", "")
        user_msg_counts[uid] += 1
        role_counts[msg.get("role", "unknown")] += 1
        ts = msg.get("created_at", "")
        if ts:
            day = ts[:10]
            daily_messages[day] += 1
            if uid not in user_last_active or ts > user_last_active[uid]:
                user_last_active[uid] = ts

    # Count active users (message in last 7 days / 24h)
    now = datetime.now(timezone.utc)
    active_24h = 0
    active_7d = 0
    for uid, last_ts in user_last_active.items():
        try:
            dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            if (now - dt) < timedelta(hours=24):
                active_24h += 1
            if (now - dt) < timedelta(days=7):
                active_7d += 1
        except Exception:
            pass

    mem_cat_counts: Counter = Counter()
    user_mem_counts: Counter = Counter()
    for m in all_mems:
        mem_cat_counts[m.get("category", "other")] += 1
        user_mem_counts[m.get("user_id", "")] += 1

    # ═══════════════════════════════════════════════════════════════════
    #  TAB LAYOUT
    # ═══════════════════════════════════════════════════════════════════

    tab_overview, tab_users, tab_chats, tab_memories, tab_system = st.tabs([
        "📊 Overview", "👥 Users", "💬 Chat Logs", "🧠 Memories", "⚙️ System"
    ])

    # ───────────────────────────────────────────────────
    #  TAB 1: Overview (KPIs + charts)
    # ───────────────────────────────────────────────────
    with tab_overview:
        st.subheader("Key Metrics")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Users", counts.get("users", len(users)))
        m2.metric("Total Messages", counts.get("messages", len(all_msgs)))
        m3.metric("Total Memories", counts.get("memories", len(all_mems)))
        m4.metric("Active (24h)", active_24h)
        m5.metric("Active (7d)", active_7d)

        st.divider()

        # ── Messages per day chart ─────────────────────────────────────
        st.subheader("Messages Per Day")
        if daily_messages:
            sorted_days = sorted(daily_messages.keys())[-30:]  # last 30 days
            chart_data = {d: daily_messages[d] for d in sorted_days}
            st.bar_chart(chart_data, height=250)
        else:
            st.info("No message data yet.")

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Messages by Role")
            if role_counts:
                st.bar_chart(dict(role_counts), height=200)

        with c2:
            st.subheader("Memory Categories")
            if mem_cat_counts:
                st.bar_chart(dict(mem_cat_counts.most_common(10)), height=200)

        st.divider()

        # ── Top users by message count ─────────────────────────────────
        st.subheader("Top 10 Most Active Users")
        top_users = user_msg_counts.most_common(10)
        if top_users:
            for rank, (uid, msg_count) in enumerate(top_users, 1):
                u = user_map.get(uid, {})
                name = u.get("full_name") or uid[:8]
                email = u.get("email", "—") if u else uid[:20]
                mems = user_mem_counts.get(uid, 0)
                last = _ago(user_last_active.get(uid))
                st.markdown(
                    f"**{rank}.** {name} &nbsp;·&nbsp; `{email}` "
                    f"&nbsp;—&nbsp; **{msg_count}** msgs, **{mems}** memories "
                    f"&nbsp;·&nbsp; Last active: {last}"
                )
        else:
            st.info("No user activity yet.")

        # ── New users per day ──────────────────────────────────────────
        st.divider()
        st.subheader("New User Signups (by date)")
        signup_days: Counter = Counter()
        for u in users:
            ca = u.get("created_at", "")
            if ca:
                signup_days[ca[:10]] += 1
        if signup_days:
            sorted_signup = sorted(signup_days.keys())[-30:]
            st.bar_chart({d: signup_days[d] for d in sorted_signup}, height=200)
        else:
            st.info("No signup data.")

    # ───────────────────────────────────────────────────
    #  TAB 2: Users
    # ───────────────────────────────────────────────────
    with tab_users:
        st.subheader(f"All Users ({len(users)})")

        # Search / filter
        search_term = st.text_input("🔍 Search users (name or email)", key="admin_user_search")

        display_users = users
        if search_term:
            q = search_term.lower()
            display_users = [
                u for u in users
                if q in (u.get("full_name") or "").lower()
                or q in (u.get("id") or "").lower()
            ]

        if not display_users:
            st.info("No users found.")
        else:
            for u in display_users:
                uid = u.get("id", "")
                name = u.get("full_name") or "—"
                lang_pref = u.get("preferred_language") or "en"
                location = u.get("location") or "—"
                phone = u.get("phone") or "—"
                created = _date_str(u.get("created_at"))
                updated = _date_str(u.get("updated_at"))
                msg_count = user_msg_counts.get(uid, 0)
                mem_count = user_mem_counts.get(uid, 0)
                last = _ago(user_last_active.get(uid))

                with st.expander(f"👤 {name} — {msg_count} msgs, {mem_count} memories — Last: {last}", expanded=False):
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.markdown(f"**Name:** {name}")
                        st.markdown(f"**User ID:** `{uid}`")
                        st.markdown(f"**Language:** {lang_pref}")
                        st.markdown(f"**Location:** {location}")
                    with pc2:
                        st.markdown(f"**Phone:** {phone}")
                        st.markdown(f"**Joined:** {created}")
                        st.markdown(f"**Updated:** {updated}")
                        st.markdown(f"**Last Active:** {last}")

                    st.caption(f"Messages: {msg_count} · Memories: {mem_count}")

                    # ── User's recent messages ─────────────────────────
                    with st.expander("💬 Recent Messages", expanded=False):
                        user_msgs = [m for m in all_msgs if m.get("user_id") == uid][:30]
                        if user_msgs:
                            for msg in user_msgs:
                                role_icon = "🧑‍🌾" if msg["role"] == "user" else "🌾"
                                ts = _date_str(msg.get("created_at"))
                                content = msg.get("content", "")[:300]
                                st.markdown(
                                    f'{role_icon} **{msg["role"]}** &nbsp;·&nbsp; '
                                    f'<span style="color:{p["text_muted"]}; font-size:0.8rem;">{ts}</span>'
                                    f'<br><span style="font-size:0.88rem;">{content}</span>',
                                    unsafe_allow_html=True,
                                )
                                st.markdown("---")
                        else:
                            st.caption("No messages.")

                    # ── User's memories ────────────────────────────────
                    with st.expander("🧠 Memories", expanded=False):
                        user_mems = [m for m in all_mems if m.get("user_id") == uid][:30]
                        if user_mems:
                            for mem in user_mems:
                                cat = mem.get("category", "")
                                imp = mem.get("importance", 5)
                                access = mem.get("access_count", 0)
                                content = mem.get("content", "")
                                ts = _date_str(mem.get("created_at"))
                                st.markdown(
                                    f'📌 **[{cat}]** {content} &nbsp;·&nbsp; '
                                    f'Imp: {"●" * imp}{"○" * (10-imp)} &nbsp;·&nbsp; '
                                    f'Accessed: {access}x &nbsp;·&nbsp; {ts}'
                                )
                        else:
                            st.caption("No memories.")

                    # ── Admin actions ──────────────────────────────────
                    st.divider()
                    ac1, ac2, ac3 = st.columns(3)
                    with ac1:
                        if st.button(f"🗑️ Delete Chat History", key=f"admin_del_chat_{uid}"):
                            try:
                                client = SupabaseManager._authed_client()
                                client.table("chat_history").delete().eq("user_id", uid).execute()
                                st.success(f"Deleted chat for {name}")
                                _clear_admin_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    with ac2:
                        if st.button(f"🧹 Delete Memories", key=f"admin_del_mem_{uid}"):
                            try:
                                client = SupabaseManager._authed_client()
                                client.table("memories").delete().eq("user_id", uid).execute()
                                st.success(f"Deleted memories for {name}")
                                _clear_admin_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    with ac3:
                        if st.button(f"💣 Delete All Data", key=f"admin_del_all_{uid}", type="primary"):
                            result = SupabaseManager.admin_delete_user_data(uid)
                            st.success(f"Deleted — Chat: {result['chat_deleted']}, Memories: {result['memories_deleted']}")
                            _clear_admin_cache()
                            st.rerun()

    # ───────────────────────────────────────────────────
    #  TAB 3: Chat Logs
    # ───────────────────────────────────────────────────
    with tab_chats:
        st.subheader(f"Chat History ({len(all_msgs)} messages)")

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            user_options = ["All Users"] + [
                f"{user_map.get(uid, {}).get('full_name', uid[:8])} ({uid[:8]})"
                for uid in sorted(user_msg_counts.keys(), key=lambda x: user_msg_counts[x], reverse=True)
            ]
            user_ids_list = [""] + [
                uid for uid in sorted(user_msg_counts.keys(), key=lambda x: user_msg_counts[x], reverse=True)
            ]
            selected_user_idx = st.selectbox("Filter by user", options=range(len(user_options)),
                                              format_func=lambda i: user_options[i], key="chat_user_filter")
            selected_uid = user_ids_list[selected_user_idx] if selected_user_idx else ""
        with fc2:
            role_filter = st.selectbox("Filter by role", ["All", "user", "assistant"], key="chat_role_filter")
        with fc3:
            search_chat = st.text_input("🔍 Search messages", key="chat_search")

        # Apply filters
        filtered = all_msgs
        if selected_uid:
            filtered = [m for m in filtered if m.get("user_id") == selected_uid]
        if role_filter != "All":
            filtered = [m for m in filtered if m.get("role") == role_filter]
        if search_chat:
            q = search_chat.lower()
            filtered = [m for m in filtered if q in (m.get("content") or "").lower()]

        st.caption(f"Showing {len(filtered)} messages")

        # Display messages (paginated)
        page_size = 50
        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="chat_page")
        page_msgs = filtered[(page - 1) * page_size : page * page_size]

        for msg in page_msgs:
            uid = msg.get("user_id", "")
            u = user_map.get(uid, {})
            name = u.get("full_name") or uid[:8]
            role = msg.get("role", "?")
            role_icon = "🧑‍🌾" if role == "user" else "🌾"
            content = msg.get("content", "")
            sources = msg.get("sources")
            ts = _date_str(msg.get("created_at"))

            with st.container():
                st.markdown(
                    f'{role_icon} **{role}** by **{name}** '
                    f'&nbsp;·&nbsp; <span style="color:{p["text_muted"]}; font-size:0.8rem;">{ts}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(content[:500] + ("…" if len(content) > 500 else ""))
                if sources:
                    if isinstance(sources, list):
                        st.caption(f"Sources: {', '.join(str(s) for s in sources)}")
                st.markdown("---")

    # ───────────────────────────────────────────────────
    #  TAB 4: Memories
    # ───────────────────────────────────────────────────
    with tab_memories:
        st.subheader(f"All Memories ({len(all_mems)})")

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            mem_user_opts = ["All Users"] + [
                f"{user_map.get(uid, {}).get('full_name', uid[:8])} ({uid[:8]})"
                for uid in sorted(user_mem_counts.keys(), key=lambda x: user_mem_counts[x], reverse=True)
            ]
            mem_uids = [""] + [
                uid for uid in sorted(user_mem_counts.keys(), key=lambda x: user_mem_counts[x], reverse=True)
            ]
            mem_user_idx = st.selectbox("Filter by user", range(len(mem_user_opts)),
                                         format_func=lambda i: mem_user_opts[i], key="mem_user_filter")
            selected_mem_uid = mem_uids[mem_user_idx] if mem_user_idx else ""
        with mc2:
            cat_options = ["All Categories"] + sorted(set(m.get("category", "") for m in all_mems))
            cat_filter = st.selectbox("Filter by category", cat_options, key="mem_cat_filter")
        with mc3:
            search_mem = st.text_input("🔍 Search memories", key="mem_search")

        filtered_mems = all_mems
        if selected_mem_uid:
            filtered_mems = [m for m in filtered_mems if m.get("user_id") == selected_mem_uid]
        if cat_filter != "All Categories":
            filtered_mems = [m for m in filtered_mems if m.get("category") == cat_filter]
        if search_mem:
            q = search_mem.lower()
            filtered_mems = [m for m in filtered_mems if q in (m.get("content") or "").lower()]

        st.caption(f"Showing {len(filtered_mems)} memories")

        # Stats row
        if filtered_mems:
            avg_imp = sum(m.get("importance", 5) for m in filtered_mems) / len(filtered_mems)
            total_access = sum(m.get("access_count", 0) for m in filtered_mems)
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Count", len(filtered_mems))
            sc2.metric("Avg Importance", f"{avg_imp:.1f}/10")
            sc3.metric("Total Accesses", total_access)

        # Paginated memories
        mem_page_size = 50
        mem_total_pages = max(1, (len(filtered_mems) + mem_page_size - 1) // mem_page_size)
        mem_page = st.number_input("Page", min_value=1, max_value=mem_total_pages, value=1, key="mem_page")
        page_mems = filtered_mems[(mem_page - 1) * mem_page_size : mem_page * mem_page_size]

        for mem in page_mems:
            uid = mem.get("user_id", "")
            u = user_map.get(uid, {})
            name = u.get("full_name") or uid[:8]
            cat = mem.get("category", "")
            imp = mem.get("importance", 5)
            access = mem.get("access_count", 0)
            content = mem.get("content", "")
            ts = _date_str(mem.get("created_at"))

            cat_icons = {
                "personal": "👤", "location": "📍", "farming": "🌾",
                "crops": "🌿", "equipment": "🚜", "livestock": "🐄",
                "soil": "🪴", "preferences": "⚙️", "experience": "📚",
                "financial": "💰",
            }
            emoji = cat_icons.get(cat, "📌")

            st.markdown(
                f'{emoji} **[{cat}]** {content} &nbsp;·&nbsp; '
                f'by **{name}** &nbsp;·&nbsp; '
                f'Imp: {"●" * imp}{"○" * (10-imp)} &nbsp;·&nbsp; '
                f'Accessed: {access}x &nbsp;·&nbsp; {ts}'
            )

    # ───────────────────────────────────────────────────
    #  TAB 5: System
    # ───────────────────────────────────────────────────
    with tab_system:
        st.subheader("System Configuration")

        s1, s2 = st.columns(2)

        with s1:
            st.markdown("#### LLM Configuration")
            st.markdown(f"**Primary Backend:** `{Config.LLM_BACKEND}`")
            st.markdown(f"**Groq Classifier:** `{Config.GROQ_MODEL_CLASSIFIER}`")
            st.markdown(f"**Groq Agent:** `{Config.GROQ_MODEL_AGENT}`")
            st.markdown(f"**Groq Synthesis:** `{Config.GROQ_MODEL_SYNTHESIS}`")
            st.markdown(f"**Gemini Agent:** `{Config.MODEL_AGENT}`")
            st.markdown(f"**Embedding Model:** `{Config.EMBEDDING_MODEL}`")
            st.markdown(f"**Max Retries:** {Config.LLM_MAX_RETRIES}")
            st.markdown(f"**Cache Size:** {Config.LLM_CACHE_SIZE}")

        with s2:
            st.markdown("#### App Configuration")
            st.markdown(f"**Default Language:** `{Config.DEFAULT_LANGUAGE}`")
            st.markdown(f"**Supported Languages:** {len(Config.SUPPORTED_LANGUAGES)}")
            st.markdown(f"**ChromaDB Path:** `{Config.CHROMA_DB_PATH}`")
            st.markdown(f"**Supabase Configured:** {'✅' if SupabaseManager.is_configured() else '❌'}")
            st.markdown(f"**Admin Emails:** {len(Config.ADMIN_EMAILS)}")
            for email in Config.ADMIN_EMAILS:
                st.markdown(f"  - `{email}`")

        st.divider()

        # ── RAG Knowledge Base stats ───────────────────────────────────
        st.markdown("#### RAG Knowledge Base")
        try:
            from backend.knowledge_base.rag_engine import RAGEngine
            rag = RAGEngine()
            stats = rag.collection_stats()
            total_docs = sum(stats.values())
            st.metric("Total Documents", total_docs)
            if stats:
                rc1, rc2 = st.columns(2)
                with rc1:
                    for col_name, count in sorted(stats.items()):
                        st.markdown(f"📚 **{col_name}:** {count} docs")
        except Exception as e:
            st.warning(f"Could not load RAG stats: {e}")

        st.divider()

        # ── Supabase RLS check ─────────────────────────────────────────
        st.markdown("#### Database Health")
        tables = ["profiles", "chat_history", "memories"]
        for table in tables:
            try:
                client = SupabaseManager._authed_client()
                res = client.table(table).select("id", count="exact").limit(1).execute()
                count = res.count if res.count is not None else "?"
                st.markdown(f"✅ **{table}** — {count} rows")
            except Exception as e:
                st.markdown(f"❌ **{table}** — Error: {e}")

        st.divider()

        # ── Danger zone ────────────────────────────────────────────────
        st.markdown("#### ⚠️ Danger Zone")
        st.warning("These actions are irreversible!")

        dz1, dz2 = st.columns(2)
        with dz1:
            if st.button("🗑️ Clear ALL Chat History", key="danger_clear_chats", type="primary"):
                st.session_state["confirm_clear_chats"] = True
            if st.session_state.get("confirm_clear_chats"):
                st.error("Are you sure? This deletes ALL users' chat history.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ Yes, delete all chats", key="confirm_yes_chats"):
                        try:
                            client = SupabaseManager._authed_client()
                            client.table("chat_history").delete().neq("id", 0).execute()
                            st.success("All chat history deleted.")
                            st.session_state.pop("confirm_clear_chats", None)
                            _clear_admin_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                with cc2:
                    if st.button("❌ Cancel", key="cancel_chats"):
                        st.session_state.pop("confirm_clear_chats", None)
                        st.rerun()

        with dz2:
            if st.button("🧹 Clear ALL Memories", key="danger_clear_mems", type="primary"):
                st.session_state["confirm_clear_mems"] = True
            if st.session_state.get("confirm_clear_mems"):
                st.error("Are you sure? This deletes ALL users' memories.")
                cm1, cm2 = st.columns(2)
                with cm1:
                    if st.button("✅ Yes, delete all memories", key="confirm_yes_mems"):
                        try:
                            client = SupabaseManager._authed_client()
                            client.table("memories").delete().neq("id", 0).execute()
                            st.success("All memories deleted.")
                            st.session_state.pop("confirm_clear_mems", None)
                            _clear_admin_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                with cm2:
                    if st.button("❌ Cancel", key="cancel_mems"):
                        st.session_state.pop("confirm_clear_mems", None)
                        st.rerun()


if __name__ == "__main__":
    main()
