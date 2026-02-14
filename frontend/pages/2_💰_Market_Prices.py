"""Market Prices Dashboard — Mandi rates, trends & selling recommendations.

Browse real-time mandi prices across Telangana, compare markets, view price
trends, and get AI-powered selling advice.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import json

import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402
from backend.agents.market_agent import MarketAgent  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Market Prices", page_icon="💰", layout="wide")

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "💰 Market Prices Dashboard",
        "subtitle": "Live mandi prices, trends & selling recommendations for Telangana",
        "tab_prices": "📊 Price Comparison",
        "tab_trends": "📈 Price Trends",
        "tab_advisor": "🤖 AI Market Advisor",
        "crop_select": "Select Crop",
        "all_crops": "All Crops",
        "market_filter": "Filter by Market",
        "all_markets": "All Markets",
        "prices_header": "Current Mandi Prices",
        "best_mandi": "Best Mandi Recommendation",
        "msp_label": "MSP (2025-26)",
        "no_data": "No price data available for this selection.",
        "trend_header": "Price Trend (Last 14 Days)",
        "trend_crop": "Select crop for trend analysis",
        "predict_header": "Price Prediction",
        "advisor_label": "Ask about market prices, best time to sell, storage tips …",
        "advisor_placeholder": "e.g. 'When should I sell my cotton for best price?' or 'Compare rice prices across mandis'",
        "advisor_btn": "🤖 Get Market Advice",
        "thinking": "Analyzing market data …",
        "summary_header": "Market Intelligence Report",
        "crop_col": "Crop",
        "market_col": "Market (Mandi)",
        "price_col": "Price (₹/quintal)",
        "date_col": "Date",
        "msp_col": "MSP",
        "diff_col": "vs MSP",
        "season_header": "📅 Market Calendar",
        "storage_header": "📦 Storage Advisory",
    },
    "te": {
        "title": "💰 మార్కెట్ ధరల డ్యాష్‌బోర్డ్",
        "subtitle": "తెలంగాణలో ప్రత్యక్ష మండి ధరలు, ధోరణులు & అమ్మకపు సిఫార్సులు",
        "tab_prices": "📊 ధరల పోలిక",
        "tab_trends": "📈 ధర ధోరణులు",
        "tab_advisor": "🤖 AI మార్కెట్ సలహాదారు",
        "crop_select": "పంటను ఎంచుకోండి",
        "all_crops": "అన్ని పంటలు",
        "market_filter": "మార్కెట్ ద్వారా ఫిల్టర్",
        "all_markets": "అన్ని మార్కెట్లు",
        "prices_header": "ప్రస్తుత మండి ధరలు",
        "best_mandi": "ఉత్తమ మండి సిఫార్సు",
        "msp_label": "MSP (2025-26)",
        "no_data": "ఈ ఎంపికకు ధర డేటా అందుబాటులో లేదు.",
        "trend_header": "ధర ధోరణి (గత 14 రోజులు)",
        "trend_crop": "ధోరణి విశ్లేషణ కోసం పంటను ఎంచుకోండి",
        "predict_header": "ధర అంచనా",
        "advisor_label": "మార్కెట్ ధరలు, అమ్మకానికి ఉత్తమ సమయం, నిల్వ చిట్కాల గురించి అడగండి …",
        "advisor_placeholder": "ఉదా. 'ఉత్తమ ధరకు నా పత్తిని ఎప్పుడు అమ్మాలి?'",
        "advisor_btn": "🤖 మార్కెట్ సలహా పొందండి",
        "thinking": "మార్కెట్ డేటాను విశ్లేషిస్తోంది …",
        "summary_header": "మార్కెట్ ఇంటెలిజెన్స్ నివేదిక",
        "crop_col": "పంట",
        "market_col": "మార్కెట్ (మండి)",
        "price_col": "ధర (₹/క్వింటాల్)",
        "date_col": "తేదీ",
        "msp_col": "MSP",
        "diff_col": "MSP తో పోలిక",
        "season_header": "📅 మార్కెట్ క్యాలెండర్",
        "storage_header": "📦 నిల్వ సలహా",
    },
    "hi": {
        "title": "💰 मंडी भाव डैशबोर्ड",
        "subtitle": "तेलंगाना में लाइव मंडी भाव, रुझान और बिक्री सुझाव",
        "tab_prices": "📊 भाव तुलना",
        "tab_trends": "📈 भाव रुझान",
        "tab_advisor": "🤖 AI मंडी सलाहकार",
        "crop_select": "फसल चुनें",
        "all_crops": "सभी फसलें",
        "market_filter": "मंडी से फ़िल्टर",
        "all_markets": "सभी मंडियां",
        "prices_header": "वर्तमान मंडी भाव",
        "best_mandi": "सर्वोत्तम मंडी सुझाव",
        "msp_label": "MSP (2025-26)",
        "no_data": "इस चयन के लिए कोई मूल्य डेटा उपलब्ध नहीं।",
        "trend_header": "भाव रुझान (पिछले 14 दिन)",
        "trend_crop": "रुझान विश्लेषण के लिए फसल चुनें",
        "predict_header": "भाव अनुमान",
        "advisor_label": "मंडी भाव, बिक्री का सही समय, भंडारण सुझाव पूछें …",
        "advisor_placeholder": "जैसे 'मुझे अपना कपास कब बेचना चाहिए?'",
        "advisor_btn": "🤖 मंडी सलाह पाएं",
        "thinking": "बाजार डेटा का विश्लेषण कर रहा है …",
        "summary_header": "मार्केट इंटेलिजेंस रिपोर्ट",
        "crop_col": "फसल",
        "market_col": "मंडी",
        "price_col": "भाव (₹/क्विंटल)",
        "date_col": "तारीख",
        "msp_col": "MSP",
        "diff_col": "MSP से तुलना",
        "season_header": "📅 मंडी कैलेंडर",
        "storage_header": "📦 भंडारण सलाह",
    },
}


def _ui(lang: str, key: str) -> str:
    return _UI.get(lang, _UI["en"]).get(key, _UI["en"][key])


# ── Cached resources ───────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading market data …")
def _get_market_agent() -> MarketAgent:
    try:
        rag = RAGEngine()
    except Exception:
        rag = None  # type: ignore[assignment]
    return MarketAgent(rag_engine=rag)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_market_intelligence() -> list[dict]:
    """Load the full market_data.json for MSP / calendar / advisory info."""
    path = os.path.join(
        _PROJECT_ROOT, "backend", "knowledge_base", "documents", "market_data.json"
    )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return raw.get("market_data", []) if isinstance(raw, dict) else raw
    except Exception:
        return []


# ── Helpers ────────────────────────────────────────────────────────────

def _msp_lookup(market_intel: list[dict]) -> dict[str, int | None]:
    """Build a crop → MSP mapping from market intelligence data."""
    lookup: dict[str, int | None] = {}
    for rec in market_intel:
        crop = rec.get("crop", "")
        msp = rec.get("msp_2025")
        if crop:
            lookup[crop] = msp
            short = crop.split("(")[0].strip()
            if short and short != crop:
                lookup[short] = msp
    return lookup


def _intel_by_crop(market_intel: list[dict]) -> dict[str, dict]:
    """Build crop → full market intel record mapping."""
    result: dict[str, dict] = {}
    for rec in market_intel:
        crop = rec.get("crop", "")
        if crop:
            result[crop] = rec
            short = crop.split("(")[0].strip()
            if short:
                result[short] = rec
    return result


def _match_intel(crop_name: str, intel_map: dict[str, dict]) -> dict | None:
    """Fuzzy-match a mandi crop name to market intelligence."""
    if crop_name in intel_map:
        return intel_map[crop_name]
    crop_lower = crop_name.lower()
    for key, val in intel_map.items():
        if crop_lower in key.lower() or key.lower() in crop_lower:
            return val
    return None


# ── Page ───────────────────────────────────────────────────────────────

def main() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE

    lang = render_sidebar()
    _user = require_auth()
    agent = _get_market_agent()
    market_intel = _load_market_intelligence()
    msp_map = _msp_lookup(market_intel)
    intel_map = _intel_by_crop(market_intel)

    # ── Header ─────────────────────────────────────────────────────────
    render_page_header(
        title=_ui(lang, 'title').replace('💰 ', ''),
        subtitle=_ui(lang, 'subtitle'),
        icon_name='rupee',
    )

    # ── All mandi data ─────────────────────────────────────────────────
    all_prices = agent._data.get("mandi_prices", [])
    all_crops = sorted(set(p.get("crop", "") for p in all_prices if p.get("crop")))
    all_markets = sorted(set(p.get("market", "") for p in all_prices if p.get("market")))

    # ── Summary KPIs ───────────────────────────────────────────────────
    _render_summary_kpis(all_prices, all_crops, all_markets, msp_map, lang)

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_prices, tab_trends, tab_advisor = st.tabs([
        _ui(lang, "tab_prices"),
        _ui(lang, "tab_trends"),
        _ui(lang, "tab_advisor"),
    ])

    with tab_prices:
        _render_price_comparison(agent, all_prices, all_crops, all_markets, msp_map, intel_map, lang)

    with tab_trends:
        _render_price_trends(agent, all_crops, msp_map, intel_map, lang)

    with tab_advisor:
        _render_ai_advisor(agent, all_crops, lang)


# ── Summary KPIs ───────────────────────────────────────────────────────

def _render_summary_kpis(
    all_prices: list[dict],
    all_crops: list[str],
    all_markets: list[str],
    msp_map: dict[str, int | None],
    lang: str,
) -> None:
    """Show top-level metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="🌾 Crops Tracked", value=len(all_crops))
    with col2:
        st.metric(label="🏪 Mandis Covered", value=len(all_markets))
    with col3:
        if all_prices:
            top = max(all_prices, key=lambda p: p.get("price_per_quintal", 0))
            st.metric(
                label="📈 Highest Price",
                value=f"₹{top['price_per_quintal']:,}",
                delta=top.get("crop", ""),
            )
        else:
            st.metric(label="📈 Highest Price", value="—")
    with col4:
        # Count unique crops with non-null MSP (deduplicate short/long names)
        seen: set[int] = set()
        for v in msp_map.values():
            if v is not None:
                seen.add(v)
        st.metric(label="🏛️ MSP Crops", value=len(seen))

    st.divider()


