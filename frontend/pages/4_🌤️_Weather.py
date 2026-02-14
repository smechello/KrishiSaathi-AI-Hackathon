"""Weather — Live conditions, 5-day forecast & AI crop advisory.

Real-time weather for Telangana districts/cities via OpenWeatherMap,
plus AI-powered crop-specific farming advice powered by RAG.
"""

from __future__ import annotations

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
from backend.agents.weather_agent import WeatherAgent  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header, icon, get_theme, get_palette  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Weather", page_icon="🌤️", layout="wide")

# ── Telangana cities ───────────────────────────────────────────────────
TELANGANA_CITIES: list[str] = [
    "Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam",
    "Mahbubnagar", "Nalgonda", "Adilabad", "Medak", "Rangareddy",
    "Suryapet", "Siddipet", "Jagtiyal", "Kamareddy", "Mancherial",
    "Nirmal", "Sangareddy", "Vikarabad", "Wanaparthy", "Yadadri",
    "Bhadradri Kothagudem", "Jangaon", "Medchal", "Peddapalli",
]

TELANGANA_CROPS: list[str] = [
    "Rice", "Cotton", "Maize", "Soybean", "Chilli",
    "Turmeric", "Groundnut", "Jowar", "Sugarcane", "Red Gram",
    "Bengal Gram", "Sunflower", "Sesame", "Castor", "Mango",
    "Orange", "Banana", "Tomato", "Onion", "Brinjal",
]

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "🌤️ Weather & Crop Advisory",
        "subtitle": "Live weather, forecasts & AI-powered farming advice for Telangana",
        "tab_current": "🌡️ Current Weather",
        "tab_forecast": "📈 5-Day Forecast",
        "tab_advisory": "🌾 Crop Advisory",
        "city_label": "Select City / District",
        "fetch_btn": "🔍 Get Weather",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "wind": "Wind Speed",
        "condition": "Condition",
        "spray_ok": "✅ Conditions suitable for spraying",
        "spray_no": "❌ NOT suitable for spraying",
        "spray_reason": "Reason",
        "forecast_header": "5-Day Weather Forecast",
        "advisory_header": "AI Crop Advisory",
        "crop_label": "Select Crop",
        "get_advisory_btn": "🌾 Get Crop Advisory",
        "advisory_thinking": "Analyzing weather impact on your crop …",
        "no_weather": "Please fetch weather first using the Current Weather tab.",
        "fetch_err": "Could not fetch weather data. Please check the city name.",
        "temp_chart": "Temperature Trend (°C)",
        "humidity_chart": "Humidity Trend (%)",
        "quick_check": "Quick Conditions Check",
    },
    "te": {
        "title": "🌤️ వాతావరణం & పంట సలహా",
        "subtitle": "తెలంగాణ కోసం ప్రత్యక్ష వాతావరణం, అంచనాలు & AI వ్యవసాయ సలహా",
        "tab_current": "🌡️ ప్రస్తుత వాతావరణం",
        "tab_forecast": "📈 5-రోజుల అంచనా",
        "tab_advisory": "🌾 పంట సలహా",
        "city_label": "నగరం / జిల్లా ఎంచుకోండి",
        "fetch_btn": "🔍 వాతావరణం చూడండి",
        "temperature": "ఉష్ణోగ్రత",
        "humidity": "తేమ",
        "wind": "గాలి వేగం",
        "condition": "పరిస్థితి",
        "spray_ok": "✅ స్ప్రే చేయడానికి అనుకూలం",
        "spray_no": "❌ స్ప్రే చేయడానికి అనుకూలం కాదు",
        "spray_reason": "కారణం",
        "forecast_header": "5-రోజుల వాతావరణ అంచనా",
        "advisory_header": "AI పంట సలహా",
        "crop_label": "పంట ఎంచుకోండి",
        "get_advisory_btn": "🌾 పంట సలహా పొందండి",
        "advisory_thinking": "మీ పంటపై వాతావరణ ప్రభావం విశ్లేషిస్తోంది …",
        "no_weather": "దయచేసి ముందు ప్రస్తుత వాతావరణం ట్యాబ్‌లో వాతావరణం చూడండి.",
        "fetch_err": "వాతావరణ డేటా పొందలేకపోయాం. నగరం పేరు తనిఖీ చేయండి.",
        "temp_chart": "ఉష్ణోగ్రత ధోరణి (°C)",
        "humidity_chart": "తేమ ధోరణి (%)",
        "quick_check": "త్వరిత పరిస్థితి తనిఖీ",
    },
    "hi": {
        "title": "🌤️ मौसम व फसल सलाह",
        "subtitle": "तेलंगाना के लिए लाइव मौसम, पूर्वानुमान व AI कृषि सलाह",
        "tab_current": "🌡️ वर्तमान मौसम",
        "tab_forecast": "📈 5-दिन पूर्वानुमान",
        "tab_advisory": "🌾 फसल सलाह",
        "city_label": "शहर / जिला चुनें",
        "fetch_btn": "🔍 मौसम देखें",
        "temperature": "तापमान",
        "humidity": "नमी",
        "wind": "हवा की गति",
        "condition": "स्थिति",
        "spray_ok": "✅ छिड़काव के लिए उपयुक्त",
        "spray_no": "❌ छिड़काव के लिए उपयुक्त नहीं",
        "spray_reason": "कारण",
        "forecast_header": "5-दिन मौसम पूर्वानुमान",
        "advisory_header": "AI फसल सलाह",
        "crop_label": "फसल चुनें",
        "get_advisory_btn": "🌾 फसल सलाह पाएं",
        "advisory_thinking": "आपकी फसल पर मौसम प्रभाव का विश्लेषण …",
        "no_weather": "कृपया पहले वर्तमान मौसम टैब में मौसम देखें।",
        "fetch_err": "मौसम डेटा प्राप्त नहीं हो सका। शहर का नाम जांचें।",
        "temp_chart": "तापमान प्रवृत्ति (°C)",
        "humidity_chart": "नमी प्रवृत्ति (%)",
        "quick_check": "त्वरित स्थिति जांच",
    },
}


