"""Goals & Simulator: SIP planner, allocation and Monte Carlo."""

import pandas as pd
import streamlit as st

from src import charts
from src.fmt import inr, inr_compact
from src.projections import EXPECTED_RETURN, lumpsum_future_value, projection_series, sip_future_value, suggest_allocation
from src.simulation import VOLATILITY, simulate_sip, summarize
from src.state import current_ctx, sticky_slider
from src.ui import kpis, page_header

ctx = current_ctx()
p, a, plan = ctx.profile, ctx.analysis, ctx.plan

page_header("Goals & Simulator", f"Plan '{p.goal_name}': {inr_compact(p.goal_amount)} in {p.goal_years} years.")

kpis([
    ("Required SIP / month", inr(plan["required_sip"])),
    ("Your monthly surplus", inr(plan["available_monthly"])),
    ("Projected corpus", inr_compact(plan["projected_corpus"])),
])
if plan["on_track"]:
    st.success(f"On track - the current surplus reaches the goal (assumed return {plan['rate'] * 100:.0f}% p.a.).")
else:
    st.error(f"Projected shortfall of {inr(plan['shortfall'])}. Raise the SIP, extend the timeline or lower the target.")
st.caption(f"After 6% inflation, {inr_compact(p.goal_amount)} in {p.goal_years} years is worth about "
           f"{inr_compact(plan['goal_today_value'])} in today's money. Returns are assumptions, not guarantees.")

sip_max = int(max(plan["required_sip"] * 1.5, a.savings, 5000))
default_sip = min(int(max(plan["available_monthly"], 0)), sip_max)
st.session_state["sip_choice"] = min(st.session_state.get("sip_choice", default_sip), sip_max)
sip_choice = sticky_slider("What-if: monthly SIP (₹)", "sip_choice", default_sip, min_value=0, max_value=sip_max, step=500)

series = projection_series(sip_choice, EXPECTED_RETURN[p.risk_level], p.goal_years, p.current_savings)
c1, c2 = st.columns([3, 2], gap="large")
c1.plotly_chart(charts.projection_line(series, p.goal_amount), width="stretch")
c2.plotly_chart(charts.allocation_donut(suggest_allocation(p.age, p.risk_level)), width="stretch")

rows = [{"Risk profile": lvl, "Assumed return": f"{rate * 100:.0f}%",
         "Projected value": inr(sip_future_value(sip_choice, rate, p.goal_years)
                                + lumpsum_future_value(p.current_savings, rate, p.goal_years))}
        for lvl, rate in EXPECTED_RETURN.items()]
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.divider()
st.markdown("### Monte Carlo simulator")
st.caption("Markets never deliver the same return every year. This runs 2,000 random market paths to show the "
           "probability of reaching your goal.")
m1, m2, m3 = st.columns(3)
with m1:
    step_up = sticky_slider("Annual SIP step-up (%)", "mc_step", 5, min_value=0, max_value=20) / 100
with m2:
    vol = sticky_slider("Market volatility (%)", "mc_vol", int(VOLATILITY[p.risk_level] * 100), min_value=2, max_value=30) / 100
with m3:
    exp_ret = sticky_slider("Expected return (% p.a.)", "mc_ret", int(EXPECTED_RETURN[p.risk_level] * 100), min_value=4, max_value=16) / 100

sim = simulate_sip(sip_choice, p.goal_years, p.current_savings, exp_ret, vol, step_up=step_up)
sm = summarize(sim, p.goal_amount)
kpis([
    ("Probability of reaching goal", f"{sm['prob_success'] * 100:.0f}%"),
    ("Median corpus", inr_compact(sm["final_p50"])),
    ("Bad case (10th percentile)", inr_compact(sm["final_p10"])),
    ("Good case (90th percentile)", inr_compact(sm["final_p90"])),
])
g1, g2 = st.columns([3, 2], gap="large")
g1.plotly_chart(charts.monte_carlo_fan(sm, p.goal_amount), width="stretch")
g2.plotly_chart(charts.final_histogram(sim["final"], p.goal_amount), width="stretch")