# ── Tab 1: Price Comparison ────────────────────────────────────────────

def _render_price_comparison(
    agent: MarketAgent,
    all_prices: list[dict],
    all_crops: list[str],
    all_markets: list[str],
    msp_map: dict[str, int | None],
    intel_map: dict[str, dict],
    lang: str,
) -> None:
    """Price comparison table with filters and best-mandi recommendation."""

    fcol1, fcol2 = st.columns(2)
    with fcol1:
        selected_crop = st.selectbox(
            _ui(lang, "crop_select"),
            options=[""] + all_crops,
            index=0,
            format_func=lambda x: _ui(lang, "all_crops") if x == "" else x,
            key="price_crop_filter",
        )
    with fcol2:
        selected_market = st.selectbox(
            _ui(lang, "market_filter"),
            options=[""] + all_markets,
            index=0,
            format_func=lambda x: _ui(lang, "all_markets") if x == "" else x,
            key="price_market_filter",
        )

    # ── Filter data ────────────────────────────────────────────────────
    filtered = all_prices
    if selected_crop:
        filtered = [p for p in filtered if p.get("crop") == selected_crop]
    if selected_market:
        filtered = [p for p in filtered if p.get("market") == selected_market]

    if not filtered:
        st.warning(_ui(lang, "no_data"))
        return

    # ── Build table rows ───────────────────────────────────────────────
    table_rows = []
    for p in filtered:
        crop_name = p.get("crop", "")
        price = p.get("price_per_quintal", 0)
        msp = msp_map.get(crop_name)

        if msp and price:
            diff = price - msp
            diff_pct = (diff / msp) * 100
            diff_str = f"✅ +₹{diff:,} (+{diff_pct:.1f}%)" if diff >= 0 else f"⚠️ ₹{diff:,} ({diff_pct:.1f}%)"
        else:
            diff_str = "—"

        table_rows.append({
            _ui(lang, "crop_col"): crop_name,
            _ui(lang, "market_col"): p.get("market", ""),
            _ui(lang, "price_col"): f"₹{price:,}",
            _ui(lang, "msp_col"): f"₹{msp:,}" if msp else "N/A",
            _ui(lang, "diff_col"): diff_str,
            _ui(lang, "date_col"): p.get("date", ""),
        })

    st.subheader(f"📊 {_ui(lang, 'prices_header')}")

    import pandas as pd  # noqa: E402
    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(len(df) * 38 + 40, 600))

    # ── Best Mandi Recommendation ──────────────────────────────────────
    if selected_crop:
        st.subheader(f"🏆 {_ui(lang, 'best_mandi')}")
        best = agent.recommend_best_mandi(selected_crop)
        if best.get("market"):
            bcol1, bcol2, bcol3 = st.columns(3)
            with bcol1:
                st.metric("Best Market", best["market"])
            with bcol2:
                st.metric("Price", f"₹{best.get('price_per_quintal', '?'):,}")
            with bcol3:
                msp = msp_map.get(selected_crop)
                st.metric(_ui(lang, "msp_label"), f"₹{msp:,}" if msp else "N/A")

            intel = _match_intel(selected_crop, intel_map)
            if intel:
                _render_crop_intel(intel, lang)
        else:
            st.info(best.get("recommendation", _ui(lang, "no_data")))


