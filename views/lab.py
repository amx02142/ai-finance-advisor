"""Planning Lab: debt payoff, FIRE and purchase affordability."""

import pandas as pd
import streamlit as st

from src import charts
from src.advisor import stream_advisor
from src.affordability import assess_purchase
from src.debt import compare_strategies
from src.fire import MAX_AGE, fire_plan
from src.fmt import inr, inr_compact
from src.projections import EXPECTED_RETURN
from src.state import current_ctx, sticky_number, sticky_slider
from src.ui import kpis, page_header, verdict_box

ctx = current_ctx()
p, a = ctx.profile, ctx.analysis

page_header("Planning Lab", "Advanced tools for debt, financial independence and big purchases.")
tab_debt, tab_fire, tab_buy = st.tabs(["Debt payoff", "FIRE planner", "Purchase analyzer"])


def _years(months):
    return f"{months // 12}y {months % 12}m" if months else "-"


# ================================================================= Debt payoff
with tab_debt:
    st.markdown("#### Pay off debt faster")
    st.caption("Edit the table (add or delete rows). Avalanche pays the highest interest rate first, snowball pays "
               "the smallest balance first.")
    defaults = pd.DataFrame([
        {"name": "Credit card", "balance": 85000, "rate_pct": 36.0, "min_payment": 4000},
        {"name": "Personal loan", "balance": 250000, "rate_pct": 14.0, "min_payment": 8000},
        {"name": "Car loan", "balance": 420000, "rate_pct": 9.5, "min_payment": 9500},
    ])
    table = st.data_editor(
        defaults, num_rows="dynamic", hide_index=True, width="stretch", key="debts_editor",
        column_config={
            "name": st.column_config.TextColumn("Debt", required=True),
            "balance": st.column_config.NumberColumn("Balance (₹)", min_value=0, format="₹%.0f"),
            "rate_pct": st.column_config.NumberColumn("Interest rate (% p.a.)", min_value=0, max_value=60, format="%.1f"),
            "min_payment": st.column_config.NumberColumn("Minimum payment / month (₹)", min_value=0, format="₹%.0f"),
        },
    )
    extra = sticky_number("Extra payment per month (₹)", "debt_extra", 5000, min_value=0, step=500)
    debts = [r for r in table.dropna().to_dict("records") if r["balance"] > 0 and r["min_payment"] > 0]
    if not debts:
        st.info("Add at least one debt with a balance and a minimum payment.")
    else:
        res = compare_strategies(debts, extra)
        av, sn, mi = res["avalanche"], res["snowball"], res["minimum"]
        if not mi["converged"]:
            st.warning("With minimum payments only, at least one debt never clears (interest outgrows the payment).")
        kpis([
            ("Avalanche - debt-free in", _years(av["months"]), f"Interest {inr(av['total_interest'])}", "off"),
            ("Snowball - debt-free in", _years(sn["months"]), f"Interest {inr(sn['total_interest'])}", "off"),
            ("Minimum only", _years(mi["months"]), f"Interest {inr(mi['total_interest'])}" if mi["converged"] else "never clears", "off"),
        ])
        if res["interest_saved"] is not None:
            st.success(f"Avalanche saves {inr(res['interest_saved'])} in interest and is "
                       f"{_years(res['months_saved'])} faster than paying only the minimums.")
        c1, c2 = st.columns(2, gap="large")
        c1.plotly_chart(charts.debt_balance_lines(av["history"]), width="stretch")
        c2.plotly_chart(charts.debt_strategy_bars(res), width="stretch")
        st.markdown("**Payoff order (avalanche)**")
        st.dataframe(pd.DataFrame(av["payoff_order"], columns=["Debt", "Cleared in month"]),
                     hide_index=True, width="stretch")

