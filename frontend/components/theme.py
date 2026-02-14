"""KrishiSaathi — Centralised theme, icons & global CSS.

Provides:
    • ``ICON`` dict — inline SVG icons (replaces emojis everywhere)
    • ``inject_global_css(theme)`` — full-page CSS for light / dark mode
    • ``get_theme()`` — read current theme from session state
    • ``render_logo_header(title, subtitle)`` — branded page header
"""

from __future__ import annotations

import base64
import os
from typing import Literal

import streamlit as st

# ── Paths ──────────────────────────────────────────────────────────────
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# ── Colour palettes ────────────────────────────────────────────────────
LIGHT = {
    "bg":            "#ffffff",
    "bg_secondary":  "#f7faf7",
    "bg_sidebar":    "#f1f8e9",
    "surface":       "#ffffff",
    "surface_hover":  "#f5f5f5",
    "card":          "#ffffff",
    "card_border":   "#e0e0e0",
    "text":          "#212121",
    "text_secondary": "#616161",
    "text_muted":     "#9e9e9e",
    "primary":       "#2e7d32",
    "primary_light":  "#4caf50",
    "primary_bg":     "#e8f5e9",
    "accent":        "#ff8f00",
    "accent_bg":     "#fff3e0",
    "info":          "#1565c0",
    "info_bg":       "#e3f2fd",
    "success":       "#2e7d32",
    "success_bg":    "#e8f5e9",
    "warning":       "#e65100",
    "warning_bg":    "#fff3e0",
    "error":         "#c62828",
    "error_bg":      "#ffebee",
    "divider":       "#e0e0e0",
    "shadow":        "rgba(0,0,0,0.08)",
    "user_bubble":   "#dcf8c6",
    "bot_bubble":    "#ffffff",
}

DARK = {
    "bg":            "#121212",
    "bg_secondary":  "#1e1e1e",
    "bg_sidebar":    "#1a2e1a",
    "surface":       "#1e1e1e",
    "surface_hover":  "#2c2c2c",
    "card":          "#242424",
    "card_border":   "#333333",
    "text":          "#e0e0e0",
    "text_secondary": "#b0b0b0",
    "text_muted":     "#757575",
    "primary":       "#66bb6a",
    "primary_light":  "#81c784",
    "primary_bg":     "#1b3d1b",
    "accent":        "#ffb74d",
    "accent_bg":     "#3e2723",
    "info":          "#64b5f6",
    "info_bg":       "#0d2137",
    "success":       "#66bb6a",
    "success_bg":    "#1b3d1b",
    "warning":       "#ffb74d",
    "warning_bg":    "#3e2723",
    "error":         "#ef5350",
    "error_bg":      "#3b1515",
    "divider":       "#333333",
    "shadow":        "rgba(0,0,0,0.3)",
    "user_bubble":   "#1b5e20",
    "bot_bubble":    "#2c2c2c",
}


def get_palette(theme: str = "light") -> dict[str, str]:
    return DARK if theme == "dark" else LIGHT


# ── Inline SVG icons (Material-style, 24×24) ──────────────────────────
# These replace emojis for a professional look.

