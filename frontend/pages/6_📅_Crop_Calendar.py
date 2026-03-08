"""Crop Calendar & Seasonal Planner — Visual crop timeline with AI recommendations.

Interactive Gantt-chart style crop calendar for Telangana, showing sowing and
harvest windows, varieties, and AI-powered personalised planting advice based
on current season, soil type, and farm size.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from backend.services.llm_helper import llm  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header, icon, get_theme, get_palette  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402
from frontend.components.voice_input import render_voice_output  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Crop Calendar", page_icon="📅", layout="wide")

# ── Month helpers ──────────────────────────────────────────────────────
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTH_NAMES)}

SEASON_COLORS = {
    "Kharif": "#4CAF50",
    "Rabi": "#2196F3",
    "Annual": "#FF9800",
    "Perennial": "#9C27B0",
    "Rabi/Kharif": "#00BCD4",
    "Zaid": "#F44336",
}

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "📅 Crop Calendar & Planner",
        "subtitle": "Telangana seasonal crop timeline, variety guide & AI planting advisor",
        "tab_calendar": "📅 Crop Timeline",
        "tab_season": "🌾 What to Plant Now",
        "tab_varieties": "🌱 Variety Guide",
        "tab_planner": "🤖 AI Crop Planner",
        "season_filter": "Filter by Season",
        "all_seasons": "All Seasons",
        "current_month": "Current Month",
        "crop_count": "Total Crops",
        "sowing_now": "Sowing Now",
        "harvesting_now": "Harvesting Now",
        "sowing_window": "Sowing Window",
        "harvest_window": "Harvest Window",
        "varieties": "Recommended Varieties",
        "notes": "Notes",
        "season": "Season",
        "no_crops_sowing": "No crops in sowing window this month",
        "no_crops_harvest": "No crops in harvest window this month",
        "planner_label": "Describe your farm and get a personalised planting plan …",
        "planner_placeholder": "e.g. 'I have 5 acres in Warangal, black cotton soil, what should I plant this month?'",
        "planner_btn": "🤖 Get Planting Plan",
        "thinking": "Generating your personalised crop plan …",
        "gantt_title": "Telangana Crop Calendar — Sowing & Harvest Windows",
        "sow_label": "Sowing",
        "harvest_label": "Harvest",
        "quick_questions": "Quick Questions",
    },
    "te": {
        "title": "📅 పంట క్యాలెండర్ & ప్లానర్",
        "subtitle": "తెలంగాణ సీజనల్ పంట టైమ్‌లైన్, రకాల గైడ్ & AI నాటే సలహా",
        "tab_calendar": "📅 పంట టైమ్‌లైన్",
        "tab_season": "🌾 ఇప్పుడు ఏమి నాటాలి",
        "tab_varieties": "🌱 రకాల గైడ్",
        "tab_planner": "🤖 AI పంట ప్లానర్",
        "season_filter": "సీజన్ ద్వారా ఫిల్టర్",
        "all_seasons": "అన్ని సీజన్లు",
        "current_month": "ప్రస్తుత నెల",
        "crop_count": "మొత్తం పంటలు",
        "sowing_now": "ఇప్పుడు విత్తడం",
        "harvesting_now": "ఇప్పుడు కోత",
        "sowing_window": "విత్తడం కాలం",
        "harvest_window": "కోత కాలం",
        "varieties": "సిఫార్సు చేసిన రకాలు",
        "notes": "గమనికలు",
        "season": "సీజన్",
        "no_crops_sowing": "ఈ నెలలో విత్తడానికి పంటలు లేవు",
        "no_crops_harvest": "ఈ నెలలో కోతకు పంటలు లేవు",
        "planner_label": "మీ పొలం గురించి చెప్పండి, వ్యక్తిగత నాటే ప్రణాళిక పొందండి …",
        "planner_placeholder": "ఉదా. 'వరంగల్ లో 5 ఎకరాలు, నల్ల రేగడి మట్టి, ఈ నెల ఏమి నాటాలి?'",
        "planner_btn": "🤖 నాటే ప్రణాళిక పొందండి",
        "thinking": "మీ వ్యక్తిగత పంట ప్రణాళికను తయారు చేస్తోంది …",
        "gantt_title": "తెలంగాణ పంట క్యాలెండర్ — విత్తనం & కోత కాలాలు",
        "sow_label": "విత్తనం",
        "harvest_label": "కోత",
        "quick_questions": "త్వరిత ప్రశ్నలు",
    },
    "hi": {
        "title": "📅 फसल कैलेंडर & प्लानर",
        "subtitle": "तेलंगाना मौसमी फसल टाइमलाइन, किस्म गाइड व AI बुवाई सलाह",
        "tab_calendar": "📅 फसल टाइमलाइन",
        "tab_season": "🌾 अभी क्या बोएं",
        "tab_varieties": "🌱 किस्म गाइड",
        "tab_planner": "🤖 AI फसल प्लानर",
        "season_filter": "मौसम से फ़िल्टर",
        "all_seasons": "सभी मौसम",
        "current_month": "वर्तमान महीना",
        "crop_count": "कुल फसलें",
        "sowing_now": "अभी बुवाई",
        "harvesting_now": "अभी कटाई",
        "sowing_window": "बुवाई अवधि",
        "harvest_window": "कटाई अवधि",
        "varieties": "अनुशंसित किस्में",
        "notes": "नोट्स",
        "season": "मौसम",
        "no_crops_sowing": "इस महीने बुवाई के लिए कोई फसल नहीं",
        "no_crops_harvest": "इस महीने कटाई के लिए कोई फसल नहीं",
        "planner_label": "अपने खेत के बारे में बताएं और व्यक्तिगत बुवाई योजना पाएं …",
        "planner_placeholder": "जैसे 'वारंगल में 5 एकड़, काली कपास मिट्टी, इस महीने क्या बोएं?'",
        "planner_btn": "🤖 बुवाई योजना पाएं",
        "thinking": "आपकी व्यक्तिगत फसल योजना बना रहे हैं …",
        "gantt_title": "तेलंगाना फसल कैलेंडर — बुवाई व कटाई अवधि",
        "sow_label": "बुवाई",
        "harvest_label": "कटाई",
        "quick_questions": "त्वरित प्रश्न",
    },
}


def _ui(key: str, lang: str) -> str:
    """Return localised UI string with auto-translate fallback."""
    if lang in _UI and key in _UI[lang]:
        return _UI[lang][key]
    en = _UI["en"].get(key, key)
    if lang == "en":
        return en
    try:
        return translator.from_english(en, lang)
    except Exception:
        return en


# ── Load crop calendar data ────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _load_crop_calendar() -> list[dict[str, Any]]:
    data_path = os.path.join(_PROJECT_ROOT, "backend", "data", "crop_calendar.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _month_in_range(month_num: int, start_month: str, end_month: str) -> bool:
    """Check if a month number falls within a start–end month range (wraps around year)."""
    start = MONTH_NUM.get(start_month, 0)
    end = MONTH_NUM.get(end_month, 0)
    if start == 0 or end == 0:
        return False
    if start <= end:
        return start <= month_num <= end
    else:  # wraps around (e.g. Nov → Feb)
        return month_num >= start or month_num <= end


def _month_span(start_month: str, end_month: str) -> list[int]:
    """Return list of month numbers in the range."""
    start = MONTH_NUM.get(start_month, 1)
    end = MONTH_NUM.get(end_month, 1)
    if start <= end:
        return list(range(start, end + 1))
    else:
        return list(range(start, 13)) + list(range(1, end + 1))


# ═══════════════════════════════════════════════════════════════════════
#  Main page
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    user = require_auth()
    if not user:
        return
    lang = render_sidebar()
    palette = get_palette()
    theme = get_theme()

    render_page_header(
        _ui("title", lang),
        _ui("subtitle", lang),
        icon_name="calendar",
    )

    crops = _load_crop_calendar()
    now = datetime.now()
    current_month_num = now.month
    current_month_name = MONTH_NAMES[current_month_num - 1]

    # ── Metrics row ────────────────────────────────────────────────────
    sowing_now = [c for c in crops if _month_in_range(current_month_num, c["sowing_start"], c["sowing_end"])]
    harvesting_now = [c for c in crops if _month_in_range(current_month_num, c["harvest_start"], c["harvest_end"])]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(_ui("current_month", lang), current_month_name)
    m2.metric(_ui("crop_count", lang), len(crops))
    m3.metric(_ui("sowing_now", lang), len(sowing_now))
    m4.metric(_ui("harvesting_now", lang), len(harvesting_now))

    st.markdown("")

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_cal, tab_season, tab_var, tab_plan = st.tabs([
        _ui("tab_calendar", lang),
        _ui("tab_season", lang),
        _ui("tab_varieties", lang),
        _ui("tab_planner", lang),
    ])

    # ═══════════════════════════════════════════════════════════════════
    #  TAB 1 — Gantt Chart Timeline
    # ═══════════════════════════════════════════════════════════════════
    with tab_cal:
        _render_gantt(crops, current_month_num, lang, palette)

    # ═══════════════════════════════════════════════════════════════════
    #  TAB 2 — What to Plant / Harvest Now
    # ═══════════════════════════════════════════════════════════════════
    with tab_season:
        _render_current_season(crops, current_month_num, current_month_name, lang, palette)

    # ═══════════════════════════════════════════════════════════════════
    #  TAB 3 — Variety Guide
    # ═══════════════════════════════════════════════════════════════════
    with tab_var:
        _render_variety_guide(crops, lang, palette)

    # ═══════════════════════════════════════════════════════════════════
    #  TAB 4 — AI Crop Planner
    # ═══════════════════════════════════════════════════════════════════
    with tab_plan:
        _render_ai_planner(crops, current_month_name, lang)


# ═══════════════════════════════════════════════════════════════════════
#  Gantt chart
# ═══════════════════════════════════════════════════════════════════════

def _render_gantt(crops: list[dict], current_month: int, lang: str, palette: dict) -> None:
    """Interactive Gantt chart of sowing and harvest windows."""

    # Season filter
    seasons = sorted({c["season"] for c in crops})
    season_choice = st.selectbox(
        _ui("season_filter", lang),
        [_ui("all_seasons", lang)] + seasons,
        key="cal_season_filter",
    )
    filtered = crops if season_choice == _ui("all_seasons", lang) else [c for c in crops if c["season"] == season_choice]

    fig = go.Figure()

    for i, crop in enumerate(filtered):
        crop_name = crop["crop"]
        sow_months = _month_span(crop["sowing_start"], crop["sowing_end"])
        harv_months = _month_span(crop["harvest_start"], crop["harvest_end"])
        season_color = SEASON_COLORS.get(crop["season"], "#607D8B")

        # Sowing bar
        if sow_months:
            fig.add_trace(go.Bar(
                y=[crop_name],
                x=[len(sow_months)],
                base=[sow_months[0] - 1],
                orientation="h",
                marker=dict(color=season_color, opacity=0.85),
                name=_ui("sow_label", lang),
                hovertemplate=f"<b>{crop_name}</b><br>{_ui('sow_label', lang)}: {crop['sowing_start']} – {crop['sowing_end']}<extra></extra>",
                showlegend=(i == 0),
                legendgroup="sow",
            ))

        # Harvest bar (lighter shade)
        if harv_months:
            fig.add_trace(go.Bar(
                y=[crop_name],
                x=[len(harv_months)],
                base=[harv_months[0] - 1],
                orientation="h",
                marker=dict(color=season_color, opacity=0.4, pattern=dict(shape="/")),
                name=_ui("harvest_label", lang),
                hovertemplate=f"<b>{crop_name}</b><br>{_ui('harvest_label', lang)}: {crop['harvest_start']} – {crop['harvest_end']}<extra></extra>",
                showlegend=(i == 0),
                legendgroup="harv",
            ))

    # Current month indicator
    fig.add_vline(
        x=current_month - 0.5,
        line_dash="dash",
        line_color="#FF5722",
        line_width=2,
        annotation_text=f"  ← {MONTH_NAMES[current_month - 1]}",
        annotation_position="top right",
        annotation_font_color="#FF5722",
    )

    fig.update_layout(
        title=_ui("gantt_title", lang),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(12)),
            ticktext=[m[:3] for m in MONTH_NAMES],
            range=[-0.5, 12],
            title="",
        ),
        yaxis=dict(autorange="reversed", title=""),
        barmode="overlay",
        height=max(400, len(filtered) * 40 + 100),
        margin=dict(l=10, r=10, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Season legend
    cols = st.columns(len(SEASON_COLORS))
    for col, (season, color) in zip(cols, SEASON_COLORS.items()):
        col.markdown(
            f'<span style="display:inline-block;width:14px;height:14px;'
            f'background:{color};border-radius:3px;margin-right:6px;vertical-align:middle;"></span>'
            f'<span style="vertical-align:middle;font-size:0.85rem;">{season}</span>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════
#  Current season
# ═══════════════════════════════════════════════════════════════════════

def _render_current_season(
    crops: list[dict], month_num: int, month_name: str, lang: str, palette: dict
) -> None:
    """Show crops that can be sown or harvested this month."""

    sowing = [c for c in crops if _month_in_range(month_num, c["sowing_start"], c["sowing_end"])]
    harvesting = [c for c in crops if _month_in_range(month_num, c["harvest_start"], c["harvest_end"])]

    st.markdown(f"### 🌱 {_ui('sowing_window', lang)} — {month_name}")
    if sowing:
        for crop in sowing:
            season_color = SEASON_COLORS.get(crop["season"], "#607D8B")
            with st.expander(f"🌿 **{crop['crop']}** — {crop['season']}", expanded=False):
                c1, c2 = st.columns(2)
                c1.markdown(f"**{_ui('sowing_window', lang)}:** {crop['sowing_start']} – {crop['sowing_end']}")
                c2.markdown(f"**{_ui('harvest_window', lang)}:** {crop['harvest_start']} – {crop['harvest_end']}")
                st.markdown(f"**{_ui('varieties', lang)}:** {', '.join(crop.get('varieties', []))}")
                if crop.get("notes"):
                    st.info(f"📝 {crop['notes']}")
    else:
        st.info(_ui("no_crops_sowing", lang))

    st.divider()

    st.markdown(f"### 🌾 {_ui('harvest_window', lang)} — {month_name}")
    if harvesting:
        for crop in harvesting:
            with st.expander(f"🌾 **{crop['crop']}** — {crop['season']}", expanded=False):
                c1, c2 = st.columns(2)
                c1.markdown(f"**{_ui('sowing_window', lang)}:** {crop['sowing_start']} – {crop['sowing_end']}")
                c2.markdown(f"**{_ui('harvest_window', lang)}:** {crop['harvest_start']} – {crop['harvest_end']}")
                st.markdown(f"**{_ui('varieties', lang)}:** {', '.join(crop.get('varieties', []))}")
                if crop.get("notes"):
                    st.info(f"📝 {crop['notes']}")
    else:
        st.info(_ui("no_crops_harvest", lang))


# ═══════════════════════════════════════════════════════════════════════
#  Variety guide
# ═══════════════════════════════════════════════════════════════════════

def _render_variety_guide(crops: list[dict], lang: str, palette: dict) -> None:
    """Searchable crop variety reference table."""

    search = st.text_input("🔍 Search crop", key="var_search", placeholder="e.g. Rice, Cotton, Tomato …")
    filtered = crops
    if search:
        term = search.lower()
        filtered = [c for c in crops if term in c["crop"].lower() or term in c.get("notes", "").lower()]

    if not filtered:
        st.info("No crops match your search.")
        return

    # Build table data
    rows = []
    for c in filtered:
        rows.append({
            "Crop": c["crop"],
            _ui("season", lang): c["season"],
            _ui("sowing_window", lang): f"{c['sowing_start']} – {c['sowing_end']}",
            _ui("harvest_window", lang): f"{c['harvest_start']} – {c['harvest_end']}",
            _ui("varieties", lang): ", ".join(c.get("varieties", [])[:3]),
        })

    st.dataframe(rows, use_container_width=True, hide_index=True, height=min(600, len(rows) * 40 + 60))

    # Detail cards
    if search and filtered:
        for crop in filtered:
            with st.expander(f"📋 {crop['crop']} — Full Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{_ui('season', lang)}:** {crop['season']}")
                    st.markdown(f"**{_ui('sowing_window', lang)}:** {crop['sowing_start']} – {crop['sowing_end']}")
                    st.markdown(f"**{_ui('harvest_window', lang)}:** {crop['harvest_start']} – {crop['harvest_end']}")
                    st.markdown(f"**Region:** {crop.get('region', 'Telangana')}")
                with col2:
                    st.markdown(f"**{_ui('varieties', lang)}:**")
                    for v in crop.get("varieties", []):
                        st.markdown(f"- {v}")
                if crop.get("notes"):
                    st.info(f"📝 {crop['notes']}")


# ═══════════════════════════════════════════════════════════════════════
#  AI Planner
# ═══════════════════════════════════════════════════════════════════════

def _render_ai_planner(crops: list[dict], current_month: str, lang: str) -> None:
    """AI-powered personalised crop planner."""

    # Restore persisted result
    result = st.session_state.get("crop_plan_result")

    # Voice or text input
    _prefill = st.session_state.pop("_crop_plan_prefill", "")
    q = st.text_area(
        _ui("planner_label", lang),
        value=_prefill,
        placeholder=_ui("planner_placeholder", lang),
        height=100,
        key="crop_plan_input",
    )

    if st.button(_ui("planner_btn", lang), type="primary", key="crop_plan_btn"):
        if not q.strip():
            st.warning("Please describe your farm or question.")
        else:
            # Build context from crop calendar
            sowing_now = [c for c in crops if _month_in_range(
                MONTH_NUM.get(current_month, 1), c["sowing_start"], c["sowing_end"]
            )]
            calendar_ctx = "\n".join(
                f"- {c['crop']} ({c['season']}): sow {c['sowing_start']}–{c['sowing_end']}, "
                f"harvest {c['harvest_start']}–{c['harvest_end']}. Varieties: {', '.join(c.get('varieties', []))}. "
                f"{c.get('notes', '')}"
                for c in crops
            )
            sowing_ctx = "\n".join(
                f"- {c['crop']} ({c['season']}): {', '.join(c.get('varieties', []))}"
                for c in sowing_now
            ) or "No crops currently in sowing window."

            prompt = f"""You are KrishiSaathi, an expert agricultural advisor for Telangana farmers.