def _ui(lang: str, key: str) -> str:
    return _UI.get(lang, _UI["en"]).get(key, _UI["en"][key])


# ── Cached resources ───────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading weather engine …")
def _get_weather_agent() -> WeatherAgent:
    try:
        rag = RAGEngine()
    except Exception:
        rag = None  # type: ignore[assignment]
    return WeatherAgent(rag_engine=rag)


# ── Weather icon helper ───────────────────────────────────────────────

_WEATHER_ICONS: dict[str, str] = {
    "clear": "☀️", "clouds": "☁️", "rain": "🌧️", "drizzle": "🌦️",
    "thunderstorm": "⛈️", "snow": "❄️", "mist": "🌫️", "haze": "🌫️",
    "fog": "🌫️", "smoke": "🌫️", "dust": "🌪️", "tornado": "🌪️",
}


def _icon(description: str) -> str:
    d = description.lower()
    for k, v in _WEATHER_ICONS.items():
        if k in d:
            return v
    return "🌤️"


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE

    lang = render_sidebar()
    _user = require_auth()
    agent = _get_weather_agent()

    # ── Header ─────────────────────────────────────────────────────────
    render_page_header(
        title=_ui(lang, 'title').replace('🌤️ ', ''),
        subtitle=_ui(lang, 'subtitle'),
        icon_name='weather',
    )

    # ── City selector at top ───────────────────────────────────────────
    ccol1, ccol2 = st.columns([2, 1])
    with ccol1:
        city = st.selectbox(
            _ui(lang, "city_label"),
            options=TELANGANA_CITIES,
            index=0,
            key="weather_city",
        )
    with ccol2:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch = st.button(_ui(lang, "fetch_btn"), type="primary", use_container_width=True, key="btn_fetch_weather")

    # ── Fetch weather ──────────────────────────────────────────────────
    if fetch:
        try:
            with st.spinner("Fetching live weather …"):
                current = agent.get_current_weather(city)
                forecast_data = agent.get_forecast(city, days=5)
                spray = agent.check_spray_conditions(current)
            st.session_state["weather_current"] = current
            st.session_state["weather_forecast"] = forecast_data
            st.session_state["weather_spray"] = spray
            st.session_state["weather_city_name"] = city
        except Exception as exc:
            logger.error("Weather fetch error: %s", exc, exc_info=True)
            st.error(_ui(lang, "fetch_err"))

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_current, tab_forecast, tab_advisory = st.tabs([
        _ui(lang, "tab_current"),
        _ui(lang, "tab_forecast"),
        _ui(lang, "tab_advisory"),
    ])

    with tab_current:
        _render_current(lang)

    with tab_forecast:
        _render_forecast(lang)

    with tab_advisory:
        _render_advisory(agent, lang)