def _render_crop_intel(intel: dict, lang: str) -> None:
    """Show season calendar & storage advisory for a crop."""
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"#### {_ui(lang, 'season_header')}")
        peak = intel.get("peak_arrival_months", [])
        lean = intel.get("lean_months", [])
        trend = intel.get("price_trend", "")

        if peak:
            st.markdown(f"**Peak Arrival:** {', '.join(peak)}")
        if lean:
            st.markdown(f"**Lean Period (Higher Prices):** {', '.join(lean)}")
        if trend:
            st.info(f"📊 **Trend:** {trend}")

    with col_b:
        st.markdown(f"#### {_ui(lang, 'storage_header')}")
        advisory = intel.get("storage_advisory", "")
        if advisory:
            st.markdown(advisory)
        major = intel.get("major_markets", [])
        if major:
            st.markdown(f"**All Markets:** {', '.join(major)}")


# ── Tab 2: Price Trends ───────────────────────────────────────────────

def _render_price_trends(
    agent: MarketAgent,
    all_crops: list[str],
    msp_map: dict[str, int | None],
    intel_map: dict[str, dict],
    lang: str,
) -> None:
    """Show price trend chart and prediction for a selected crop."""

    tcol1, tcol2 = st.columns([1, 3])

    with tcol1:
        crop = st.selectbox(
            _ui(lang, "trend_crop"),
            options=all_crops,
            index=0,
            key="trend_crop_select",
        )

    if not crop:
        return

    trend_data = agent.get_price_trend(crop, days=14)
    if not trend_data:
        st.info(_ui(lang, "no_data"))
        return

    import pandas as pd  # noqa: E402

    df_trend = pd.DataFrame(trend_data)
    df_trend["date"] = pd.to_datetime(df_trend["date"])
    msp = msp_map.get(crop)

    with tcol2:
        st.subheader(f"📈 {crop} — {_ui(lang, 'trend_header')}")

    # ── Plotly chart (with fallback) ───────────────────────────────────
    try:
        import plotly.graph_objects as go  # noqa: E402

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_trend["date"],
            y=df_trend["price"],
            mode="lines+markers",
            name=f"{crop} Price",
            line=dict(color="#2e7d32", width=3),
            marker=dict(size=8),
            hovertemplate="₹%{y:,.0f}<br>%{x|%d %b}<extra></extra>",
        ))

        if msp:
            fig.add_hline(
                y=msp,
                line_dash="dash",
                line_color="#d32f2f",
                annotation_text=f"MSP ₹{msp:,}",
                annotation_position="top left",
            )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (₹/quintal)",
            hovermode="x unified",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.line_chart(df_trend.set_index("date")["price"], height=350)
        if msp:
            st.caption(f"MSP reference: ₹{msp:,} / quintal")

    # ── Prediction ─────────────────────────────────────────────────────
    st.subheader(f"🔮 {_ui(lang, 'predict_header')}")
    pred = agent.predict_price(crop, days_ahead=7)

    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        current_prices = agent.get_current_prices(crop)
        if current_prices:
            current = current_prices[0].get("price_per_quintal", 0)
            st.metric("Current Price", f"₹{current:,}")
        else:
            st.metric("Current Price", "—")
    with pcol2:
        predicted = pred.get("predicted_price", 0)
        st.metric("Predicted (7-day)", f"₹{predicted:,.0f}")
    with pcol3:
        st.metric(_ui(lang, "msp_label"), f"₹{msp:,}" if msp else "N/A")

    st.caption(f"ℹ️ {pred.get('note', '')}")

    # ── Crop intelligence panel ────────────────────────────────────────
    intel = _match_intel(crop, intel_map)
    if intel:
        with st.expander(f"📋 {crop} — Market Intelligence", expanded=False):
            _render_crop_intel(intel, lang)


