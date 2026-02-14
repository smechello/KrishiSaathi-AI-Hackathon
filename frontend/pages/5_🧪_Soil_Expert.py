"""Soil Expert — Analyse soil, get fertilizer plans & crop rotation advice.

Browse Telangana soil types with Telugu names, calculate fertilizer doses,
explore organic alternatives, and get AI-powered soil health insights.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402
from backend.agents.soil_agent import SoilAgent  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header, icon, get_theme, get_palette  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Soil Expert", page_icon="🧪", layout="wide")

# ── Telangana crops for fertilizer calc ────────────────────────────────
CROPS: list[str] = [
    "Rice", "Cotton", "Maize", "Soybean", "Chilli",
    "Turmeric", "Groundnut", "Jowar", "Sugarcane", "Red Gram",
    "Bengal Gram", "Sunflower", "Sesame", "Castor", "Tomato",
    "Onion", "Brinjal", "Watermelon", "Mango", "Orange",
]

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "🧪 Soil Expert",
        "subtitle": "Telangana soil analysis, fertilizer calculator & AI soil health advisor",
        "tab_analyzer": "🔬 Soil Analyzer",
        "tab_fertilizer": "🧮 Fertilizer Calculator",
        "tab_rotation": "🔄 Crop Rotation",
        "tab_advisor": "🤖 AI Soil Advisor",
        "soil_label": "Select Soil Type",
        "analyze_btn": "🔬 Analyze Soil",
        "characteristics": "Soil Characteristics",
        "suitable_crops": "Suitable Crops",
        "regions": "Telangana Regions",
        "nutrient_profile": "Nutrient Profile",
        "management_tips": "Management Tips",
        "ph": "pH Range",
        "texture": "Texture",
        "drainage": "Drainage",
        "moisture": "Moisture Retention",
        "organic_matter": "Organic Matter",
        "crop_label": "Select Crop",
        "land_label": "Land Size (Acres)",
        "calc_btn": "🧮 Calculate Fertilizer",
        "fert_header": "Fertilizer Recommendation",
        "organic_header": "Organic Alternatives",
        "cost_estimate": "Estimated Cost",
        "rotation_header": "Crop Rotation Plan",
        "rotation_crop_label": "Current Crop",
        "rotation_btn": "🔄 Get Rotation Plan",
        "advisor_label": "Ask about soil health, nutrients, or management …",
        "advisor_placeholder": "e.g. 'How to improve black cotton soil fertility?' or 'Best fertilizer for rice in red soil?'",
        "advisor_btn": "🤖 Get Soil Advice",
        "thinking": "Analyzing soil data …",
        "summary_header": "Soil Analysis",
    },
    "te": {
        "title": "🧪 మట్టి నిపుణుడు",
        "subtitle": "తెలంగాణ మట్టి విశ్లేషణ, ఎరువుల లెక్కింపు & AI మట్టి ఆరోగ్య సలహా",
        "tab_analyzer": "🔬 మట్టి విశ్లేషణ",
        "tab_fertilizer": "🧮 ఎరువుల లెక్కింపు",
        "tab_rotation": "🔄 పంట మార్పిడి",
        "tab_advisor": "🤖 AI మట్టి సలహాదారు",
        "soil_label": "మట్టి రకం ఎంచుకోండి",
        "analyze_btn": "🔬 మట్టి విశ్లేషించండి",
        "characteristics": "మట్టి లక్షణాలు",
        "suitable_crops": "అనుకూల పంటలు",
        "regions": "తెలంగాణ ప్రాంతాలు",
        "nutrient_profile": "పోషక ప్రొఫైల్",
        "management_tips": "నిర్వహణ చిట్కాలు",
        "ph": "pH పరిధి",
        "texture": "ఆకృతి",
        "drainage": "నీరు బయటకు పోవడం",
        "moisture": "తేమ నిల్వ",
        "organic_matter": "సేంద్రియ పదార్థం",
        "crop_label": "పంట ఎంచుకోండి",
        "land_label": "భూమి విస్తీర్ణం (ఎకరాలు)",
        "calc_btn": "🧮 ఎరువులు లెక్కించండి",
        "fert_header": "ఎరువుల సిఫారసు",
        "organic_header": "సేంద్రియ ప్రత్యామ్నాయాలు",
        "cost_estimate": "అంచనా ఖర్చు",
        "rotation_header": "పంట మార్పిడి ప్రణాళిక",
        "rotation_crop_label": "ప్రస్తుత పంట",
        "rotation_btn": "🔄 మార్పిడి ప్రణాళిక పొందండి",
        "advisor_label": "మట్టి ఆరోగ్యం, పోషకాలు లేదా నిర్వహణ గురించి అడగండి …",
        "advisor_placeholder": "ఉదా. 'నల్ల రేగడి మట్టి సారాన్ని ఎలా పెంచాలి?'",
        "advisor_btn": "🤖 మట్టి సలహా పొందండి",
        "thinking": "మట్టి డేటా విశ్లేషిస్తోంది …",
        "summary_header": "మట్టి విశ్లేషణ",
    },
    "hi": {
        "title": "🧪 मिट्टी विशेषज्ञ",
        "subtitle": "तेलंगाना मिट्टी विश्लेषण, उर्वरक कैलकुलेटर व AI मिट्टी स्वास्थ्य सलाह",
        "tab_analyzer": "🔬 मिट्टी विश्लेषण",
        "tab_fertilizer": "🧮 उर्वरक कैलकुलेटर",
        "tab_rotation": "🔄 फसल चक्र",
        "tab_advisor": "🤖 AI मिट्टी सलाहकार",
        "soil_label": "मिट्टी प्रकार चुनें",
        "analyze_btn": "🔬 मिट्टी विश्लेषण करें",
        "characteristics": "मिट्टी विशेषताएं",
        "suitable_crops": "उपयुक्त फसलें",
        "regions": "तेलंगाना क्षेत्र",
        "nutrient_profile": "पोषक तत्व प्रोफाइल",
        "management_tips": "प्रबंधन सुझाव",
        "ph": "pH सीमा",
        "texture": "बनावट",
        "drainage": "जल निकासी",
        "moisture": "नमी धारण",
        "organic_matter": "कार्बनिक पदार्थ",
        "crop_label": "फसल चुनें",
        "land_label": "भूमि (एकड़)",
        "calc_btn": "🧮 उर्वरक गणना करें",
        "fert_header": "उर्वरक सिफारिश",
        "organic_header": "जैविक विकल्प",
        "cost_estimate": "अनुमानित लागत",
        "rotation_header": "फसल चक्र योजना",
        "rotation_crop_label": "वर्तमान फसल",
        "rotation_btn": "🔄 चक्र योजना पाएं",
        "advisor_label": "मिट्टी स्वास्थ्य, पोषक तत्वों या प्रबंधन के बारे में पूछें …",
        "advisor_placeholder": "जैसे 'काली कपास मिट्टी की उर्वरता कैसे बढ़ाएं?'",
        "advisor_btn": "🤖 मिट्टी सलाह पाएं",
        "thinking": "मिट्टी डेटा का विश्लेषण …",
        "summary_header": "मिट्टी विश्लेषण",
    },
}


def _ui(lang: str, key: str) -> str:
    return _UI.get(lang, _UI["en"]).get(key, _UI["en"][key])


# ── Cached resources ───────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading soil engine …")
def _get_soil_agent() -> SoilAgent:
    try:
        rag = RAGEngine()
    except Exception:
        rag = None  # type: ignore[assignment]
    return SoilAgent(rag_engine=rag)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_soil_database() -> list[dict]:
    """Load the full soil_data.json."""
    path = os.path.join(_PROJECT_ROOT, "backend", "knowledge_base", "documents", "soil_data.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return raw.get("soils", raw.get("soil_types", raw)) if isinstance(raw, dict) else raw
    except Exception:
        return []


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE

    lang = render_sidebar()
    _user = require_auth()
    agent = _get_soil_agent()
    soils = _load_soil_database()

    # ── Header ─────────────────────────────────────────────────────────
    render_page_header(
        title=_ui(lang, 'title').replace('🧪 ', ''),
        subtitle=_ui(lang, 'subtitle'),
        icon_name='soil',
    )

    # ── Summary KPIs ───────────────────────────────────────────────────
    all_crops: set[str] = set()
    for s in soils:
        for c in s.get("suitable_crops", []):
            all_crops.add(c)

    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        st.metric("🧪 Soil Types", len(soils))
    with kc2:
        st.metric("🌾 Crops Covered", len(all_crops))
    with kc3:
        st.metric("📍 Telangana Focus", "All 33 Districts")
    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_analyzer, tab_fert, tab_rotation, tab_advisor = st.tabs([
        _ui(lang, "tab_analyzer"),
        _ui(lang, "tab_fertilizer"),
        _ui(lang, "tab_rotation"),
        _ui(lang, "tab_advisor"),
    ])

    with tab_analyzer:
        _render_analyzer(soils, agent, lang)

    with tab_fert:
        _render_fertilizer(agent, lang)

    with tab_rotation:
        _render_rotation(agent, lang)

    with tab_advisor:
        _render_advisor(agent, lang)


# ── Tab 1: Soil Analyzer ──────────────────────────────────────────────

def _render_analyzer(soils: list[dict], agent: SoilAgent, lang: str) -> None:
    """Browse Telangana soil types with full details."""

    # Build dropdown options with Telugu names
    options = []
    soil_map: dict[str, dict] = {}
    for s in soils:
        name = s.get("type", s.get("name", "Unknown"))
        local = s.get("local_name", "")
        label = f"{name}  ({local})" if local else name
        options.append(label)
        soil_map[label] = s

    if not options:
        st.warning("No soil data available.")
        return

    selected = st.selectbox(
        _ui(lang, "soil_label"),
        options=options,
        index=0,
        key="soil_type_select",
    )

    soil = soil_map.get(selected, {})
    if not soil:
        return

    name = soil.get("type", soil.get("name", ""))
    local_name = soil.get("local_name", "")
    desc = soil.get("description", "")
    chars = soil.get("characteristics", {})
    nutrients = soil.get("nutrient_profile", {})
    crops = soil.get("suitable_crops", [])
    regions = soil.get("regions", [])
    tips = soil.get("management_tips", [])

    # ── Header card ────────────────────────────────────────────────────
    soil_icon = icon("soil", size=24, color=get_palette(get_theme())["primary"])
    st.markdown(
        f"""
        <div class="ks-hero">
            <h2>{soil_icon} {name}</h2>
            <p style="font-size:1.1rem; margin:0.3rem 0;">
                Telugu: <b>{local_name}</b></p>
            <p>{desc}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        # Characteristics
        st.markdown(f"#### 📊 {_ui(lang, 'characteristics')}")
        if isinstance(chars, dict):
            for k, v in chars.items():
                label = k.replace("_", " ").title()
                ui_key = k.lower().replace(" ", "_")
                display = _ui(lang, ui_key) if ui_key in _UI.get(lang, {}) else label
                st.markdown(f"- **{display}:** {v}")
        st.markdown("")

        # Suitable crops
        st.markdown(f"#### 🌾 {_ui(lang, 'suitable_crops')}")
        if crops:
            st.markdown(", ".join(f"**{c}**" for c in crops))

        # Regions
        st.markdown(f"#### 📍 {_ui(lang, 'regions')}")
        if regions:
            st.markdown(", ".join(regions))

    with col2:
        # Nutrient profile chart
        st.markdown(f"#### 🧬 {_ui(lang, 'nutrient_profile')}")
        if isinstance(nutrients, dict) and nutrients:
            _render_nutrient_chart(nutrients, name)

        # Management tips
        st.markdown(f"#### 💡 {_ui(lang, 'management_tips')}")
        if tips:
            for tip in tips:
                st.markdown(f"- {tip}")