# ================================================================= FIRE
with tab_fire:
    st.markdown("#### Financial independence (FIRE)")
    st.caption("How much do you need so that investments can fund your lifestyle forever, and when will you get there?")
    c1, c2, c3 = st.columns(3)
    with c1:
        max_age = max(75, p.age + 5)
        st.session_state["fire_age"] = min(max(st.session_state.get("fire_age", 55), p.age + 1), max_age)
        retire_age = sticky_slider("Target retirement age", "fire_age", 55, min_value=p.age + 1, max_value=max_age)
        expenses_today = sticky_number("Monthly expenses in retirement (today's ₹)", "fire_exp",
                                       max(int(round(a.total_expenses, -2)), 1000), min_value=1000, step=1000)
    with c2:
        corpus = sticky_number("Current investments (₹)", "fire_corpus", int(p.current_savings), min_value=0, step=10_000)
        monthly = sticky_number("Monthly investment (₹)", "fire_monthly", int(max(a.savings, 0)), min_value=0, step=1000)
    with c3:
        ret = sticky_slider("Expected return (% p.a.)", "fire_ret", int(EXPECTED_RETURN[p.risk_level] * 100), min_value=4, max_value=14) / 100
        infl = sticky_slider("Inflation (% p.a.)", "fire_infl", 6, min_value=3, max_value=10) / 100
    d1, d2 = st.columns(2)
    swr = sticky_slider("Safe withdrawal rate (%)", "fire_swr", 3.5, min_value=2.5, max_value=5.0, step=0.1) / 100
    step_up = sticky_slider("Annual investment step-up (%)", "fire_step", 5, min_value=0, max_value=15) / 100

    fp = fire_plan(p.age, retire_age, expenses_today, corpus, monthly, ret, infl, swr, step_up)
    kpis([
        ("FIRE number at retirement", inr_compact(fp["fire_number"]), f"{inr(fp['expenses_at_retirement_monthly'])}/month then", "off"),
        ("Projected corpus", inr_compact(fp["projected_corpus"])),
        ("Required monthly investment", inr(fp["required_monthly"]) if not fp["on_track"] else "On track ✓"),
        ("Financial independence age", str(fp["fi_age"]) if fp["fi_age"] else f"Beyond {MAX_AGE}"),
    ])
    if fp["on_track"]:
        verdict_box(f"On track: you can retire at {retire_age} with a surplus of {inr_compact(fp['projected_corpus'] - fp['fire_number'])}.", "success")
    else:
        verdict_box(f"Shortfall of {inr_compact(fp['gap'])} at {retire_age}. Invest about {inr(fp['required_monthly'])} per month "
                    "(with your step-up) or retire later.", "warning")
    st.plotly_chart(charts.fire_chart(fp["series"], retire_age), width="stretch")
    st.caption(f"Coast FIRE: having {inr_compact(fp['coast_number'])} invested today would grow to your target by "
               f"{retire_age} even if you stopped investing. The 4% rule comes from US data; 3-3.5% is a more cautious "
               "choice for India's higher inflation.")

# ================================================================= Purchase analyzer
with tab_buy:
    st.markdown("#### Can I afford it?")
    st.caption("Model a car, home or other big purchase and see the effect on your savings, EMI share and emergency fund.")
    b1, b2, b3 = st.columns(3)
    with b1:
        what = st.text_input("What are you buying?", value=st.session_state.get("buy_what", "Car"), key="w_buy_what")
        st.session_state["buy_what"] = what
        price = sticky_number("Price (₹)", "buy_price", 1_000_000, min_value=10_000, step=50_000)
    with b2:
        down = sticky_number("Down payment (₹)", "buy_down", 200_000, min_value=0, step=10_000)
        rate = sticky_slider("Loan interest rate (% p.a.)", "buy_rate", 9.5, min_value=5.0, max_value=24.0, step=0.1) / 100
    with b3:
        tenor = sticky_slider("Loan tenor (years)", "buy_tenor", 5, min_value=1, max_value=30)
        running = sticky_number("Extra monthly running cost (₹)", "buy_run", 4000, min_value=0, step=500)

    try:
        res = assess_purchase(p, price, min(down, price), rate, tenor, running)
    except ValueError as err:
        st.error(str(err))
        st.stop()
    b, af = res["before"], res["after"]
    kpis([
        ("Monthly EMI", inr(res["emi"])),
        ("Total interest", inr_compact(res["total_interest"])),
        ("Total cost of ownership", inr_compact(res["total_cost"])),
    ])
    verdict_box(res["verdict"], res["tone"])
    for reason in res["reasons"]:
        st.markdown(f"- {reason}")
    d1, d2 = st.columns([3, 2], gap="large")
    d1.plotly_chart(charts.before_after_bars(b, af), width="stretch")
    with d2:
        st.dataframe(pd.DataFrame({
            "Metric": ["Monthly savings", "Savings rate", "EMI share of income", "Emergency fund", "Health score"],
            "Before": [inr(b.savings), f"{b.savings_pct:.0f}%", f"{b.debt_to_income * 100:.0f}%",
                       f"{b.emergency_months_covered:.1f} mo", f"{b.health_score}/100"],
            "After": [inr(af.savings), f"{af.savings_pct:.0f}%", f"{af.debt_to_income * 100:.0f}%",
                      f"{af.emergency_months_covered:.1f} mo", f"{af.health_score}/100"],
        }), hide_index=True, width="stretch")
    if st.button("✦ Ask Gemini for a second opinion", disabled=not ctx.ai_on,
                 help=None if ctx.ai_on else "Add GEMINI_API_KEY to your .env file."):
        question = (
            f"I am considering buying: {what}. Price {inr(price)}, down payment {inr(down)}, loan rate {rate * 100:.1f}% "
            f"for {tenor} years, EMI {inr(res['emi'])}, extra running cost {inr(running)}/month. After the purchase my savings "
            f"rate would be {af.savings_pct:.0f}%, EMI share {af.debt_to_income * 100:.0f}% and emergency fund "
            f"{af.emergency_months_covered:.1f} months. The calculator verdict was '{res['verdict']}'. "
            "Give me an honest second opinion and two alternatives that reduce the risk."
        )
        with st.container(border=True):
            st.write_stream(stream_advisor(question, p, a, ctx.plan, api_key=ctx.key.key,
                                           extra_context=ctx.stmt_context, model=ctx.model))
