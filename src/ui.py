"""Reusable UI components and the global stylesheet."""

from __future__ import annotations

import html
from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea {font-family: 'Inter', 'Segoe UI', sans-serif;}
.block-container {padding-top: 4.6rem; padding-bottom: 3rem; max-width: 1320px;}
footer, #MainMenu {visibility: hidden;}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {background: linear-gradient(180deg, #F5F7FF 0%, #EEF2FF 100%); border-right: 1px solid #E0E7FF;}
section[data-testid="stSidebar"] h5 {margin: 1.1rem 0 .3rem 0; font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: #6366F1;}
.brand {display:flex; align-items:center; gap:12px; margin: .2rem 0 .6rem 0;}
.brand-logo {display:inline-flex; width:40px; height:40px; align-items:center; justify-content:center; border-radius:12px;
  background: linear-gradient(135deg, #4F46E5, #06B6D4); color:#fff; font-size:20px; box-shadow: 0 6px 16px rgba(79,70,229,.35);}
.brand-name {font-weight:800; font-size:1.15rem; color:#1E1B4B; line-height:1.1;}
.brand-tag {font-size:.72rem; color:#64748B;}

/* ---------- page header ---------- */
.page-head {margin: 0 0 1.1rem 0;}
.page-head h1 {font-size: 1.85rem; font-weight: 800; color:#0F172A; margin:0; padding:0; letter-spacing:-.02em;}
.page-head p {margin:.25rem 0 0 0; color:#64748B; font-size:1rem;}

/* ---------- cards ---------- */
div[data-testid="stMetric"] {background:#fff; border:1px solid #E2E8F0; border-radius:16px; padding:16px 20px;
  box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 6px 18px rgba(15,23,42,.04);}
div[data-testid="stMetric"] label {color:#64748B; font-weight:500;}
div[data-testid="stMetricValue"] {font-weight:700; letter-spacing:-.01em; font-size:1.7rem;}
div[data-testid="stMetricValue"] > div {white-space: normal; overflow: visible; text-overflow: clip;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
.stButton > button, .stDownloadButton > button {border-radius:12px; font-weight:600;}
button[kind="primary"] {background: linear-gradient(135deg, #4F46E5, #7C3AED); border:none;}
button[data-baseweb="tab"] {font-weight:600;}

/* ---------- pills ---------- */
.pill {display:inline-block; padding:3px 12px; border-radius:999px; font-size:.78rem; font-weight:600;}
.pill-ok {background:#DCFCE7; color:#166534;} .pill-warn {background:#FEF3C7; color:#92400E;}
.pill-ai {background:#EDE9FE; color:#5B21B6;} .pill-off {background:#F1F5F9; color:#475569;}
.muted {color:#64748B; font-size:.78rem;}

/* ---------- action cards ---------- */
.action {background:#fff; border:1px solid #E2E8F0; border-left:5px solid #94A3B8; border-radius:14px;
  padding:14px 18px; margin-bottom:12px; box-shadow:0 1px 2px rgba(15,23,42,.04);}
.action.High {border-left-color:#EF4444;} .action.Medium {border-left-color:#F59E0B;} .action.Low {border-left-color:#10B981;}
.action .top {display:flex; align-items:center; gap:10px; margin-bottom:4px;}
.action .title {font-weight:700; color:#0F172A; font-size:1.02rem;}
.action .detail {color:#334155; font-size:.93rem; line-height:1.5;}
.action .meta {margin-top:8px; font-size:.8rem; color:#64748B;}
.tag {font-size:.68rem; font-weight:700; padding:2px 8px; border-radius:6px; text-transform:uppercase; letter-spacing:.04em;}
.tag.High {background:#FEE2E2; color:#991B1B;} .tag.Medium {background:#FEF3C7; color:#92400E;} .tag.Low {background:#DCFCE7; color:#166534;}
.summary-box {background:linear-gradient(135deg,#EEF2FF,#F0F9FF); border:1px solid #E0E7FF; border-radius:14px; padding:14px 18px;
  color:#1E293B; margin-bottom:14px;}
.verdict {border-radius:14px; padding:16px 20px; font-weight:700; font-size:1.1rem; margin-bottom:10px;}
.verdict.success {background:#DCFCE7; color:#166534;} .verdict.warning {background:#FEF3C7; color:#92400E;}
.verdict.error {background:#FEE2E2; color:#991B1B;}
.footer-note {color:#94A3B8; font-size:.78rem; margin-top:2rem; text-align:center;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-head"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def source_pill(mode: str, model: Optional[str] = None) -> str:
    if mode == "ai":
        label = f"✦ Gemini · {model}" if model else "✦ Gemini"
        return f'<span class="pill pill-ai">{html.escape(label)}</span>'
    return '<span class="pill pill-off">Rule-based engine</span>'


def render_actions(actions: Iterable[Dict]) -> None:
    """Prioritised action cards. All text is HTML-escaped because it may come from an AI model."""
    for a in actions:
        pr = a["priority"] if a["priority"] in ("High", "Medium", "Low") else "Medium"
        meta = " · ".join(
            part for part in (f"Impact: {a['impact']}" if a.get("impact") else "",
                              f"When: {a['timeframe']}" if a.get("timeframe") else "") if part
        )
        st.markdown(
            f'<div class="action {pr}"><div class="top"><span class="tag {pr}">{pr}</span>'
            f'<span class="title">{html.escape(a["title"])}</span></div>'
            f'<div class="detail">{html.escape(a["detail"])}</div>'
            + (f'<div class="meta">{html.escape(meta)}</div>' if meta else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def verdict_box(text: str, tone: str) -> None:
    st.markdown(f'<div class="verdict {tone}">{html.escape(text)}</div>', unsafe_allow_html=True)


def footer(disclaimer: str) -> None:
    st.markdown(f'<div class="footer-note">{html.escape(disclaimer)}</div>', unsafe_allow_html=True)


def kpis(items: List[Tuple]) -> None:
    """items: (label, value[, delta[, delta_color]]) rendered as a metric row."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, *rest = item
        delta = rest[0] if rest else None
        color = rest[1] if len(rest) > 1 else "normal"
        col.metric(label, value, delta, delta_color=color)