# ── Tab 1: Current Weather ────────────────────────────────────────────

def _render_current(lang: str) -> None:
    current: dict | None = st.session_state.get("weather_current")
    if not current:
        st.info(_ui(lang, "no_weather"))
        return

    city_name = st.session_state.get("weather_city_name", "")
    desc = current.get("description", "Clear")
    wicon = _icon(desc)

    # ── Big weather display ────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="ks-hero">
            <h2>{wicon} {city_name}</h2>
            <h1 style="margin:0; font-size:3.5rem;">{current.get('temperature_c', '--')}°C</h1>
            <p style="font-size:1.2rem; margin:0;">{desc.title()}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric(f"🌡️ {_ui(lang, 'temperature')}", f"{current.get('temperature_c', '--')}°C")
    with mc2:
        st.metric(f"💧 {_ui(lang, 'humidity')}", f"{current.get('humidity', '--')}%")
    with mc3:
        st.metric(f"💨 {_ui(lang, 'wind')}", f"{current.get('wind_speed', '--')} km/h")
    with mc4:
        st.metric(f"🌤️ {_ui(lang, 'condition')}", desc.title())

    # ── Spray check ────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"🧪 {_ui(lang, 'quick_check')}")

    spray: dict | None = st.session_state.get("weather_spray")
    if spray:
        can_spray = spray.get("spray", False)
        reason = spray.get("reason", "")

        if can_spray:
            st.success(_ui(lang, "spray_ok"))
        else:
            st.error(_ui(lang, "spray_no"))

        if reason:
            st.info(f"**{_ui(lang, 'spray_reason')}:** {reason}")

    # ── Quick advisories (rule-based) ──────────────────────────────────
    temp = current.get("temperature_c", 25)
    hum = current.get("humidity", 50)
    wind = current.get("wind_speed", 0)

    alerts = []
    if isinstance(temp, (int, float)):
        if temp >= 40:
            alerts.append("🔥 **Extreme Heat**: Irrigate crops twice daily. Provide shade to nurseries.")
        elif temp >= 35:
            alerts.append("🌡️ **High Temperature**: Increase irrigation frequency. Mulch around plants.")
        elif temp <= 5:
            alerts.append("❄️ **Frost Risk**: Cover sensitive crops. Avoid irrigation in evening.")
    if isinstance(hum, (int, float)):
        if hum >= 85:
            alerts.append("🍄 **High Humidity**: Watch for fungal diseases. Apply preventive fungicide.")
        elif hum <= 30:
            alerts.append("🏜️ **Very Dry**: Increase irrigation. Watch for spider mites.")
    if isinstance(wind, (int, float)) and wind >= 30:
        alerts.append("💨 **Strong Winds**: Stake tall crops. Delay spraying operations.")

    if alerts:
        st.markdown("---")
        st.markdown("**⚠️ Weather Alerts:**")
        for a in alerts:
            st.markdown(a)


# ── Tab 2: 5-Day Forecast ─────────────────────────────────────────────