# ── Tab 3: AI Market Advisor ──────────────────────────────────────────

def _render_ai_advisor(
    agent: MarketAgent,
    all_crops: list[str],
    lang: str,
) -> None:
    """Free-form AI-powered market advice using RAG."""

    st.markdown(f"#### {_ui(lang, 'tab_advisor')}")

    acol1, acol2 = st.columns([1, 3])
    with acol1:
        advisor_crop = st.selectbox(
            _ui(lang, "crop_select"),
            options=[""] + all_crops,
            index=0,
            format_func=lambda x: _ui(lang, "all_crops") if x == "" else x,
            key="advisor_crop_select",
        )
    with acol2:
        query = st.text_area(
            _ui(lang, "advisor_label"),
            placeholder=_ui(lang, "advisor_placeholder"),
            height=100,
            key="advisor_query",
        )

    ask_btn = st.button(
        _ui(lang, "advisor_btn"),
        type="primary",
        use_container_width=True,
        key="btn_advisor",
        disabled=not query,
    )

    if ask_btn and query:
        query_en = query
        if lang != "en":
            query_en = translator.to_english(query, src=lang)

        with st.spinner(_ui(lang, "thinking")):
            start = time.time()
            try:
                result = agent.get_price_summary(
                    crop=advisor_crop or "",
                    query=query_en,
                )
                elapsed = time.time() - start

                summary = result.get("summary", "")
                sources = result.get("sources", [])

                if lang != "en" and summary:
                    summary = translator.from_english(summary, dest=lang)

                st.subheader(f"📋 {_ui(lang, 'summary_header')}")
                st.markdown(summary)

                if sources:
                    src_str = " · ".join(f"`{s}`" for s in sources)
                    st.caption(f"📚 Sources: {src_str}")

                st.caption(f"⏱️ {elapsed:.1f}s")

            except Exception as exc:
                logger.error("Market advisor error: %s", exc, exc_info=True)
                st.error(f"Analysis failed: {exc}")

    elif ask_btn and not query:
        st.warning(_ui(lang, "no_data"))

    # ── Quick question buttons ─────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "What are today's best prices for rice in Telangana?",
            "When is the best time to sell cotton?",
            "Compare mandi prices for turmeric across markets",
            "What government MSP is available for pulses?",
            "Storage tips for onion to get off-season prices",
        ],
        "te": [
            "తెలంగాణలో ఈ రోజు వరి ఉత్తమ ధరలు ఏమిటి?",
            "పత్తి అమ్మడానికి ఉత్తమ సమయం ఎప్పుడు?",
            "మార్కెట్లలో పసుపు మండి ధరలను పోల్చండి",
            "పప్పు ధాన్యాలకు ప్రభుత్వ MSP ఎంత?",
            "సీజన్ బయటి ధరల కోసం ఉల్లి నిల్వ చిట్కాలు",
        ],
        "hi": [
            "तेलंगाना में आज चावल के सर्वोत्तम भाव क्या हैं?",
            "कपास बेचने का सबसे अच्छा समय कब है?",
            "मंडियों में हल्दी के भाव की तुलना करें",
            "दालों के लिए सरकारी MSP कितना है?",
            "सीजन के बाहर भाव पाने के लिए प्याज भंडारण सुझाव",
        ],
    }

    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown("**💡 Quick Questions:**")
    cols = st.columns(len(qs))
    for i, (col, q) in enumerate(zip(cols, qs)):
        with col:
            if st.button(q[:30] + "…" if len(q) > 30 else q, key=f"qq_{i}", use_container_width=True):
                st.session_state["advisor_query"] = q
                st.rerun()


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