Current month: {current_month}

=== FULL CROP CALENDAR (Telangana) ===
{calendar_ctx}

=== CROPS CURRENTLY IN SOWING WINDOW ===
{sowing_ctx}

Farmer's question: {q}

Provide a detailed, personalised crop planting plan. Include:
1. Which crops to plant NOW based on the current month
2. Recommended varieties with brief reasons
3. Step-by-step timeline for the next 3–6 months
4. Soil preparation and input requirements
5. Expected yield and market considerations
6. Risk factors and mitigation tips

Keep the advice practical and specific to Telangana conditions.
Write in a helpful, encouraging tone suitable for farmers."""

            with st.spinner(_ui("thinking", lang)):
                t0 = time.time()
                try:
                    raw_resp = llm.generate(prompt, role="agent")
                    answer = raw_resp if isinstance(raw_resp, str) else raw_resp.get("text", str(raw_resp))
                    elapsed = time.time() - t0
                    result = {"answer": answer, "elapsed": elapsed}
                    st.session_state["crop_plan_result"] = result
                except Exception as e:
                    logger.error("AI planner error: %s", e)
                    st.error(f"Could not generate plan: {e}")
                    result = None

    # ── Render persisted result ────────────────────────────────────────
    if result:
        st.divider()
        st.markdown("### 📋 Your Personalised Crop Plan")
        st.markdown(result.get("answer", ""))
        render_voice_output(result.get("answer", ""), language=lang, key_suffix="crop_plan")
        st.caption(f"⏱️ {result.get('elapsed', 0):.1f}s")

    # ── Quick questions ────────────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "Best crops to plant in March?",
            "Which Kharif crops for 3 acres?",
            "Cotton vs Red Gram — which is better now?",
            "Rabi season plan for Warangal",
            "High-profit crops for small farms",
        ],
        "te": [
            "మార్చిలో ఏ పంటలు నాటాలి?",
            "3 ఎకరాలకు ఖరీఫ్ పంటలు?",
            "పత్తి vs కంది — ఏది మంచిది?",
            "వరంగల్ రబీ ప్రణాళిక",
            "చిన్న పొలాలకు లాభదాయక పంటలు",
        ],
        "hi": [
            "मार्च में कौन सी फसल बोएं?",
            "3 एकड़ के लिए खरीफ फसलें?",
            "कपास vs अरहर — क्या बेहतर?",
            "वारंगल रबी योजना",
            "छोटे खेतों के लिए लाभदायक फसलें",
        ],
    }
    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown(f"**💡 {_ui('quick_questions', lang)}:**")
    cols = st.columns(len(qs))
    for i, (col, q_txt) in enumerate(zip(cols, qs)):
        with col:
            label = q_txt[:28] + "…" if len(q_txt) > 28 else q_txt
            if st.button(label, key=f"cropq_{i}", use_container_width=True):
                st.session_state["_crop_plan_prefill"] = q_txt
                st.rerun()


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
