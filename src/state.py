"""Shared Streamlit state: sidebar profile, AI settings and the per-run context object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

from . import llm
from .advisor import build_context
from .budget import NEEDS, RISK_LEVELS, WANTS, BudgetAnalysis, FinanceProfile, analyze_budget
from .config import APP_NAME, APP_TAGLINE, ENV_PATH, MODEL_CHOICES, KeyInfo, default_model, resolve_key
from .forecast import forecast_series
from .projections import goal_plan
from .transactions import build_statement_context, monthly_expenses

DEFAULT_EXPENSES = {
    "Rent / Home Loan": 14000, "Groceries & Food": 7000, "Utilities & Bills": 3500, "Transport": 4000,
    "EMI / Debt": 3500, "Insurance": 1500, "Health": 1000, "Dining Out": 3000, "Shopping": 3000,
    "Entertainment": 1500, "Travel": 1500, "Subscriptions": 1200, "Other": 2000,
}
GOALS = ["Retirement", "Home", "Car", "Child's Education", "Wedding", "Travel", "Custom"]

SIDEBAR_DEFAULTS = {
    "age": 28, "income": 58000, "savings": 120000, "risk": "Medium",
    "goal_name": "Retirement", "goal_amt": 5_000_000, "goal_years": 15,
    **{f"e_{k}": v for k, v in DEFAULT_EXPENSES.items()},
}


@dataclass
class Ctx:
    profile: FinanceProfile
    analysis: BudgetAnalysis
    plan: dict
    key: KeyInfo
    model: str
    stmt: Optional[pd.DataFrame]
    stmt_context: str
    snapshot: tuple

    @property
    def ai_on(self) -> bool:
        return self.key.available

    def full_context(self) -> str:
        return build_context(self.profile, self.analysis, self.plan, self.stmt_context)


# ----------------------------------------------------------------------------- sticky widgets
# Widgets that are not rendered on the current page lose their state in Streamlit. These helpers
# mirror every value into a plain session key so page-level inputs survive page navigation.
def sticky_number(label, key, default, **kw):
    value = st.number_input(label, value=st.session_state.get(key, default), key=f"w_{key}", **kw)
    st.session_state[key] = value
    return value


def sticky_slider(label, key, default, **kw):
    value = st.slider(label, value=st.session_state.get(key, default), key=f"w_{key}", **kw)
    st.session_state[key] = value
    return value


def sticky_select(label, key, options, default, **kw):
    stored = st.session_state.get(key, default)
    index = options.index(stored) if stored in options else options.index(default)
    value = st.selectbox(label, options, index=index, key=f"w_{key}", **kw)
    st.session_state[key] = value
    return value


# ----------------------------------------------------------------------------- sidebar
def init_state() -> None:
    for key, value in SIDEBAR_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def reset_profile() -> None:
    for key, value in SIDEBAR_DEFAULTS.items():
        st.session_state[key] = value


def render_sidebar() -> None:
    """Sidebar: brand, profile, goal, expenses and AI settings. Runs on every page."""
    with st.sidebar:
        st.markdown(
            f'<div class="brand"><span class="brand-logo">◆</span><div><div class="brand-name">{APP_NAME}</div>'
            f'<div class="brand-tag">{APP_TAGLINE}</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("##### Profile")
        st.number_input("Age", 18, 80, key="age")
        st.number_input("Monthly income (₹)", min_value=0, step=1000, key="income")
        st.number_input("Savings & investments (₹)", min_value=0, step=5000, key="savings")
        st.select_slider("Risk appetite", options=list(RISK_LEVELS), key="risk")

        st.markdown("##### Goal")
        st.selectbox("Financial goal", GOALS, key="goal_name")
        st.number_input("Target amount (₹)", min_value=10000, step=100_000, key="goal_amt")
        st.slider("Years to achieve", 1, 40, key="goal_years")

        st.markdown("##### Monthly expenses (₹)")
        with st.expander("Needs", expanded=False):
            for cat in NEEDS:
                st.number_input(cat, min_value=0, step=500, key=f"e_{cat}")
        with st.expander("Wants", expanded=False):
            for cat in WANTS:
                st.number_input(cat, min_value=0, step=500, key=f"e_{cat}")
        st.button("Reset to defaults", on_click=reset_profile, width="stretch")

        render_ai_settings()


def render_ai_settings() -> None:
    st.markdown("##### Gemini AI")
    info = resolve_key(st.session_state.get("key_override"))
    if info.available:
        st.markdown(
            f'<span class="pill pill-ok">● Connected</span> <span class="muted">{info.masked} via {info.source}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<span class="pill pill-warn">● Offline mode</span>', unsafe_allow_html=True)
        hint = (
            "Your `.env` still contains the placeholder text. Replace it with your real key."
            if info.placeholder_found
            else f"Add `GEMINI_API_KEY=your_key` to the `{ENV_PATH.name}` file in the project folder, save it and refresh this page."
        )
        st.caption(hint)
    with st.expander("AI settings"):
        st.session_state.setdefault("model_choice", default_model())
        options = MODEL_CHOICES if st.session_state["model_choice"] in MODEL_CHOICES else [st.session_state["model_choice"]] + MODEL_CHOICES
        st.selectbox("Model", options, key="model_choice",
                     help="If a model is unavailable the app automatically tries the next one.")
        st.text_input("Override key for this session", type="password", key="key_override",
                      help="Optional. Normally the key comes from your .env file.")
        info = resolve_key(st.session_state.get("key_override"))
        if st.button("Test connection", disabled=not info.available, width="stretch"):
            try:
                llm.generate("Reply with the single word OK.", [{"role": "user", "content": "ping"}], info.key,
                             model=st.session_state["model_choice"], max_tokens=1024)
                st.success(f"Connected - answered by {llm.LAST_MODEL}")
            except Exception as exc:
                st.error(llm.friendly_error(exc))


# ----------------------------------------------------------------------------- context
def build_ctx() -> Ctx:
    """Create the per-run context from session state. Raises ValueError on invalid inputs."""
    ss = st.session_state
    profile = FinanceProfile(
        age=int(ss["age"]),
        monthly_income=float(ss["income"]),
        expenses={cat: float(ss[f"e_{cat}"]) for cat in DEFAULT_EXPENSES},
        risk_level=ss["risk"],
        goal_name=ss["goal_name"],
        goal_amount=float(ss["goal_amt"]),
        goal_years=int(ss["goal_years"]),
        current_savings=float(ss["savings"]),
    )
    analysis = analyze_budget(profile)
    plan = goal_plan(profile.goal_amount, profile.goal_years, profile.risk_level, profile.current_savings,
                     max(analysis.savings, 0))
    stmt = ss.get("stmt")
    stmt_context = ""
    if stmt is not None and len(stmt):
        try:
            stmt_context = build_statement_context(stmt, forecast_series(monthly_expenses(stmt), 3))
        except ValueError:
            stmt_context = ""
    snapshot = (profile.age, profile.monthly_income, tuple(profile.expenses.items()), profile.risk_level,
                profile.goal_name, profile.goal_amount, profile.goal_years, profile.current_savings)
    return Ctx(profile, analysis, plan, resolve_key(ss.get("key_override")),
               ss.get("model_choice", default_model()), stmt, stmt_context, snapshot)


def current_ctx() -> Ctx:
    return st.session_state["_ctx"]


# ----------------------------------------------------------------------------- tax inputs (shared with Reports)
TAX_DEFAULTS = {"tax_gross": 1_800_000, "tax_80c": 150_000, "tax_80d": 25_000, "tax_nps": 0,
                "tax_hra": 0, "tax_home": 0, "tax_other": 0, "tax_emp_nps": 0}


def tax_inputs():
    """(gross salary, Deductions) from the Tax Planner inputs, or their defaults."""
    from .tax import Deductions

    g = lambda k: st.session_state.get(k, TAX_DEFAULTS[k])  # noqa: E731
    return float(g("tax_gross")), Deductions(
        sec_80c=g("tax_80c"), sec_80d=g("tax_80d"), nps_80ccd_1b=g("tax_nps"), hra_exempt=g("tax_hra"),
        home_loan_interest=g("tax_home"), other=g("tax_other"), employer_nps=g("tax_emp_nps"))
