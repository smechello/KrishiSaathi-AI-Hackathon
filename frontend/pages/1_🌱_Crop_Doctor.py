"""Crop Doctor — Image-based & text-based crop disease diagnosis.

Upload a photo of your diseased crop or describe symptoms to get an instant
AI-powered diagnosis with treatment recommendations.
"""

from __future__ import annotations

import logging
import os
import sys
import time

import streamlit as st
from PIL import Image

# ── Project root ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.config import Config  # noqa: E402
from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402
from backend.agents.crop_doctor_agent import CropDoctorAgent  # noqa: E402
from backend.services.translation_service import translator  # noqa: E402
from frontend.components.sidebar import render_sidebar  # noqa: E402
from frontend.components.theme import render_page_header  # noqa: E402
from frontend.components.auth import require_auth  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(page_title="KrishiSaathi — Crop Doctor", page_icon="🌱", layout="wide")

# ── Localised UI strings ──────────────────────────────────────────────
_UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "🌱 Crop Doctor",
        "subtitle": "Upload a photo or describe symptoms to diagnose crop diseases",
        "tab_image": "📷 Image Diagnosis",
        "tab_text": "📝 Text Diagnosis",
        "upload_label": "Upload crop image",
        "upload_help": "Take a clear photo of the affected leaf, stem, or fruit. Supported formats: JPG, PNG, WEBP",
        "crop_select": "Select your crop (optional — improves accuracy)",
        "context_label": "Additional details (optional)",
        "context_placeholder": "e.g. 'Appeared 3 days ago, lower leaves affected'",
        "diagnose_btn": "🔬 Diagnose from Image",
        "text_label": "Describe the symptoms you see",
        "text_placeholder": "e.g. 'My paddy leaves have brown spots with a yellow border, affecting the lower canopy'",
        "text_btn": "🔬 Diagnose from Description",
        "thinking": "Dr. Krishi is analyzing …",
        "results": "Diagnosis Results",
        "no_image": "Please upload an image first.",
        "no_text": "Please describe the symptoms.",
        "tips_header": "📸 Tips for Best Results",
        "common_header": "🌾 Common Telangana Crop Diseases",
    },
    "te": {
        "title": "🌱 పంట వైద్యుడు",
        "subtitle": "పంట వ్యాధులను నిర్ధారించడానికి ఫోటో అప్‌లోడ్ చేయండి లేదా లక్షణాలను వివరించండి",
        "tab_image": "📷 చిత్రం ద్వారా నిర్ధారణ",
        "tab_text": "📝 వివరణ ద్వారా నిర్ధారణ",
        "upload_label": "పంట చిత్రాన్ని అప్‌లోడ్ చేయండి",
        "upload_help": "ప్రభావిత ఆకు, కాండం లేదా పండు యొక్క స్పష్టమైన ఫోటో తీయండి",
        "crop_select": "మీ పంటను ఎంచుకోండి (ఐచ్ఛికం)",
        "context_label": "అదనపు వివరాలు (ఐచ్ఛికం)",
        "context_placeholder": "ఉదా. '3 రోజుల క్రితం కనిపించింది, కింది ఆకులు ప్రభావితమయ్యాయి'",
        "diagnose_btn": "🔬 చిత్రం నుండి నిర్ధారణ",
        "text_label": "మీరు చూస్తున్న లక్షణాలను వివరించండి",
        "text_placeholder": "ఉదా. 'నా వరి ఆకులపై పసుపు అంచుతో గోధుమ మచ్చలు ఉన్నాయి'",
        "text_btn": "🔬 వివరణ నుండి నిర్ధారణ",
        "thinking": "డా. కృషి విశ్లేషిస్తున్నారు …",
        "results": "నిర్ధారణ ఫలితాలు",
        "no_image": "దయచేసి ముందుగా చిత్రాన్ని అప్‌లోడ్ చేయండి.",
        "no_text": "దయచేసి లక్షణాలను వివరించండి.",
        "tips_header": "📸 మంచి ఫలితాల కోసం చిట్కాలు",
        "common_header": "🌾 తెలంగాణలో సాధారణ పంట వ్యాధులు",
    },
    "hi": {
        "title": "🌱 फसल डॉक्टर",
        "subtitle": "फसल रोग पहचान के लिए फोटो अपलोड करें या लक्षण बताएं",
        "tab_image": "📷 फोटो से पहचान",
        "tab_text": "📝 विवरण से पहचान",
        "upload_label": "फसल की फोटो अपलोड करें",
        "upload_help": "प्रभावित पत्ती, तने या फल की साफ फोटो लें",
        "crop_select": "अपनी फसल चुनें (वैकल्पिक)",
        "context_label": "अतिरिक्त जानकारी (वैकल्पिक)",
        "context_placeholder": "जैसे '3 दिन पहले दिखा, निचली पत्तियाँ प्रभावित'",
        "diagnose_btn": "🔬 फोटो से पहचान करें",
        "text_label": "दिख रहे लक्षण बताएं",
        "text_placeholder": "जैसे 'मेरे धान के पत्तों पर पीली किनारी वाले भूरे धब्बे हैं'",
        "text_btn": "🔬 विवरण से पहचान करें",
        "thinking": "डॉ. कृषि विश्लेषण कर रहे हैं …",
        "results": "पहचान परिणाम",
        "no_image": "कृपया पहले एक फोटो अपलोड करें।",
        "no_text": "कृपया लक्षण बताएं।",
        "tips_header": "📸 अच्छे परिणाम के लिए सुझाव",
        "common_header": "🌾 आम फसल रोग",
    },
}

