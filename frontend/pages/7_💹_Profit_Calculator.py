"""Profit & Loss Calculator — AI-powered crop financial planner.

Helps Telangana farmers estimate investment, revenue, and profit per crop
per acre. Includes side-by-side crop comparison, subsidy integration, and
an AI financial advisor that generates personalised farming budgets.
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
from backend.services.translation_service import translator  # noqa: E402
from backend.services.llm_helper import llm  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header, icon, get_theme, get_palette  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402
from frontend.components.voice_input import render_voice_output  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Profit Calculator", page_icon="💹", layout="wide")


# ═══════════════════════════════════════════════════════════════════════
#  Telangana Crop Economics Database (per acre, in INR)
#  Sources: Telangana Agriculture Department, ICAR, NABARD cost studies,
#           Commission for Agricultural Costs & Prices (CACP) 2025-26
# ═══════════════════════════════════════════════════════════════════════

CROP_ECONOMICS: dict[str, dict[str, Any]] = {
    "Rice": {
        "season": "Kharif / Rabi",
        "duration_days": 120,
        "costs": {
            "seeds": 1200,
            "fertilizers": 3500,
            "pesticides": 2000,
            "irrigation": 3000,
            "labor": 8000,
            "machinery": 3500,
            "miscellaneous": 1500,
        },
        "yield_quintals": 25,
        "market_price_per_quintal": 2200,
        "msp_per_quintal": 2300,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "High",
        "notes": "Staple crop. MSP procurement active in Telangana. Rythu Bandhu ₹5,000/season.",
    },
    "Cotton": {
        "season": "Kharif",
        "duration_days": 180,
        "costs": {
            "seeds": 2400,
            "fertilizers": 4000,
            "pesticides": 4500,
            "irrigation": 2500,
            "labor": 7000,
            "machinery": 2500,
            "miscellaneous": 1800,
        },
        "yield_quintals": 8,
        "market_price_per_quintal": 6800,
        "msp_per_quintal": 7121,
        "subsidy_per_acre": 5000,
        "risk_level": "Medium",
        "water_requirement": "Medium",
        "notes": "Major cash crop. Bt Cotton dominant. Price volatile but MSP available.",
    },
    "Maize": {
        "season": "Kharif / Rabi",
        "duration_days": 100,
        "costs": {
            "seeds": 1800,
            "fertilizers": 3000,
            "pesticides": 1500,
            "irrigation": 2000,
            "labor": 5500,
            "machinery": 2500,
            "miscellaneous": 1200,
        },
        "yield_quintals": 30,
        "market_price_per_quintal": 2100,
        "msp_per_quintal": 2090,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "Medium",
        "notes": "Good demand from poultry/starch. Short duration. Suitable for intercropping.",
    },
    "Chilli": {
        "season": "Kharif",
        "duration_days": 150,
        "costs": {
            "seeds": 3000,
            "fertilizers": 5000,
            "pesticides": 6000,
            "irrigation": 3500,
            "labor": 10000,
            "machinery": 2000,
            "miscellaneous": 2000,
        },
        "yield_quintals": 8,
        "market_price_per_quintal": 14500,
        "msp_per_quintal": 0,
        "subsidy_per_acre": 5000,
        "risk_level": "High",
        "water_requirement": "Medium",
        "notes": "High profit potential but extremely price-volatile. No MSP safety net.",
    },
    "Turmeric": {
        "season": "Kharif",
        "duration_days": 240,
        "costs": {
            "seeds": 15000,
            "fertilizers": 5000,
            "pesticides": 2500,
            "irrigation": 4000,
            "labor": 12000,
            "machinery": 3000,
            "miscellaneous": 2500,
        },
        "yield_quintals": 25,
        "market_price_per_quintal": 12500,
        "msp_per_quintal": 0,
        "subsidy_per_acre": 5000,
        "risk_level": "Medium",
        "water_requirement": "High",
        "notes": "Nizamabad speciality. Long duration but excellent returns. Needs cold storage.",
    },
    "Soybean": {
        "season": "Kharif",
        "duration_days": 100,
        "costs": {
            "seeds": 2500,
            "fertilizers": 2000,
            "pesticides": 1500,
            "irrigation": 1000,
            "labor": 5000,
            "machinery": 2000,
            "miscellaneous": 1000,
        },
        "yield_quintals": 10,
        "market_price_per_quintal": 4600,
        "msp_per_quintal": 4892,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "Low",
        "notes": "Rain-fed friendly. Good for Adilabad/Nirmal. Nitrogen-fixing improves soil.",
    },
    "Red Gram (Tur)": {
        "season": "Kharif",
        "duration_days": 180,
        "costs": {
            "seeds": 1000,
            "fertilizers": 2000,
            "pesticides": 2000,
            "irrigation": 1500,
            "labor": 5000,
            "machinery": 2000,
            "miscellaneous": 1000,
        },
        "yield_quintals": 6,
        "market_price_per_quintal": 7200,
        "msp_per_quintal": 7550,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "Low",
        "notes": "Important pulse. MSP procurement strong. Drought-tolerant.",
    },
    "Bengal Gram (Chana)": {
        "season": "Rabi",
        "duration_days": 110,
        "costs": {
            "seeds": 2500,
            "fertilizers": 2000,
            "pesticides": 1500,
            "irrigation": 1500,
            "labor": 4500,
            "machinery": 2000,
            "miscellaneous": 1000,
        },
        "yield_quintals": 8,
        "market_price_per_quintal": 5400,
        "msp_per_quintal": 5650,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "Low",
        "notes": "Major rabi pulse. Rain-fed and irrigated. Good MSP procurement.",
    },
    "Groundnut": {
        "season": "Kharif",
        "duration_days": 120,
        "costs": {
            "seeds": 4000,
            "fertilizers": 2500,
            "pesticides": 1500,
            "irrigation": 2000,
            "labor": 6000,
            "machinery": 2500,
            "miscellaneous": 1500,
        },
        "yield_quintals": 10,
        "market_price_per_quintal": 5800,
        "msp_per_quintal": 6377,
        "subsidy_per_acre": 5000,
        "risk_level": "Medium",
        "water_requirement": "Medium",
        "notes": "Important oilseed. Pod yield depends on rainfall. MSP available.",
    },
    "Sunflower": {
        "season": "Rabi",
        "duration_days": 100,
        "costs": {
            "seeds": 1500,
            "fertilizers": 2500,
            "pesticides": 1200,
            "irrigation": 2000,
            "labor": 4500,
            "machinery": 2000,
            "miscellaneous": 1000,
        },
        "yield_quintals": 6,
        "market_price_per_quintal": 6200,
        "msp_per_quintal": 6760,
        "subsidy_per_acre": 5000,
        "risk_level": "Medium",
        "water_requirement": "Medium",
        "notes": "Rabi oilseed. Good for Medak/Sangareddy. MSP procurement available.",
    },
    "Sugarcane": {
        "season": "Annual",
        "duration_days": 365,
        "costs": {
            "seeds": 8000,
            "fertilizers": 6000,
            "pesticides": 2000,
            "irrigation": 8000,
            "labor": 15000,
            "machinery": 5000,
            "miscellaneous": 3000,
        },
        "yield_quintals": 350,
        "market_price_per_quintal": 315,
        "msp_per_quintal": 340,
        "subsidy_per_acre": 5000,
        "risk_level": "Low",
        "water_requirement": "Very High",
        "notes": "Annual crop. Guaranteed purchase by sugar factories. Needs heavy irrigation.",
    },
    "Tomato": {
        "season": "Rabi / Kharif",
        "duration_days": 90,
        "costs": {
            "seeds": 2000,
            "fertilizers": 4000,
            "pesticides": 4000,
            "irrigation": 3000,
            "labor": 10000,
            "machinery": 2000,
            "miscellaneous": 2000,
        },
        "yield_quintals": 100,
        "market_price_per_quintal": 1800,
        "msp_per_quintal": 0,
        "subsidy_per_acre": 5000,
        "risk_level": "Very High",
        "water_requirement": "Medium",
        "notes": "Extremely volatile prices (₹500–₹4000/qtl). High profit OR heavy loss.",
    },
    "Onion": {
        "season": "Rabi",
        "duration_days": 120,
        "costs": {
            "seeds": 3000,
            "fertilizers": 3500,
            "pesticides": 2500,
            "irrigation": 3000,
            "labor": 8000,
            "machinery": 2000,
            "miscellaneous": 2000,
        },
        "yield_quintals": 80,
        "market_price_per_quintal": 2200,
        "msp_per_quintal": 0,
        "subsidy_per_acre": 5000,
        "risk_level": "High",
        "water_requirement": "Medium",
        "notes": "Price-volatile. Needs good storage. Can be very profitable in right season.",
    },
    "Jowar (Sorghum)": {
        "season": "Kharif / Rabi",
        "duration_days": 110,
        "costs": {
            "seeds": 600,
            "fertilizers": 1500,
            "pesticides": 800,
            "irrigation": 500,
            "labor": 4000,
            "machinery": 1500,
            "miscellaneous": 800,
        },
        "yield_quintals": 12,
        "market_price_per_quintal": 3200,
        "msp_per_quintal": 3371,
        "subsidy_per_acre": 5000,
        "risk_level": "Very Low",
        "water_requirement": "Very Low",
        "notes": "Drought-tolerant millet. Low input cost. Rising demand as health food.",
    },
    "Mango": {
        "season": "Perennial",
        "duration_days": 365,
        "costs": {
            "seeds": 0,
            "fertilizers": 3000,
            "pesticides": 2500,
            "irrigation": 3000,
            "labor": 6000,
            "machinery": 1000,
            "miscellaneous": 2000,
        },
        "yield_quintals": 40,
        "market_price_per_quintal": 4500,
        "msp_per_quintal": 0,
        "subsidy_per_acre": 5000,
        "risk_level": "Medium",
        "water_requirement": "Medium",
        "notes": "Perennial — maintenance cost only (after 5-yr establishment). Benishan dominant.",
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  UI Strings
# ═══════════════════════════════════════════════════════════════════════

_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "Profit & Loss Calculator",
        "subtitle": "Estimate costs, revenue & profit for Telangana crops — compare and plan smarter",
        "tab_calc": "💰 Crop Economics",
        "tab_compare": "📊 Compare Crops",
        "tab_advisor": "🤖 AI Financial Advisor",
        "crop_label": "Select Crop",
        "acres_label": "Land Size (Acres)",
        "price_label": "Expected Price (₹/Quintal)",
        "yield_label": "Expected Yield (Quintals/Acre)",
        "calc_btn": "💰 Calculate Profit",
        "total_investment": "Total Investment",
        "gross_revenue": "Gross Revenue",
        "net_profit": "Net Profit",
        "roi": "Return on Investment",
        "cost_breakdown": "Cost Breakdown",
        "revenue_breakdown": "Revenue Breakdown",
        "subsidy_note": "Includes Rythu Bandhu",
        "per_acre": "per acre",
        "risk": "Risk Level",
        "water": "Water Requirement",
        "duration": "Crop Duration",
        "days": "days",
        "msp_note": "MSP",
        "market_note": "Market Price",
        "compare_label": "Select Crops to Compare (2–5)",
        "compare_btn": "📊 Compare",
        "profit_comparison": "Profit Comparison",
        "investment_comparison": "Investment Comparison",
        "roi_comparison": "ROI Comparison",
        "risk_comparison": "Risk Assessment",
        "advisor_label": "Describe your farm situation for personalised financial advice …",
        "advisor_placeholder": "e.g. 'I have 5 acres in Karimnagar, borewell, black soil. Budget is 2 lakhs. What should I grow for maximum profit?'",
        "advisor_btn": "🤖 Get Financial Plan",
        "thinking": "Analysing your farm economics …",
        "quick_questions": "Quick Questions",
        "profitable": "Profitable",
        "loss": "Loss",
    },
    "te": {
        "title": "లాభ-నష్ట కాల్క్యులేటర్",
        "subtitle": "తెలంగాణ పంటల ఖర్చు, ఆదాయం & లాభం అంచనా — పోల్చి తెలివిగా ప్రణాళిక",
        "tab_calc": "💰 పంట ఆర్థికం",
        "tab_compare": "📊 పంటలు పోల్చండి",
        "tab_advisor": "🤖 AI ఆర్థిక సలహాదారు",
        "crop_label": "పంట ఎంచుకోండి",
        "acres_label": "భూమి విస్తీర్ణం (ఎకరాలు)",
        "price_label": "అంచనా ధర (₹/క్వింటాల్)",
        "yield_label": "అంచనా దిగుబడి (క్వింటాళ్లు/ఎకరం)",
        "calc_btn": "💰 లాభం లెక్కించండి",
        "total_investment": "మొత్తం పెట్టుబడి",
        "gross_revenue": "మొత్తం ఆదాయం",
        "net_profit": "నికర లాభం",
        "roi": "పెట్టుబడిపై రాబడి",
        "cost_breakdown": "ఖర్చుల వివరాలు",
        "revenue_breakdown": "ఆదాయ వివరాలు",
        "subsidy_note": "రైతు బంధు చేర్చారు",
        "per_acre": "ఎకరానికి",
        "risk": "రిస్క్ స్థాయి",
        "water": "నీటి అవసరం",
        "duration": "పంట కాలం",
        "days": "రోజులు",
        "msp_note": "కనీస మద్దతు ధర",
        "market_note": "మార్కెట్ ధర",
        "compare_label": "పోల్చడానికి పంటలు ఎంచుకోండి (2–5)",
        "compare_btn": "📊 పోల్చండి",
        "profit_comparison": "లాభం పోలిక",
        "investment_comparison": "పెట్టుబడి పోలిక",
        "roi_comparison": "ROI పోలిక",
        "risk_comparison": "రిస్క్ అంచనా",
        "advisor_label": "మీ పొలం పరిస్థితిని వివరించండి, వ్యక్తిగత ఆర్థిక సలహా పొందండి …",
        "advisor_placeholder": "ఉదా. 'కరీంనగర్ లో 5 ఎకరాలు, బోరు బావి, నల్ల రేగడి మట్టి. బడ్జెట్ 2 లక్షలు. ఏ పంట నాటాలి?'",
        "advisor_btn": "🤖 ఆర్థిక ప్రణాళిక పొందండి",
        "thinking": "మీ పంట ఆర్థికాలను విశ్లేషిస్తోంది …",
        "quick_questions": "త్వరిత ప్రశ్నలు",
        "profitable": "లాభదాయకం",
        "loss": "నష్టం",
    },
    "hi": {
        "title": "लाभ-हानि कैलकुलेटर",
        "subtitle": "तेलंगाना फसलों की लागत, आय व मुनाफ़ा अनुमान — तुलना करें, बेहतर योजना बनाएं",
        "tab_calc": "💰 फसल अर्थशास्त्र",
        "tab_compare": "📊 फसलें तुलना",
        "tab_advisor": "🤖 AI वित्तीय सलाहकार",
        "crop_label": "फसल चुनें",
        "acres_label": "भूमि (एकड़)",
        "price_label": "अनुमानित मूल्य (₹/क्विंटल)",
        "yield_label": "अनुमानित उपज (क्विंटल/एकड़)",
        "calc_btn": "💰 मुनाफ़ा गणना करें",
        "total_investment": "कुल निवेश",
        "gross_revenue": "कुल आय",
        "net_profit": "शुद्ध लाभ",
        "roi": "निवेश पर प्रतिफल",
        "cost_breakdown": "लागत विवरण",
        "revenue_breakdown": "आय विवरण",
        "subsidy_note": "रायतू बंधु शामिल",
        "per_acre": "प्रति एकड़",
        "risk": "जोखिम स्तर",
        "water": "पानी की ज़रूरत",
        "duration": "फसल अवधि",
        "days": "दिन",
        "msp_note": "MSP",
        "market_note": "बाज़ार मूल्य",
        "compare_label": "तुलना के लिए फसलें चुनें (2–5)",
        "compare_btn": "📊 तुलना करें",
        "profit_comparison": "लाभ तुलना",
        "investment_comparison": "निवेश तुलना",
        "roi_comparison": "ROI तुलना",
        "risk_comparison": "जोखिम आकलन",
        "advisor_label": "अपने खेत के बारे में बताएं और व्यक्तिगत आर्थिक सलाह पाएं …",
        "advisor_placeholder": "जैसे 'करीमनगर में 5 एकड़, बोरवेल, काली मिट्टी। बजट 2 लाख। क्या बोएं?'",
        "advisor_btn": "🤖 वित्तीय योजना पाएं",
        "thinking": "आपकी फसल अर्थव्यवस्था का विश्लेषण …",
        "quick_questions": "त्वरित प्रश्न",
        "profitable": "लाभदायक",
        "loss": "हानि",
    },
}


def _ui(key: str, lang: str) -> str:
    if lang in _UI and key in _UI[lang]:
        return _UI[lang][key]
    en = _UI["en"].get(key, key)
    if lang == "en":
        return en
    try:
        return translator.from_english(en, lang)
    except Exception:
        return en


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

RISK_COLORS = {
    "Very Low": "#4CAF50",
    "Low": "#8BC34A",
    "Medium": "#FF9800",
    "High": "#F44336",
    "Very High": "#B71C1C",
}

RISK_SCORES = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Very High": 5}


def _calc_economics(crop_name: str, acres: float, price_override: float | None = None,
                    yield_override: float | None = None) -> dict[str, Any]:
    """Calculate complete economics for a crop."""
    data = CROP_ECONOMICS[crop_name]
    costs = data["costs"]

    total_cost_per_acre = sum(costs.values())
    total_cost = total_cost_per_acre * acres

    actual_yield = yield_override if yield_override is not None else data["yield_quintals"]
    actual_price = price_override if price_override is not None else data["market_price_per_quintal"]

    gross_revenue_per_acre = actual_yield * actual_price
    gross_revenue = gross_revenue_per_acre * acres

    subsidy_total = data["subsidy_per_acre"] * acres

    net_profit_per_acre = gross_revenue_per_acre - total_cost_per_acre + data["subsidy_per_acre"]
    net_profit = net_profit_per_acre * acres

    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0

    return {
        "crop": crop_name,
        "acres": acres,
        "costs": {k: v * acres for k, v in costs.items()},
        "cost_per_acre": total_cost_per_acre,
        "total_cost": total_cost,
        "yield_per_acre": actual_yield,
        "total_yield": actual_yield * acres,
        "price_per_quintal": actual_price,
        "gross_revenue_per_acre": gross_revenue_per_acre,
        "gross_revenue": gross_revenue,
        "subsidy_per_acre": data["subsidy_per_acre"],
        "subsidy_total": subsidy_total,
        "net_profit_per_acre": net_profit_per_acre,
        "net_profit": net_profit,
        "roi": roi,
        "msp": data["msp_per_quintal"],
        "risk": data["risk_level"],
        "water": data["water_requirement"],
        "duration": data["duration_days"],
        "season": data["season"],
        "notes": data["notes"],
    }


# ═══════════════════════════════════════════════════════════════════════
#  Tab 1 — Crop Economics Calculator
# ═══════════════════════════════════════════════════════════════════════

def _render_calculator(lang: str, palette: dict) -> None:
    crop_names = list(CROP_ECONOMICS.keys())

    c1, c2 = st.columns([2, 1])
    with c1:
        crop = st.selectbox(_ui("crop_label", lang), crop_names, key="pc_crop")
    with c2:
        acres = st.number_input(_ui("acres_label", lang), min_value=0.5, max_value=500.0,
                                value=5.0, step=0.5, key="pc_acres")

    data = CROP_ECONOMICS[crop]

    # Default values
    price_adj = data["market_price_per_quintal"]
    yield_adj = float(data["yield_quintals"])

    # Adjustable parameters
    with st.expander("⚙️ Adjust Price & Yield Estimates", expanded=False):
        adj1, adj2 = st.columns(2)
        with adj1:
            price_adj = st.number_input(
                _ui("price_label", lang),
                min_value=0, max_value=100000,
                value=data["market_price_per_quintal"],
                step=50, key="pc_price",
            )
        with adj2:
            yield_adj = st.number_input(
                _ui("yield_label", lang),
                min_value=0.0, max_value=1000.0,
                value=float(data["yield_quintals"]),
                step=0.5, key="pc_yield",
            )
        if data["msp_per_quintal"] > 0:
            st.caption(f"📌 {_ui('msp_note', lang)}: ₹{data['msp_per_quintal']:,.0f}/quintal  |  "
                       f"{_ui('market_note', lang)}: ₹{data['market_price_per_quintal']:,.0f}/quintal")

    econ = _calc_economics(crop, acres, price_adj, yield_adj)

    # ── KPI Cards ──────────────────────────────────────────────────────
    st.markdown("")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(_ui("total_investment", lang), f"₹{econ['total_cost']:,.0f}",
              delta=f"₹{econ['cost_per_acre']:,.0f} {_ui('per_acre', lang)}", delta_color="off")
    k2.metric(_ui("gross_revenue", lang), f"₹{econ['gross_revenue']:,.0f}",
              delta=f"₹{econ['gross_revenue_per_acre']:,.0f} {_ui('per_acre', lang)}", delta_color="off")

    profit_color = "normal" if econ["net_profit"] >= 0 else "inverse"
    k3.metric(_ui("net_profit", lang), f"₹{econ['net_profit']:,.0f}",
              delta=f"₹{econ['net_profit_per_acre']:,.0f} {_ui('per_acre', lang)}", delta_color=profit_color)
    k4.metric(_ui("roi", lang), f"{econ['roi']:.1f}%",
              delta=_ui("profitable", lang) if econ["roi"] > 0 else _ui("loss", lang),
              delta_color="normal" if econ["roi"] > 0 else "inverse")

    # ── Info badges ────────────────────────────────────────────────────
    risk_color = RISK_COLORS.get(data["risk_level"], "#607D8B")
    i1, i2, i3, i4 = st.columns(4)
    i1.markdown(f"**{_ui('risk', lang)}:** <span style='color:{risk_color};font-weight:700'>"
                f"{data['risk_level']}</span>", unsafe_allow_html=True)
    i2.markdown(f"**{_ui('water', lang)}:** {data['water_requirement']}")
    i3.markdown(f"**{_ui('duration', lang)}:** {data['duration_days']} {_ui('days', lang)}")
    i4.markdown(f"**{_ui('subsidy_note', lang)}:** ₹{econ['subsidy_total']:,.0f}")

    st.markdown("")

    # ── Charts ─────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown(f"#### {_ui('cost_breakdown', lang)}")
        cost_labels = list(econ["costs"].keys())
        cost_vals = list(econ["costs"].values())
        fig_cost = go.Figure(data=[go.Pie(
            labels=[l.capitalize() for l in cost_labels],
            values=cost_vals,
            hole=0.45,
            marker=dict(colors=["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0",
                                "#9966FF", "#FF9F40", "#C9CBCF"]),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>",
        )])
        fig_cost.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with ch2:
        st.markdown(f"#### {_ui('revenue_breakdown', lang)}")
        rev_items = ["Crop Sale", "Rythu Bandhu Subsidy"]
        rev_vals = [econ["gross_revenue"], econ["subsidy_total"]]
        cost_item = econ["total_cost"]

        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=["Revenue"], y=[econ["gross_revenue"]],
            name="Crop Sale", marker_color="#4CAF50",
            hovertemplate="Crop Sale: ₹%{y:,.0f}<extra></extra>",
        ))
        fig_rev.add_trace(go.Bar(
            x=["Revenue"], y=[econ["subsidy_total"]],
            name="Subsidy", marker_color="#FF9800",
            hovertemplate="Subsidy: ₹%{y:,.0f}<extra></extra>",
        ))
        fig_rev.add_trace(go.Bar(
            x=["Cost"], y=[cost_item],
            name="Total Cost", marker_color="#F44336",
            hovertemplate="Total Cost: ₹%{y:,.0f}<extra></extra>",
        ))
        fig_rev.update_layout(
            barmode="stack", height=320,
            margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis_title="₹",
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    # ── Notes ──────────────────────────────────────────────────────────
    if data.get("notes"):
        st.info(f"📝 {data['notes']}")


# ═══════════════════════════════════════════════════════════════════════
#  Tab 2 — Crop Comparison
# ═══════════════════════════════════════════════════════════════════════

def _render_comparison(lang: str, palette: dict) -> None:
    crop_names = list(CROP_ECONOMICS.keys())

    sel = st.multiselect(
        _ui("compare_label", lang),
        crop_names,
        default=["Rice", "Cotton", "Chilli"],
        max_selections=5,
        key="pc_compare_crops",
    )

    if len(sel) < 2:
        st.warning("Please select at least 2 crops to compare.")
        return

    comp_acres = st.number_input(_ui("acres_label", lang), min_value=0.5, max_value=500.0,
                                 value=5.0, step=0.5, key="pc_comp_acres")

    results = [_calc_economics(c, comp_acres) for c in sel]

    # ── Summary Table ──────────────────────────────────────────────────
    table_data = []
    for r in results:
        table_data.append({
            "Crop": r["crop"],
            f"{_ui('total_investment', lang)} (₹)": f"₹{r['total_cost']:,.0f}",
            f"{_ui('gross_revenue', lang)} (₹)": f"₹{r['gross_revenue']:,.0f}",
            f"{_ui('net_profit', lang)} (₹)": f"₹{r['net_profit']:,.0f}",
            f"{_ui('roi', lang)} (%)": f"{r['roi']:.1f}%",
            _ui("risk", lang): r["risk"],
        })
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # ── Profit Comparison Bar Chart ────────────────────────────────────
    st.markdown(f"#### {_ui('profit_comparison', lang)}")
    colors = ["#4CAF50" if r["net_profit"] >= 0 else "#F44336" for r in results]
    fig_profit = go.Figure(data=[go.Bar(
        x=[r["crop"] for r in results],
        y=[r["net_profit"] for r in results],
        marker_color=colors,
        text=[f"₹{r['net_profit']:,.0f}" for r in results],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Net Profit: ₹%{y:,.0f}<extra></extra>",
    )])
    fig_profit.update_layout(
        height=350, yaxis_title="Net Profit (₹)",
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_profit, use_container_width=True)

    # ── ROI Comparison ─────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown(f"#### {_ui('roi_comparison', lang)}")
        fig_roi = go.Figure(data=[go.Bar(
            x=[r["crop"] for r in results],
            y=[r["roi"] for r in results],
            marker_color=["#2196F3"] * len(results),
            text=[f"{r['roi']:.1f}%" for r in results],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>ROI: %{y:.1f}%<extra></extra>",
        )])
        fig_roi.update_layout(
            height=300, yaxis_title="ROI (%)",
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_roi, use_container_width=True)

    with ch2:
        st.markdown(f"#### {_ui('risk_comparison', lang)}")
        risk_vals = [RISK_SCORES.get(r["risk"], 3) for r in results]
        risk_colors = [RISK_COLORS.get(r["risk"], "#607D8B") for r in results]
        fig_risk = go.Figure(data=[go.Bar(
            x=[r["crop"] for r in results],
            y=risk_vals,
            marker_color=risk_colors,
            text=[r["risk"] for r in results],
            textposition="inside",
            hovertemplate="<b>%{x}</b><br>Risk: %{text}<extra></extra>",
        )])
        fig_risk.update_layout(
            height=300,
            yaxis=dict(title="Risk Score", tickmode="array", tickvals=[1, 2, 3, 4, 5],
                       ticktext=["Very Low", "Low", "Medium", "High", "Very High"]),
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    # ── Radar Chart — Overall Score ────────────────────────────────────
    st.markdown("#### Overall Crop Score")
    fig_radar = go.Figure()
    categories = ["Profit", "Low Risk", "Low Water", "Short Duration", "MSP Safety"]

    for r in results:
        data_r = CROP_ECONOMICS[r["crop"]]
        profit_score = min(max(r["roi"] / 20, 0), 5)  # 0–100% → 0–5
        risk_score = 6 - RISK_SCORES.get(r["risk"], 3)  # invert: low risk = high
        water_map = {"Very Low": 5, "Low": 4, "Medium": 3, "High": 2, "Very High": 1}
        water_score = water_map.get(data_r["water_requirement"], 3)
        duration_score = max(1, 5 - data_r["duration_days"] / 100)
        msp_score = 4 if data_r["msp_per_quintal"] > 0 else 1

        fig_radar.add_trace(go.Scatterpolar(
            r=[profit_score, risk_score, water_score, duration_score, msp_score],
            theta=categories,
            fill="toself",
            name=r["crop"],
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        height=400,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # ── AI Recommendation ──────────────────────────────────────────────
    best = max(results, key=lambda r: r["roi"])
    safest = min(results, key=lambda r: RISK_SCORES.get(r["risk"], 3))

    st.success(f"💡 **Highest ROI:** {best['crop']} ({best['roi']:.1f}%) — "
               f"Net profit ₹{best['net_profit']:,.0f} on {comp_acres} acres")
    if safest["crop"] != best["crop"]:
        st.info(f"🛡️ **Lowest Risk:** {safest['crop']} ({safest['risk']}) — "
                f"Net profit ₹{safest['net_profit']:,.0f}")


# ═══════════════════════════════════════════════════════════════════════
#  Tab 3 — AI Financial Advisor
# ═══════════════════════════════════════════════════════════════════════

def _render_ai_advisor(lang: str) -> None:
    result = st.session_state.get("fin_plan_result")

    q = st.text_area(
        _ui("advisor_label", lang),
        placeholder=_ui("advisor_placeholder", lang),
        height=100,
        key="fin_plan_input",
    )

    if st.button(_ui("advisor_btn", lang), type="primary", key="fin_plan_btn"):
        if not q.strip():
            st.warning("Please describe your farm and budget.")
        else:
            # Build comprehensive context from crop economics
            econ_ctx = "\n".join(
                f"- {name}: Cost ₹{sum(d['costs'].values()):,}/acre, "
                f"Yield {d['yield_quintals']}q/acre, Price ₹{d['market_price_per_quintal']}/q, "
                f"MSP ₹{d['msp_per_quintal']}/q, "
                f"Profit ₹{d['yield_quintals'] * d['market_price_per_quintal'] - sum(d['costs'].values()) + d['subsidy_per_acre']:,}/acre, "
                f"ROI {(d['yield_quintals'] * d['market_price_per_quintal'] - sum(d['costs'].values()) + d['subsidy_per_acre']) / sum(d['costs'].values()) * 100:.0f}%, "
                f"Risk: {d['risk_level']}, Water: {d['water_requirement']}, "
                f"Duration: {d['duration_days']} days, Season: {d['season']}"
                for name, d in CROP_ECONOMICS.items()
            )

            prompt = f"""You are KrishiSaathi, an expert agricultural financial advisor for Telangana farmers.

