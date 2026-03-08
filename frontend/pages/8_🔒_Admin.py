"""Admin Dashboard — Full management console.

Accessible only to users whose email is in ``ADMIN_EMAILS``.
Provides: metrics, user management, chat logs, memory viewer,
knowledge-base management, live configuration editor, and system tools.

Performance: uses lazy tab routing (only the selected section loads data).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
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
)
from frontend.components.auth import require_auth, is_admin  # noqa: E402

logger = logging.getLogger(__name__)

st.set_page_config(page_title="KrishiSaathi — Admin", page_icon="🔒", layout="wide")

# ═══════════════════════════════════════════════════════════════════════
#  Navigation tabs (only selected section loads data → fast)
# ═══════════════════════════════════════════════════════════════════════

_TABS = [
    "📊 Overview",
    "👥 Users",
    "📧 Email Center",
    "📱 Telegram",
    "💬 Chat Logs",
    "🧠 Memories",
    "📚 Knowledge Base",
    "⚙️ Configuration",
    "🔧 System",
]


# ═══════════════════════════════════════════════════════════════════════
#  Cached data loaders — called lazily inside each section
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def _load_counts() -> dict:
    return SupabaseManager.admin_get_counts()


@st.cache_data(ttl=300, show_spinner=False)
def _load_users() -> list[dict]:
    return SupabaseManager.admin_list_users()


@st.cache_data(ttl=300, show_spinner=False)
def _load_messages() -> list[dict]:
    return SupabaseManager.admin_get_all_chat_history(limit=2000)


@st.cache_data(ttl=300, show_spinner=False)
def _load_memories() -> list[dict]:
    return SupabaseManager.admin_get_all_memories(limit=2000)


@st.cache_data(ttl=300, show_spinner=False)
def _load_telegram_users() -> list[dict]:
    try:
        return SupabaseManager.admin_list_telegram_users()
    except Exception:
        return []


def _clear_all_caches() -> None:
    _load_counts.clear()
    _load_users.clear()
    _load_messages.clear()
    _load_memories.clear()
    _load_telegram_users.clear()


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _ts(val) -> str:
    """Normalize a timestamp to an ISO-format string.

    RDS (psycopg2) returns ``datetime`` objects; Supabase returns ISO strings.
    """
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _ago(raw_ts) -> str:
    if not raw_ts:
        return "—"
    try:
        if isinstance(raw_ts, datetime):
            dt = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if delta.days > 365:
            return f"{delta.days // 365}y ago"
        if delta.days > 30:
            return f"{delta.days // 30}mo ago"
        if delta.days > 0:
            return f"{delta.days}d ago"
        h = delta.seconds // 3600
        if h > 0:
            return f"{h}h ago"
        m = delta.seconds // 60
        return f"{m}m ago" if m > 0 else "just now"
    except Exception:
        return str(raw_ts)[:10]


def _date_str(raw_ts) -> str:
    if not raw_ts:
        return "—"
    try:
        if isinstance(raw_ts, datetime):
            return raw_ts.strftime("%Y-%m-%d %H:%M")
        return datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(raw_ts)[:16]


def _build_msg_stats(msgs: list[dict]) -> tuple[Counter, Counter, Counter, dict]:
    """Return (user_msg_counts, daily_counts, role_counts, user_last_active)."""
    user_msg_counts: Counter = Counter()
    daily: Counter = Counter()
    roles: Counter = Counter()
    last_active: dict[str, str] = {}
    for msg in msgs:
        uid = msg.get("user_id", "")
        user_msg_counts[uid] += 1
        roles[msg.get("role", "unknown")] += 1
        ts = _ts(msg.get("created_at", ""))
        if ts:
            daily[ts[:10]] += 1
            if uid not in last_active or ts > last_active[uid]:
                last_active[uid] = ts
    return user_msg_counts, daily, roles, last_active


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1 — Overview
# ═══════════════════════════════════════════════════════════════════════

def _render_overview() -> None:
    with st.spinner("Loading metrics…"):
        counts = _load_counts()
        users = _load_users()

    st.subheader("Key Metrics")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Users", counts.get("users", len(users)))
    m2.metric("Total Messages", counts.get("messages", 0))
    m3.metric("Total Memories", counts.get("memories", 0))
    m4.metric("Registered", len(users))
    m5.metric("Telegram Users", counts.get("telegram_users", 0))
    m6.metric("Admin Emails", len(Config.ADMIN_EMAILS))

    st.divider()

    # Detailed analytics (heavier load — cached after first call)
    with st.spinner("Loading analytics…"):
        all_msgs = _load_messages()
        all_mems = _load_memories()

    user_msg_counts, daily, roles, last_active = _build_msg_stats(all_msgs)

    now = datetime.now(timezone.utc)
    active_24h = active_7d = 0
    for ts in last_active.values():
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if (now - dt) < timedelta(hours=24):
                active_24h += 1
            if (now - dt) < timedelta(days=7):
                active_7d += 1
        except Exception:
            pass

    st.markdown(f"**Active (24 h):** {active_24h} &nbsp;|&nbsp; **Active (7 d):** {active_7d}")
    st.divider()

    st.subheader("Messages Per Day (last 30 days)")
    if daily:
        sorted_days = sorted(daily.keys())[-30:]
        st.bar_chart({d: daily[d] for d in sorted_days}, height=250)
    else:
        st.info("No message data yet.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Messages by Role")
        if roles:
            st.bar_chart(dict(roles), height=200)
    with c2:
        mem_cats: Counter = Counter()
        for m in all_mems:
            mem_cats[m.get("category", "other")] += 1
        st.subheader("Memory Categories")
        if mem_cats:
            st.bar_chart(dict(mem_cats.most_common(10)), height=200)

    st.divider()

    user_map = {u["id"]: u for u in users}
    st.subheader("Top 10 Most Active Users")
    top = user_msg_counts.most_common(10)
    if top:
        for rank, (uid, cnt) in enumerate(top, 1):
            u = user_map.get(uid, {})
            name = u.get("full_name") or uid[:8]
            st.markdown(f"**{rank}.** {name} — **{cnt}** msgs · Last: {_ago(last_active.get(uid))}")
    else:
        st.info("No activity yet.")

    st.divider()
    st.subheader("User Signups")
    signup: Counter = Counter()
    for u in users:
        ca = _ts(u.get("created_at", ""))
        if ca:
            signup[ca[:10]] += 1
    if signup:
        st.bar_chart({d: signup[d] for d in sorted(signup.keys())[-30:]}, height=200)


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2 — Users
# ═══════════════════════════════════════════════════════════════════════

def _render_users() -> None:
    p = get_palette(get_theme())

    with st.spinner("Loading users…"):
        users = _load_users()
        all_msgs = _load_messages()
        all_mems = _load_memories()

    user_msg_counts, _daily, _roles, last_active = _build_msg_stats(all_msgs)
    user_mem_counts: Counter = Counter()
    for m in all_mems:
        user_mem_counts[m.get("user_id", "")] += 1

    st.subheader(f"All Users ({len(users)})")
    search = st.text_input("🔍 Search users (name or ID)", key="admin_user_search")

    display = users
    if search:
        q = search.lower()
        display = [
            u for u in users
            if q in (u.get("full_name") or "").lower()
            or q in (u.get("id") or "").lower()
        ]

    if not display:
        st.info("No users found.")
        return

    for u in display:
        uid = u.get("id", "")
        name = u.get("full_name") or "—"
        mcnt = user_msg_counts.get(uid, 0)
        memcnt = user_mem_counts.get(uid, 0)
        last = _ago(last_active.get(uid))

        with st.expander(f"👤 {name} — {mcnt} msgs, {memcnt} memories — Last: {last}", expanded=False):
            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown(f"**Name:** {name}")
                st.markdown(f"**User ID:** `{uid}`")
                st.markdown(f"**Language:** {u.get('preferred_language') or 'en'}")
                st.markdown(f"**Location:** {u.get('location') or '—'}")
            with pc2:
                st.markdown(f"**Phone:** {u.get('phone') or '—'}")
                st.markdown(f"**Joined:** {_date_str(u.get('created_at'))}")
                st.markdown(f"**Updated:** {_date_str(u.get('updated_at'))}")
                st.markdown(f"**Last Active:** {last}")

            # Use tabs instead of nested expanders (Streamlit forbids nesting)
            u_tab_msgs, u_tab_mems, u_tab_actions = st.tabs(["💬 Messages", "🧠 Memories", "⚙️ Actions"])

            with u_tab_msgs:
                user_msgs = [m for m in all_msgs if m.get("user_id") == uid][:25]
                if user_msgs:
                    for msg in user_msgs:
                        ri = "🧑‍🌾" if msg["role"] == "user" else "🌾"
                        st.markdown(
                            f'{ri} **{msg["role"]}** · '
                            f'<span style="color:{p["text_muted"]};font-size:0.8rem">{_date_str(msg.get("created_at"))}</span>'
                            f'<br><span style="font-size:0.88rem">{(msg.get("content") or "")[:300]}</span>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("---")
                else:
                    st.caption("No messages.")

            with u_tab_mems:
                user_mems = [m for m in all_mems if m.get("user_id") == uid][:25]
                if user_mems:
                    for mem in user_mems:
                        imp = mem.get("importance", 5)
                        st.markdown(
                            f'📌 **[{mem.get("category", "")}]** {mem.get("content", "")} · '
                            f'Imp: {"●" * imp}{"○" * (10 - imp)} · {_date_str(mem.get("created_at"))}'
                        )
                else:
                    st.caption("No memories.")

            with u_tab_actions:
                ac1, ac2, ac3 = st.columns(3)
            with ac1:
                if st.button("🗑️ Delete Chat", key=f"del_c_{uid}"):
                    try:
                        SupabaseManager.admin_delete_user_chats(uid)
                        st.success("Chat deleted"); _clear_all_caches(); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with ac2:
                if st.button("🧹 Delete Memories", key=f"del_m_{uid}"):
                    try:
                        SupabaseManager.admin_delete_user_memories(uid)
                        st.success("Memories deleted"); _clear_all_caches(); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with ac3:
                if st.button("💣 Delete All Data", key=f"del_a_{uid}", type="primary"):
                    SupabaseManager.admin_delete_user_data(uid)
                    st.success("All data deleted"); _clear_all_caches(); st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  TAB — Email Center
# ═══════════════════════════════════════════════════════════════════════

def _render_email_center() -> None:
    from backend.services.email_service import EmailService, EMAIL_TEMPLATES

    p = get_palette(get_theme())
    configured = EmailService.is_configured()

    st.subheader("📧 Email Center")

    if not configured:
        st.error(
            "Email service is not configured. Set `EMAIL_ADDRESS` and `EMAIL_PASSWORD` "
            "in your `.env` file to enable sending emails."
        )
        return

    # ── Load user list ─────────────────────────────────────────────────
    with st.spinner("Loading user emails…"):
        users = _load_users()

    emails_list = [
        {"email": u.get("email", ""), "full_name": u.get("full_name", ""), "id": u.get("id", "")}
        for u in users if u.get("email")
    ]

    # ── Summary metrics ────────────────────────────────────────────────
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Registered Users", len(emails_list))
    mc2.metric("Email Templates", len(EMAIL_TEMPLATES))
    mc3.metric("Email Service", "✅ Active" if configured else "❌ Off")

    st.divider()

    # ── Sub-sections ───────────────────────────────────────────────────
    email_section = st.radio(
        "email_nav",
        ["📋 User Emails", "✉️ Send Custom Email", "📢 Broadcast", "📄 Templates"],
        horizontal=True,
        key="email_nav",
        label_visibility="collapsed",
    )

    # ═══════════════════════════════════════════════════════════════════
    #  Section: User Emails list
    # ═══════════════════════════════════════════════════════════════════
    if "User Emails" in email_section:
        st.markdown("#### 📋 Registered User Emails")
        search_q = st.text_input("🔍 Search by name or email", key="em_search")

        display = emails_list
        if search_q:
            q = search_q.lower()
            display = [
                u for u in emails_list
                if q in u["email"].lower() or q in (u.get("full_name") or "").lower()
            ]

        st.caption(f"Showing {len(display)} of {len(emails_list)} users")

        if display:
            # Table header
            hc1, hc2, hc3, hc4 = st.columns([3, 4, 2, 2])
            hc1.markdown("**Name**")
            hc2.markdown("**Email**")
            hc3.markdown("**User ID**")
            hc4.markdown("**Action**")

            for i, u in enumerate(display):
                c1, c2, c3, c4 = st.columns([3, 4, 2, 2])
                c1.markdown(u.get("full_name") or "—")
                c2.markdown(f'`{u["email"]}`')
                c3.markdown(f'`{u["id"][:8]}…`')
                if c4.button("✉️", key=f"quickemail_{i}", help=f"Send email to {u['email']}"):
                    st.session_state["_email_to"] = u["email"]
                    st.session_state["_email_name"] = u.get("full_name", "Farmer")
                    st.session_state["email_nav"] = "✉️ Send Custom Email"
                    st.rerun()
        else:
            st.info("No users found.")

    # ═══════════════════════════════════════════════════════════════════
    #  Section: Send Custom Email
    # ═══════════════════════════════════════════════════════════════════
    elif "Send Custom Email" in email_section:
        st.markdown("#### ✉️ Send Custom Email")

        # Template picker
        template_names = ["Custom (blank)"] + [t["name"] for t in EMAIL_TEMPLATES]
        selected_tpl = st.selectbox("Start from template", template_names, key="em_tpl_pick")

        # Pre-fill from template
        tpl = None
        if selected_tpl != "Custom (blank)":
            tpl = next((t for t in EMAIL_TEMPLATES if t["name"] == selected_tpl), None)

        prefill_to = st.session_state.pop("_email_to", "")
        prefill_name = st.session_state.pop("_email_name", "")

        with st.form("send_email_form"):
            to_email = st.text_input("To (email)", value=prefill_to, placeholder="user@example.com")
            recipient_name = st.text_input("Recipient name", value=prefill_name or "Farmer")
            subject = st.text_input("Subject", value=tpl["subject"] if tpl else "")
            heading = st.text_input("Heading", value=tpl["heading"] if tpl else "")

            bc1, bc2 = st.columns(2)
            with bc1:
                badge_text = st.text_input(
                    "Badge text (optional)",
                    value=tpl.get("badge_text", "") if tpl else "",
                    placeholder="e.g. NEW FEATURE",
                )
            with bc2:
                badge_color = st.color_picker(
                    "Badge color",
                    value=tpl.get("badge_color", "#2E7D32") if tpl else "#2E7D32",
                )

            default_body = tpl["body_html"].strip() if tpl else ""
            body_html = st.text_area(
                "Body (HTML allowed)",
                value=default_body,
                height=250,
                placeholder="<p>Your message here…</p>",
            )

            cc1, cc2 = st.columns(2)
            with cc1:
                cta_text = st.text_input(
                    "Button text (optional)",
                    value=tpl.get("cta_text", "") if tpl else "",
                    placeholder="e.g. Open KrishiSaathi",
                )
            with cc2:
                cta_url = st.text_input(
                    "Button URL (optional)",
                    value=(tpl.get("cta_url", "").replace("{APP_URL}", Config.APP_URL) if tpl else ""),
                    placeholder=Config.APP_URL,
                )

            send_btn = st.form_submit_button("📨 Send Email", type="primary")

        if send_btn:
            if not to_email or not subject or not heading:
                st.error("Email, Subject, and Heading are required.")
            else:
                with st.spinner(f"Sending email to {to_email}…"):
                    ok = EmailService.send_custom_email(
                        to_email=to_email,
                        subject=subject,
                        heading=heading,
                        body_html=body_html or "<p>No content provided.</p>",
                        recipient_name=recipient_name,
                        cta_text=cta_text or None,
                        cta_url=cta_url or None,
                        badge_text=badge_text or None,
                        badge_color=badge_color,
                    )
                if ok:
                    st.success(f"✅ Email sent to **{to_email}**!")
                    st.balloons()
                else:
                    st.error("Failed to send email. Check server logs.")

    # ═══════════════════════════════════════════════════════════════════
    #  Section: Broadcast
    # ═══════════════════════════════════════════════════════════════════
    elif "Broadcast" in email_section:
        st.markdown("#### 📢 Broadcast Email to All Users")
        st.caption(f"This will send an email to **{len(emails_list)}** registered users.")

        # Template picker
        template_names = ["Custom (blank)"] + [t["name"] for t in EMAIL_TEMPLATES]
        selected_tpl = st.selectbox("Start from template", template_names, key="bc_tpl_pick")

        tpl = None
        if selected_tpl != "Custom (blank)":
            tpl = next((t for t in EMAIL_TEMPLATES if t["name"] == selected_tpl), None)

        with st.form("broadcast_form"):
            bc_subject = st.text_input("Subject", value=tpl["subject"] if tpl else "")
            bc_heading = st.text_input("Heading", value=tpl["heading"] if tpl else "")

            bbc1, bbc2 = st.columns(2)
            with bbc1:
                bc_badge = st.text_input(
                    "Badge text (optional)",
                    value=tpl.get("badge_text", "") if tpl else "",
                )
            with bbc2:
                bc_badge_color = st.color_picker(
                    "Badge color",
                    value=tpl.get("badge_color", "#2E7D32") if tpl else "#2E7D32",
                    key="bc_badge_color",
                )

            bc_body = st.text_area(
                "Body (HTML allowed)",
                value=tpl["body_html"].strip() if tpl else "",
                height=250,
                key="bc_body",
            )

            bcc1, bcc2 = st.columns(2)
            with bcc1:
                bc_cta_text = st.text_input(
                    "Button text (optional)",
                    value=tpl.get("cta_text", "") if tpl else "",
                    key="bc_cta_text",
                )
            with bcc2:
                bc_cta_url = st.text_input(
                    "Button URL (optional)",
                    value=(tpl.get("cta_url", "").replace("{APP_URL}", Config.APP_URL) if tpl else ""),
                    key="bc_cta_url",
                )

            st.warning(
                f"⚠️ This will send an email to **{len(emails_list)} users**. "
                "Make sure the content is correct before proceeding."
            )
            bc_confirm = st.checkbox("I confirm I want to broadcast to all users", key="bc_confirm")
            bc_send = st.form_submit_button("📢 Send Broadcast", type="primary")

        if bc_send:
            if not bc_confirm:
                st.error("Please confirm the broadcast by checking the box.")
            elif not bc_subject or not bc_heading:
                st.error("Subject and Heading are required.")
            else:
                progress = st.progress(0, text="Sending broadcast…")
                with st.spinner(f"Broadcasting to {len(emails_list)} users…"):
                    result = EmailService.send_broadcast(
                        recipients=emails_list,
                        subject=bc_subject,
                        heading=bc_heading,
                        body_html=bc_body or "<p>No content provided.</p>",
                        cta_text=bc_cta_text or None,
                        cta_url=bc_cta_url or None,
                        badge_text=bc_badge or None,
                        badge_color=bc_badge_color,
                    )
                progress.progress(100, text="Done!")

                if result["failed"] == 0:
                    st.success(f"✅ Broadcast sent to **{result['sent']}** users!")
                    st.balloons()
                else:
                    st.warning(
                        f"Sent: {result['sent']} | Failed: {result['failed']}\n\n"
                        f"Failed emails: {', '.join(result['errors'][:10])}"
                    )

    # ═══════════════════════════════════════════════════════════════════
    #  Section: Template Gallery
    # ═══════════════════════════════════════════════════════════════════
    elif "Templates" in email_section:
        st.markdown("#### 📄 Pre-loaded Email Templates")
        st.caption("Click on any template to preview. Use them in custom emails or broadcasts.")

        for tpl in EMAIL_TEMPLATES:
            badge_html = ""
            if tpl.get("badge_text"):
                badge_html = (
                    f'<span style="background:{tpl["badge_color"]};color:#fff;'
                    f'padding:2px 8px;border-radius:10px;font-size:10px;'
                    f'font-weight:700;letter-spacing:0.5px;margin-right:8px;">'
                    f'{tpl["badge_text"]}</span>'
                )

            with st.expander(f'{badge_html} **{tpl["name"]}**', expanded=False):
                st.markdown(f'**Subject:** {tpl["subject"]}')
                st.markdown(f'**Heading:** {tpl["heading"]}')
                if tpl.get("cta_text"):
                    st.markdown(f'**CTA:** {tpl["cta_text"]} → `{tpl.get("cta_url", "")}`')
                st.divider()
                st.markdown("**Preview:**")
                # Show body HTML rendered
                preview_body = tpl["body_html"].replace("{APP_URL}", Config.APP_URL)
                st.markdown(preview_body, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  TAB — Telegram Users
# ═══════════════════════════════════════════════════════════════════════

def _render_telegram() -> None:
    p = get_palette(get_theme())

    with st.spinner("Loading Telegram users…"):
        tg_users = _load_telegram_users()

    st.subheader(f"📱 Telegram Users ({len(tg_users)})")

    if not tg_users:
        st.info(
            "No Telegram users yet. Share the bot link: "
            "[t.me/Krishi_Saathi_bot](https://t.me/Krishi_Saathi_bot)"
        )
        return

    # Summary metrics
    total_msgs = sum(u.get("total_messages", 0) for u in tg_users)
    active_count = sum(1 for u in tg_users if not u.get("is_blocked", False))
    blocked_count = sum(1 for u in tg_users if u.get("is_blocked", False))

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total TG Users", len(tg_users))
    mc2.metric("Active", active_count)
    mc3.metric("Blocked", blocked_count)
    mc4.metric("Total TG Messages", total_msgs)

    st.divider()

    # Filter
    filter_col1, filter_col2 = st.columns([1, 3])
    with filter_col1:
        show_filter = st.selectbox(
            "Filter",
            ["All", "Active", "Blocked"],
            key="tg_filter",
        )

    filtered = tg_users
    if show_filter == "Active":
        filtered = [u for u in tg_users if not u.get("is_blocked")]
    elif show_filter == "Blocked":
        filtered = [u for u in tg_users if u.get("is_blocked")]

    # User list
    for tg_user in filtered:
        tid = tg_user.get("telegram_id", "?")
        username = tg_user.get("username") or "—"
        first_name = tg_user.get("first_name", "") or ""
        last_name = tg_user.get("last_name", "") or ""
        display = f"{first_name} {last_name}".strip() or username
        lang = tg_user.get("language", "en")
        msgs = tg_user.get("total_messages", 0)
        blocked = tg_user.get("is_blocked", False)
        last_active = _ago(tg_user.get("last_active"))
        joined = _date_str(tg_user.get("created_at"))
        profile_id = tg_user.get("profile_id") or "—"

        status_badge = "🔴 Blocked" if blocked else "🟢 Active"
        header = f"{display}  (@{username})  —  {status_badge}  |  💬 {msgs} msgs  |  🕐 {last_active}"

        with st.expander(header, expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
| Field | Value |
|---|---|
| **Telegram ID** | `{tid}` |
| **Username** | @{username} |
| **Name** | {display} |
| **Language** | {lang} |
| **Profile ID** | `{profile_id}` |
| **Joined** | {joined} |
| **Last Active** | {last_active} |
| **Messages** | {msgs} |
""")

            with col2:
                st.markdown("**Actions**")

                # Block / Unblock toggle
                if blocked:
                    if st.button(f"✅ Unblock", key=f"unblock_{tid}", use_container_width=True):
                        SupabaseManager.tg_set_blocked(tid, False)
                        st.success(f"Unblocked {display}")
                        _load_telegram_users.clear()
                        st.rerun()
                else:
                    if st.button(f"🚫 Block", key=f"block_{tid}", use_container_width=True):
                        SupabaseManager.tg_set_blocked(tid, True)
                        st.warning(f"Blocked {display}")
                        _load_telegram_users.clear()
                        st.rerun()

                # View chat history (if profile linked)
                if profile_id and profile_id != "—":
                    try:
                        user_msgs = SupabaseManager.admin_get_all_chat_history(user_id=profile_id, limit=20)
                        if user_msgs:
                            st.markdown(f"**Recent Messages ({len(user_msgs)}):**")
                            for msg in user_msgs[:10]:
                                role = msg.get("role", "?")
                                content = str(msg.get("content", ""))[:200]
                                ts = _date_str(msg.get("created_at"))
                                icon = "👤" if role == "user" else "🌾"
                                st.caption(f"{icon} {ts}: {content}")
                    except Exception:
                        pass

                # Delete user
                st.markdown("---")
                if st.button(
                    f"🗑️ Delete User & Data",
                    key=f"del_tg_{tid}",
                    type="secondary",
                    use_container_width=True,
                ):
                    SupabaseManager.admin_delete_telegram_user(tid)
                    st.success(f"Deleted Telegram user {display}")
                    _load_telegram_users.clear()
                    _clear_all_caches()
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3 — Chat Logs
# ═══════════════════════════════════════════════════════════════════════

