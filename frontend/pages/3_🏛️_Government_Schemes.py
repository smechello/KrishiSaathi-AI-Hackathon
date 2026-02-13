"""Government Schemes — Browse, check eligibility & apply for farm schemes.

Explore central and Telangana state schemes with eligibility details,
documents required, benefit amounts, and direct application links.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

import streamlit as st

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402
from backend.agents.scheme_agent import SchemeAgent  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Government Schemes", page_icon="🏛️", layout="wide")

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "🏛️ Government Schemes",
        "subtitle": "Central & Telangana schemes for farmers — eligibility, benefits & how to apply",
        "tab_browse": "📋 Browse Schemes",
        "tab_eligibility": "✅ Check Eligibility",
        "tab_advisor": "🤖 AI Scheme Advisor",
        "filter_type": "Scheme Type",
        "all_types": "All Schemes",
        "state": "State (Telangana)",
        "central": "Central (All India)",
        "search_label": "Search schemes",
        "search_placeholder": "e.g. 'subsidy', 'insurance', 'irrigation'",
        "benefit": "Benefit",
        "eligibility": "Eligibility",
        "documents": "Documents Required",
        "how_to_apply": "How to Apply",
        "portal": "Official Portal",
        "helpline": "Helpline",
        "no_results": "No schemes match your search.",
        "elig_header": "Check Your Eligibility",
        "elig_land": "Land holding (acres)",
        "elig_category": "Category",
        "elig_state": "State",
        "elig_income": "Annual income (₹)",
        "elig_age": "Age",
        "elig_btn": "✅ Check Eligibility",
        "elig_result": "Schemes You May Be Eligible For",
        "advisor_label": "Ask about any government scheme, subsidy or benefit …",
        "advisor_placeholder": "e.g. 'What documents do I need for Rythu Bandhu?' or 'Am I eligible for PM-KISAN?'",
        "advisor_btn": "🤖 Get Scheme Advice",
        "thinking": "Checking scheme details …",
        "summary_header": "Scheme Information",
    },
    "te": {
        "title": "🏛️ ప్రభుత్వ పథకాలు",
        "subtitle": "రైతుల కోసం కేంద్ర & తెలంగాణ పథకాలు — అర్హత, ప్రయోజనాలు & దరఖాస్తు విధానం",
        "tab_browse": "📋 పథకాలు చూడండి",
        "tab_eligibility": "✅ అర్హత తనిఖీ",
        "tab_advisor": "🤖 AI పథకం సలహాదారు",
        "filter_type": "పథకం రకం",
        "all_types": "అన్ని పథకాలు",
        "state": "రాష్ట్రం (తెలంగాణ)",
        "central": "కేంద్రం (అఖిల భారత)",
        "search_label": "పథకాలు వెతకండి",
        "search_placeholder": "ఉదా. 'సబ్సిడీ', 'బీమా', 'నీటిపారుదల'",
        "benefit": "ప్రయోజనం",
        "eligibility": "అర్హత",
        "documents": "అవసరమైన పత్రాలు",
        "how_to_apply": "దరఖాస్తు విధానం",
        "portal": "అధికారిక పోర్టల్",
        "helpline": "సహాయ నంబర్",
        "no_results": "మీ శోధనకు పథకాలు లేవు.",
        "elig_header": "మీ అర్హతను తనిఖీ చేయండి",
        "elig_land": "భూమి విస్తీర్ణం (ఎకరాలు)",
        "elig_category": "వర్గం",
        "elig_state": "రాష్ట్రం",
        "elig_income": "వార్షిక ఆదాయం (₹)",
        "elig_age": "వయస్సు",
        "elig_btn": "✅ అర్హత తనిఖీ చేయండి",
        "elig_result": "మీకు అర్హత ఉన్న పథకాలు",
        "advisor_label": "ఏదైనా ప్రభుత్వ పథకం, సబ్సిడీ లేదా ప్రయోజనం గురించి అడగండి …",
        "advisor_placeholder": "ఉదా. 'రైతుబంధు కోసం ఏ పత్రాలు అవసరం?'",
        "advisor_btn": "🤖 పథకం సలహా పొందండి",
        "thinking": "పథకం వివరాలు తనిఖీ చేస్తోంది …",
        "summary_header": "పథకం సమాచారం",
    },
    "hi": {
        "title": "🏛️ सरकारी योजनाएं",
        "subtitle": "किसानों के लिए केंद्र व तेलंगाना योजनाएं — पात्रता, लाभ व आवेदन",
        "tab_browse": "📋 योजनाएं देखें",
        "tab_eligibility": "✅ पात्रता जांचें",
        "tab_advisor": "🤖 AI योजना सलाहकार",
        "filter_type": "योजना प्रकार",
        "all_types": "सभी योजनाएं",
        "state": "राज्य (तेलंगाना)",
        "central": "केंद्र (अखिल भारत)",
        "search_label": "योजनाएं खोजें",
        "search_placeholder": "जैसे 'सब्सिडी', 'बीमा', 'सिंचाई'",
        "benefit": "लाभ",
        "eligibility": "पात्रता",
        "documents": "आवश्यक दस्तावेज",
        "how_to_apply": "आवेदन कैसे करें",
        "portal": "आधिकारिक पोर्टल",
        "helpline": "हेल्पलाइन",
        "no_results": "आपकी खोज से कोई योजना नहीं मिली।",
        "elig_header": "अपनी पात्रता जांचें",
        "elig_land": "भूमि (एकड़)",
        "elig_category": "श्रेणी",
        "elig_state": "राज्य",
        "elig_income": "वार्षिक आय (₹)",
        "elig_age": "आयु",
        "elig_btn": "✅ पात्रता जांचें",
        "elig_result": "आपके लिए पात्र योजनाएं",
        "advisor_label": "किसी भी सरकारी योजना, सब्सिडी या लाभ के बारे में पूछें …",
        "advisor_placeholder": "जैसे 'रायतु बंधु के लिए कौन से दस्तावेज चाहिए?'",
        "advisor_btn": "🤖 योजना सलाह पाएं",
        "thinking": "योजना विवरण जांच रहा है …",
        "summary_header": "योजना जानकारी",
    },
}


def _ui(lang: str, key: str) -> str:
    return _UI.get(lang, _UI["en"]).get(key, _UI["en"][key])


# ── Cached resources ───────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading scheme data …")
def _get_scheme_agent() -> SchemeAgent:
    try:
        rag = RAGEngine()
    except Exception:
        rag = None  # type: ignore[assignment]
    return SchemeAgent(rag_engine=rag)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_schemes_database() -> list[dict]:
    """Load the full schemes_database.json."""
    path = os.path.join(_PROJECT_ROOT, "backend", "data", "schemes_database.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return raw.get("schemes", []) if isinstance(raw, dict) else raw
    except Exception:
        return []


# ── Page ───────────────────────────────────────────────────────────────

def main() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE

    lang = render_sidebar()
    agent = _get_scheme_agent()
    schemes = _load_schemes_database()

    # ── Header ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center; padding:0.5rem 0 0.2rem 0;">
            <h1 style="margin:0; color:#2e7d32;">{_ui(lang, 'title')}</h1>
            <p style="color:#666; margin:0 0 0.8rem 0;">{_ui(lang, 'subtitle')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Summary KPIs ───────────────────────────────────────────────────
    state_count = sum(1 for s in schemes if s.get("type") == "state")
    central_count = sum(1 for s in schemes if s.get("type") == "central")
    active_count = sum(1 for s in schemes if s.get("active", True))

    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1:
        st.metric("📋 Total Schemes", len(schemes))
    with kc2:
        st.metric("🏛️ Telangana State", state_count)
    with kc3:
        st.metric("🇮🇳 Central Govt", central_count)
    with kc4:
        st.metric("✅ Active Now", active_count)
    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_browse, tab_elig, tab_advisor = st.tabs([
        _ui(lang, "tab_browse"),
        _ui(lang, "tab_eligibility"),
        _ui(lang, "tab_advisor"),
    ])

    with tab_browse:
        _render_browse(schemes, lang)

    with tab_elig:
        _render_eligibility(agent, schemes, lang)

    with tab_advisor:
        _render_advisor(agent, lang)


# ── Tab 1: Browse Schemes ─────────────────────────────────────────────

def _render_browse(schemes: list[dict], lang: str) -> None:
    """Filterable scheme cards with full details."""

    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        type_filter = st.selectbox(
            _ui(lang, "filter_type"),
            options=["all", "state", "central"],
            format_func=lambda x: {
                "all": _ui(lang, "all_types"),
                "state": _ui(lang, "state"),
                "central": _ui(lang, "central"),
            }.get(x, x),
            key="scheme_type_filter",
        )
    with fcol2:
        search_text = st.text_input(
            _ui(lang, "search_label"),
            placeholder=_ui(lang, "search_placeholder"),
            key="scheme_search",
        )

    # ── Filter ─────────────────────────────────────────────────────────
    filtered = schemes
    if type_filter != "all":
        filtered = [s for s in filtered if s.get("type") == type_filter]
    if search_text:
        q = search_text.lower()
        filtered = [
            s for s in filtered
            if q in s.get("name", "").lower()
            or q in s.get("description", "").lower()
            or q in json.dumps(s.get("benefits", {})).lower()
        ]

    if not filtered:
        st.warning(_ui(lang, "no_results"))
        return

    # ── Render scheme cards ────────────────────────────────────────────
    for scheme in filtered:
        _render_scheme_card(scheme, lang)


def _render_scheme_card(scheme: dict, lang: str) -> None:
    """Render a single scheme as an expandable card."""
    name = scheme.get("name", "Unknown Scheme")
    s_type = scheme.get("type", "")
    badge = "🏛️ State" if s_type == "state" else "🇮🇳 Central"
    active = scheme.get("active", True)
    status_badge = "🟢 Active" if active else "🔴 Inactive"

    benefits = scheme.get("benefits", {})
    if isinstance(benefits, dict):
        benefit_amount = benefits.get("amount", "—")
        benefit_freq = benefits.get("frequency", "")
    else:
        benefit_amount = str(benefits)
        benefit_freq = ""

    with st.expander(f"{badge}  **{name}**  —  {benefit_amount}  {status_badge}", expanded=False):
        st.markdown(f"_{scheme.get('description', '')}_")

        col1, col2 = st.columns(2)

        with col1:
            # Benefits
            st.markdown(f"#### 💰 {_ui(lang, 'benefit')}")
            st.markdown(f"**Amount:** {benefit_amount}")
            if benefit_freq:
                st.markdown(f"**Frequency:** {benefit_freq}")
            if isinstance(benefits, dict) and benefits.get("mode"):
                st.markdown(f"**Mode:** {benefits['mode']}")

            # Eligibility
            st.markdown(f"#### ✅ {_ui(lang, 'eligibility')}")
            elig = scheme.get("eligibility", {})
            if isinstance(elig, dict):
                for k, v in elig.items():
                    label = k.replace("_", " ").title()
                    st.markdown(f"- **{label}:** {v}")
            elif isinstance(elig, list):
                for item in elig:
                    st.markdown(f"- {item}")

        with col2:
            # Documents
            st.markdown(f"#### 📄 {_ui(lang, 'documents')}")
            docs = scheme.get("documents_required", scheme.get("documents", []))
            if docs:
                for doc in docs:
                    st.markdown(f"- {doc}")
            else:
                st.markdown("- Contact local office")

            # Application
            st.markdown(f"#### 📝 {_ui(lang, 'how_to_apply')}")
            process = scheme.get("application_process", "")
            if process:
                st.markdown(process)

            # Links
            portal = scheme.get("portal", "")
            helpline = scheme.get("helpline", "")
            if portal:
                st.markdown(f"🌐 **{_ui(lang, 'portal')}:** [{portal}]({portal})")
            if helpline:
                st.markdown(f"📞 **{_ui(lang, 'helpline')}:** {helpline}")


# ── Tab 2: Eligibility Checker ────────────────────────────────────────

def _render_eligibility(agent: SchemeAgent, schemes: list[dict], lang: str) -> None:
    """Simple eligibility checker form."""

    st.subheader(f"✅ {_ui(lang, 'elig_header')}")

    col1, col2 = st.columns(2)

    with col1:
        land_acres = st.number_input(
            _ui(lang, "elig_land"),
            min_value=0.0, max_value=1000.0, value=2.0, step=0.5,
            key="elig_land",
        )
        category = st.selectbox(
            _ui(lang, "elig_category"),
            options=["General", "OBC", "SC", "ST", "Minority"],
            key="elig_category",
        )
        age = st.number_input(
            _ui(lang, "elig_age"),
            min_value=18, max_value=100, value=35,
            key="elig_age",
        )

    with col2:
        state = st.selectbox(
            _ui(lang, "elig_state"),
            options=["Telangana", "Andhra Pradesh", "Karnataka", "Maharashtra", "Other"],
            key="elig_state",
        )
        income = st.number_input(
            _ui(lang, "elig_income"),
            min_value=0, max_value=10000000, value=200000, step=50000,
            key="elig_income",
        )
        has_land = st.checkbox("I own agricultural land", value=True, key="elig_has_land")

    check_btn = st.button(_ui(lang, "elig_btn"), type="primary", use_container_width=True, key="btn_elig")

    if check_btn:
        # Build profile and run matching
        eligible_schemes = []
        for scheme in schemes:
            eligible = True
            s_elig = scheme.get("eligibility", {})

            # State check
            s_state = ""
            if isinstance(s_elig, dict):
                s_state = s_elig.get("state", "All India")
            if "telangana only" in str(s_state).lower() and state != "Telangana":
                eligible = False

            # Land check
            if isinstance(s_elig, dict):
                land_req = s_elig.get("land_holding", "").lower()
                if "land-owning" in land_req or "land holding" in land_req:
                    if not has_land:
                        eligible = False

            # Age check
            if isinstance(s_elig, dict):
                age_req = s_elig.get("age", "")
                if age_req:
                    parts = age_req.replace("years", "").strip().split("-")
                    if len(parts) == 2:
                        try:
                            lo, hi = int(parts[0].strip()), int(parts[1].strip())
                            if age < lo or age > hi:
                                eligible = False
                        except ValueError:
                            pass

            if eligible:
                eligible_schemes.append(scheme)

        if eligible_schemes:
            st.success(f"🎉 You may be eligible for **{len(eligible_schemes)}** schemes!")
            st.subheader(f"📋 {_ui(lang, 'elig_result')}")
            for scheme in eligible_schemes:
                _render_scheme_card(scheme, lang)
        else:
            st.warning("No matching schemes found. Try adjusting your profile or check with your local agriculture office.")


# ── Tab 3: AI Scheme Advisor ──────────────────────────────────────────

def _render_advisor(agent: SchemeAgent, lang: str) -> None:
    """Free-form AI-powered scheme advice."""

    st.markdown(f"#### {_ui(lang, 'tab_advisor')}")

    query = st.text_area(
        _ui(lang, "advisor_label"),
        placeholder=_ui(lang, "advisor_placeholder"),
        height=100,
        key="scheme_advisor_query",
    )

    ask_btn = st.button(
        _ui(lang, "advisor_btn"),
        type="primary",
        use_container_width=True,
        key="btn_scheme_advisor",
        disabled=not query,
    )

    if ask_btn and query:
        query_en = query
        if lang != "en":
            query_en = translator.to_english(query, src=lang)

        with st.spinner(_ui(lang, "thinking")):
            start = time.time()
            try:
                result = agent.answer_scheme_query(query_en)
                elapsed = time.time() - start

                answer = result.get("answer", "")
                sources = result.get("sources", [])

                if lang != "en" and answer:
                    answer = translator.from_english(answer, dest=lang)

                st.subheader(f"📋 {_ui(lang, 'summary_header')}")
                st.markdown(answer)

                if sources:
                    src_str = " · ".join(f"`{s}`" for s in sources)
                    st.caption(f"📚 Sources: {src_str}")
                st.caption(f"⏱️ {elapsed:.1f}s")

            except Exception as exc:
                logger.error("Scheme advisor error: %s", exc, exc_info=True)
                st.error(f"Query failed: {exc}")

    elif ask_btn and not query:
        st.warning(_ui(lang, "no_results"))

    # ── Quick questions ────────────────────────────────────────────────
    st.divider()
    quick_qs = {
        "en": [
            "What is Rythu Bandhu and how to apply?",
            "Am I eligible for PM-KISAN?",
            "How to get subsidy for drip irrigation?",
            "What insurance schemes exist for farmers?",
            "Documents needed for Kisan Credit Card",
        ],
        "te": [
            "రైతుబంధు అంటే ఏమిటి, ఎలా దరఖాస్తు చేయాలి?",
            "నాకు PM-KISAN అర్హత ఉందా?",
            "బిందు సేద్యానికి సబ్సిడీ ఎలా పొందాలి?",
            "రైతుల కోసం ఏ బీమా పథకాలు ఉన్నాయి?",
            "కిసాన్ క్రెడిట్ కార్డ్ కోసం అవసరమైన పత్రాలు",
        ],
        "hi": [
            "रायतु बंधु क्या है और कैसे आवेदन करें?",
            "क्या मैं PM-KISAN के लिए पात्र हूं?",
            "ड्रिप सिंचाई के लिए सब्सिडी कैसे पाएं?",
            "किसानों के लिए कौन सी बीमा योजनाएं हैं?",
            "किसान क्रेडिट कार्ड के लिए दस्तावेज",
        ],
    }

    qs = quick_qs.get(lang, quick_qs["en"])
    st.markdown("**💡 Quick Questions:**")
    cols = st.columns(len(qs))
    for i, (col, q) in enumerate(zip(cols, qs)):
        with col:
            if st.button(q[:28] + "…" if len(q) > 28 else q, key=f"sq_{i}", use_container_width=True):
                st.session_state["scheme_advisor_query"] = q
                st.rerun()


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    main()