def _render_forecast(lang: str) -> None:
    forecast: list[dict] | None = st.session_state.get("weather_forecast")
    if not forecast:
        st.info(_ui(lang, "no_weather"))
        return

    city_name = st.session_state.get("weather_city_name", "")
    st.subheader(f"📈 {_ui(lang, 'forecast_header')} — {city_name}")

    # ── Forecast cards ─────────────────────────────────────────────────
    cols = st.columns(min(len(forecast), 5))
    pal = get_palette(get_theme())
    for i, (col, day) in enumerate(zip(cols, forecast[:5])):
        date_str = day.get("date", f"Day {i+1}")
        temp = day.get("temp_c", day.get("temperature_c", "--"))
        hum = day.get("humidity", "--")
        desc = day.get("description", "Clear")
        wicon = _icon(desc)

        with col:
            st.markdown(
                f"""
                <div class="ks-card" style="text-align:center; padding:0.8rem;">
                    <b>{date_str}</b><br>
                    <span style="font-size:2rem;">{wicon}</span><br>
                    <span style="font-size:1.5rem; color:{pal['primary']};">{temp}°C</span><br>
                    <span style="color:{pal['text_muted']};">💧 {hum}%</span><br>
                    <span style="color:{pal['text_muted']}; font-size:0.85rem;">{desc.title()}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Plotly charts ──────────────────────────────────────────────────
    dates = [d.get("date", f"Day {i+1}") for i, d in enumerate(forecast[:5])]
    temps = [d.get("temp_c", d.get("temperature_c", 0)) for d in forecast[:5]]
    hums = [d.get("humidity", 0) for d in forecast[:5]]

    ch1, ch2 = st.columns(2)

    with ch1:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=dates, y=temps, mode="lines+markers",
            line=dict(color="#e65100", width=3),
            marker=dict(size=10, color="#e65100"),
            name="Temp °C",
        ))
        fig_temp.update_layout(
            title=_ui(lang, "temp_chart"),
            yaxis_title="°C",
            template="plotly_white",
            height=300,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with ch2:
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Bar(
            x=dates, y=hums,
            marker_color="#1976d2",
            name="Humidity %",
        ))
        fig_hum.update_layout(
            title=_ui(lang, "humidity_chart"),
            yaxis_title="%",
            template="plotly_white",
            height=300,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_hum, use_container_width=True)


# ── Tab 3: AI Crop Advisory ───────────────────────────────────────────

def _render_advisory(agent: WeatherAgent, lang: str) -> None:
    st.subheader(f"🌾 {_ui(lang, 'advisory_header')}")

    current: dict | None = st.session_state.get("weather_current")
    city_name = st.session_state.get("weather_city_name", "Hyderabad")

    acol1, acol2 = st.columns([2, 1])
    with acol1:
        crop = st.selectbox(
            _ui(lang, "crop_label"),
            options=TELANGANA_CROPS,
            index=0,
            key="advisory_crop",
        )
    with acol2:
        st.markdown("<br>", unsafe_allow_html=True)
        adv_btn = st.button(
            _ui(lang, "get_advisory_btn"),
            type="primary",
            use_container_width=True,
            key="btn_crop_advisory",
        )

    if adv_btn:
        with st.spinner(_ui(lang, "advisory_thinking")):
            start = time.time()
            try:
                result = agent.get_weather_advisory(city=city_name, crop=crop)
                elapsed = time.time() - start

                advisory = result.get("advisory", "")
                weather_data = result.get("weather", {})
                sources = result.get("sources", [])

                if lang != "en" and advisory:
                    advisory = translator.from_english(advisory, dest=lang)

                # Weather summary on top
                if weather_data:
                    wtemp = weather_data.get("temperature_c", "--")
                    whum = weather_data.get("humidity", "--")
                    wdesc = weather_data.get("description", "")
                    st.info(f"📍 **{city_name}** — {_icon(wdesc)} {wdesc.title()} | 🌡️ {wtemp}°C | 💧 {whum}%")

                st.markdown(advisory)

                if sources:
                    src_str = " · ".join(f"`{s}`" for s in sources)
                    st.caption(f"📚 Sources: {src_str}")
                st.caption(f"⏱️ {elapsed:.1f}s")

            except Exception as exc:
                logger.error("Crop advisory error: %s", exc, exc_info=True)
                st.error(f"Advisory failed: {exc}")

    # ── Quick crop advisories ──────────────────────────────────────────
    if current:
        st.divider()
        st.markdown("**🌾 Quick Rule-Based Advice:**")
        for crop_name in ["Rice", "Cotton", "Chilli"]:
            try:
                advice = agent.get_crop_advisory(crop_name, current)
                if advice:
                    with st.expander(f"🌱 {crop_name}", expanded=False):
                        if isinstance(advice, dict):
                            for k, v in advice.items():
                                st.markdown(f"- **{k}:** {v}")
                        elif isinstance(advice, list):
                            for a in advice:
                                st.markdown(f"- {a}")
                        else:
                            st.markdown(str(advice))
            except Exception:
                pass


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
