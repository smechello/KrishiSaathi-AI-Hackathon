"""
8_🌾_Meri_Fasal.py  –  My Farm · Smart Diary & AI Daily Planner
═══════════════════════════════════════════════════════════════════
Track your fields, log activities, see crop growth stages in
real-time, and get AI-powered daily action items tailored to
YOUR farm.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys
import time
import uuid

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── project imports ────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from frontend.components.sidebar import render_sidebar          # noqa: E402
from frontend.components.auth import require_auth               # noqa: E402
from frontend.components.voice import (                         # noqa: E402
    render_voice_input,
    render_voice_output,
)

try:
    from backend.services.llm_helper import llm                 # noqa: E402
except Exception:
    llm = None

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Meri Fasal – My Farm",
    page_icon="🌾",
    layout="wide",
)

# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

TELANGANA_DISTRICTS = [
    "Adilabad", "Bhadradri Kothagudem", "Hyderabad", "Jagtial", "Jangaon",
    "Jayashankar Bhupalpally", "Jogulamba Gadwal", "Kamareddy", "Karimnagar",
    "Khammam", "Kumuram Bheem", "Mahabubabad", "Mahabubnagar", "Mancherial",
    "Medak", "Medchal-Malkajgiri", "Mulugu", "Nagarkurnool", "Nalgonda",
    "Narayanpet", "Nirmal", "Nizamabad", "Peddapalli", "Rajanna Sircilla",
    "Rangareddy", "Sangareddy", "Siddipet", "Suryapet", "Vikarabad",
    "Wanaparthy", "Warangal", "Yadadri Bhuvanagiri",
]

SOIL_TYPES = [
    "Black Cotton Soil", "Red Soil", "Laterite Soil", "Alluvial Soil",
    "Sandy Loam", "Clay Loam", "Sandy Clay", "Chalka (Mixed)",
]

ACTIVITY_TYPES = {
    "sowing":     {"icon": "🌱", "label": {"en": "Sowing / Planting",   "te": "విత్తడం",           "hi": "बुवाई"}},
    "irrigation": {"icon": "💧", "label": {"en": "Irrigation",          "te": "నీటి పారుదల",       "hi": "सिंचाई"}},
    "fertilizer": {"icon": "🧪", "label": {"en": "Fertilizer / Manure", "te": "ఎరువులు",           "hi": "उर्वरक"}},
    "pesticide":  {"icon": "🐛", "label": {"en": "Pest / Disease Ctrl", "te": "పురుగు నియంత్రణ",   "hi": "कीट नियंत्रण"}},
    "weeding":    {"icon": "🌿", "label": {"en": "Weeding",             "te": "కలుపు తీయడం",       "hi": "निराई"}},
    "harvest":    {"icon": "🌾", "label": {"en": "Harvest",             "te": "పంట కోత",           "hi": "कटाई"}},
    "sale":       {"icon": "💰", "label": {"en": "Sale / Market",       "te": "అమ్మకం",            "hi": "बिक्री"}},
    "other":      {"icon": "📝", "label": {"en": "Other",               "te": "ఇతర",              "hi": "अन्य"}},
}

# ═══════════════════════════════════════════════════════════════════════
#  Crop Growth-Stage Database  (10 major Telangana crops)
# ═══════════════════════════════════════════════════════════════════════

CROP_GROWTH: dict[str, dict] = {
    "Rice (Paddy)": {
        "total_days": 120, "season": "Kharif",
        "stages": [
            {"name": "Nursery",       "pct": 20, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Maintain 2–3 cm water in nursery. Seed treatment with fungicide recommended."},
            {"name": "Tillering",     "pct": 25, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply urea 1st dose (40 kg/acre). Maintain 5 cm water. Watch for stem borer."},
            {"name": "Flowering",     "pct": 20, "color": "#fde4cf", "icon": "🌸",
             "tips": "Apply potash. Do NOT drain water. Critical pest-watch period for BPH."},
            {"name": "Grain Filling", "pct": 20, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Maintain moisture. Watch blast disease. Avoid excess nitrogen."},
            {"name": "Maturity",      "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Drain field 10 days before harvest. Harvest at 20–22% grain moisture."},
        ],
        "water_interval": 4, "fert_days": [0, 25, 50, 75],
    },
    "Cotton": {
        "total_days": 170, "season": "Kharif",
        "stages": [
            {"name": "Germination",         "pct": 10, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Ensure soil moisture. Thin to 60 cm spacing after 15 days."},
            {"name": "Vegetative",          "pct": 25, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply DAP + urea. Control jassids, thrips & whitefly early."},
            {"name": "Squaring & Flowering","pct": 25, "color": "#fde4cf", "icon": "🌸",
             "tips": "Apply potash. Bollworm monitoring critical. Irrigate every 10 days."},
            {"name": "Boll Development",    "pct": 25, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Continue pest watch. Avoid excess water. Apply micronutrient spray."},
            {"name": "Boll Opening",        "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Pick cotton in 3–4 rounds as bolls open. Avoid picking wet cotton."},
        ],
        "water_interval": 10, "fert_days": [0, 30, 60, 90],
    },
    "Maize": {
        "total_days": 115, "season": "Kharif / Rabi",
        "stages": [
            {"name": "Germination",         "pct": 12, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Gap-fill within 10 days. Keep soil moist but not waterlogged."},
            {"name": "Vegetative",          "pct": 30, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply urea at knee-height. Earthing-up at 30 days. Active weed control."},
            {"name": "Tasseling & Silking", "pct": 18, "color": "#fde4cf", "icon": "🌸",
             "tips": "CRITICAL water need — even 1 day of stress = 8% yield loss."},
            {"name": "Grain Filling",       "pct": 25, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Apply urea last dose. Monitor fall armyworm. Maintain moisture."},
            {"name": "Maturity",            "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when husk brown & grain hard. Dry to 14% moisture."},
        ],
        "water_interval": 7, "fert_days": [0, 25, 50, 75],
    },
    "Red Gram (Tur)": {
        "total_days": 160, "season": "Kharif",
        "stages": [
            {"name": "Germination",    "pct": 10, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Rhizobium seed treatment before sowing. Maintain proper spacing."},
            {"name": "Vegetative",     "pct": 30, "color": "#98f5e1", "icon": "🌿",
             "tips": "Weed at 25 days. Nipping at 45 days encourages branching."},
            {"name": "Flowering",      "pct": 20, "color": "#fde4cf", "icon": "🌸",
             "tips": "Spray 2% urea foliar. Monitor pod borer (Helicoverpa) closely."},
            {"name": "Pod Development","pct": 25, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Install pheromone traps. Spray NPV/Ha for borer control."},
            {"name": "Maturity",       "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when 80% pods dry. Sun-dry 3–4 days before threshing."},
        ],
        "water_interval": 15, "fert_days": [0, 30],
    },
    "Bengal Gram (Chana)": {
        "total_days": 110, "season": "Rabi",
        "stages": [
            {"name": "Germination",  "pct": 12, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Seed treatment with Trichoderma. Maintain 30 × 10 cm spacing."},
            {"name": "Vegetative",   "pct": 28, "color": "#98f5e1", "icon": "🌿",
             "tips": "One light irrigation at 30 days. Weed control at 20–25 days."},
            {"name": "Flowering",    "pct": 22, "color": "#fde4cf", "icon": "🌸",
             "tips": "Avoid excess water. Pod borer monitoring — install pheromone traps."},
            {"name": "Pod Filling",  "pct": 23, "color": "#f1c0e8", "icon": "🌾",
             "tips": "One irrigation if dry spell > 15 days. Watch for wilt disease."},
            {"name": "Maturity",     "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when leaves turn yellow & pods dry. Thresh on clean floor."},
        ],
        "water_interval": 20, "fert_days": [0],
    },
    "Soybean": {
        "total_days": 100, "season": "Kharif",
        "stages": [
            {"name": "Germination",     "pct": 12, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Inoculate with Rhizobium & PSB. Avoid deep sowing (3–4 cm max)."},
            {"name": "Vegetative",      "pct": 28, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply full DAP dose. Complete weed control within 20 days."},
            {"name": "Flowering",       "pct": 22, "color": "#fde4cf", "icon": "🌸",
             "tips": "No water stress! Spray DAP 2% foliar for better pod setting."},
            {"name": "Pod Development", "pct": 23, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Watch stem fly & girdle beetle. Maintain soil moisture."},
            {"name": "Maturity",        "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when 95% pods turn brown. Do not delay — shattering risk!"},
        ],
        "water_interval": 8, "fert_days": [0, 30],
    },
    "Turmeric": {
        "total_days": 270, "season": "Kharif",
        "stages": [
            {"name": "Sprouting",         "pct": 10, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Treat rhizomes with mancozeb. Plant at 25 × 30 cm. Mulch beds."},
            {"name": "Vegetative Growth", "pct": 30, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply urea + potash at 60 days. Earthing-up twice. Regular weeding."},
            {"name": "Active Tillering",  "pct": 25, "color": "#fde4cf", "icon": "🌸",
             "tips": "Rhizome development peak. Irrigate every 7 days without fail."},
            {"name": "Rhizome Bulking",   "pct": 20, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Apply last nitrogen dose. Prevent waterlogging — rhizome rot risk."},
            {"name": "Maturity",          "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when leaves dry (7–9 months). Boil, dry & polish rhizomes."},
        ],
        "water_interval": 7, "fert_days": [0, 40, 80, 120],
    },
    "Chilli": {
        "total_days": 180, "season": "Kharif / Rabi",
        "stages": [
            {"name": "Nursery & Transplant","pct": 15, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Raise nursery in pro-trays. Transplant 35-day seedlings at 60 × 45 cm."},
            {"name": "Vegetative",          "pct": 20, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply urea + micronutrients. Staking if needed. Watch thrips."},
            {"name": "Flowering",           "pct": 20, "color": "#fde4cf", "icon": "🌸",
             "tips": "Boron spray for fruit set. Monitor murda complex (thrips + mites)."},
            {"name": "Fruiting",            "pct": 30, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Pick every 10–15 days. Spray for fruit borer. Drip irrigation ideal."},
            {"name": "Final Harvest",       "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Last 2–3 pickings. Sun-dry red chillies 8–10 days. Grade by size."},
        ],
        "water_interval": 5, "fert_days": [0, 30, 60, 90, 120],
    },
    "Groundnut": {
        "total_days": 120, "season": "Kharif",
        "stages": [
            {"name": "Germination",          "pct": 12, "color": "#b9fbc0", "icon": "🌱",
             "tips": "Treat seed with Trichoderma. Sow at 30 × 10 cm. Gypsum in furrow."},
            {"name": "Vegetative",           "pct": 25, "color": "#98f5e1", "icon": "🌿",
             "tips": "Weed at 20 & 35 days. Apply gypsum at flowering (400 kg/ha)."},
            {"name": "Flowering & Pegging",  "pct": 23, "color": "#fde4cf", "icon": "🌸",
             "tips": "CRITICAL — no water stress. Calcium + boron essential for peg entry."},
            {"name": "Pod Development",      "pct": 25, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Maintain soil moisture. Watch tikka leaf spot. Stop irrigation 10 days before harvest."},
            {"name": "Maturity",             "pct": 15, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when inner shell shows dark marks. Dry to 8% moisture."},
        ],
        "water_interval": 6, "fert_days": [0, 25, 45],
    },
    "Wheat": {
        "total_days": 135, "season": "Rabi",
        "stages": [
            {"name": "Germination",        "pct": 12, "color": "#b9fbc0", "icon": "🌱",
             "tips": "First irrigation 21 days after sowing (crown root initiation stage)."},
            {"name": "Tillering",          "pct": 22, "color": "#98f5e1", "icon": "🌿",
             "tips": "Apply 1st top-dress urea. Irrigate at tillering stage."},
            {"name": "Booting & Heading",  "pct": 22, "color": "#fde4cf", "icon": "🌸",
             "tips": "2nd irrigation. Foliar zinc spray. Watch for yellow rust."},
            {"name": "Grain Filling",      "pct": 24, "color": "#f1c0e8", "icon": "🌾",
             "tips": "Last irrigation at dough stage. Avoid terminal heat stress."},
            {"name": "Maturity",           "pct": 20, "color": "#a3c4f3", "icon": "✅",
             "tips": "Harvest when golden yellow & grain hard. Thresh within 3 days."},
        ],
        "water_interval": 10, "fert_days": [0, 21, 45],
    },
}

CROP_NAMES = sorted(CROP_GROWTH.keys())

# ═══════════════════════════════════════════════════════════════════════
#  UI Translations
# ═══════════════════════════════════════════════════════════════════════

_UI: dict[str, dict[str, str]] = {
    "page_title":     {"en": "🌾 Meri Fasal — My Farm",
                       "te": "🌾 మేరీ ఫసల్ — నా పొలం",
                       "hi": "🌾 मेरी फसल — मेरा खेत"},
    "page_subtitle":  {"en": "Smart Farm Diary & AI Daily Planner",
                       "te": "స్మార్ట్ ఫార్మ్ డైరీ & AI దైనిక ప్లానర్",
                       "hi": "स्मार्ट फार्म डायरी और AI दैनिक प्लानर"},
    "tab_farm":       {"en": "🏡 My Farm",       "te": "🏡 నా పొలం",        "hi": "🏡 मेरा खेत"},
    "tab_log":        {"en": "📝 Activity Log",  "te": "📝 కార్యకలాప లాగ్", "hi": "📝 गतिविधि लॉग"},
    "tab_planner":    {"en": "🤖 AI Daily Planner",
                       "te": "🤖 AI దైనిక ప్లానర్",
                       "hi": "🤖 AI दैनिक प्लानर"},
    "tab_dashboard":  {"en": "📊 Farm Dashboard",
                       "te": "📊 ఫార్మ్ డ్యాష్‌బోర్డ్",
                       "hi": "📊 फार्म डैशबोर्ड"},
    "add_field":      {"en": "Add New Field",    "te": "కొత్త పొలం జోడించు", "hi": "नया खेत जोड़ें"},
    "field_name":     {"en": "Field Name",       "te": "పొలం పేరు",          "hi": "खेत का नाम"},
    "area":           {"en": "Area (acres)",     "te": "విస్తీర్ణం (ఎకరాలు)","hi": "क्षेत्र (एकड़)"},
    "district":       {"en": "District",         "te": "జిల్లా",              "hi": "जिला"},
    "soil":           {"en": "Soil Type",        "te": "మట్టి రకం",          "hi": "मिट्टी प्रकार"},
    "add_crop":       {"en": "Add Crop",         "te": "పంట జోడించు",        "hi": "फसल जोड़ें"},
    "sowing_date":    {"en": "Sowing Date",      "te": "విత్తన తేదీ",        "hi": "बुवाई तिथि"},
    "no_fields":      {"en": "No fields added yet. Add your first field or load demo data!",
                       "te": "ఇంకా పొలాలు జోడించలేదు. మీ మొదటి పొలాన్ని జోడించండి!",
                       "hi": "अभी तक कोई खेत नहीं जोड़ा। अपना पहला खेत जोड़ें!"},
    "load_demo":      {"en": "🎯 Load Demo Farm",
                       "te": "🎯 డెమో ఫారం లోడ్ చేయండి",
                       "hi": "🎯 डेमो फार्म लोड करें"},
    "quick_questions":{"en": "Quick Questions",  "te": "శీఘ్ర ప్రశ్నలు",     "hi": "त्वरित प्रश्न"},
    "farm_health":    {"en": "Farm Health Score", "te": "పొలం ఆరోగ్య స్కోరు", "hi": "खेत स्वास्थ्य स्कोर"},
    "total_investment":{"en": "Total Investment", "te": "మొత్తం పెట్టుబడి",   "hi": "कुल निवेश"},
    "total_fields":   {"en": "Total Fields",     "te": "మొత్తం పొలాలు",       "hi": "कुल खेत"},
    "active_crops":   {"en": "Active Crops",     "te": "యాక్టివ్ పంటలు",      "hi": "सक्रिय फसलें"},
}


def _ui(key: str, lang: str = "en") -> str:
    return _UI.get(key, {}).get(lang, _UI.get(key, {}).get("en", key))


# ═══════════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════════

def _init_state() -> None:
    """Initialise session state for farm data."""
    st.session_state.setdefault("mf_fields", [])
    st.session_state.setdefault("mf_activities", [])


def _get_growth_info(crop_name: str, sowing_date: dt.date) -> dict:
    """Return growth-stage details for *crop_name* sown on *sowing_date*."""
    data = CROP_GROWTH.get(crop_name)
    if not data:
        return {"stage": {"name": "Unknown", "icon": "❓", "tips": "", "pct": 100, "color": "#ccc"},
                "day": 0, "pct": 0, "total_days": 0, "remaining": 0, "data": None, "completed": False}

    today = dt.date.today()
    days = max(0, (today - sowing_date).days)
    total = data["total_days"]
    pct_done = min(days / total * 100, 100) if total else 0

    cum = 0
    current_stage = data["stages"][-1]
    for s in data["stages"]:
        cum += s["pct"]
        if pct_done <= cum:
            current_stage = s
            break

    return {
        "stage": current_stage,
        "day": days,
        "pct": pct_done,
        "total_days": total,
        "remaining": max(0, total - days),
        "data": data,
        "completed": days >= total,
    }


def _render_growth_bar(crop_name: str, sowing_date: dt.date, uid: str) -> dict | None:
    """Render an HTML growth-stage progress bar and return growth info."""
    info = _get_growth_info(crop_name, sowing_date)
    data = CROP_GROWTH.get(crop_name)
    if not data:
        st.caption(f"⚠️ Growth data unavailable for {crop_name}")
        return info

    pct = info["pct"]
    stages = data["stages"]

    # Coloured segmented HTML bar
    bar = (
        '<div style="display:flex;height:32px;border-radius:10px;'
        'overflow:hidden;border:1px solid #555;margin:4px 0;">'
    )
    cum = 0.0
    for s in stages:
        filled = pct >= cum + s["pct"]
        current = cum < pct <= cum + s["pct"]
        opacity = "1.0" if filled else ("0.9" if current else "0.30")
        border = "border-bottom:3px solid #e74c3c;" if current else ""
        bar += (
            f'<div style="width:{s["pct"]}%;background:{s["color"]};opacity:{opacity};'
            f'{border}display:flex;align-items:center;justify-content:center;'
            f'font-size:12px;white-space:nowrap;overflow:hidden;"'
            f' title="{s["name"]}: {s["tips"]}">'
            f'{s["icon"]}'
            f'</div>'
        )
        cum += s["pct"]
    bar += '</div>'

    st.markdown(bar, unsafe_allow_html=True)

    stage = info["stage"]
    st.caption(
        f"📅 Day **{info['day']}** / {info['total_days']} · "
        f"{stage['icon']} **{stage['name']}** · "
        f"⏳ {info['remaining']} days remaining"
    )
    return info


# ── Demo data ─────────────────────────────────────────────────────────

def _load_demo_data() -> None:
    """Populate session state with a realistic demo farm."""
    today = dt.date.today()

    f1_id, f2_id = str(uuid.uuid4()), str(uuid.uuid4())

    fields = [
        {
            "id": f1_id, "name": "Main Farm – Raju", "area": 5.0,
            "soil_type": "Black Cotton Soil", "district": "Warangal",
            "crops": [
                {"id": str(uuid.uuid4()), "name": "Maize",
                 "sowing_date": (today - dt.timedelta(days=62)).isoformat(),
                 "status": "growing"},
                {"id": str(uuid.uuid4()), "name": "Bengal Gram (Chana)",
                 "sowing_date": (today - dt.timedelta(days=95)).isoformat(),
                 "status": "growing"},
            ],
        },
        {
            "id": f2_id, "name": "Lakshmi Plot", "area": 3.0,
            "soil_type": "Red Soil", "district": "Nizamabad",
            "crops": [
                {"id": str(uuid.uuid4()), "name": "Chilli",
                 "sowing_date": (today - dt.timedelta(days=80)).isoformat(),
                 "status": "growing"},
                {"id": str(uuid.uuid4()), "name": "Wheat",
                 "sowing_date": (today - dt.timedelta(days=100)).isoformat(),
                 "status": "growing"},
            ],
        },
    ]

    acts_raw = [
        # ── Main Farm – Maize ──
        (f1_id, "Maize",   "sowing",     62, 2500, "Sowed hybrid maize 900M Gold"),
        (f1_id, "Maize",   "fertilizer", 52, 1800, "DAP 50 kg/acre basal dose"),
        (f1_id, "Maize",   "irrigation", 48, 400,  "Furrow irrigation"),
        (f1_id, "Maize",   "weeding",    38, 1200, "Manual weeding + pre-emergent herbicide"),
        (f1_id, "Maize",   "irrigation", 32, 400,  "Sprinkler irrigation"),
        (f1_id, "Maize",   "fertilizer", 22, 1400, "Urea top-dress 1st dose"),
        (f1_id, "Maize",   "pesticide",  14, 900,  "Fall armyworm spray — Emamectin benzoate"),
        (f1_id, "Maize",   "irrigation",  8, 400,  "Drip irrigation"),
        # ── Main Farm – Bengal Gram ──
        (f1_id, "Bengal Gram (Chana)", "sowing",     95, 1800, "JG-11 variety sown, Trichoderma treated"),
        (f1_id, "Bengal Gram (Chana)", "irrigation",  65, 350, "Light sprinkler irrigation"),
        (f1_id, "Bengal Gram (Chana)", "pesticide",   45, 700, "Pod borer — pheromone traps + NPV spray"),
        (f1_id, "Bengal Gram (Chana)", "fertilizer",  90, 600, "DAP basal 20 kg/acre"),
        # ── Lakshmi Plot – Chilli ──
        (f2_id, "Chilli",  "sowing",     80, 3500, "Teja variety transplanted from pro-trays"),
        (f2_id, "Chilli",  "fertilizer", 60, 2200, "DAP + Urea + Micronutrient mix"),
        (f2_id, "Chilli",  "irrigation", 45, 500,  "Drip irrigation"),
        (f2_id, "Chilli",  "pesticide",  30, 1100, "Thrips spray — Fipronil 5 SC"),
        (f2_id, "Chilli",  "irrigation", 18, 500,  "Drip irrigation"),
        (f2_id, "Chilli",  "fertilizer", 10, 1800, "19:19:19 water-soluble fertilizer"),
        # ── Lakshmi Plot – Wheat ──
        (f2_id, "Wheat",   "sowing",     100, 2000, "HD-2967 variety sown"),
        (f2_id, "Wheat",   "fertilizer",  80, 1500, "Urea 1st top-dress at CRI stage"),
        (f2_id, "Wheat",   "irrigation",  60, 400,  "Border strip irrigation"),
        (f2_id, "Wheat",   "irrigation",  30, 400,  "Border strip irrigation"),
        (f2_id, "Wheat",   "fertilizer",  55, 1200, "Urea 2nd dose + zinc sulfate spray"),
    ]

    activities = [
        {
            "id": str(uuid.uuid4()),
            "field_id": fid,
            "crop": crop,
            "type": atype,
            "date": (today - dt.timedelta(days=ago)).isoformat(),
            "cost": cost,
            "notes": notes,
        }
        for fid, crop, atype, ago, cost, notes in acts_raw
    ]

    st.session_state["mf_fields"] = fields
    st.session_state["mf_activities"] = activities


# ── Aggregate helpers ─────────────────────────────────────────────────

def _get_all_active_crops() -> list[dict]:
    """Flat list of every growing crop enriched with field metadata."""
    result = []
    for f in st.session_state.get("mf_fields", []):
        for c in f.get("crops", []):
            if c.get("status") == "growing":
                result.append({
                    **c,
                    "field_name":     f["name"],
                    "field_id":       f["id"],
                    "field_area":     f["area"],
                    "field_soil":     f["soil_type"],
                    "field_district": f["district"],
                    "sowing_dt":      dt.date.fromisoformat(c["sowing_date"]),
                })
    return result


def _calc_farm_health() -> int:
    """Compute a 0-100 'Farm Health Score'."""
    fields     = st.session_state.get("mf_fields", [])
    activities = st.session_state.get("mf_activities", [])
    if not fields:
        return 0

    score = 0

    # 1  Field registration (max 20)
    score += min(20, len(fields) * 10)

    # 2  Crop diversity (max 20)
    crops: set[str] = set()
    for f in fields:
        for c in f.get("crops", []):
            crops.add(c["name"])
    score += min(20, len(crops) * 5)

    # 3  Recent activity regularity (max 30)
    if activities:
        recent = [
            a for a in activities
            if (dt.date.today() - dt.date.fromisoformat(a["date"])).days <= 14
        ]
        score += min(30, len(recent) * 5)

    # 4  Activity coverage per crop (max 30)
    active = _get_all_active_crops()
    if active:
        cov = []
        for c in active:
            n = sum(1 for a in activities if a["crop"] == c["name"] and a["field_id"] == c["field_id"])
            cov.append(min(1.0, n / 3))
        if cov:
            score += int(30 * (sum(cov) / len(cov)))

    return min(100, score)


# ═══════════════════════════════════════════════════════════════════════
#  Tab 1 — My Farm
# ═══════════════════════════════════════════════════════════════════════

def _render_my_farm(lang: str) -> None:
    fields = st.session_state["mf_fields"]

    # ── Add-field form ─────────────────────────────────────────────────
    with st.expander(f"➕ {_ui('add_field', lang)}", expanded=not fields):
        with st.form("add_field_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                fname = st.text_input(_ui("field_name", lang),
                                      placeholder="e.g. Main Farm")
                farea = st.number_input(_ui("area", lang),
                                        min_value=0.1, max_value=500.0,
                                        value=2.0, step=0.5)
            with fc2:
                fsoil     = st.selectbox(_ui("soil", lang), SOIL_TYPES)
                fdistrict = st.selectbox(_ui("district", lang), TELANGANA_DISTRICTS)

            if st.form_submit_button(f"➕ {_ui('add_field', lang)}", type="primary"):
                if not fname.strip():
                    st.warning("Please enter a field name.")
                else:
                    st.session_state["mf_fields"].append({
                        "id": str(uuid.uuid4()),
                        "name": fname.strip(),
                        "area": farea,
                        "soil_type": fsoil,
                        "district": fdistrict,
                        "crops": [],
                    })
                    st.rerun()

    # ── Empty state ────────────────────────────────────────────────────
    if not fields:
        st.info(_ui("no_fields", lang))
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button(_ui("load_demo", lang), type="primary",
                         use_container_width=True, key="demo_farm_btn"):
                _load_demo_data()
                st.rerun()
        return

    # ── Field cards ────────────────────────────────────────────────────
    for field in fields:
        with st.container():
            st.markdown(f"### 🏡 {field['name']}")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("📍 District", field["district"])
            mc2.metric("📐 Area",     f"{field['area']} ac")
            mc3.metric("🌱 Crops",    len(field.get("crops", [])))
            mc4.metric("🟤 Soil",     field["soil_type"][:15])

            # -- add crop ---------------------------------------------------
            with st.expander(f"➕ {_ui('add_crop', lang)} to {field['name']}"):
                with st.form(f"add_crop_{field['id']}", clear_on_submit=True):
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        crop_name = st.selectbox("Crop", CROP_NAMES,
                                                 key=f"cn_{field['id']}")
                    with cc2:
                        sowing_date = st.date_input(
                            _ui("sowing_date", lang),
                            value=dt.date.today() - dt.timedelta(days=30),
                            key=f"sd_{field['id']}",
                        )
                    if st.form_submit_button(f"🌱 {_ui('add_crop', lang)}"):
                        new_crop = {
                            "id":          str(uuid.uuid4()),
                            "name":        crop_name,
                            "sowing_date": sowing_date.isoformat(),
                            "status":      "growing",
                        }
                        field["crops"].append(new_crop)
                        # auto-log sowing activity
                        st.session_state["mf_activities"].append({
                            "id":       str(uuid.uuid4()),
                            "field_id": field["id"],
                            "crop":     crop_name,
                            "type":     "sowing",
                            "date":     sowing_date.isoformat(),
                            "cost":     0,
                            "notes":    f"Sowed {crop_name}",
                        })
                        st.rerun()

            # -- growth bars ------------------------------------------------
            for crop in field.get("crops", []):
                if crop.get("status") != "growing":
                    continue
                sow_dt = dt.date.fromisoformat(crop["sowing_date"])
                st.markdown(f"**{crop['name']}** — sown {sow_dt.strftime('%d %b %Y')}")
                info = _render_growth_bar(crop["name"], sow_dt,
                                          f"{field['id']}_{crop['id']}")
                if info and isinstance(info.get("stage"), dict):
                    st.info(f"💡 **Tip:** {info['stage'].get('tips', '')}")
                st.markdown("---")

            # -- remove field -----------------------------------------------
            if st.button("🗑️ Remove field", key=f"del_f_{field['id']}"):
                st.session_state["mf_fields"] = [
                    f for f in st.session_state["mf_fields"]
                    if f["id"] != field["id"]
                ]
                st.rerun()

        st.divider()


# ═══════════════════════════════════════════════════════════════════════
#  Tab 2 — Activity Log
# ═══════════════════════════════════════════════════════════════════════

def _render_activity_log(lang: str) -> None:
    fields     = st.session_state["mf_fields"]
    activities = st.session_state["mf_activities"]

    if not fields:
        st.info("Add a field in the **My Farm** tab first.")
        return

    # ── Log form ───────────────────────────────────────────────────────
    with st.expander("➕ Log New Activity", expanded=True):
        with st.form("log_activity", clear_on_submit=True):
            lc1, lc2, lc3 = st.columns(3)
            with lc1:
                field_map = {f["id"]: f["name"] for f in fields}
                sel_fid = st.selectbox(
                    "Field", list(field_map.keys()),
                    format_func=lambda x: field_map[x], key="log_field",
                )
            with lc2:
                sel_field = next((f for f in fields if f["id"] == sel_fid), None)
                crop_opts = ([c["name"] for c in sel_field.get("crops", [])]
                             if sel_field else CROP_NAMES)
                if not crop_opts:
                    crop_opts = CROP_NAMES
                sel_crop = st.selectbox("Crop", crop_opts, key="log_crop")
            with lc3:
                act_keys = list(ACTIVITY_TYPES.keys())
                sel_type = st.selectbox(
                    "Activity",
                    act_keys,
                    format_func=lambda x: (
                        f"{ACTIVITY_TYPES[x]['icon']} "
                        f"{ACTIVITY_TYPES[x]['label'][lang]}"
                    ),
                    key="log_type",
                )
            lc4, lc5, lc6 = st.columns(3)
            with lc4:
                act_date = st.date_input("Date", value=dt.date.today(),
                                         key="log_date")
            with lc5:
                act_cost = st.number_input("Cost (₹)", min_value=0,
                                           value=0, step=100, key="log_cost")
            with lc6:
                act_notes = st.text_input("Notes", placeholder="Details…",
                                          key="log_notes")

            if st.form_submit_button("📝 Log Activity", type="primary"):
                st.session_state["mf_activities"].append({
                    "id":       str(uuid.uuid4()),
                    "field_id": sel_fid,
                    "crop":     sel_crop,
                    "type":     sel_type,
                    "date":     act_date.isoformat(),
                    "cost":     act_cost,
                    "notes":    act_notes,
                })
                st.toast(
                    f"{ACTIVITY_TYPES[sel_type]['icon']} "
                    f"{sel_type.title()} logged!", icon="✅")
                st.rerun()

    # ── History ────────────────────────────────────────────────────────
    if not activities:
        st.info("No activities logged yet. Use the form above to start!")
        return

    st.markdown("### 📋 Activity History")

    fc1, fc2 = st.columns(2)
    with fc1:
        filter_field = st.selectbox(
            "Filter by Field",
            ["All"] + [f["name"] for f in fields],
            key="act_filt_field",
        )
    with fc2:
        filter_type = st.selectbox(
            "Filter by Type",
            ["All"] + list(ACTIVITY_TYPES.keys()),
            format_func=lambda x: (
                "All Types" if x == "All"
                else f"{ACTIVITY_TYPES[x]['icon']} {ACTIVITY_TYPES[x]['label'][lang]}"
            ),
            key="act_filt_type",
        )

    field_name_map = {f["id"]: f["name"] for f in fields}
    view = sorted(activities, key=lambda x: x["date"], reverse=True)

    if filter_field != "All":
        fid = next((f["id"] for f in fields if f["name"] == filter_field), None)
        view = [a for a in view if a["field_id"] == fid]
    if filter_type != "All":
        view = [a for a in view if a["type"] == filter_type]

    for act in view:
        at = ACTIVITY_TYPES.get(act["type"], ACTIVITY_TYPES["other"])
        fname = field_name_map.get(act["field_id"], "?")
        cost_s = f"₹{act['cost']:,}" if act["cost"] else "—"
        st.markdown(
            f"**{at['icon']} {act['date']}** · {at['label'][lang]} · "
            f"🌾 {act['crop']} · 🏡 {fname} · 💰 {cost_s}"
        )
        if act.get("notes"):
            st.caption(f"   📝 {act['notes']}")

    st.divider()
    tot = sum(a.get("cost", 0) for a in view)
    st.markdown(f"**Showing {len(view)} activities · ₹{tot:,} total spend**")


# ═══════════════════════════════════════════════════════════════════════
#  Tab 3 — AI Daily Planner
# ═══════════════════════════════════════════════════════════════════════

def _render_ai_planner(lang: str) -> None:
    active_crops = _get_all_active_crops()
    activities   = st.session_state.get("mf_activities", [])

    if not active_crops:
        st.info("Add fields and crops in the **My Farm** tab to get "
                "personalised daily plans.")
        if st.button(_ui("load_demo", lang), type="primary", key="demo_ai"):
            _load_demo_data()
            st.rerun()
        return

    today = dt.date.today()

    # ── Build context string ───────────────────────────────────────────
    lines: list[str] = []
    for c in active_crops:
        info = _get_growth_info(c["name"], c["sowing_dt"])
        stage = info["stage"]
        s_name = stage["name"] if isinstance(stage, dict) else str(stage)
        s_tips = stage.get("tips", "") if isinstance(stage, dict) else ""

        crop_acts = sorted(
            [a for a in activities
             if a["crop"] == c["name"] and a["field_id"] == c["field_id"]],
            key=lambda x: x["date"], reverse=True,
        )[:5]
        act_str = "; ".join(f"{a['type']}({a['date']})" for a in crop_acts) or "none"

        w_int = CROP_GROWTH.get(c["name"], {}).get("water_interval", 7)
        last_irr = next((a for a in crop_acts if a["type"] == "irrigation"), None)
        d_water = ((today - dt.date.fromisoformat(last_irr["date"])).days
                   if last_irr else 999)

        lines.append(
            f"• {c['name']} @ {c['field_name']} ({c['field_area']} ac, "
            f"{c['field_soil']}, {c['field_district']}): "
            f"Day {info['day']}/{info['total_days']}, "
            f"Stage: {s_name}, {info['remaining']} days to harvest. "
            f"Water interval: {w_int}d, last irrigated: {d_water}d ago. "
            f"Tip: {s_tips}. Recent: {act_str}"
        )
    farm_ctx = "\n".join(lines)

    # ── Quick crop status cards ────────────────────────────────────────
    st.markdown("### 🌱 Current Crop Status")
    n_cols = min(len(active_crops), 4)
    cols = st.columns(n_cols)
    for i, c in enumerate(active_crops):
        with cols[i % n_cols]:
            info = _get_growth_info(c["name"], c["sowing_dt"])
            stage = info["stage"]
            s_icon = stage["icon"] if isinstance(stage, dict) else "🌿"
            s_name = stage["name"] if isinstance(stage, dict) else "?"
            st.markdown(f"**{c['name']}**")
            st.caption(f"{c['field_name']}")
            st.progress(min(info["pct"] / 100, 1.0),
                        text=f"{s_icon} {s_name} — Day {info['day']}")

    st.divider()

    # ── Smart alerts ───────────────────────────────────────────────────
    st.markdown("### ⚠️ Smart Alerts")
    alert_n = 0
    for c in active_crops:
        data = CROP_GROWTH.get(c["name"], {})
        w_int = data.get("water_interval", 7)
        crop_acts = [
            a for a in activities
            if a["crop"] == c["name"] and a["field_id"] == c["field_id"]
        ]

        # -- irrigation overdue
        last_irr = next(
            (a for a in sorted(crop_acts, key=lambda x: x["date"], reverse=True)
             if a["type"] == "irrigation"),
            None,
        )
        if last_irr:
            d_since = (today - dt.date.fromisoformat(last_irr["date"])).days
            if d_since > w_int:
                st.warning(
                    f"💧 **{c['name']}** ({c['field_name']}): "
                    f"Last irrigated **{d_since}** days ago — "
                    f"recommended every {w_int} days!"
                )
                alert_n += 1
        else:
            st.warning(
                f"💧 **{c['name']}** ({c['field_name']}): "
                f"No irrigation recorded! Recommended every {w_int} days."
            )
            alert_n += 1

        # -- fertilizer due
        fert_days = data.get("fert_days", [])
        info = _get_growth_info(c["name"], c["sowing_dt"])
        for fd in fert_days:
            if info["day"] >= fd - 3 and info["day"] <= fd + 7:
                last_f = next(
                    (a for a in sorted(crop_acts, key=lambda x: x["date"], reverse=True)
                     if a["type"] == "fertilizer"),
                    None,
                )
                if not last_f or (today - dt.date.fromisoformat(last_f["date"])).days > 12:
                    st.info(
                        f"🧪 **{c['name']}** ({c['field_name']}): "
                        f"Fertilizer recommended around Day {fd} — "
                        f"you're at Day {info['day']}."
                    )
                    alert_n += 1
                break  # only one fert alert per crop

        # -- harvest approaching
        if 0 < info["remaining"] <= 10:
            st.success(
                f"🌾 **{c['name']}** ({c['field_name']}): "
                f"Harvest expected in ~{info['remaining']} days!"
            )
            alert_n += 1

    if alert_n == 0:
        st.success("✅ All looking good — no urgent alerts right now.")

    # ── AI advice ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🤖 AI Daily Planner")

    result = st.session_state.get("mf_planner_result")

    _prefill = st.session_state.pop("_mf_planner_prefill", "")
    q = st.text_area(
        "Ask anything about your farm, or generate today's plan:",
        value=_prefill,
        placeholder="e.g. What should I do today? / Any pest risk for cotton?",
        height=100,
        key="mf_planner_input",
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        gen_plan = st.button("📋 Generate Today's Plan", type="primary",
                             use_container_width=True, key="mf_gen")
    with bc2:
        ask_q = st.button("🔍 Ask Custom Question",
                          use_container_width=True, key="mf_ask")

    if gen_plan or ask_q:
        custom = q.strip() if ask_q and q.strip() else ""
        lang_name = {"te": "Telugu", "hi": "Hindi"}.get(lang, "English")
        prompt = (
            f"You are KrishiSaathi, an expert agricultural advisor for "
            f"Telangana, India.\nToday: {today.strftime('%d %B %Y')}\n\n"
            f"FARMER'S FARM DATA:\n{farm_ctx}\n\n"
            + (f"FARMER'S QUESTION: {custom}\n\n" if custom else
               "Generate today's action plan.\n\n")
            + "Provide:\n"
              "1. 🔴 URGENT actions (do today)\n"
              "2. 🟡 IMPORTANT actions (this week)\n"
              "3. 🟢 ROUTINE actions (good practice)\n"
              "4. ⚠️ WARNINGS (pest / disease / weather risks)\n"
              "5. 💡 PRO TIPS for current growth stages\n\n"
              "Be specific — mention crop names, field names, exact days, "
              "and actionable steps. Use emojis.\n"
              f"Respond in {lang_name}."
        )
        with st.spinner("🤖 Generating your personalised farm plan…"):
            t0 = time.time()
            try:
                raw = llm.generate(prompt, role="agent")
                answer = raw if isinstance(raw, str) else raw.get("text", str(raw))
                result = {"answer": answer, "elapsed": time.time() - t0}
                st.session_state["mf_planner_result"] = result
            except Exception as e:
                logger.error("AI planner error: %s", e)
                st.error(f"Could not generate plan: {e}")
                result = None

    if result:
        st.divider()
        st.markdown("### 📋 Your Personalised Farm Plan")
        st.markdown(result.get("answer", ""))
        render_voice_output(result.get("answer", ""), language=lang,
                            key_suffix="mf_plan")
        st.caption(f"⏱️ {result.get('elapsed', 0):.1f}s")

    # ── Quick questions ────────────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "What should I do on my farm today?",
            "Which crop needs urgent attention?",
            "Is it safe to spray pesticide now?",
            "When should I harvest my crops?",
            "How to increase yield at this stage?",
        ],
        "te": [
            "ఈ రోజు నా పొలంలో ఏం చేయాలి?",
            "ఏ పంటకు అత్యవసర చర్య అవసరం?",
            "ఇప్పుడు పురుగుమందు చల్లడం సురక్షితమా?",
            "నా పంటలు ఎప్పుడు కోయాలి?",
            "ఈ దశలో దిగుబడి ఎలా పెంచాలి?",
        ],
        "hi": [
            "आज मुझे खेत में क्या करना चाहिए?",
            "किस फसल को तुरंत ध्यान चाहिए?",
            "क्या अभी कीटनाशक छिड़कना सुरक्षित है?",
            "फसल कब काटनी चाहिए?",
            "इस चरण में उपज कैसे बढ़ाएं?",
        ],
    }
    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown(f"**💡 {_ui('quick_questions', lang)}:**")
    qcols = st.columns(len(qs))
    for i, (col, q_txt) in enumerate(zip(qcols, qs)):
        with col:
            label = q_txt[:28] + "…" if len(q_txt) > 28 else q_txt
            if st.button(label, key=f"mfq_{i}", use_container_width=True):
                st.session_state["_mf_planner_prefill"] = q_txt
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  Tab 4 — Farm Dashboard
# ═══════════════════════════════════════════════════════════════════════

def _render_dashboard(lang: str) -> None:
    fields     = st.session_state["mf_fields"]
    activities = st.session_state["mf_activities"]
    active     = _get_all_active_crops()

    if not fields:
        st.info("Add fields and crops to see your farm dashboard.")
        return

    # ── KPI row ────────────────────────────────────────────────────────
    health = _calc_farm_health()
    hc1, hc2, hc3, hc4 = st.columns(4)

    with hc1:
        color = "#2ecc71" if health >= 70 else "#f39c12" if health >= 40 else "#e74c3c"
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health,
            title={"text": _ui("farm_health", lang), "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0, 40],  "color": "#ffeaea"},
                    {"range": [40, 70], "color": "#fff3cd"},
                    {"range": [70, 100],"color": "#d4edda"},
                ],
            },
        ))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True, key="health_gauge")

    with hc2:
        st.metric(_ui("total_fields", lang), len(fields))
        st.metric(_ui("active_crops", lang), len(active))
    with hc3:
        total_area = sum(f["area"] for f in fields)
        st.metric("📐 Total Area", f"{total_area:.1f} acres")
        total_cost = sum(a.get("cost", 0) for a in activities)
        st.metric(_ui("total_investment", lang), f"₹{total_cost:,}")
    with hc4:
        st.metric("📊 Activities", len(activities))
        if activities:
            at_counts: dict[str, int] = {}
            for a in activities:
                at_counts[a["type"]] = at_counts.get(a["type"], 0) + 1
            top = max(at_counts, key=at_counts.get)  # type: ignore[arg-type]
            at_i = ACTIVITY_TYPES.get(top, {})
            st.metric("🔄 Most Frequent",
                      f"{at_i.get('icon', '')} {top.title()}")

    st.divider()

    if not activities:
        st.info("Log activities to unlock charts and insights.")
        return

    # ── Expense by category ────────────────────────────────────────────
    st.markdown("### 💰 Expense Analysis")
    dc1, dc2 = st.columns(2)

    with dc1:
        cat: dict[str, int] = {}
        for a in activities:
            lbl = f"{ACTIVITY_TYPES.get(a['type'], {}).get('icon', '📝')} {a['type'].title()}"
            cat[lbl] = cat.get(lbl, 0) + a.get("cost", 0)
        cat = {k: v for k, v in cat.items() if v > 0}
        if cat:
            fig = px.pie(
                names=list(cat.keys()), values=list(cat.values()),
                title="Expense by Activity Type",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=370, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True, key="pie_cat")

    with dc2:
        fmap = {f["id"]: f["name"] for f in fields}
        fc: dict[str, int] = {}
        for a in activities:
            fn = fmap.get(a["field_id"], "?")
            fc[fn] = fc.get(fn, 0) + a.get("cost", 0)
        fc = {k: v for k, v in fc.items() if v > 0}
        if fc:
            fig = px.bar(
                x=list(fc.keys()), y=list(fc.values()),
                title="Expense by Field",
                labels={"x": "Field", "y": "Cost (₹)"},
                color=list(fc.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(height=370, showlegend=False,
                              margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True, key="bar_field")

    # ── Expense timeline ───────────────────────────────────────────────
    st.markdown("### 📈 Expense Over Time")
    dated: dict[str, int] = {}
    for a in sorted(activities, key=lambda x: x["date"]):
        dated[a["date"]] = dated.get(a["date"], 0) + a.get("cost", 0)

    if dated:
        dates_   = list(dated.keys())
        daily    = list(dated.values())
        cum: list[int] = []
        run = 0
        for d in daily:
            run += d
            cum.append(run)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=dates_, y=daily, name="Daily Spend",
                             marker_color="#74b9ff"))
        fig.add_trace(go.Scatter(x=dates_, y=cum, name="Cumulative",
                                 line=dict(color="#e17055", width=3)))
        fig.update_layout(
            height=370, xaxis_title="Date", yaxis_title="₹",
            title="Daily & Cumulative Investment",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, key="timeline")

    # ── Crop-wise summary ──────────────────────────────────────────────
    st.markdown("### 🌾 Crop-wise Investment")
    csm: dict[str, dict] = {}
    for a in activities:
        cn = a["crop"]
        if cn not in csm:
            csm[cn] = {"total": 0, "n": 0, "types": set()}
        csm[cn]["total"] += a.get("cost", 0)
        csm[cn]["n"]     += 1
        csm[cn]["types"].add(a["type"])

    ccols = st.columns(min(len(csm), 4)) if csm else []
    for i, (crop, d) in enumerate(csm.items()):
        with ccols[i % len(ccols)]:
            st.markdown(f"**🌾 {crop}**")
            st.metric("Investment", f"₹{d['total']:,}")
            st.caption(f"{d['n']} activities · {len(d['types'])} types")


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    user = require_auth()
    if not user:
        return
    render_sidebar()
    _init_state()

    lang = st.session_state.get("app_language", "en")

    st.markdown(f"# {_ui('page_title', lang)}")
    st.caption(_ui("page_subtitle", lang))

    tabs = st.tabs([
        _ui("tab_farm", lang),
        _ui("tab_log", lang),
        _ui("tab_planner", lang),
        _ui("tab_dashboard", lang),
    ])

    with tabs[0]:
        _render_my_farm(lang)
    with tabs[1]:
        _render_activity_log(lang)
    with tabs[2]:
        _render_ai_planner(lang)
    with tabs[3]:
        _render_dashboard(lang)


if __name__ == "__main__":
    main()
else:
    main()