def _render_chats() -> None:
    p = get_palette(get_theme())

    with st.spinner("Loading chat logs…"):
        all_msgs = _load_messages()
        users = _load_users()

    user_map = {u["id"]: u for u in users}
    user_msg_counts, *_ = _build_msg_stats(all_msgs)

    st.subheader(f"Chat History ({len(all_msgs)} messages)")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        user_opts = ["All Users"] + [
            f'{user_map.get(uid, {}).get("full_name", uid[:8])} ({uid[:8]})'
            for uid in sorted(user_msg_counts.keys(), key=lambda x: user_msg_counts[x], reverse=True)
        ]
        uid_list = [""] + [
            uid for uid in sorted(user_msg_counts.keys(), key=lambda x: user_msg_counts[x], reverse=True)
        ]
        sel_idx = st.selectbox("Filter by user", range(len(user_opts)),
                               format_func=lambda i: user_opts[i], key="cl_user")
        sel_uid = uid_list[sel_idx] if sel_idx else ""
    with fc2:
        role_f = st.selectbox("Filter by role", ["All", "user", "assistant"], key="cl_role")
    with fc3:
        search_q = st.text_input("🔍 Search messages", key="cl_search")

    filtered = all_msgs
    if sel_uid:
        filtered = [m for m in filtered if m.get("user_id") == sel_uid]
    if role_f != "All":
        filtered = [m for m in filtered if m.get("role") == role_f]
    if search_q:
        q = search_q.lower()
        filtered = [m for m in filtered if q in (m.get("content") or "").lower()]

    st.caption(f"Showing {len(filtered)} messages")

    page_size = 50
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="cl_page")
    page_msgs = filtered[(page - 1) * page_size: page * page_size]

    for msg in page_msgs:
        uid = msg.get("user_id", "")
        u = user_map.get(uid, {})
        name = u.get("full_name") or uid[:8]
        role = msg.get("role", "?")
        ri = "🧑‍🌾" if role == "user" else "🌾"
        ts = _date_str(msg.get("created_at"))
        content = msg.get("content", "")
        sources = msg.get("sources")

        with st.container():
            st.markdown(
                f'{ri} **{role}** by **{name}** · '
                f'<span style="color:{p["text_muted"]};font-size:0.8rem">{ts}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(content[:500] + ("…" if len(content) > 500 else ""))
            if sources and isinstance(sources, list):
                st.caption(f"Sources: {', '.join(str(s) for s in sources)}")
            st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 4 — Memories
# ═══════════════════════════════════════════════════════════════════════

def _render_memories() -> None:
    with st.spinner("Loading memories…"):
        all_mems = _load_memories()
        users = _load_users()

    user_map = {u["id"]: u for u in users}
    user_mem_counts: Counter = Counter()
    for m in all_mems:
        user_mem_counts[m.get("user_id", "")] += 1

    st.subheader(f"All Memories ({len(all_mems)})")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        mopts = ["All Users"] + [
            f'{user_map.get(uid, {}).get("full_name", uid[:8])} ({uid[:8]})'
            for uid in sorted(user_mem_counts.keys(), key=lambda x: user_mem_counts[x], reverse=True)
        ]
        muids = [""] + [
            uid for uid in sorted(user_mem_counts.keys(), key=lambda x: user_mem_counts[x], reverse=True)
        ]
        mi = st.selectbox("Filter by user", range(len(mopts)),
                          format_func=lambda i: mopts[i], key="ml_user")
        sel_uid = muids[mi] if mi else ""
    with mc2:
        cats = ["All Categories"] + sorted({m.get("category", "") for m in all_mems})
        cat_f = st.selectbox("Filter by category", cats, key="ml_cat")
    with mc3:
        search_m = st.text_input("🔍 Search memories", key="ml_search")

    filtered = all_mems
    if sel_uid:
        filtered = [m for m in filtered if m.get("user_id") == sel_uid]
    if cat_f != "All Categories":
        filtered = [m for m in filtered if m.get("category") == cat_f]
    if search_m:
        q = search_m.lower()
        filtered = [m for m in filtered if q in (m.get("content") or "").lower()]

    st.caption(f"Showing {len(filtered)} memories")

    if filtered:
        avg_imp = sum(m.get("importance", 5) for m in filtered) / len(filtered)
        total_acc = sum(m.get("access_count", 0) for m in filtered)
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Count", len(filtered))
        sc2.metric("Avg Importance", f"{avg_imp:.1f}/10")
        sc3.metric("Total Accesses", total_acc)

    page_size = 50
    tp = max(1, (len(filtered) + page_size - 1) // page_size)
    pg = st.number_input("Page", min_value=1, max_value=tp, value=1, key="ml_page")
    page_mems = filtered[(pg - 1) * page_size: pg * page_size]

    cat_icons = {
        "personal": "👤", "location": "📍", "farming": "🌾",
        "crops": "🌿", "equipment": "🚜", "livestock": "🐄",
        "soil": "🪴", "preferences": "⚙️", "experience": "📚",
        "financial": "💰",
    }

    for mem in page_mems:
        uid = mem.get("user_id", "")
        u = user_map.get(uid, {})
        name = u.get("full_name") or uid[:8]
        cat = mem.get("category", "")
        imp = mem.get("importance", 5)
        emoji = cat_icons.get(cat, "📌")
        st.markdown(
            f'{emoji} **[{cat}]** {mem.get("content", "")} · '
            f'by **{name}** · '
            f'Imp: {"●" * imp}{"○" * (10 - imp)} · '
            f'Accessed: {mem.get("access_count", 0)}x · {_date_str(mem.get("created_at"))}'
        )


# ═══════════════════════════════════════════════════════════════════════
#  TAB 5 — Knowledge Base
# ═══════════════════════════════════════════════════════════════════════

def _get_rag():
    """Lazy-import RAGEngine to keep page load fast."""
    from backend.knowledge_base.rag_engine import RAGEngine
    return RAGEngine()


def _render_knowledge_base() -> None:
    st.subheader("RAG Knowledge Base")

    # ── Collection overview ────────────────────────────────────────────
    try:
        rag = _get_rag()
        collections = rag.list_all_collections()
    except Exception as e:
        st.error(f"Could not connect to Knowledge Base: {e}")
        return

    total_docs = sum(c["count"] for c in collections)
    st.metric("Total Documents", total_docs)

    if collections:
        cols_per_row = 4
        rows = [collections[i:i + cols_per_row] for i in range(0, len(collections), cols_per_row)]
        for row in rows:
            cols = st.columns(cols_per_row)
            for col_ui, c in zip(cols, row):
                col_ui.markdown(f'📚 **{c["name"]}**\n\n`{c["count"]}` docs')

    st.divider()

    # ── Sub-sections ───────────────────────────────────────────────────
    kb_section = st.radio(
        "Knowledge Base Action",
        ["📤 Upload JSON", "📝 Add Document", "🌐 Fetch from API", "🔗 Saved API Sources", "🔍 Browse / Delete"],
        horizontal=True, key="kb_action", label_visibility="collapsed",
    )

    # ── Upload JSON ────────────────────────────────────────────────────
    if kb_section == "📤 Upload JSON":
        st.markdown("#### Upload JSON File")
        st.caption("Upload a JSON file containing an array of records to ingest into a collection.")

        uploaded = st.file_uploader("Choose JSON file", type=["json"], key="kb_json_upload")
        col_name = st.text_input("Collection name", placeholder="e.g. custom_data", key="kb_json_col")
        root_key = st.text_input("Root key (optional)", placeholder="Leave blank for auto-detect or bare arrays", key="kb_json_root")

        if uploaded and col_name:
            try:
                raw = json.loads(uploaded.read().decode("utf-8"))
                # Preview
                if isinstance(raw, list):
                    st.info(f"Detected: array with **{len(raw)}** records")
                    if raw:
                        st.json(raw[0])
                elif isinstance(raw, dict):
                    list_keys = {k: len(v) for k, v in raw.items() if isinstance(v, list)}
                    st.info(f"Detected: object with keys `{list(raw.keys())}`. List-valued keys: {list_keys}")
                    if list_keys:
                        first_key = next(iter(list_keys))
                        st.json(raw[first_key][0] if raw[first_key] else {})

                if st.button("🚀 Ingest into Knowledge Base", key="kb_json_ingest", type="primary"):
                    with st.spinner("Embedding & ingesting…"):
                        count = rag.add_json_documents(raw, col_name.strip(), root_key.strip() or None)
                    st.success(f"✅ Ingested **{count}** documents into `{col_name}`")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

    # ── Add single document ────────────────────────────────────────────
    elif kb_section == "📝 Add Document":
        st.markdown("#### Add Text Document")
        st.caption("Manually add a single text document to any collection.")

        col_name = st.text_input("Collection name", key="kb_doc_col")
        doc_id = st.text_input("Document ID (optional)", key="kb_doc_id",
                               placeholder="Auto-generated if blank")
        doc_text = st.text_area("Document text", height=200, key="kb_doc_text",
                                placeholder="Enter the full text of the document…")
        meta_str = st.text_input("Metadata JSON (optional)", key="kb_doc_meta",
                                 placeholder='{"source": "manual", "category": "farming"}')

        if col_name and doc_text:
            if st.button("➕ Add Document", key="kb_doc_add", type="primary"):
                meta = {}
                if meta_str:
                    try:
                        meta = json.loads(meta_str)
                    except json.JSONDecodeError:
                        st.error("Invalid metadata JSON")
                        return
                with st.spinner("Embedding & storing…"):
                    rag.add_text_document(
                        doc_text, col_name.strip(),
                        doc_id=doc_id.strip() or None,
                        metadata=meta or None,
                    )
                st.success(f"✅ Document added to `{col_name}`")

    # ── Fetch from API URL ─────────────────────────────────────────────
    elif kb_section == "🌐 Fetch from API":
        st.markdown("#### Fetch Data from External API")
        st.caption("Enter an API URL that returns JSON. Preview the data, then ingest into a collection.")

        api_url = st.text_input("API URL", key="kb_api_url", placeholder="https://api.example.com/data")
        h1, h2 = st.columns(2)
        with h1:
            header_key = st.text_input("Header key (optional)", key="kb_api_hk",
                                       placeholder="Authorization")
        with h2:
            header_val = st.text_input("Header value (optional)", key="kb_api_hv",
                                       placeholder="Bearer YOUR_TOKEN")

        api_headers = {}
        if header_key and header_val:
            api_headers[header_key] = header_val

        ac1, ac2 = st.columns(2)
        with ac1:
            api_col = st.text_input("Target collection", key="kb_api_col", placeholder="api_data")
        with ac2:
            api_root = st.text_input("Root key (optional)", key="kb_api_root",
                                     placeholder="data.items")

        if api_url:
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("🔍 Preview", key="kb_api_preview"):
                    with st.spinner("Fetching…"):
                        preview = rag.fetch_url_preview(api_url, api_headers or None)
                    if preview.get("success"):
                        st.session_state["_api_preview"] = preview
                        st.success(f"Status: {preview.get('status_code')} · Type: {preview.get('type')}")
                        if preview.get("list_keys"):
                            st.info(f"List-valued keys: {preview['list_keys']}")
                        st.json(preview.get("sample", {}))
                    else:
                        st.error(f"Failed: {preview.get('error')}")

            with bc2:
                if api_col and st.button("🚀 Fetch & Ingest", key="kb_api_ingest", type="primary"):
                    with st.spinner("Fetching & ingesting…"):
                        result = rag.add_from_url(
                            api_url, api_col.strip(),
                            root_key=api_root.strip() or None,
                            headers=api_headers or None,
                        )
                    if result.get("success"):
                        st.success(f"✅ Ingested **{result['documents_added']}** documents into `{api_col}`")
                        # Offer to save as source
                        if st.button("💾 Save as API Source", key="kb_api_save"):
                            _save_api_source(api_url, api_col, api_root, api_headers, result["documents_added"])
                            st.success("Saved!")
                    else:
                        st.error(f"Failed: {result.get('error')}")

    # ── Saved API Sources ──────────────────────────────────────────────
    elif kb_section == "🔗 Saved API Sources":
        st.markdown("#### Saved API Data Sources")
        st.caption("Manage saved external APIs for re-fetching real-time data.")

        settings = Config.load_admin_settings()
        sources = settings.get("api_sources", [])

        if not sources:
            st.info("No saved API sources. Use 'Fetch from API' to add one.")
        else:
            for idx, src in enumerate(sources):
                with st.expander(f'🔗 {src.get("name", src.get("url", "?")[:40])} → `{src.get("collection", "?")}`', expanded=False):
                    st.markdown(f'**URL:** `{src.get("url", "")}`')
                    st.markdown(f'**Collection:** `{src.get("collection", "")}`')
                    st.markdown(f'**Root Key:** `{src.get("root_key", "—")}`')
                    st.markdown(f'**Last Fetched:** {src.get("last_fetched", "Never")}')
                    st.markdown(f'**Docs Ingested:** {src.get("docs_ingested", 0)}')

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("🔄 Re-fetch Now", key=f"api_refetch_{idx}"):
                            with st.spinner("Fetching…"):
                                result = rag.add_from_url(
                                    src["url"], src["collection"],
                                    root_key=src.get("root_key") or None,
                                    headers=src.get("headers") or None,
                                )
                            if result.get("success"):
                                src["last_fetched"] = datetime.now(timezone.utc).isoformat()
                                src["docs_ingested"] = result["documents_added"]
                                Config.save_admin_settings(settings)
                                st.success(f"✅ Ingested {result['documents_added']} docs")
                                st.rerun()
                            else:
                                st.error(result.get("error"))
                    with sc2:
                        if st.button("🗑️ Remove Source", key=f"api_del_{idx}"):
                            sources.pop(idx)
                            settings["api_sources"] = sources
                            Config.save_admin_settings(settings)
                            st.success("Removed"); st.rerun()

        # Quick-add form
        st.divider()
        st.markdown("**Add New API Source**")
        with st.form("add_api_source"):
            n_name = st.text_input("Name", placeholder="Market Prices API")
            n_url = st.text_input("URL", placeholder="https://api.example.com/prices")
            n_col = st.text_input("Collection", placeholder="live_prices")
            n_root = st.text_input("Root key (optional)", placeholder="data")
            n_hk = st.text_input("Header key (optional)")
            n_hv = st.text_input("Header value (optional)")
            if st.form_submit_button("💾 Save Source"):
                if n_name and n_url and n_col:
                    new_src = {
                        "id": str(uuid.uuid4())[:8],
                        "name": n_name,
                        "url": n_url,
                        "collection": n_col,
                        "root_key": n_root or None,
                        "headers": {n_hk: n_hv} if n_hk and n_hv else {},
                        "last_fetched": None,
                        "docs_ingested": 0,
                    }
                    sources.append(new_src)
                    settings["api_sources"] = sources
                    Config.save_admin_settings(settings)
                    st.success(f"✅ Source '{n_name}' saved!"); st.rerun()
                else:
                    st.error("Name, URL, and Collection are required.")

    # ── Browse / Delete Collections ────────────────────────────────────
    elif kb_section == "🔍 Browse / Delete":
        st.markdown("#### Browse Collections")

        if not collections:
            st.info("No collections found.")
            return

        col_names = [c["name"] for c in collections]
        sel_col = st.selectbox("Select collection", col_names, key="kb_browse_col")

        if sel_col:
            col_info = next((c for c in collections if c["name"] == sel_col), None)
            if col_info:
                st.markdown(f"**Documents:** {col_info['count']}")

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("👁️ View Sample Documents", key="kb_browse_sample"):
                    sample = rag.get_collection_sample(sel_col, limit=10)
                    if sample:
                        for doc in sample:
                            with st.expander(f'📄 {doc["id"]}', expanded=False):
                                st.text(doc["document"])
                                if doc.get("metadata"):
                                    st.json(doc["metadata"])
                    else:
                        st.info("No documents in this collection.")

            with bc2:
                if st.button("🔄 Re-ingest from Source Files", key="kb_reingest"):
                    with st.spinner("Re-ingesting…"):
                        stats = rag.ingest_documents()
                    st.success(f"Re-ingested: {stats}")

            with bc3:
                if st.button("🗑️ Delete Collection", key="kb_del_col", type="primary"):
                    st.session_state["_confirm_del_col"] = sel_col

            if st.session_state.get("_confirm_del_col") == sel_col:
                st.error(f"⚠️ Delete collection **{sel_col}**? This removes all documents!")
                de1, de2 = st.columns(2)
                with de1:
                    if st.button("✅ Yes, delete", key="kb_del_confirm"):
                        rag.delete_collection_by_name(sel_col)
                        st.session_state.pop("_confirm_del_col", None)
                        st.success(f"Deleted `{sel_col}`"); st.rerun()
                with de2:
                    if st.button("❌ Cancel", key="kb_del_cancel"):
                        st.session_state.pop("_confirm_del_col", None)
                        st.rerun()


def _save_api_source(url: str, col: str, root_key: str, headers: dict, count: int) -> None:
    """Persist an API source to admin settings."""
    settings = Config.load_admin_settings()
    sources = settings.get("api_sources", [])
    sources.append({
        "id": str(uuid.uuid4())[:8],
        "name": url.split("/")[-1] or "API Source",
        "url": url,
        "collection": col,
        "root_key": root_key or None,
        "headers": headers,
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "docs_ingested": count,
    })
    settings["api_sources"] = sources
    Config.save_admin_settings(settings)


# ═══════════════════════════════════════════════════════════════════════
#  TAB 6 — Configuration
# ═══════════════════════════════════════════════════════════════════════

def _render_configuration() -> None:
    st.subheader("Live Configuration Editor")
    st.caption("Changes take effect immediately and persist across restarts.")

    current = Config.get_current_admin_settings()
    llm = current["llm"]
    app_cfg = current["app"]

    with st.form("admin_config_form"):
        st.markdown("#### LLM Backend")
        backend_options = ["bedrock", "groq", "gemini"]
        backend_labels = {
            "bedrock": "🟠 AWS Bedrock (Primary — Claude 3.5 Sonnet)",
            "groq": "🟢 Groq Cloud (Fallback — Llama 3.x)",
            "gemini": "🔵 Google Gemini (Fallback)",
        }
        cur_idx = backend_options.index(llm["backend"]) if llm["backend"] in backend_options else 0
        backend = st.selectbox(
            "Primary Backend", backend_options, index=cur_idx,
            format_func=lambda k: backend_labels.get(k, k),
        )

        if backend == "bedrock":
            st.info(
                "☁️ **AWS Bedrock** requires an IAM Role attached to the EC2 instance "
                "with `AmazonBedrockFullAccess` policy. No API keys needed — "
                "authentication is handled by the instance role."
            )

        st.markdown("---")
        st.markdown("#### Fallback Models (Groq)")
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            groq_cls = st.text_input("Classifier", value=llm["groq_classifier"])
        with gc2:
            groq_agt = st.text_input("Agent", value=llm["groq_agent"])
        with gc3:
            groq_syn = st.text_input("Synthesis", value=llm["groq_synthesis"])

        st.markdown("#### Fallback Models (Gemini)")
        gm1, gm2, gm3 = st.columns(3)
        with gm1:
            gem_cls = st.text_input("Classifier ", value=llm["gemini_classifier"])
        with gm2:
            gem_agt = st.text_input("Agent ", value=llm["gemini_agent"])
        with gm3:
            gem_syn = st.text_input("Synthesis ", value=llm["gemini_synthesis"])

        embed_model = st.text_input("Embedding Model", value=llm["embedding_model"])

        st.markdown("---")
        st.markdown("#### ☁️ AWS Bedrock Models")
        st.caption("Used when backend is set to **bedrock**. Models must be enabled in AWS Console → Bedrock → Model Access.")
        br1, br2 = st.columns(2)
        with br1:
            br_cls = st.text_input("Bedrock Classifier", value=llm.get("bedrock_classifier", Config.BEDROCK_MODEL_CLASSIFIER))
            br_agt = st.text_input("Bedrock Agent", value=llm.get("bedrock_agent", Config.BEDROCK_MODEL_AGENT))
        with br2:
            br_syn = st.text_input("Bedrock Synthesis", value=llm.get("bedrock_synthesis", Config.BEDROCK_MODEL_SYNTHESIS))
            br_vis = st.text_input("Bedrock Vision", value=llm.get("bedrock_vision", Config.BEDROCK_MODEL_VISION))
        br_region = st.text_input("Bedrock Region", value=llm.get("bedrock_region", Config.BEDROCK_REGION))

        st.markdown("---")
        st.markdown("#### LLM Call Settings")
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            max_retries = st.number_input("Max Retries", min_value=1, max_value=10, value=llm["max_retries"])
        with lc2:
            retry_delay = st.number_input("Retry Base Delay (s)", min_value=1, max_value=120, value=llm["retry_delay"])
        with lc3:
            cache_size = st.number_input("Cache Size", min_value=0, max_value=10000, value=llm["cache_size"])

        st.markdown("---")
        st.markdown("#### App Settings")
        lang_options = list(Config.SUPPORTED_LANGUAGES.keys())
        lang_idx = lang_options.index(app_cfg["default_language"]) if app_cfg["default_language"] in lang_options else 0
        default_lang = st.selectbox("Default Language",
                                    lang_options,
                                    index=lang_idx,
                                    format_func=lambda k: f"{k} — {Config.SUPPORTED_LANGUAGES[k]}")

        submitted = st.form_submit_button("💾 Save & Apply", type="primary")

    if submitted:
        new_settings = {
            "llm": {
                "backend": backend,
                "groq_classifier": groq_cls,
                "groq_agent": groq_agt,
                "groq_synthesis": groq_syn,
                "gemini_classifier": gem_cls,
                "gemini_agent": gem_agt,
                "gemini_synthesis": gem_syn,
                "embedding_model": embed_model,
                "bedrock_region": br_region,
                "bedrock_classifier": br_cls,
                "bedrock_agent": br_agt,
                "bedrock_synthesis": br_syn,
                "bedrock_vision": br_vis,
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "cache_size": cache_size,
            },
            "app": {
                "default_language": default_lang,
            },
            "api_sources": current.get("api_sources", []),
        }
        Config.save_admin_settings(new_settings)

        # Reload LLM singleton with new config
        try:
            from backend.services.llm_helper import llm
            llm.reload_config()
        except Exception:
            pass

        st.success("✅ Configuration saved & applied!")
        st.balloons()

    # ── LLM runtime info ───────────────────────────────────────────────
    st.divider()
    st.markdown("#### LLM Runtime Info")
    try:
        from backend.services.llm_helper import llm
        cs = llm.cache_stats()
        mm = llm.model_map

        ic1, ic2, ic3 = st.columns(3)
        ic1.metric("Cached Responses", cs["cached_entries"])
        ic2.metric("Cache Limit", cs["max_size"])
        ic3.metric("Backend", Config.LLM_BACKEND.upper())

        st.markdown(f"**Active Model Map:** `{mm}`")

        if st.button("🧹 Clear LLM Cache", key="cfg_clear_cache"):
            llm.clear_cache()
            st.success("LLM cache cleared!")
    except Exception as e:
        st.warning(f"Could not load LLM info: {e}")

    # ── Admin emails (read-only) ───────────────────────────────────────
    st.divider()
    st.markdown("#### Admin Emails")
    st.caption("Configured via `.env` file (`ADMIN_EMAILS` or `ADMIN_MAILS`)")
    for em in Config.ADMIN_EMAILS:
        st.markdown(f"- `{em}`")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 7 — System
# ═══════════════════════════════════════════════════════════════════════

def _render_system() -> None:
    st.subheader("System Health & Tools")

    # ── Database health ────────────────────────────────────────────────
    st.markdown("#### Database Health")
    try:
        counts = SupabaseManager.admin_get_counts()
        st.markdown(f"✅ **profiles** — {counts.get('users', '?')} rows")
        st.markdown(f"✅ **chat_history** — {counts.get('messages', '?')} rows")
        st.markdown(f"✅ **memories** — {counts.get('memories', '?')} rows")
    except Exception as e:
        st.markdown(f"❌ Database health check failed: {e}")

    st.divider()

    # ── RAG stats ──────────────────────────────────────────────────────
    st.markdown("#### RAG Knowledge Base")
    try:
        rag = _get_rag()
        stats = rag.collection_stats()
        total = sum(stats.values())
        st.metric("Total Documents", total)
        for col_name, cnt in sorted(stats.items()):
            st.markdown(f"📚 **{col_name}:** {cnt} docs")
    except Exception as e:
        st.warning(f"Could not load RAG stats: {e}")

    st.divider()

    # ── Environment info ───────────────────────────────────────────────
    st.markdown("#### Environment")
    import platform
    ei1, ei2, ei3 = st.columns(3)
    ei1.markdown(f"**Python:** {platform.python_version()}")
    ei2.markdown(f"**Streamlit:** {st.__version__}")
    ei3.markdown(f"**OS:** {platform.system()} {platform.release()}")

    st.markdown(f"**AWS RDS Database:** {'✅' if Config.RDS_HOST else '❌ Not configured'}")
    st.markdown(f"**AWS Bedrock IAM:** {'✅ Attached' if Config.BEDROCK_REGION else '❌ Missing'}")
    st.markdown(f"**Auth Backend:** {'✅' if SupabaseManager.is_configured() else '❌ Not configured'}")
    st.markdown(f"**OpenWeather Key:** {'✅ Set' if Config.OPENWEATHER_API_KEY else '❌ Missing'}")

    st.divider()

    # ── Danger zone ────────────────────────────────────────────────────
    st.markdown("#### ⚠️ Danger Zone")
    st.warning("These actions are irreversible!")

    dz1, dz2, dz3 = st.columns(3)
    with dz1:
        if st.button("🗑️ Clear ALL Chats", key="dz_chats", type="primary"):
            st.session_state["_dz_chats"] = True
        if st.session_state.get("_dz_chats"):
            st.error("Delete ALL users' chat history?")
            y1, n1 = st.columns(2)
            with y1:
                if st.button("✅ Yes", key="dz_chats_y"):
                    try:
                        SupabaseManager.admin_clear_all_chats()
                        st.success("Done"); st.session_state.pop("_dz_chats", None)
                        _clear_all_caches(); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with n1:
                if st.button("❌ No", key="dz_chats_n"):
                    st.session_state.pop("_dz_chats", None); st.rerun()

    with dz2:
        if st.button("🧹 Clear ALL Memories", key="dz_mems", type="primary"):
            st.session_state["_dz_mems"] = True
        if st.session_state.get("_dz_mems"):
            st.error("Delete ALL users' memories?")
            y2, n2 = st.columns(2)
            with y2:
                if st.button("✅ Yes", key="dz_mems_y"):
                    try:
                        SupabaseManager.admin_clear_all_memories()
                        st.success("Done"); st.session_state.pop("_dz_mems", None)
                        _clear_all_caches(); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with n2:
                if st.button("❌ No", key="dz_mems_n"):
                    st.session_state.pop("_dz_mems", None); st.rerun()

    with dz3:
        if st.button("🔥 Reset Admin Config", key="dz_config"):
            st.session_state["_dz_config"] = True
        if st.session_state.get("_dz_config"):
            st.error("Reset all admin config to defaults?")
            y3, n3 = st.columns(2)
            with y3:
                if st.button("✅ Yes", key="dz_config_y"):
                    try:
                        if os.path.exists(Config.ADMIN_SETTINGS_FILE):
                            os.remove(Config.ADMIN_SETTINGS_FILE)
                        st.success("Config reset to defaults")
                        st.session_state.pop("_dz_config", None); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with n3:
                if st.button("❌ No", key="dz_config_n"):
                    st.session_state.pop("_dz_config", None); st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    render_sidebar()
    user = require_auth()

    if not is_admin():
        render_page_header(
            title="Access Denied",
            subtitle="This page is restricted to administrators.",
            icon_name="shield",
        )
        st.error("You do not have admin access.")
        st.info(f"Your email: **{user.get('email', '—')}**")
        st.stop()

    render_page_header(
        title="Admin Dashboard",
        subtitle="System management, analytics & knowledge base",
        icon_name="shield",
    )

    # ── Top toolbar ────────────────────────────────────────────────────
    tc1, tc2, _ = st.columns([1, 1, 4])
    with tc1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            _clear_all_caches()
            st.rerun()
    with tc2:
        st.caption(f"Admin: {user.get('email', '?')}")

    st.divider()

    # ── Navigation — only selected section renders → fast ──────────────
    selected = st.radio(
        "admin_navigation",
        _TABS,
        horizontal=True,
        key="admin_nav",
        label_visibility="collapsed",
    )

    st.markdown("")  # spacer

    if "Overview" in selected:
        _render_overview()
    elif "Users" in selected:
        _render_users()
    elif "Email Center" in selected:
        _render_email_center()
    elif "Telegram" in selected:
        _render_telegram()
    elif "Chat Logs" in selected:
        _render_chats()
    elif "Memories" in selected:
        _render_memories()
    elif "Knowledge Base" in selected:
        _render_knowledge_base()
    elif "Configuration" in selected:
        _render_configuration()
    elif "System" in selected:
        _render_system()


if __name__ == "__main__":
    main()