def _render_nutrient_chart(nutrients: dict, soil_name: str) -> None:
    """Radar chart for soil nutrient profile."""
    level_map = {"high": 3, "medium": 2, "low": 1, "very low": 0.5, "very high": 3.5}

    labels = []
    values = []
    for k, v in nutrients.items():
        labels.append(k.upper())
        if isinstance(v, (int, float)):
            values.append(v)
        else:
            values.append(level_map.get(str(v).lower(), 2))

    if not labels:
        return

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(76,175,80,0.3)",
        line=dict(color="#2e7d32", width=2),
        name=soil_name,
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3], ticktext=["Low", "Med", "High"]),
        ),
        showlegend=False,
        height=300,
        margin=dict(l=40, r=40, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Tab 2: Fertilizer Calculator ──────────────────────────────────────

def _render_fertilizer(agent: SoilAgent, lang: str) -> None:
    """Crop-wise fertilizer recommendation with cost."""

    st.subheader(f"🧮 {_ui(lang, 'fert_header')}")

    fc1, fc2 = st.columns(2)
    with fc1:
        crop = st.selectbox(
            _ui(lang, "crop_label"),
            options=CROPS,
            index=0,
            key="fert_crop",
        )
    with fc2:
        land = st.number_input(
            _ui(lang, "land_label"),
            min_value=0.5, max_value=500.0, value=2.0, step=0.5,
            key="fert_land",
        )

    calc_btn = st.button(
        _ui(lang, "calc_btn"),
        type="primary",
        use_container_width=True,
        key="btn_calc_fert",
    )

    if calc_btn:
        with st.spinner(_ui(lang, "thinking")):
            try:
                fert = agent.get_fertilizer_recommendation(crop, land)
                organic = agent.get_organic_alternatives(crop)
            except Exception as exc:
                logger.error("Fertilizer calc error: %s", exc, exc_info=True)
                st.error(f"Calculation failed: {exc}")
                return

        # ── Chemical fertilizers ───────────────────────────────────────
        st.markdown(f"### 🧪 {_ui(lang, 'fert_header')} — {crop} ({land} acres)")

        if isinstance(fert, dict):
            # NPK values
            npk = fert.get("npk", {})
            products = fert.get("products", fert.get("fertilizers", {}))
            total_cost = fert.get("total_cost", fert.get("estimated_cost", 0))

            if npk:
                nc1, nc2, nc3 = st.columns(3)
                with nc1:
                    st.metric("🟢 Nitrogen (N)", f"{npk.get('N', npk.get('n', '--'))} kg")
                with nc2:
                    st.metric("🔵 Phosphorus (P)", f"{npk.get('P', npk.get('p', '--'))} kg")
                with nc3:
                    st.metric("🟠 Potassium (K)", f"{npk.get('K', npk.get('k', '--'))} kg")

            if isinstance(products, dict):
                st.markdown("#### 📦 Products Required:")
                prod_cols = st.columns(min(len(products), 4)) if products else []
                for i, (prod_name, details) in enumerate(products.items()):
                    with prod_cols[i % len(prod_cols)] if prod_cols else st.container():
                        if isinstance(details, dict):
                            qty = details.get("quantity", details.get("qty", "--"))
                            cost = details.get("cost", "--")
                            _pal = get_palette(get_theme())
                            st.markdown(
                                f"""
                                <div class="ks-card" style="text-align:center; padding:0.8rem; margin:0.3rem 0;">
                                    <b>{prod_name}</b><br>
                                    <span style="font-size:1.3rem; color:{_pal['primary']};">{qty}</span><br>
                                    <span style="color:{_pal['text_muted']};">₹{cost}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(f"- **{prod_name}:** {details}")
            elif isinstance(products, list):
                for p in products:
                    st.markdown(f"- {p}")

            if total_cost:
                st.success(f"💰 **{_ui(lang, 'cost_estimate')}:** ₹{total_cost:,.0f} for {land} acres")

        elif isinstance(fert, str):
            st.markdown(fert)

        # ── Organic alternatives ───────────────────────────────────────
        st.divider()
        st.markdown(f"### 🌿 {_ui(lang, 'organic_header')}")

        if isinstance(organic, dict):
            for org_name, org_details in organic.items():
                with st.expander(f"🌱 {org_name}", expanded=False):
                    if isinstance(org_details, dict):
                        for k, v in org_details.items():
                            st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                    else:
                        st.markdown(str(org_details))
        elif isinstance(organic, list):
            for item in organic:
                if isinstance(item, dict):
                    name = item.get("name", "Alternative")
                    with st.expander(f"🌱 {name}", expanded=False):
                        for k, v in item.items():
                            if k != "name":
                                st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                else:
                    st.markdown(f"- {item}")
        elif isinstance(organic, str):
            st.markdown(organic)


# ── Tab 3: Crop Rotation ──────────────────────────────────────────────

def _render_rotation(agent: SoilAgent, lang: str) -> None:
    """Suggest crop rotation plans."""

    st.subheader(f"🔄 {_ui(lang, 'rotation_header')}")

    rotation_crops = ["Rice", "Cotton", "Maize", "Chilli", "Soybean", "Red Gram", "Groundnut", "Turmeric"]

    rcol1, rcol2 = st.columns([2, 1])
    with rcol1:
        crop = st.selectbox(
            _ui(lang, "rotation_crop_label"),
            options=rotation_crops,
            index=0,
            key="rotation_crop",
        )
    with rcol2:
        st.markdown("<br>", unsafe_allow_html=True)
        rot_btn = st.button(
            _ui(lang, "rotation_btn"),
            type="primary",
            use_container_width=True,
            key="btn_rotation",
        )

    if rot_btn:
        with st.spinner(_ui(lang, "thinking")):
            try:
                rotation = agent.suggest_crop_rotation(crop)
            except Exception as exc:
                logger.error("Rotation error: %s", exc, exc_info=True)
                st.error(f"Rotation plan failed: {exc}")
                return

        st.markdown(f"### 🔄 Rotation Plan for **{crop}**")

        if isinstance(rotation, dict):
            for year_key, details in rotation.items():
                yr_label = year_key.replace("_", " ").title()
                with st.expander(f"📅 {yr_label}", expanded=True):
                    if isinstance(details, dict):
                        for k, v in details.items():
                            st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                    elif isinstance(details, list):
                        for d in details:
                            st.markdown(f"- {d}")
                    else:
                        st.markdown(str(details))
        elif isinstance(rotation, list):
            for i, item in enumerate(rotation):
                with st.expander(f"📅 Year {i+1}", expanded=True):
                    if isinstance(item, dict):
                        for k, v in item.items():
                            st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                    else:
                        st.markdown(str(item))
        elif isinstance(rotation, str):
            st.markdown(rotation)
        else:
            st.markdown(str(rotation))


# ── Tab 4: AI Soil Advisor ────────────────────────────────────────────

def _render_advisor(agent: SoilAgent, lang: str) -> None:
    """Free-form AI-powered soil advice."""

    st.markdown(f"#### {_ui(lang, 'tab_advisor')}")

    # Pick up deferred quick-question if any
    _default_q = st.session_state.pop("_soil_quick_q", "")

    query = st.text_area(
        _ui(lang, "advisor_label"),
        value=_default_q,
        placeholder=_ui(lang, "advisor_placeholder"),
        height=100,
        key="soil_advisor_query",
    )

    ask_btn = st.button(
        _ui(lang, "advisor_btn"),
        type="primary",
        use_container_width=True,
        key="btn_soil_advisor",
        disabled=not query,
    )

    if ask_btn and query:
        query_en = query
        if lang != "en":
            query_en = translator.to_english(query, src=lang)

        with st.spinner(_ui(lang, "thinking")):
            start = time.time()
            try:
                result = agent.answer_soil_query(query_en)
                elapsed = time.time() - start

                answer = result.get("answer", "")
                sources = result.get("sources", [])

                if lang != "en" and answer:
                    answer = translator.from_english(answer, dest=lang)

                st.subheader(f"🧪 {_ui(lang, 'summary_header')}")
                st.markdown(answer)

                if sources:
                    src_str = " · ".join(f"`{s}`" for s in sources)
                    st.caption(f"📚 Sources: {src_str}")
                st.caption(f"⏱️ {elapsed:.1f}s")

            except Exception as exc:
                logger.error("Soil advisor error: %s", exc, exc_info=True)
                st.error(f"Query failed: {exc}")

    # ── Quick questions ────────────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "How to improve black cotton soil?",
            "Best fertilizer for rice in red soil?",
            "How to reduce soil salinity?",
            "Organic farming in laterite soil",
            "Soil health card benefits",
        ],
        "te": [
            "నల్ల రేగడి మట్టిని ఎలా మెరుగుపరచాలి?",
            "ఎర్ర మట్టిలో వరికి ఉత్తమ ఎరువు?",
            "మట్టి లవణీయతను ఎలా తగ్గించాలి?",
            "లేటరైట్ మట్టిలో సేంద్రియ వ్యవసాయం",
            "మట్టి ఆరోగ్య కార్డు ప్రయోజనాలు",
        ],
        "hi": [
            "काली कपास मिट्टी कैसे सुधारें?",
            "लाल मिट्टी में चावल के लिए सबसे अच्छा उर्वरक?",
            "मिट्टी की लवणता कैसे कम करें?",
            "लैटेराइट मिट्टी में जैविक खेती",
            "मिट्टी स्वास्थ्य कार्ड के लाभ",
        ],
    }

    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown("**💡 Quick Questions:**")
    cols = st.columns(len(qs))
    for i, (col, q) in enumerate(zip(cols, qs)):
        with col:
            if st.button(q[:28] + "…" if len(q) > 28 else q, key=f"soilq_{i}", use_container_width=True):
                st.session_state["_soil_quick_q"] = q
                st.rerun()


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
