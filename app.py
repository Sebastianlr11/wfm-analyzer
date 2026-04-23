"""
WFM Analyzer — StrategyQuant .sqx analysis dashboard
Run with: streamlit run app.py
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from analyzer import analyze_strategy, rank_strategies
from parser import parse_sqx


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="WFM Analyzer",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────
C = {
    "bg":         "#08080c",
    "bg_deep":    "#050507",
    "surface":    "#0f0f14",
    "surface_h":  "#15151c",
    "surface_g":  "rgba(20,20,28,0.72)",
    "border":     "#1a1a24",
    "border_s":   "#242432",
    "border_g":   "rgba(255,255,255,0.06)",
    "text":       "#f3f3f5",
    "text_dim":   "#a8a8b5",
    "muted":      "#6e6e80",
    "subtle":     "#3f3f52",
    "accent":     "#7c6bff",
    "accent_2":   "#4ea8ff",
    "accent_d":   "#5b4dd9",
    "green":      "#34d399",
    "green_d":    "#10b981",
    "red":        "#fb5a6f",
    "red_d":      "#e02d4a",
    "yellow":     "#fbbf24",
    "gold":       "#f5c04a",
}


# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; -webkit-font-smoothing: antialiased; }}
code, .mono {{ font-family: 'JetBrains Mono', monospace !important; font-feature-settings: 'zero', 'ss01'; }}

/* App background with ambient light */
.stApp {{
    background:
      radial-gradient(ellipse 1200px 600px at 15% -10%, rgba(124,107,255,0.10), transparent 60%),
      radial-gradient(ellipse 900px 500px at 95% 0%, rgba(78,168,255,0.06), transparent 55%),
      radial-gradient(ellipse 800px 400px at 50% 110%, rgba(124,107,255,0.05), transparent 60%),
      linear-gradient(180deg, {C['bg']} 0%, {C['bg_deep']} 100%);
    background-attachment: fixed;
}}

/* Grain overlay for depth */
.stApp::before {{
    content: "";
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.035 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
    opacity: 0.5; mix-blend-mode: overlay;
}}

/* Hide default chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1.2rem 2rem 3rem !important; max-width: 1600px !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {C['border_s']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {C['muted']}; }}

/* Default buttons — glass outline */
.stButton > button {{
    background: rgba(255,255,255,0.025) !important;
    color: {C['text']} !important;
    border: 1px solid {C['border_g']} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.1rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
    transition: all 0.18s cubic-bezier(.4,0,.2,1) !important;
    letter-spacing: 0 !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}}
.stButton > button:hover {{
    border-color: rgba(124,107,255,0.55) !important;
    color: {C['text']} !important;
    background: rgba(124,107,255,0.08) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(124,107,255,0.15), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}}
.stButton > button:focus {{
    box-shadow: 0 0 0 2px rgba(124,107,255,0.35) !important;
    outline: none !important;
}}

/* Primary button — gradient with shimmer */
.primary-btn .stButton > button {{
    background: linear-gradient(135deg, {C['accent']} 0%, {C['accent_2']} 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 4px 18px rgba(124,107,255,0.35), inset 0 1px 0 rgba(255,255,255,0.18) !important;
    position: relative;
    overflow: hidden;
}}
.primary-btn .stButton > button:hover {{
    background: linear-gradient(135deg, {C['accent_d']} 0%, {C['accent']} 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 26px rgba(124,107,255,0.5), inset 0 1px 0 rgba(255,255,255,0.22) !important;
}}

/* Filter pills */
.flt-btn .stButton > button {{
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid {C['border_g']} !important;
    color: {C['muted']} !important;
    border-radius: 999px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    padding: 0.38rem 0.5rem !important;
    min-height: 30px !important;
    backdrop-filter: blur(6px) !important;
}}
.flt-btn .stButton > button:hover {{
    color: {C['text']} !important;
    border-color: rgba(255,255,255,0.15) !important;
    background: rgba(255,255,255,0.05) !important;
    transform: none !important;
}}
.flt-active .stButton > button {{
    background: linear-gradient(135deg, rgba(124,107,255,0.18), rgba(78,168,255,0.12)) !important;
    border-color: rgba(124,107,255,0.5) !important;
    color: #e4deff !important;
    box-shadow: 0 0 14px rgba(124,107,255,0.22), inset 0 1px 0 rgba(255,255,255,0.08) !important;
}}

/* Strategy select button (invisible row click target) */
.strat-click .stButton > button {{
    background: transparent !important;
    border: 1px dashed rgba(255,255,255,0.06) !important;
    color: {C['muted']} !important;
    font-size: 0.68rem !important;
    padding: 0.3rem 0.5rem !important;
    margin-top: -2px !important;
    width: 100% !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    box-shadow: none !important;
}}
.strat-click .stButton > button:hover {{
    color: {C['accent']} !important;
    border-color: rgba(124,107,255,0.4) !important;
    background: rgba(124,107,255,0.04) !important;
    transform: none !important;
    box-shadow: none !important;
}}
.strat-click.active .stButton > button {{
    color: #e4deff !important;
    border: 1px solid rgba(124,107,255,0.45) !important;
    background: linear-gradient(135deg, rgba(124,107,255,0.12), rgba(78,168,255,0.06)) !important;
    box-shadow: 0 0 12px rgba(124,107,255,0.18) !important;
}}

/* Matrix segmented control */
.seg .stButton > button {{
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid {C['border_g']} !important;
    color: {C['text_dim']} !important;
    border-radius: 0 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 0.6rem !important;
    box-shadow: none !important;
}}
.seg .stButton > button:hover {{
    color: {C['text']} !important;
    border-color: rgba(255,255,255,0.15) !important;
    background: rgba(255,255,255,0.04) !important;
    transform: none !important;
    box-shadow: none !important;
}}
.seg.active .stButton > button {{
    color: #e4deff !important;
    border-color: rgba(124,107,255,0.55) !important;
    background: linear-gradient(135deg, rgba(124,107,255,0.15), rgba(78,168,255,0.08)) !important;
    box-shadow: 0 0 14px rgba(124,107,255,0.22), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}}
.seg-left .stButton > button {{ border-radius: 8px 0 0 8px !important; }}
.seg-right .stButton > button {{ border-radius: 0 8px 8px 0 !important; }}

/* File uploader — glass */
[data-testid="stFileUploader"] {{
    border: 1px dashed rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.01)) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    transition: all 0.2s ease;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: rgba(124,107,255,0.5) !important;
    background: linear-gradient(180deg, rgba(124,107,255,0.04), rgba(78,168,255,0.02)) !important;
    box-shadow: 0 4px 20px rgba(124,107,255,0.08);
}}
[data-testid="stFileUploader"] section {{ padding: 12px !important; }}
[data-testid="stFileUploader"] small {{ color: {C['muted']} !important; }}

/* Expander */
[data-testid="stExpander"] {{
    border: 1px solid {C['border_g']} !important;
    border-radius: 10px !important;
    background: rgba(255,255,255,0.018) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
}}
[data-testid="stExpander"] summary {{
    padding: 11px 14px !important;
    font-size: 0.82rem !important;
    color: {C['text_dim']} !important;
}}

/* Sliders */
[data-testid="stSlider"] > div {{ color: {C['text_dim']} !important; }}
[data-testid="stSlider"] label {{ color: {C['text_dim']} !important; font-size: 0.8rem !important; }}

/* Progress */
.stProgress > div > div {{
    background: linear-gradient(90deg, {C['accent']}, {C['accent_2']}) !important;
    box-shadow: 0 0 12px rgba(124,107,255,0.5);
}}

/* Download button */
[data-testid="stDownloadButton"] button {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid {C['border_g']} !important;
    color: {C['text_dim']} !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
    backdrop-filter: blur(6px) !important;
    transition: all 0.18s ease;
}}
[data-testid="stDownloadButton"] button:hover {{
    border-color: rgba(124,107,255,0.45) !important;
    color: {C['text']} !important;
    background: rgba(124,107,255,0.06) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(124,107,255,0.12);
}}

/* Divider */
hr {{
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, {C['border']} 20%, {C['border']} 80%, transparent) !important;
    margin: 1rem 0 !important;
}}

/* Tabs (if used anywhere) */
[data-baseweb="tab-list"] {{ border-bottom: 1px solid {C['border']} !important; gap: 0 !important; }}
[data-baseweb="tab"] {{
    background: transparent !important;
    color: {C['muted']} !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-bottom: 2px solid transparent !important;
}}
[data-baseweb="tab"][aria-selected="true"] {{
    color: {C['text']} !important;
    border-bottom-color: {C['accent']} !important;
}}

/* Toast/alert overrides */
[data-testid="stAlert"] {{
    background: linear-gradient(135deg, rgba(52,211,153,0.08), rgba(78,168,255,0.04)) !important;
    border: 1px solid rgba(52,211,153,0.25) !important;
    border-radius: 10px !important;
    color: {C['text']} !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 4px 20px rgba(52,211,153,0.08) !important;
}}

/* Text input */
[data-testid="stTextInput"] input {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid {C['border_g']} !important;
    color: {C['text']} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    padding: 0.5rem 0.8rem !important;
    backdrop-filter: blur(6px) !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: rgba(124,107,255,0.55) !important;
    box-shadow: 0 0 0 2px rgba(124,107,255,0.22) !important;
    background: rgba(124,107,255,0.04) !important;
}}
[data-testid="stTextInput"] input::placeholder {{ color: {C['muted']} !important; }}

/* Selectbox (for sort) */
[data-baseweb="select"] > div {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid {C['border_g']} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    min-height: 38px !important;
    backdrop-filter: blur(6px) !important;
    transition: border-color 0.15s ease;
}}
[data-baseweb="select"] > div:hover {{ border-color: rgba(124,107,255,0.4) !important; }}

/* kbd hint */
.kbd {{
    display: inline-block;
    background: {C['bg']};
    border: 1px solid {C['border_s']};
    color: {C['text_dim']};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 6px;
    line-height: 1.4;
}}

/* Strategy row hover animation */
.strat-row {{
    transition: all 0.18s cubic-bezier(.4,0,.2,1);
    position: relative;
    overflow: hidden;
}}
.strat-row:hover {{
    border-color: rgba(255,255,255,0.14) !important;
    transform: translateX(2px);
    background: rgba(255,255,255,0.03) !important;
}}
.strat-row.selected {{
    box-shadow: 0 0 0 1px rgba(124,107,255,0.55), 0 8px 28px rgba(124,107,255,0.18), inset 0 1px 0 rgba(255,255,255,0.06) !important;
    background: linear-gradient(135deg, rgba(124,107,255,0.10), rgba(78,168,255,0.04)) !important;
}}
.strat-row.selected::before {{
    content: ""; position: absolute; left: 0; top: 10%; bottom: 10%; width: 3px;
    background: linear-gradient(180deg, {C['accent']}, {C['accent_2']});
    border-radius: 0 2px 2px 0;
    box-shadow: 0 0 10px {C['accent']};
}}

/* Delta chip */
.delta {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 4px;
    vertical-align: middle;
}}

/* Responsive breakpoints */
@media (max-width: 1200px) {{
    .block-container {{ padding: 1rem 1.2rem 2.5rem !important; }}
    .hide-md {{ display: none !important; }}
}}
@media (max-width: 900px) {{
    .block-container {{ padding: 0.8rem 0.9rem 2rem !important; }}
    .hide-sm {{ display: none !important; }}
    h2 {{ font-size: 1.15rem !important; }}
    .summary-bar {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .summary-bar > div {{ min-width: 110px !important; }}
    .metrics-row {{ gap: 18px !important; }}
    .metrics-row > div {{ min-width: 46% !important; }}
}}
@media (max-width: 640px) {{
    .hide-xs {{ display: none !important; }}
    .strat-header {{ flex-direction: column; align-items: flex-start !important; gap: 8px !important; }}
    .detail-meta {{ gap: 6px !important; font-size: 0.78rem !important; }}
    .metrics-row {{ gap: 14px !important; }}
    .metrics-row > div {{ min-width: 100% !important; }}
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PLOTLY DARK LAYOUT
# ─────────────────────────────────────────────
_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=C["text_dim"], size=11),
    margin=dict(l=8, r=8, t=12, b=8),
)

# Cinematic diverging scales — deep wine → ember → amber → emerald
_RETDD_CS = [[0.0, "#1a0b1a"], [0.2, "#3b0f1e"], [0.4, "#e0425f"],
             [0.6, "#f5c04a"], [0.8, "#34d399"], [1.0, "#10b981"]]
_FIT_CS   = [[0.0, "#1a0b1a"], [0.2, "#3b0f1e"], [0.35, "#e0425f"],
             [0.55, "#f5c04a"], [0.75, "#34d399"], [1.0, "#10b981"]]
_PS_CS    = [[0.0, "#1a0b1a"], [0.3, "#3b0f1e"], [0.5, "#e0425f"],
             [0.7, "#f5c04a"], [0.85, "#34d399"], [1.0, "#10b981"]]


# ─────────────────────────────────────────────
# HTML HELPERS
# ─────────────────────────────────────────────

def eyebrow(text):
    return (f'<div style="color:{C["muted"]};font-size:0.66rem;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1.4px;">{text}</div>')


def status_dot(status, size=8, glow=True):
    color = C["green"] if status == "APPROVED" else (
            C["red"] if status == "DISCARDED" else C["yellow"])
    glow_css = f"box-shadow:0 0 8px {color}88;" if glow else ""
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'border-radius:50%;background:{color};{glow_css}"></span>')


def status_label(status):
    color = C["green"] if status == "APPROVED" else (
            C["red"] if status == "DISCARDED" else C["yellow"])
    txt = {"APPROVED": "Approved", "DISCARDED": "Discarded", "ERROR": "Error"}.get(status, status)
    return f'<span style="color:{color};font-weight:600;font-size:0.82rem;">{txt}</span>'


def inline_metric(label, value, color=None, sub=None):
    color = color or C["text"]
    sub_html = (f'<div style="color:{C["muted"]};font-size:0.72rem;margin-top:3px;'
                f'font-weight:400;">{sub}</div>') if sub else ""
    return f'''
    <div style="flex:1;min-width:110px;">
      <div style="color:{C["muted"]};font-size:0.66rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:1.2px;">{label}</div>
      <div style="color:{color};font-size:1.5rem;font-weight:600;
                  font-family:'JetBrains Mono',monospace;margin-top:6px;line-height:1;">{value}</div>
      {sub_html}
    </div>
    '''


def summary_stat(label, value, color=None, glow=False):
    color = color or C["text"]
    glow_css = f"text-shadow: 0 0 20px {color}66, 0 0 4px {color}33;" if glow else ""
    return f'''
    <div style="flex:1;min-width:120px;padding:18px 22px;
                border-right:1px solid {C["border"]};">
      <div style="color:{C["muted"]};font-size:0.64rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:1.4px;">{label}</div>
      <div style="color:{color};font-size:1.9rem;font-weight:700;
                  font-family:'JetBrains Mono',monospace;margin-top:10px;line-height:1;
                  letter-spacing:-0.5px;{glow_css}">{value}</div>
    </div>
    '''


def check_mark(ok):
    if ok:
        return f'<span style="color:{C["green"]};font-weight:600;font-size:0.82rem;">✓&nbsp;Pass</span>'
    return f'<span style="color:{C["red"]};font-weight:600;font-size:0.82rem;">✗&nbsp;Fail</span>'


def delta_badge(value, threshold, as_pct_points=False):
    """Render a delta vs threshold. Positive = green, negative = red."""
    diff = value - threshold
    sign = "+" if diff >= 0 else "−"
    color = C["green"] if diff >= 0 else C["red"]
    bg = "rgba(63,185,80,0.10)" if diff >= 0 else "rgba(248,81,73,0.10)"
    mag = abs(diff * 100) if as_pct_points else abs(diff)
    fmt = f"{mag:.1f}pp" if as_pct_points else f"{mag:.3f}"
    return (f'<span class="delta" style="color:{color};background:{bg};">'
            f'{sign}{fmt}</span>')


def score_mini_bar(val, width=60):
    """Compact score bar used inside strategy list rows."""
    pct = int(max(0.0, min(1.0, val)) * 100)
    if pct >= 70:
        grad = f"linear-gradient(90deg, {C['green_d']}, {C['green']})"
        glow = C["green"]
    elif pct >= 50:
        grad = f"linear-gradient(90deg, {C['yellow']}, {C['gold']})"
        glow = C["yellow"]
    else:
        grad = f"linear-gradient(90deg, {C['red_d']}, {C['red']})"
        glow = C["red"]
    return (f'<div style="width:{width}px;height:4px;background:rgba(255,255,255,0.06);'
            f'border-radius:999px;overflow:hidden;">'
            f'<div style="width:{pct}%;height:100%;background:{grad};'
            f'border-radius:999px;box-shadow:0 0 8px {glow}aa;"></div></div>')


def build_summary_text(results):
    """
    Render a plain-text summary, ordered alphabetically by strategy name
    (mismo orden que muestra StrategyQuant X para ir cruzando la lista):
      N. StrategyName    →  200 runs / 30% OOS    (if APPROVED)
      N. StrategyName    →  DECLINADA             (if DISCARDED)
      N. StrategyName    →  ERROR (reason)        (if ERROR)
    """
    if not results:
        return ""

    sorted_results = sorted(
        results, key=lambda r: r.get("strategy_name", "").lower()
    )

    names = [r.get("strategy_name", "Unknown") for r in sorted_results]
    max_name_len = min(max(len(n) for n in names), 55)

    n_total = len(sorted_results)
    n_ok = sum(1 for r in sorted_results if r.get("status") == "APPROVED")
    n_disc = sum(1 for r in sorted_results if r.get("status") == "DISCARDED")
    n_err = sum(1 for r in sorted_results if r.get("status") == "ERROR")

    header = [
        "WFM Analyzer — Resumen de estrategias",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total: {n_total}  ·  Aprobadas: {n_ok}  ·  "
        f"Descartadas: {n_disc}  ·  Errores: {n_err}",
        "Orden: alfabético (igual que StrategyQuant X)",
        "=" * (max_name_len + 38),
        "",
    ]

    width = len(str(n_total))
    lines = []
    for i, r in enumerate(sorted_results, 1):
        name = (r.get("strategy_name", "Unknown")[:max_name_len]).ljust(max_name_len)
        status = r.get("status", "ERROR")
        if status == "APPROVED":
            verdict = f"{r['best_runs']} runs / {r['best_oos_pct']}% OOS"
        elif status == "DISCARDED":
            verdict = "DECLINADA — no sirve"
        else:
            verdict = f"ERROR — {r.get('error', 'archivo inválido')}"
        lines.append(f"{str(i).rjust(width)}. {name}  →  {verdict}")

    return "\n".join(header + lines)


def build_summary_json(results):
    """Structured JSON export: summary + per-strategy records.

    Listado ordenado alfabéticamente por nombre (mismo orden que StrategyQuant X).
    """
    sorted_results = sorted(
        results, key=lambda r: r.get("strategy_name", "").lower()
    )

    n_total = len(sorted_results)
    n_ok = sum(1 for r in sorted_results if r.get("status") == "APPROVED")
    n_disc = sum(1 for r in sorted_results if r.get("status") == "DISCARDED")
    n_err = sum(1 for r in sorted_results if r.get("status") == "ERROR")

    strategies = []
    for i, r in enumerate(sorted_results, 1):
        status = r.get("status", "ERROR")
        record = {
            "index": i,
            "name": r.get("strategy_name", "Unknown"),
            "status": status,
        }
        if status == "APPROVED":
            record["optimization"] = {
                "runs": r.get("best_runs"),
                "oos_pct": r.get("best_oos_pct"),
                "label": f"{r.get('best_runs')} runs / {r.get('best_oos_pct')}% OOS",
            }
            record["metrics"] = {
                "score": r.get("score"),
                "fitness_oos": r.get("fitness_score"),
                "param_stability": r.get("ps_value"),
                "green_cells": r.get("green_count"),
                "total_cells": r.get("total_cells"),
                "green_pct": r.get("green_pct"),
                "zone_mean": r.get("zone_mean"),
                "zone_std": r.get("zone_std"),
            }
        elif status == "DISCARDED":
            record["verdict"] = "DECLINADA — no sirve"
            record["metrics"] = {
                "score": r.get("score"),
                "fitness_oos": r.get("fitness_score"),
                "param_stability": r.get("ps_value"),
                "green_cells": r.get("green_count"),
                "total_cells": r.get("total_cells"),
            }
        else:
            record["error"] = r.get("error", "archivo inválido")
        strategies.append(record)

    payload = {
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "thresholds": st.session_state.get("thresholds", {}),
        "summary": {
            "total": n_total,
            "approved": n_ok,
            "discarded": n_disc,
            "errors": n_err,
        },
        "strategies": strategies,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def filter_pill(label, active, key, count=None):
    """Render a clickable filter pill as markdown — caller pairs with st.button."""
    color = C["accent"] if active else C["text_dim"]
    border = C["accent"] if active else C["border_s"]
    bg = "rgba(91,140,255,0.08)" if active else "transparent"
    count_html = (f'<span style="color:{C["muted"]};margin-left:6px;'
                  f'font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;">'
                  f'{count}</span>') if count is not None else ""
    return (f'<span style="display:inline-flex;align-items:center;background:{bg};'
            f'border:1px solid {border};color:{color};padding:4px 10px;'
            f'border-radius:14px;font-size:0.72rem;font-weight:500;'
            f'letter-spacing:0.3px;">{label}{count_html}</span>')


# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────

def make_heatmap(matrix, runs_range, oos_range, zone_info=None, colorscale=None, height=520):
    cs = colorscale or _RETDD_CS
    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=[f"{o}%" for o in oos_range],
        y=[f"{r}" for r in runs_range],
        colorscale=cs,
        showscale=True,
        text=[[f"{matrix[i, j]:.2f}" for j in range(matrix.shape[1])]
              for i in range(matrix.shape[0])],
        texttemplate="%{text}",
        textfont=dict(size=11, family="JetBrains Mono", color="#0a0a0a"),
        hovertemplate="Runs: %{y}<br>OOS: %{x}<br>Valor: %{z:.4f}<extra></extra>",
        xgap=2, ygap=2,
        colorbar=dict(
            thickness=8, len=0.85,
            tickfont=dict(color=C["muted"], size=10),
            outlinewidth=0,
            bgcolor="rgba(0,0,0,0)",
        ),
    ))

    if zone_info:
        ci, cj = zone_info["center_i"], zone_info["center_j"]
        j0, j1 = zone_info["j_start"], zone_info["j_end"] - 1
        i0, i1 = zone_info["i_start"], zone_info["i_end"] - 1
        fig.add_shape(type="rect",
                      x0=j0 - 0.5, x1=j1 + 0.5, y0=i0 - 0.5, y1=i1 + 0.5,
                      line=dict(color=C["accent"], width=2.5), layer="above")
        fig.add_shape(type="rect",
                      x0=cj - 0.5, x1=cj + 0.5, y0=ci - 0.5, y1=ci + 0.5,
                      line=dict(color="#fbbf24", width=3), layer="above")
        fig.add_annotation(
            x=f"{oos_range[cj]}%", y=f"{runs_range[ci]}",
            text="★", showarrow=False,
            font=dict(size=20, color="#fbbf24"),
        )

    fig.update_layout(
        xaxis=dict(title=dict(text="OOS %", font=dict(color=C["muted"], size=11)),
                   tickfont=dict(color=C["text_dim"], size=11),
                   showgrid=False, zeroline=False),
        yaxis=dict(title=dict(text="Runs", font=dict(color=C["muted"], size=11)),
                   tickfont=dict(color=C["text_dim"], size=11),
                   showgrid=False, zeroline=False),
        height=height, **_DARK,
    )
    return fig


# ─────────────────────────────────────────────
# STRATEGY LIST (sidebar)
# ─────────────────────────────────────────────

def apply_filters(results, search, status_filter, sort_by):
    """Filter + sort results, return list of (original_idx, result) tuples."""
    items = list(enumerate(results))
    if status_filter != "all":
        wanted = {"approved": "APPROVED", "discarded": "DISCARDED",
                  "error": "ERROR"}[status_filter]
        items = [t for t in items if t[1].get("status") == wanted]
    if search:
        q = search.lower().strip()
        items = [t for t in items if q in t[1].get("strategy_name", "").lower()]
    if sort_by == "name":
        items.sort(key=lambda t: t[1].get("strategy_name", "").lower())
    # "score" keeps original rank order (already sorted by rank_strategies)
    return items


def render_strategy_list(results, selected_idx):
    # ── Search input ──
    st.text_input(
        "search",
        placeholder="Buscar estrategia...",
        label_visibility="collapsed",
        key="strat_search",
    )

    # ── Filter pills row — styled buttons ──
    counts = {
        "all":       len(results),
        "approved":  sum(1 for r in results if r.get("status") == "APPROVED"),
        "discarded": sum(1 for r in results if r.get("status") == "DISCARDED"),
        "error":     sum(1 for r in results if r.get("status") == "ERROR"),
    }
    current = st.session_state.strat_filter
    fp_cols = st.columns(4, gap="small")
    for col, key, label in [
        (fp_cols[0], "all",       "Todas"),
        (fp_cols[1], "approved",  "OK"),
        (fp_cols[2], "discarded", "NO"),
        (fp_cols[3], "error",     "ERR"),
    ]:
        active = current == key
        col.markdown(
            f'<div class="flt-btn {"flt-active" if active else ""}">',
            unsafe_allow_html=True,
        )
        if col.button(f"{label}  {counts[key]}",
                      key=f"flt_{key}", use_container_width=True):
            st.session_state.strat_filter = key
            st.rerun()
        col.markdown("</div>", unsafe_allow_html=True)

    # ── Sort selector ──
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    sort_cols = st.columns([1, 1])
    with sort_cols[0]:
        st.markdown(
            f'<div style="color:{C["muted"]};font-size:0.68rem;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1px;padding-top:11px;">'
            f'Ordenar por</div>',
            unsafe_allow_html=True,
        )
    with sort_cols[1]:
        sort_choice = st.selectbox(
            "sort", options=["score", "name"],
            format_func=lambda x: "Score" if x == "score" else "Nombre",
            index=["score", "name"].index(st.session_state.strat_sort),
            label_visibility="collapsed", key="sort_select",
        )
        if sort_choice != st.session_state.strat_sort:
            st.session_state.strat_sort = sort_choice
            st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Apply filters ──
    items = apply_filters(
        results,
        st.session_state.strat_search,
        st.session_state.strat_filter,
        st.session_state.strat_sort,
    )

    if not items:
        st.markdown(
            f'<div style="padding:2rem 1rem;text-align:center;color:{C["muted"]};'
            f'font-size:0.82rem;border:1px dashed {C["border"]};border-radius:8px;">'
            f'Sin resultados para este filtro.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Scroll wrapper ──
    st.markdown(
        '<div style="max-height:640px;overflow-y:auto;padding-right:4px;">',
        unsafe_allow_html=True,
    )

    for original_idx, r in items:
        is_sel = original_idx == selected_idx
        status = r.get("status", "ERROR")
        name = r.get("strategy_name", "Unknown")
        score = r.get("score", 0)
        best = (f"{r['best_runs']}r · {r['best_oos_pct']}% OOS"
                if "best_runs" in r else "—")

        dot_color = (C["green"] if status == "APPROVED" else
                     C["red"] if status == "DISCARDED" else C["yellow"])

        rank_color = C["muted"]
        if status == "APPROVED" and original_idx < 3:
            rank_color = ["#fbbf24", "#c0c0c0", "#cd7f32"][original_idx]
        elif status == "APPROVED":
            rank_color = C["text_dim"]

        row_class = "strat-row selected" if is_sel else "strat-row"
        row_bg = "transparent" if is_sel else "rgba(255,255,255,0.015)"
        row_border = "transparent" if is_sel else C["border"]
        name_color = C["text"] if is_sel else C["text_dim"]
        score_color = C["accent"] if is_sel else C["text_dim"]

        st.markdown(f"""
        <div class="{row_class}" style="background:{row_bg};border:1px solid {row_border};
                    border-radius:10px;padding:11px 13px 11px 16px;margin-bottom:7px;
                    backdrop-filter:blur(8px);">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="color:{rank_color};font-family:'JetBrains Mono',monospace;
                         font-size:0.7rem;font-weight:700;min-width:24px;
                         letter-spacing:0.3px;">
              #{original_idx + 1:02d}</span>
            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
                         background:{dot_color};box-shadow:0 0 10px {dot_color}aa, 0 0 2px {dot_color};
                         flex-shrink:0;"></span>
            <span style="color:{name_color};font-size:0.83rem;
                         font-weight:{600 if is_sel else 500};flex:1;
                         letter-spacing:-0.1px;
                         overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                  title="{name}">{name}</span>
            <span style="color:{score_color};font-family:'JetBrains Mono',monospace;
                         font-size:0.78rem;font-weight:600;">
              {score:.3f}</span>
          </div>
          <div style="margin-top:7px;padding-left:42px;display:flex;
                      align-items:center;gap:10px;">
            <span style="color:{C['muted']};font-size:0.72rem;
                         font-family:'JetBrains Mono',monospace;flex:1;
                         overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              {best}</span>
            {score_mini_bar(score, 56)}
          </div>
        </div>
        """, unsafe_allow_html=True)

        btn_class = "strat-click active" if is_sel else "strat-click"
        st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
        clicked = st.button(
            "Abierta" if is_sel else "Abrir",
            key=f"sel_{original_idx}",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        if clicked and not is_sel:
            st.session_state.selected_idx = original_idx
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DETAIL PANEL
# ─────────────────────────────────────────────

_MATRIX_OPTIONS = [
    ("retdd",   "IS Ret/DD",        _RETDD_CS, "IS Return / Drawdown ratio (surface 3D de SQX)"),
    ("fitness", "Fitness OOS",      _FIT_CS,   "Fitness OOS normalizado 0-1"),
    ("ps",      "Param Stability",  _PS_CS,    "Sys. Param Permutation stability"),
]


def render_detail(result):
    name = result["strategy_name"]
    status = result["status"]
    runs = result.get("best_runs", "?")
    oos = result.get("best_oos_pct", "?")
    score = result.get("score", 0)
    fit = result.get("fitness_score", 0)
    ps = result.get("ps_value", 0)
    green = result.get("green_count", 0)
    total = result.get("total_cells", 9)
    wfm_ok = result.get("wfm_pass", False)
    ps_ok = result.get("ps_pass", False)
    green_pct = result.get("green_pct", 0)
    zone_info = result.get("zone_info", {})
    zone_name = result.get("zone_matrix_name", "retdd")

    # ─── Strategy header (single line) ───
    st.markdown(f"""
    <div class="strat-header" style="display:flex;align-items:flex-end;
                justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:4px;">
      <div style="flex:1;min-width:250px;">
        {eyebrow("Estrategia")}
        <h2 style="margin:8px 0 0;font-size:1.65rem;
                    font-weight:700;letter-spacing:-0.5px;line-height:1.15;
                    background:linear-gradient(135deg, #ffffff 0%, #b4b4c4 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;
                    overflow:hidden;text-overflow:ellipsis;">{name}</h2>
        <div class="detail-meta" style="margin-top:12px;display:flex;
                    align-items:center;gap:14px;flex-wrap:wrap;">
          <span style="display:inline-flex;align-items:center;gap:8px;
                       padding:4px 10px;border-radius:999px;
                       background:rgba(255,255,255,0.03);
                       border:1px solid {C['border_g']};">
            {status_dot(status, 8)}{status_label(status)}
          </span>
          <span style="color:{C['subtle']};">·</span>
          <span style="color:{C['muted']};font-size:0.82rem;">Score</span>
          <span style="color:{C['text']};font-family:'JetBrains Mono',monospace;
                       font-size:0.98rem;font-weight:700;letter-spacing:-0.3px;">{score:.3f}</span>
          <span style="color:{C['subtle']};">·</span>
          <span style="color:{C['muted']};font-size:0.82rem;">Optimización</span>
          <span style="font-family:'JetBrains Mono',monospace;
                       font-size:0.98rem;font-weight:700;letter-spacing:-0.3px;
                       background:linear-gradient(135deg, {C['accent']}, {C['accent_2']});
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       background-clip:text;">
            {runs} runs / {oos}% OOS</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── Inline metrics row with delta vs thresholds ───
    fit_thr = st.session_state.thresholds["fitness"]
    ps_thr = st.session_state.thresholds["ps"]
    min_green = st.session_state.thresholds["min_green"]

    fit_color = C["green"] if fit >= fit_thr else (C["yellow"] if fit >= fit_thr - 0.15 else C["red"])
    ps_color = C["green"] if ps_ok else C["red"]
    green_color = C["green"] if wfm_ok else C["red"]

    pw = zone_info.get("pw_dev", 0)
    card = zone_info.get("card_dev", 0)

    fit_val_html = f'{fit:.3f}{delta_badge(fit, fit_thr)}'
    ps_val_html = f'{ps:.3f}{delta_badge(ps, ps_thr)}'

    # Green cells delta: by count vs min_green
    gc_diff = green - min_green
    gc_sign = "+" if gc_diff >= 0 else "−"
    gc_color = C["green"] if gc_diff >= 0 else C["red"]
    gc_bg = "rgba(63,185,80,0.10)" if gc_diff >= 0 else "rgba(248,81,73,0.10)"
    gc_badge = (f'<span class="delta" style="color:{gc_color};background:{gc_bg};">'
                f'{gc_sign}{abs(gc_diff)}</span>')
    green_val_html = f'{green}/{total}{gc_badge}'

    metrics_html = f'''
    <div class="metrics-row" style="display:flex;gap:32px;flex-wrap:wrap;
                                     align-items:flex-start;padding:6px 0;">
      {inline_metric("Fitness OOS", fit_val_html, fit_color,
                     sub=f"threshold {fit_thr:.2f} · {check_mark(fit >= fit_thr)}")}
      {inline_metric("Param Stability", ps_val_html, ps_color,
                     sub=f"threshold {ps_thr:.2f} · {check_mark(ps_ok)}")}
      {inline_metric("Green Cells", green_val_html, green_color,
                     sub=f"{green_pct:.0f}% verdes · min {min_green} · {check_mark(wfm_ok)}")}
      {inline_metric("Zone Flatness", f"{pw:.2f}", C["text"],
                     sub=f"max card. dev {card:.2f}")}
    </div>
    '''
    st.markdown(metrics_html, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── Matrix toggle ───
    active_matrix = st.session_state.get("active_matrix", "retdd")

    # Disable retdd option if matrix is empty
    retdd_mx = result.get("retdd_matrix")
    has_retdd = retdd_mx is not None and np.any(retdd_mx > 0)
    if not has_retdd and active_matrix == "retdd":
        active_matrix = "ps"
        st.session_state.active_matrix = "ps"

    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-bottom:10px;">'
        f'{eyebrow("Superficie")}'
        f'<span style="color:{C["muted"]};font-size:0.72rem;">'
        f'★ óptimo · recuadro azul = zona estable 3×3</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3, _spacer = st.columns([1, 1, 1, 4])
    toggles = [
        (b1, "retdd",   "IS Ret/DD",       "seg-left",  has_retdd),
        (b2, "fitness", "Fitness OOS",     "",          True),
        (b3, "ps",      "Param Stability", "seg-right", True),
    ]
    for col, key, label, edge, enabled in toggles:
        active_class = "active" if active_matrix == key else ""
        disabled_style = "opacity:0.4;pointer-events:none;" if not enabled else ""
        col.markdown(
            f'<div class="seg {edge} {active_class}" style="{disabled_style}">',
            unsafe_allow_html=True,
        )
        if col.button(label if enabled else f"{label} (n/a)",
                      key=f"mx_{key}", use_container_width=True):
            if enabled:
                st.session_state.active_matrix = key
                st.rerun()
        col.markdown("</div>", unsafe_allow_html=True)

    # ─── Active heatmap ───
    matrix_map = {
        "retdd":   (result.get("retdd_matrix"),   _RETDD_CS),
        "fitness": (result.get("fitness_matrix"), _FIT_CS),
        "ps":      (result.get("ps_matrix"),      _PS_CS),
    }
    mx, cs = matrix_map[active_matrix]
    if mx is None or not np.any(mx):
        mx = result["fitness_matrix"]
        cs = _FIT_CS

    fig = make_heatmap(
        mx, result["runs_range"], result["oos_range"],
        zone_info=zone_info, colorscale=cs, height=520,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ─── Zone footer ───
    mean_v = zone_info.get("mean", 0)
    std_v = zone_info.get("std", 0)
    basis = "IS Ret/DD" if zone_name == "retdd" else "Param Stability"
    st.markdown(f"""
    <div style="color:{C['muted']};font-size:0.76rem;padding-top:10px;
                border-top:1px solid {C['border']};margin-top:10px;
                display:flex;gap:24px;flex-wrap:wrap;align-items:center;">
      <span>Zona detectada sobre <b style="color:{C['text_dim']};">{basis}</b></span>
      <span>·</span>
      <span>pairwise dev <b style="color:{C['text_dim']};
            font-family:'JetBrains Mono',monospace;">{pw:.3f}</b></span>
      <span>·</span>
      <span>max cardinal dev <b style="color:{C['text_dim']};
            font-family:'JetBrains Mono',monospace;">{card:.3f}</b></span>
      <span>·</span>
      <span>mean <b style="color:{C['text_dim']};
            font-family:'JetBrains Mono',monospace;">{mean_v:.3f}</b></span>
      <span>·</span>
      <span>std <b style="color:{C['text_dim']};
            font-family:'JetBrains Mono',monospace;">{std_v:.3f}</b></span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []
if "selected_idx" not in st.session_state:
    st.session_state.selected_idx = 0
if "thresholds" not in st.session_state:
    st.session_state.thresholds = {"fitness": 0.70, "ps": 0.75, "min_green": 7}
if "active_matrix" not in st.session_state:
    st.session_state.active_matrix = "retdd"
if "strat_search" not in st.session_state:
    st.session_state.strat_search = ""
if "strat_filter" not in st.session_state:
    st.session_state.strat_filter = "all"   # all | approved | discarded | error
if "strat_sort" not in st.session_state:
    st.session_state.strat_sort = "score"   # score | name


# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding-bottom:18px;margin-bottom:22px;
            border-bottom:1px solid {C['border']};position:relative;">
  <div style="display:flex;align-items:center;gap:14px;min-width:0;">
    <div style="width:36px;height:36px;
                background:linear-gradient(135deg, {C['accent']} 0%, {C['accent_2']} 100%);
                border-radius:10px;display:flex;align-items:center;
                justify-content:center;color:#fff;font-weight:800;font-size:1.05rem;
                font-family:'JetBrains Mono',monospace;flex-shrink:0;
                box-shadow:0 4px 20px rgba(124,107,255,0.45),
                           inset 0 1px 0 rgba(255,255,255,0.25),
                           inset 0 -1px 0 rgba(0,0,0,0.2);
                letter-spacing:-1px;">W</div>
    <div style="min-width:0;">
      <div style="font-size:1.08rem;font-weight:700;
                   letter-spacing:-0.4px;line-height:1.2;
                   background:linear-gradient(135deg, #ffffff 0%, #c4c4d4 100%);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;">WFM Analyzer</div>
      <div class="hide-xs" style="color:{C['muted']};font-size:0.7rem;margin-top:2px;
                   letter-spacing:0.3px;">
        StrategyQuant · Walk Forward Matrix</div>
    </div>
  </div>
  <div class="hide-sm" style="display:flex;align-items:center;gap:10px;
              color:{C['muted']};font-size:0.7rem;
              font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;">
    <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                 background:{C['green']};box-shadow:0 0 8px {C['green']};
                 animation:pulse 2s ease-in-out infinite;"></span>
    <span>v2.0 · live</span>
  </div>
</div>
<style>
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }}
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UPLOAD + CONTROLS
# ─────────────────────────────────────────────
up_col, run_col, cfg_col = st.columns([5, 1.2, 1.5], gap="medium")

with up_col:
    st.markdown(eyebrow("Archivos .sqx"), unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        " ", type=["sqx"], accept_multiple_files=True,
        label_visibility="collapsed",
    )

with run_col:
    st.markdown(eyebrow("Análisis"), unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    run_btn = st.button("▶  Analizar", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with cfg_col:
    st.markdown(eyebrow("Umbrales"), unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    with st.expander("Ajustar", expanded=False):
        st.session_state.thresholds["fitness"] = st.slider(
            "Fitness OOS mínimo", 0.50, 0.95,
            st.session_state.thresholds["fitness"], 0.01)
        st.session_state.thresholds["ps"] = st.slider(
            "Param Stability mínimo", 0.60, 0.95,
            st.session_state.thresholds["ps"], 0.01)
        st.session_state.thresholds["min_green"] = st.slider(
            "Green cells mínimas", 5, 9,
            st.session_state.thresholds["min_green"], 1)


# ─────────────────────────────────────────────
# RUN ANALYSIS
# ─────────────────────────────────────────────
if run_btn and uploaded_files:
    prog = st.progress(0, text="Procesando…")
    raw = []
    for i, uf in enumerate(uploaded_files):
        prog.progress((i + 1) / len(uploaded_files), text=f"Analizando {uf.name}")
        with tempfile.NamedTemporaryFile(suffix=".sqx", delete=False) as tmp:
            tmp.write(uf.read())
            tmp_path = tmp.name
        sqx = parse_sqx(tmp_path)
        raw.append(analyze_strategy(
            sqx,
            fitness_threshold=st.session_state.thresholds["fitness"],
            ps_threshold=st.session_state.thresholds["ps"],
            min_green=st.session_state.thresholds["min_green"],
        ))
    prog.empty()
    st.session_state.results = rank_strategies(raw)
    st.session_state.selected_idx = 0
    n_ok = sum(1 for r in st.session_state.results if r.get("status") == "APPROVED")
    st.success(f"Análisis completo — {n_ok} aprobadas de {len(raw)}")
elif run_btn:
    st.warning("Sube al menos un archivo .sqx primero.")


# ─────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────
if st.session_state.results:
    results = st.session_state.results
    n_total = len(results)
    n_ok = sum(1 for r in results if r.get("status") == "APPROVED")
    n_disc = sum(1 for r in results if r.get("status") == "DISCARDED")
    n_err = sum(1 for r in results if r.get("status") == "ERROR")
    top_score = max((r.get("score", 0) for r in results), default=0)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ─── Summary bar — glass panel ───
    st.markdown(f"""
    <div class="summary-bar" style="display:flex;
                background:linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
                border:1px solid {C['border_g']};
                border-radius:14px;overflow:hidden;margin-bottom:22px;
                backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
                box-shadow:0 4px 30px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04);">
      {summary_stat("Total", n_total, C["text"])}
      {summary_stat("Aprobadas", n_ok, C["green"], glow=True)}
      {summary_stat("Descartadas", n_disc, C["red"])}
      {summary_stat("Errores", n_err, C["yellow"])}
      <div style="flex:1;min-width:120px;padding:18px 22px;position:relative;
                  background:linear-gradient(135deg, rgba(124,107,255,0.06), rgba(78,168,255,0.02));">
        <div style="color:{C["muted"]};font-size:0.64rem;font-weight:600;
                    text-transform:uppercase;letter-spacing:1.4px;">Top Score</div>
        <div style="font-size:1.9rem;font-weight:700;
                    font-family:'JetBrains Mono',monospace;margin-top:10px;line-height:1;
                    letter-spacing:-0.5px;
                    background:linear-gradient(135deg, {C['accent']}, {C['accent_2']});
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;
                    filter:drop-shadow(0 0 12px rgba(124,107,255,0.5));">
          {top_score:.3f}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Summary list + export (always visible at top) ───
    summary_text = build_summary_text(results)
    summary_json = build_summary_json(results)
    ts_label = datetime.now().strftime("%Y%m%d_%H%M")

    st.markdown(f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:10px;padding:14px 18px;margin-bottom:16px;
                display:flex;align-items:center;justify-content:space-between;
                gap:16px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;min-width:0;">
        <div>
          {eyebrow("Resumen exportable")}
          <div style="color:{C['text']};font-size:0.92rem;font-weight:600;
                      margin-top:4px;">
            Lista completa · {n_total} estrategia{'s' if n_total != 1 else ''}
          </div>
        </div>
        <span style="color:{C['subtle']};" class="hide-sm">·</span>
        <div class="hide-sm" style="color:{C['muted']};font-size:0.78rem;max-width:340px;">
          Descarga JSON/TXT, o expande abajo y copia la lista desde el recuadro.
        </div>
      </div>
      <div style="flex:0 0 auto;"></div>
    </div>
    """, unsafe_allow_html=True)

    dl1, dl2, exp_col = st.columns([1.2, 1.2, 4], gap="small")
    with dl1:
        st.download_button(
            "⬇  Descargar JSON",
            data=summary_json.encode("utf-8"),
            file_name=f"wfm_resumen_{ts_label}.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json_top",
        )
    with dl2:
        st.download_button(
            "⬇  Descargar .txt",
            data=summary_text.encode("utf-8"),
            file_name=f"wfm_resumen_{ts_label}.txt",
            mime="text/plain",
            use_container_width=True,
            key="dl_txt_top",
        )

    with st.expander(f"Ver lista completa ({n_total} estrategias) — clic para copiar",
                     expanded=False):
        st.code(summary_text, language="text")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ─── Two-column layout ───
    left_col, right_col = st.columns([1, 2.8], gap="large")

    with left_col:
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'margin-bottom:12px;">'
            f'{eyebrow(f"Estrategias · {n_total}")}'
            f'</div>',
            unsafe_allow_html=True,
        )
        render_strategy_list(results, st.session_state.selected_idx)

    with right_col:
        selected = results[st.session_state.selected_idx]
        if selected.get("status") == "ERROR":
            st.markdown(f"""
            <div style="padding:3rem 2rem;text-align:center;
                        border:1px solid {C['border']};border-radius:10px;
                        background:{C['surface']};">
              <div style="color:{C['yellow']};font-size:2rem;margin-bottom:14px;">⚠</div>
              <div style="color:{C['text']};font-size:1rem;font-weight:600;">
                Error al procesar</div>
              <div style="color:{C['muted']};font-size:0.85rem;margin-top:8px;">
                {selected.get('error', 'Error desconocido')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            render_detail(selected)

else:
    # ─── Empty state ───
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="border:1px dashed rgba(255,255,255,0.09);border-radius:16px;
                padding:5rem 2rem;text-align:center;
                background:
                  radial-gradient(ellipse 400px 200px at 50% 0%, rgba(124,107,255,0.08), transparent 70%),
                  linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.005));
                backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
                position:relative;overflow:hidden;
                box-shadow:inset 0 1px 0 rgba(255,255,255,0.04);">
      <div style="position:absolute;top:-50%;left:50%;transform:translateX(-50%);
                  width:400px;height:400px;
                  background:radial-gradient(circle, rgba(124,107,255,0.12), transparent 60%);
                  filter:blur(40px);pointer-events:none;"></div>
      <div style="position:relative;z-index:1;">
        <div style="font-size:3rem;margin-bottom:24px;line-height:1;
                    background:linear-gradient(135deg, {C['accent']}, {C['accent_2']});
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;
                    filter:drop-shadow(0 0 20px rgba(124,107,255,0.5));
                    font-family:'JetBrains Mono',monospace;">◆</div>
        <div style="color:{C['text']};font-size:1.15rem;font-weight:700;
                    letter-spacing:-0.3px;">Sin datos cargados</div>
        <div style="color:{C['text_dim']};font-size:0.88rem;margin-top:10px;
                    max-width:460px;margin-left:auto;margin-right:auto;line-height:1.6;">
          Sube uno o varios archivos <b style="color:{C['text']};">.sqx</b>
          y pulsa <b style="color:{C['accent']};">Analizar</b> para comenzar.
        </div>
        <div style="color:{C['muted']};font-size:0.74rem;margin-top:22px;
                    letter-spacing:0.3px;">
          Carga masiva · Zona estable detectada · Ranking automático
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BOTTOM STATUS BAR
# ─────────────────────────────────────────────
_results = st.session_state.get("results", [])
_total_sb = len(_results)
_ok_sb = sum(1 for r in _results if r.get("status") == "APPROVED")
_active_mx = st.session_state.get("active_matrix", "retdd")
_mx_label = {"retdd": "IS Ret/DD", "fitness": "Fitness OOS", "ps": "Param Stability"}[_active_mx]
_filter = st.session_state.get("strat_filter", "all")
_sort = st.session_state.get("strat_sort", "score")

_status_color = C["green"] if _total_sb else C["muted"]
_status_text = (f'<span style="color:{_status_color};">●</span>&nbsp;'
                f'{_ok_sb}/{_total_sb} aprobadas' if _total_sb else
                f'<span style="color:{C["muted"]};">●</span>&nbsp;sin datos')

st.markdown(f"""
<div style="position:fixed;bottom:0;left:0;right:0;z-index:999;
            background:linear-gradient(180deg, rgba(8,8,12,0.6), rgba(5,5,7,0.92));
            backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);
            border-top:1px solid {C['border_g']};
            padding:8px 22px;display:flex;align-items:center;
            justify-content:space-between;gap:12px;font-size:0.7rem;
            font-family:'JetBrains Mono',monospace;color:{C['muted']};
            letter-spacing:0.3px;">
  <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;min-width:0;">
    <span>{_status_text}</span>
    <span class="hide-xs">·</span>
    <span class="hide-xs">filtro <b style="color:{C['text_dim']};">{_filter}</b></span>
    <span class="hide-sm">·</span>
    <span class="hide-sm">orden <b style="color:{C['text_dim']};">{_sort}</b></span>
    <span class="hide-sm">·</span>
    <span class="hide-sm">superficie <b style="color:{C['text_dim']};">{_mx_label}</b></span>
  </div>
  <div class="hide-xs" style="display:flex;gap:14px;align-items:center;">
    <span>thr&nbsp;<b style="color:{C['text_dim']};">fit {st.session_state.thresholds['fitness']:.2f}</b></span>
    <span>·</span>
    <span><b style="color:{C['text_dim']};">ps {st.session_state.thresholds['ps']:.2f}</b></span>
    <span>·</span>
    <span><b style="color:{C['text_dim']};">min {st.session_state.thresholds['min_green']}</b></span>
  </div>
</div>
<div style="height:34px;"></div>
""", unsafe_allow_html=True)