ICON: dict[str, str] = {
    # ── Navigation / pages ─────────────────────────────────────────────
    "home": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "crop": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 20h10"/><path d="M10 20c5.5-2.5 8-6.5 8-12"/><path d="M6 12c0 5 2.5 8 8 8"/><path d="M6 12c0-5.5 3.5-8 8-8s8 2.5 8 8"/><path d="M6 12S2 8 2 4c4 0 8 4 8 4"/></svg>',
    "market": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    "scheme": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
    "weather": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "soil": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 22h20"/><path d="M12 2v6"/><path d="M12 8c-3 0-6 3-6 8h12c0-5-3-8-6-8z"/><circle cx="5" cy="20" r="1"/><circle cx="12" cy="20" r="1"/><circle cx="19" cy="20" r="1"/></svg>',

    # ── Actions & indicators ───────────────────────────────────────────
    "language": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "analyze": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "camera": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
    "text": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "chart": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "trend": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "calculator": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/><line x1="8" y1="10" x2="8" y2="10.01"/><line x1="12" y1="10" x2="12" y2="10.01"/><line x1="16" y1="10" x2="16" y2="10.01"/><line x1="8" y1="14" x2="8" y2="14.01"/><line x1="12" y1="14" x2="12" y2="14.01"/><line x1="8" y1="18" x2="8" y2="18.01"/><line x1="12" y1="18" x2="12" y2="18.01"/></svg>',
    "rotate": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>',
    "robot": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16.01"/><line x1="16" y1="16" x2="16" y2="16.01"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "browse": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    "filter": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    "thermometer": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>',
    "droplet": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>',
    "wind": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></svg>',
    "star": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "source": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "clear": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "sun": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "moon": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    "leaf": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.5 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>',
    "heart": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "alert": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "info": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    "brain": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44A2.5 2.5 0 0 1 4.5 17.5a2.5 2.5 0 0 1-.44-4.96A2.5 2.5 0 0 1 4.5 8a2.5 2.5 0 0 1 .44-4.96A2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44A2.5 2.5 0 0 0 19.5 17.5a2.5 2.5 0 0 0 .44-4.96A2.5 2.5 0 0 0 19.5 8a2.5 2.5 0 0 0-.44-4.96A2.5 2.5 0 0 0 14.5 2z"/></svg>',
    "link": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    "phone": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.68 2.35a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.75.32 1.54.55 2.35.68A2 2 0 0 1 22 16.92z"/></svg>',
    "rupee": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="18" y2="3"/><line x1="6" y1="8" x2="18" y2="8"/><path d="M6 3c0 7 8 10 8 10l-8 8"/></svg>',
}


def icon(name: str, size: int | None = None, color: str | None = None) -> str:
    """Return an inline SVG icon HTML string, optionally resized/recolored."""
    svg = ICON.get(name, "")
    if size:
        svg = svg.replace('width="20"', f'width="{size}"').replace('height="20"', f'height="{size}"')
        svg = svg.replace('width="18"', f'width="{size}"').replace('height="18"', f'height="{size}"')
        svg = svg.replace('width="14"', f'width="{size}"').replace('height="14"', f'height="{size}"')
    if color:
        svg = svg.replace('stroke="currentColor"', f'stroke="{color}"')
        svg = svg.replace('fill="currentColor"', f'fill="{color}"')
    return svg


# ── Logo helper ────────────────────────────────────────────────────────