=== TELANGANA CROP ECONOMICS DATABASE (per acre, INR) ===
{econ_ctx}

=== GOVERNMENT SUBSIDIES ===
- Rythu Bandhu: ₹5,000/acre/season (₹10,000/year) for all land-owning farmers
- Rythu Bima: ₹5,00,000 life insurance (free for Rythu Bandhu beneficiaries)
- PM-KISAN: ₹6,000/year for eligible farmers
- Crop Insurance (PM-FASAL): Premium subsidy available

Farmer's question: {q}

Provide a DETAILED financial plan. You MUST include:
1. EXACT cost breakdown per acre for recommended crop(s) (seeds, fertilizers, pesticides, irrigation, labor, machinery)
2. Expected yield and revenue calculation with actual market prices
3. Net profit and ROI percentage
4. If multiple crops recommended, provide a split-acre strategy with combined profit
5. Risk assessment and mitigation (MSP safety, crop insurance)
6. Government subsidies the farmer can claim and how to apply
7. Monthly cash-flow timeline (when money goes out vs comes in)
8. Comparison with alternate crops showing why your recommendation is better

Use REAL numbers from the database above. Format with tables and clear sections.
Be encouraging but honest about risks. If budget is tight, suggest low-investment crops first."""

            with st.spinner(_ui("thinking", lang)):
                t0 = time.time()
                try:
                    raw = llm.generate(prompt, role="agent")
                    answer = raw if isinstance(raw, str) else raw.get("text", str(raw))
                    elapsed = time.time() - t0
                    result = {"answer": answer, "elapsed": elapsed}
                    st.session_state["fin_plan_result"] = result
                except Exception as e:
                    logger.error("AI financial advisor error: %s", e)
                    st.error(f"Could not generate plan: {e}")
                    result = None

    if result:
        st.divider()
        st.markdown("### 📋 Your Financial Plan")
        st.markdown(result.get("answer", ""))
        render_voice_output(result.get("answer", ""), language=lang, key_suffix="fin_plan")
        st.caption(f"⏱️ {result.get('elapsed', 0):.1f}s")

    # ── Quick questions ────────────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "5 acres, black soil, 2L budget",
            "Most profitable Kharif crop?",
            "Cotton vs Chilli — which earns more?",
            "Low-investment crops for 2 acres",
            "How to earn ₹5 lakh from farming?",
        ],
        "te": [
            "5 ఎకరాలు, నల్ల మట్టి, 2L బడ్జెట్",
            "లాభదాయక ఖరీఫ్ పంట?",
            "పత్తి vs మిర్చి — ఏది ఎక్కువ?",
            "2 ఎకరాలకు తక్కువ పెట్టుబడి పంటలు",
            "వ్యవసాయంలో 5 లక్షలు ఎలా?",
        ],
        "hi": [
            "5 एकड़, काली मिट्टी, 2L बजट",
            "सबसे लाभदायक खरीफ फसल?",
            "कपास vs मिर्ची — कौन ज़्यादा?",
            "2 एकड़ कम निवेश फसलें",
            "खेती से 5 लाख कैसे कमाएं?",
        ],
    }
    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown(f"**💡 {_ui('quick_questions', lang)}:**")
    cols = st.columns(len(qs))
    for i, (col, q_txt) in enumerate(zip(cols, qs)):
        with col:
            label = q_txt[:28] + "…" if len(q_txt) > 28 else q_txt
            if st.button(label, key=f"finq_{i}", use_container_width=True):
                st.session_state["fin_plan_input"] = q_txt
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    user = require_auth()
    if not user:
        return
    lang = render_sidebar()
    palette = get_palette()

    render_page_header(
        _ui("title", lang),
        _ui("subtitle", lang),
        icon_name="rupee",
    )

    tab_calc, tab_compare, tab_advisor = st.tabs([
        _ui("tab_calc", lang),
        _ui("tab_compare", lang),
        _ui("tab_advisor", lang),
    ])

    with tab_calc:
        _render_calculator(lang, palette)

    with tab_compare:
        _render_comparison(lang, palette)

    with tab_advisor:
        _render_ai_advisor(lang)


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