# ── Telangana crops for the selector ───────────────────────────────────
TELANGANA_CROPS = [
    "", "Rice (Paddy)", "Cotton", "Maize", "Red Gram (Tur)", "Bengal Gram (Chickpea)",
    "Soybean", "Groundnut", "Sunflower", "Chilli", "Turmeric", "Tomato",
    "Onion", "Brinjal (Eggplant)", "Okra (Lady Finger)", "Mango", "Orange",
    "Banana", "Sugarcane", "Jowar (Sorghum)", "Bajra (Pearl Millet)",
    "Green Gram (Moong)", "Black Gram (Urad)", "Sesame", "Castor",
    "Wheat", "Watermelon", "Papaya", "Pomegranate", "Grape",
]


def _ui(lang: str, key: str) -> str:
    return _UI.get(lang, _UI["en"]).get(key, _UI["en"][key])


# ── Cached resources ───────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initialising Crop Doctor …")
def _get_crop_doctor() -> CropDoctorAgent:
    try:
        rag = RAGEngine()
    except Exception:
        rag = None  # type: ignore[assignment]
    return CropDoctorAgent(rag_engine=rag)


# ── Page ───────────────────────────────────────────────────────────────
def main() -> None:
    # Session defaults
    if "language" not in st.session_state:
        st.session_state["language"] = Config.DEFAULT_LANGUAGE

    lang = render_sidebar()
    _user = require_auth()
    doctor = _get_crop_doctor()

    # ── Header ─────────────────────────────────────────────────────────
    render_page_header(
        title=_ui(lang, 'title').replace('🌱 ', ''),
        subtitle=_ui(lang, 'subtitle'),
        icon_name='crop',
    )

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_img, tab_txt = st.tabs([_ui(lang, "tab_image"), _ui(lang, "tab_text")])

    # ================================================================
    # TAB 1: IMAGE DIAGNOSIS
    # ================================================================
    with tab_img:
        col_upload, col_result = st.columns([1, 1], gap="large")

        with col_upload:
            uploaded = st.file_uploader(
                _ui(lang, "upload_label"),
                type=["jpg", "jpeg", "png", "webp"],
                help=_ui(lang, "upload_help"),
                key="crop_uploader",
            )

            crop_name = st.selectbox(
                _ui(lang, "crop_select"),
                options=TELANGANA_CROPS,
                index=0,
                key="crop_selector",
            )

            extra_context = st.text_area(
                _ui(lang, "context_label"),
                placeholder=_ui(lang, "context_placeholder"),
                height=80,
                key="image_context",
            )

            # Show uploaded image preview
            if uploaded:
                image = Image.open(uploaded)
                st.image(image, caption=uploaded.name, use_container_width=True)

            diagnose_img = st.button(
                _ui(lang, "diagnose_btn"),
                use_container_width=True,
                type="primary",
                key="btn_diagnose_img",
                disabled=not uploaded,
            )

            # ── Photo tips (collapsible) ───────────────────────────────
            with st.expander(_ui(lang, "tips_header"), expanded=False):
                st.markdown(
                    """
                    1. **Lighting** — Take photos in natural daylight, avoid shadows
                    2. **Focus** — Get close to the affected area, ensure clear focus
                    3. **Background** — Hold the leaf/fruit against a plain background
                    4. **Multiple angles** — If possible, photograph top and bottom of leaf
                    5. **Healthy comparison** — Include a healthy leaf next to the diseased one
                    6. **Context** — Mention the crop name and growth stage for better results
                    """
                )

        with col_result:
            if diagnose_img:
                if not uploaded:
                    st.warning(_ui(lang, "no_image"))
                else:
                    # Build context string
                    ctx_parts: list[str] = []
                    if crop_name:
                        ctx_parts.append(f"Crop: {crop_name}")
                    if extra_context:
                        ctx_parts.append(extra_context)
                    ctx = ". ".join(ctx_parts) if ctx_parts else None

                    image = Image.open(uploaded)
                    with st.spinner(_ui(lang, "thinking")):
                        start = time.time()
                        try:
                            result = doctor.diagnose_from_image(
                                pil_image=image,
                                context=ctx,
                            )
                            elapsed = time.time() - start
                            diagnosis = result.get("diagnosis", "")
                            sources = result.get("sources", [])

                            # Translate if needed
                            if lang != "en" and diagnosis:
                                diagnosis = translator.from_english(diagnosis, dest=lang)

                            st.subheader(f"📋 {_ui(lang, 'results')}")
                            st.markdown(diagnosis)

                            if sources:
                                src_str = " · ".join(f"`{s}`" for s in sources)
                                st.caption(f"📚 Sources: {src_str}")

                            st.caption(f"⏱️ {elapsed:.1f}s")

                        except Exception as exc:
                            logger.error("Image diagnosis error: %s", exc, exc_info=True)
                            st.error(f"Diagnosis failed: {exc}")

    # ================================================================
    # TAB 2: TEXT DIAGNOSIS
    # ================================================================
    with tab_txt:
        col_input, col_output = st.columns([1, 1], gap="large")

        with col_input:
            crop_name_txt = st.selectbox(
                _ui(lang, "crop_select"),
                options=TELANGANA_CROPS,
                index=0,
                key="crop_selector_txt",
            )

            symptoms = st.text_area(
                _ui(lang, "text_label"),
                placeholder=_ui(lang, "text_placeholder"),
                height=150,
                key="symptom_input",
            )

            diagnose_txt = st.button(
                _ui(lang, "text_btn"),
                use_container_width=True,
                type="primary",
                key="btn_diagnose_txt",
                disabled=not symptoms,
            )

            # ── Common diseases quick-reference ────────────────────────
            with st.expander(_ui(lang, "common_header"), expanded=False):
                _render_common_diseases()

        with col_output:
            if diagnose_txt:
                if not symptoms:
                    st.warning(_ui(lang, "no_text"))
                else:
                    query_parts: list[str] = []
                    if crop_name_txt:
                        query_parts.append(f"Crop: {crop_name_txt}.")
                    # Translate symptoms to English if needed
                    if lang != "en":
                        query_parts.append(translator.to_english(symptoms, src=lang))
                    else:
                        query_parts.append(symptoms)
                    full_query = " ".join(query_parts)

                    with st.spinner(_ui(lang, "thinking")):
                        start = time.time()
                        try:
                            result = doctor.diagnose_from_text(full_query)
                            elapsed = time.time() - start
                            diagnosis = result.get("diagnosis", "")
                            sources = result.get("sources", [])

                            if lang != "en" and diagnosis:
                                diagnosis = translator.from_english(diagnosis, dest=lang)

                            st.subheader(f"📋 {_ui(lang, 'results')}")
                            st.markdown(diagnosis)

                            if sources:
                                src_str = " · ".join(f"`{s}`" for s in sources)
                                st.caption(f"📚 Sources: {src_str}")

                            st.caption(f"⏱️ {elapsed:.1f}s")

                        except Exception as exc:
                            logger.error("Text diagnosis error: %s", exc, exc_info=True)
                            st.error(f"Diagnosis failed: {exc}")