def _logo_b64() -> str:
    """Return the logo.svg as base64 data URI."""
    path = os.path.join(_ASSETS, "logo.svg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


# ── Global CSS injection ──────────────────────────────────────────────

def inject_global_css(theme: str = "light") -> None:
    """Inject the full-page CSS for the selected theme."""
    p = get_palette(theme)
    css = _build_css(p, theme)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _build_css(p: dict[str, str], theme: str) -> str:
    """Build the complete CSS string for the given palette."""
    return f"""
/* ================================================================== */
/*  KrishiSaathi — Global Theme ({theme})                              */
/* ================================================================== */

/* ── Google Fonts ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Root variables ───────────────────────────────────────────────── */
:root {{
    --ks-bg: {p['bg']};
    --ks-bg2: {p['bg_secondary']};
    --ks-surface: {p['surface']};
    --ks-card: {p['card']};
    --ks-card-border: {p['card_border']};
    --ks-text: {p['text']};
    --ks-text2: {p['text_secondary']};
    --ks-muted: {p['text_muted']};
    --ks-primary: {p['primary']};
    --ks-primary-lt: {p['primary_light']};
    --ks-primary-bg: {p['primary_bg']};
    --ks-accent: {p['accent']};
    --ks-accent-bg: {p['accent_bg']};
    --ks-divider: {p['divider']};
    --ks-shadow: {p['shadow']};
    --ks-radius: 12px;
    --ks-radius-sm: 8px;
    --ks-radius-lg: 16px;
}}

/* ── Base — force backgrounds & text on ALL Streamlit containers ──── */
html, body,
.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {{
    background: {p['bg']} !important;
    background-color: {p['bg']} !important;
    color: {p['text']} !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    color-scheme: {'dark' if theme == 'dark' else 'light'} !important;
}}

/* ── Bottom sticky bar (chat input container) ──────────────────────── */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div {{
    background: {p['bg']} !important;
    background-color: {p['bg']} !important;
}}

/* ── Header bar ───────────────────────────────────────────────────── */
[data-testid="stHeader"],
header[data-testid="stHeader"] {{
    background: {p['bg']} !important;
    background-color: {p['bg']} !important;
}}

/* ── Force text color everywhere ──────────────────────────────────── */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp span, .stApp li, .stApp div, .stApp label,
.stApp td, .stApp th,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] a {{
    color: {p['text']} !important;
}}

/* ── Smooth transitions for theme changes ─────────────────────────── */
* {{ transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease; }}

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {{
    background: {p['bg_sidebar']} !important;
    border-right: 1px solid {p['divider']} !important;
}}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {{
    color: {p['text']} !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stButton button {{
    color: {p['text']} !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {p['divider']} !important;
}}

/* ── Cards ─────────────────────────────────────────────────────────── */
.ks-card {{
    background: {p['card']} !important;
    border: 1px solid {p['card_border']};
    border-radius: var(--ks-radius);
    padding: 1.2rem;
    box-shadow: 0 2px 8px {p['shadow']};
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    color: {p['text']} !important;
}}
.ks-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 16px {p['shadow']};
}}
.ks-card * {{
    color: inherit !important;
}}

/* ── KPI metrics ───────────────────────────────────────────────────── */
[data-testid="stMetric"],
[data-testid="stMetric"] > div {{
    background: {p['card']} !important;
    border: 1px solid {p['card_border']};
    border-radius: var(--ks-radius);
    padding: 1rem !important;
    box-shadow: 0 1px 4px {p['shadow']};
}}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {{
    color: {p['text_secondary']} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] div {{
    color: {p['primary']} !important;
    font-weight: 700 !important;
}}

/* ── Buttons ───────────────────────────────────────────────────────── */
.stButton > button {{
    border-radius: var(--ks-radius-sm) !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.15s ease !important;
    border: none !important;
    padding: 0.5rem 1.2rem !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {p['primary']}, {p['primary_light']}) !important;
    color: white !important;
    box-shadow: 0 2px 8px {p['shadow']} !important;
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px {p['shadow']} !important;
    transform: translateY(-1px);
}}
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {{
    background: {p['surface']} !important;
    color: {p['primary']} !important;
    border: 1.5px solid {p['primary']} !important;
}}
.stButton > button:not([kind="primary"]):hover {{
    background: {p['primary_bg']} !important;
}}

/* ── Expanders ─────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: {p['card']} !important;
    border: 1px solid {p['card_border']} !important;
    border-radius: var(--ks-radius) !important;
    box-shadow: 0 1px 4px {p['shadow']};
    margin-bottom: 0.5rem;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    color: {p['text']} !important;
}}
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p {{
    color: {p['text']} !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background: {p['card']} !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] * {{
    color: {p['text']} !important;
}}

/* ── Tabs ──────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.5rem;
    background: {p['bg_secondary']};
    border-radius: var(--ks-radius);
    padding: 0.3rem;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: var(--ks-radius-sm);
    font-weight: 500;
    padding: 0.6rem 1.2rem;
    background: transparent;
    color: {p['text_secondary']} !important;
    border: none !important;
}}
.stTabs [aria-selected="true"] {{
    background: {p['card']} !important;
    color: {p['primary']} !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px {p['shadow']};
}}
.stTabs [data-baseweb="tab-panel"] {{
    background: transparent !important;
}}

/* ── Inputs ────────────────────────────────────────────────────────── */
.stTextInput > div > div,
.stSelectbox > div > div,
.stNumberInput > div > div,
.stTextArea > div > div {{
    border-radius: var(--ks-radius-sm) !important;
    border-color: {p['card_border']} !important;
    background: {p['surface']} !important;
    color: {p['text']} !important;
}}
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {{
    color: {p['text']} !important;
    background: {p['surface']} !important;
    caret-color: {p['primary']} !important;
}}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {{
    color: {p['text_muted']} !important;
}}
.stTextInput > div > div:focus-within,
.stSelectbox > div > div:focus-within,
.stTextArea > div > div:focus-within {{
    border-color: {p['primary']} !important;
    box-shadow: 0 0 0 2px {p['primary_bg']} !important;
}}

/* Selectbox dropdown menu — aggressive overrides for all baseweb internals */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="menu"] ul,
[data-baseweb="list"] {{
    background: {p['card']} !important;
    background-color: {p['card']} !important;
    border: 1px solid {p['card_border']} !important;
    color: {p['text']} !important;
}}
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"],
[data-baseweb="list"] li,
[data-baseweb="list"] [role="option"],
[data-baseweb="menu"] li *,
[data-baseweb="menu"] [role="option"] *,
[data-baseweb="list"] li *,
[data-baseweb="list"] [role="option"] * {{
    color: {p['text']} !important;
    background: {p['card']} !important;
    background-color: {p['card']} !important;
}}
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="list"] li:hover,
[data-baseweb="list"] [role="option"]:hover,
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="menu"] [role="option"][aria-selected="true"],
[data-baseweb="list"] li[aria-selected="true"],
[data-baseweb="list"] [role="option"][aria-selected="true"] {{
    background: {p['primary_bg']} !important;
    background-color: {p['primary_bg']} !important;
}}
[data-baseweb="menu"] li:hover *,
[data-baseweb="menu"] [role="option"]:hover *,
[data-baseweb="list"] li:hover *,
[data-baseweb="list"] [role="option"]:hover * {{
    background: {p['primary_bg']} !important;
    background-color: {p['primary_bg']} !important;
    color: {p['text']} !important;
}}
/* Selectbox control itself */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {{
    background: {p['surface']} !important;
    background-color: {p['surface']} !important;
    color: {p['text']} !important;
    border-color: {p['card_border']} !important;
}}
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] input {{
    color: {p['text']} !important;
}}
/* Selectbox clear & arrow icons */
[data-baseweb="select"] svg {{
    fill: {p['text_muted']} !important;
}}
/* Dropdown overlay / popover shadow in dark */
[data-baseweb="popover"] > div > div {{
    background: {p['card']} !important;
    background-color: {p['card']} !important;
}}

/* ── Chat messages ─────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {{
    background: {p['card']} !important;
    border: 1px solid {p['card_border']} !important;
    border-radius: var(--ks-radius-lg) !important;
    padding: 1rem !important;
    box-shadow: 0 1px 3px {p['shadow']};
}}
[data-testid="stChatMessage"] * {{
    color: {p['text']} !important;
}}
[data-testid="stChatMessage"] code {{
    background: {p['bg_secondary']} !important;
    color: {p['primary']} !important;
}}
.stChatInput > div {{
    border-color: {p['primary']} !important;
    border-radius: var(--ks-radius) !important;
    background: {p['surface']} !important;
}}
.stChatInput textarea,
.stChatInput input {{
    color: {p['text']} !important;
    background: {p['surface']} !important;
}}
.stChatInput textarea::placeholder {{
    color: {p['text_muted']} !important;
}}

/* ── st.info / st.success / st.warning / st.error boxes ───────────── */
[data-testid="stAlert"] {{
    border-radius: var(--ks-radius-sm) !important;
}}
div[data-testid="stAlert"] > div {{
    color: {p['text']} !important;
}}
/* info */
.stAlert [data-testid="stAlertContentInfo"],
div[role="alert"]:has(.st-emotion-cache-info) {{
    background: {p['info_bg']} !important;
}}
/* success */
.stAlert [data-testid="stAlertContentSuccess"] {{
    background: {p['success_bg']} !important;
}}
/* warning */
.stAlert [data-testid="stAlertContentWarning"] {{
    background: {p['warning_bg']} !important;
}}
/* error */
.stAlert [data-testid="stAlertContentError"] {{
    background: {p['error_bg']} !important;
}}

/* ── Dividers ──────────────────────────────────────────────────────── */
hr {{
    border-color: {p['divider']} !important;
    opacity: 0.5;
}}

/* ── Scrollbar (subtle) ────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: {p['text_muted']};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {p['text_secondary']};
}}

/* ── Page header ───────────────────────────────────────────────────── */
.ks-page-header {{
    text-align: center;
    padding: 0.8rem 0 0.5rem 0;
}}
.ks-page-header h1 {{
    margin: 0;
    color: {p['primary']} !important;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}}
.ks-page-header .ks-subtitle {{
    color: {p['text_secondary']} !important;
    margin: 0.2rem 0 0.8rem 0;
    font-size: 0.95rem;
    font-weight: 400;
}}

/* ── Status badges ─────────────────────────────────────────────────── */
.ks-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}}
.ks-badge-state {{
    background: {p['primary_bg']};
    color: {p['primary']} !important;
}}
.ks-badge-central {{
    background: {p['info_bg']};
    color: {p['info']} !important;
}}
.ks-badge-active {{
    background: {p['success_bg']};
    color: {p['success']} !important;
}}
.ks-badge-inactive {{
    background: {p['error_bg']};
    color: {p['error']} !important;
}}

/* ── Hero card (used on weather, soil analyzer) ────────────────────── */
.ks-hero {{
    background: linear-gradient(135deg, {p['primary_bg']}, {p['bg_secondary']});
    border: 1px solid {p['card_border']};
    border-radius: var(--ks-radius-lg);
    padding: 1.5rem;
    text-align: center;
    margin-bottom: 1rem;
}}
.ks-hero h1, .ks-hero h2 {{
    color: {p['primary']} !important;
    margin: 0 0 0.3rem 0;
    font-weight: 700;
}}
.ks-hero p, .ks-hero span {{
    color: {p['text']} !important;
}}

/* ── Quick-action grid buttons ─────────────────────────────────────── */
.ks-quick-btn {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0.9rem;
    background: {p['surface']};
    border: 1px solid {p['card_border']};
    border-radius: var(--ks-radius-sm);
    color: {p['text']};
    font-size: 0.88rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none;
    width: 100%;
}}
.ks-quick-btn:hover {{
    background: {p['primary_bg']};
    border-color: {p['primary']};
    color: {p['primary']};
}}

/* ── Sidebar branding ──────────────────────────────────────────────── */
.ks-sidebar-brand {{
    text-align: center;
    padding: 0.5rem 0 0.8rem 0;
}}
.ks-sidebar-brand img {{
    width: 56px;
    height: 56px;
    margin-bottom: 0.3rem;
}}
.ks-sidebar-brand h2 {{
    margin: 0;
    color: {p['primary']} !important;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    letter-spacing: -0.5px;
}}
.ks-sidebar-brand p {{
    margin: 0;
    color: {p['text_secondary']} !important;
    font-size: 0.8rem;
}}

/* ── Theme toggle ──────────────────────────────────────────────────── */
.ks-theme-toggle {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    font-size: 0.85rem;
    color: {p['text_secondary']};
}}

/* ── Footer ────────────────────────────────────────────────────────── */
.ks-footer {{
    text-align: center;
    font-size: 0.75rem;
    color: {p['text_muted']} !important;
    padding: 0.5rem 0;
    line-height: 1.6;
}}
.ks-footer svg {{
    vertical-align: middle;
}}

/* ── Alerts / info boxes custom ────────────────────────────────────── */
.ks-alert {{
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.8rem 1rem;
    border-radius: var(--ks-radius-sm);
    font-size: 0.9rem;
    margin: 0.5rem 0;
}}
.ks-alert-warning {{
    background: {p['warning_bg']};
    color: {p['warning']} !important;
    border-left: 3px solid {p['warning']};
}}
.ks-alert-info {{
    background: {p['info_bg']};
    color: {p['info']} !important;
    border-left: 3px solid {p['info']};
}}
.ks-alert-success {{
    background: {p['success_bg']};
    color: {p['success']} !important;
    border-left: 3px solid {p['success']};
}}

/* ── Source citation ────────────────────────────────────────────────── */
.ks-sources {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    color: {p['text_muted']} !important;
    margin-top: 0.4rem;
}}
.ks-sources code {{
    background: {p['bg_secondary']} !important;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.75rem;
    color: {p['text_muted']} !important;
}}

/* ── Data table overrides ──────────────────────────────────────────── */
.stDataFrame {{
    border-radius: var(--ks-radius) !important;
    overflow: hidden;
}}
.stDataFrame [data-testid="stDataFrameResizable"] {{
    background: {p['card']} !important;
}}

/* ── Column containers ─────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"],
[data-testid="stColumn"] {{
    background: transparent !important;
}}

/* ── Tooltips / popovers ───────────────────────────────────────────── */
[data-baseweb="tooltip"] {{
    background: {p['card']} !important;
    color: {p['text']} !important;
}}

/* ── Plotly chart containers ───────────────────────────────────────── */
.stPlotlyChart {{
    background: transparent !important;
}}

/* ── Code blocks ───────────────────────────────────────────────────── */
.stApp pre, .stApp code {{
    background: {p['bg_secondary']} !important;
    color: {p['text']} !important;
}}

/* ── Disabled buttons ──────────────────────────────────────────────── */
.stButton > button:disabled {{
    background: {p['bg_secondary']} !important;
    color: {p['text_muted']} !important;
    border-color: {p['card_border']} !important;
    opacity: 0.7;
}}

/* ── Number input buttons ──────────────────────────────────────────── */
.stNumberInput button {{
    background: {p['surface']} !important;
    color: {p['text']} !important;
    border-color: {p['card_border']} !important;
}}

/* ── Multiselect / tags ────────────────────────────────────────────── */
[data-baseweb="tag"] {{
    background: {p['primary_bg']} !important;
    color: {p['primary']} !important;
}}

/* ── File uploader ─────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    background: {p['surface']} !important;
    border-color: {p['card_border']} !important;
    border-radius: var(--ks-radius) !important;
}}
[data-testid="stFileUploader"] * {{
    color: {p['text']} !important;
}}

/* ── Spinner ───────────────────────────────────────────────────────── */
[data-testid="stSpinner"] {{
    color: {p['primary']} !important;
}}

/* ── Caption ───────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {{
    color: {p['text_muted']} !important;
}}
"""


# ── Page header helper ─────────────────────────────────────────────────

def render_page_header(title: str, subtitle: str, icon_name: str = "") -> None:
    """Render a branded page header with icon + title + subtitle."""
    icon_html = ""
    if icon_name:
        icon_html = icon(icon_name, size=28, color=get_palette(get_theme())["primary"])

    st.markdown(
        f"""
        <div class="ks-page-header">
            <h1>{icon_html} {title}</h1>
            <p class="ks-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Theme management ──────────────────────────────────────────────────

def get_theme() -> str:
    """Return 'light' or 'dark' from session state."""
    return st.session_state.get("ks_theme", "light")


def set_theme(theme: str) -> None:
    st.session_state["ks_theme"] = theme
