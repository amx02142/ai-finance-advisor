"""Overview: KPIs, health score, prioritised AI action plan, spending charts."""

import html

import streamlit as st

from src import charts, llm
from src.advisor import generate_action_plan, rule_based_plan
from src.fmt import inr
from src.state import current_ctx
from src.ui import kpis, page_header, render_actions, source_pill

ctx = current_ctx()
a, p = ctx.analysis, ctx.profile

page_header("Financial Overview", "Your complete money picture, health score and the next best actions.")

kpis([
    ("Monthly income", inr(a.total_income)),
    ("Monthly expenses", inr(a.total_expenses), f"{a.needs_pct + a.wants_pct:.0f}% of income", "off"),
    ("Monthly savings", inr(a.savings), f"{a.savings_pct:.0f}% savings rate"),
    ("Emergency fund", f"{a.emergency_months_covered:.1f} months", "target 6 months", "off"),
])
st.write("")

left, right = st.columns([2, 3], gap="large")
with left:
    st.plotly_chart(charts.health_gauge(a.health_score), width="stretch")
    with st.container(border=True):
        st.markdown("**Risk alerts**")
        if a.flags:
            for flag in a.flags:
                st.markdown(f"- {flag}")
        else:
            st.success("All key ratios are healthy.")

with right:
    head, btn = st.columns([3, 2])
    head.markdown("#### Priority actions")
    if btn.button("✦ Generate AI plan", type="primary", width="stretch", disabled=not ctx.ai_on,
                  help=None if ctx.ai_on else "Add GEMINI_API_KEY to your .env file to enable Gemini."):
        with st.spinner("Gemini is analysing your finances…"):
            plan_dict, mode, error = generate_action_plan(p, a, ctx.plan, ctx.key.key, ctx.stmt_context, ctx.model)
        st.session_state["action_plan"] = {"plan": plan_dict, "mode": mode, "model": llm.LAST_MODEL,
                                           "snapshot": ctx.snapshot}
        if error:
            st.warning(f"Gemini could not produce a plan ({error}). Showing the rule-based plan instead.")

    saved = st.session_state.get("action_plan")
    if saved and saved["snapshot"] == ctx.snapshot:
        plan_dict, mode, model = saved["plan"], saved["mode"], saved["model"]
    else:
        plan_dict, mode, model = rule_based_plan(p, a, ctx.plan), "offline", None
    st.markdown(source_pill(mode, model), unsafe_allow_html=True)
    if plan_dict.get("summary"):
        st.markdown(f'<div class="summary-box">{html.escape(plan_dict["summary"])}</div>', unsafe_allow_html=True)
    render_actions(plan_dict["actions"])

st.write("")
c1, c2 = st.columns(2, gap="large")
if a.total_expenses > 0:
    c1.plotly_chart(charts.expense_pie(p.expenses), width="stretch")
c2.plotly_chart(charts.rule_comparison_bar(a), width="stretch")