def _render_common_diseases() -> None:
    """Show a quick-reference grid of common Telangana crop diseases."""
    diseases = [
        {"crop": "Rice", "disease": "Blast (Leaf & Neck)", "severity": "🔴 High", "symptom": "Diamond-shaped grey spots"},
        {"crop": "Rice", "disease": "Sheath Blight", "severity": "🟡 Medium", "symptom": "Oval lesions on leaf sheath"},
        {"crop": "Rice", "disease": "BPH (Brown Plant Hopper)", "severity": "🔴 High", "symptom": "Hopper burn — circular drying patches"},
        {"crop": "Cotton", "disease": "Bollworm", "severity": "🔴 High", "symptom": "Holes in bolls, frass visible"},
        {"crop": "Cotton", "disease": "Leaf Curl Virus", "severity": "🔴 High", "symptom": "Upward curling, thickened veins"},
        {"crop": "Tomato", "disease": "Early Blight", "severity": "🟡 Medium", "symptom": "Concentric ring spots on older leaves"},
        {"crop": "Tomato", "disease": "Late Blight", "severity": "🔴 High", "symptom": "Water-soaked dark lesions, white mold"},
        {"crop": "Chilli", "disease": "Anthracnose", "severity": "🟡 Medium", "symptom": "Sunken dark spots on fruit"},
        {"crop": "Maize", "disease": "Fall Armyworm", "severity": "🔴 High", "symptom": "Ragged holes in whorl leaves, frass"},
        {"crop": "Groundnut", "disease": "Tikka Disease", "severity": "🟡 Medium", "symptom": "Circular brown spots on leaves"},
    ]

    for d in diseases:
        st.markdown(
            f"**{d['crop']}** — {d['disease']} {d['severity']}\n"
            f"> _{d['symptom']}_"
        )


if __name__ == "__main__":
    main()
else:
    main()
