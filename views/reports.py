"""Reports: downloadable Markdown / HTML / CSV."""

import pandas as pd
import streamlit as st

from src.advisor import rule_based_plan
from src.fmt import inr, inr_compact
from src.projections import EXPECTED_RETURN
from src.report import build_report, to_html
from src.simulation import VOLATILITY, simulate_sip, summarize
from src.state import current_ctx, tax_inputs
from src.tax import compare_regimes
from src.transactions import rule_based_insights
from src.forecast import forecast_series
from src.transactions import monthly_expenses
from src.ui import page_header

ctx = current_ctx()
p, a = ctx.profile, ctx.analysis
page_header("Reports", "Download a complete, shareable summary of your finances.")

saved = st.session_state.get("action_plan")
if saved and saved["snapshot"] == ctx.snapshot:
    action_plan, source = saved["plan"], (f"Gemini ({saved['model']})" if saved["mode"] == "ai" else "rule-based engine")
else:
    action_plan, source = rule_based_plan(p, a, ctx.plan), "rule-based engine"

statement_md = ""
if ctx.stmt is not None:
    statement_md = (st.session_state.get("stmt_ai")
                    or rule_based_insights(ctx.stmt, forecast_series(monthly_expenses(ctx.stmt), 3)))

sip = int(max(ctx.plan["available_monthly"], 0))
sm = summarize(simulate_sip(sip, p.goal_years, p.current_savings, EXPECTED_RETURN[p.risk_level],
                            VOLATILITY[p.risk_level], step_up=0.05), p.goal_amount)
mc_md = (f"- SIP {inr(sip)} per month with a 5% annual step-up, return {EXPECTED_RETURN[p.risk_level] * 100:.0f}%, "
         f"volatility {VOLATILITY[p.risk_level] * 100:.0f}%.\n"
         f"- Probability of reaching the goal: **{sm['prob_success'] * 100:.0f}%**\n"
         f"- Median {inr_compact(sm['final_p50'])} | bad case {inr_compact(sm['final_p10'])} | good case {inr_compact(sm['final_p90'])}")

gross, ded = tax_inputs()
cmp = compare_regimes(gross, ded)
tax_md = (f"- Gross salary {inr(gross)}\n- New regime tax: {inr(cmp['new'].total_tax)} | Old regime tax: {inr(cmp['old'].total_tax)}\n"
          f"- Better: **{cmp['better']}** (saves {inr(cmp['saving'])})")

report_md = build_report(p, a, ctx.plan, action_plan, statement_md, mc_md, tax_md, source)

c1, c2, c3 = st.columns(3)
c1.download_button("⬇ Markdown report", report_md, file_name="finpilot_report.md", mime="text/markdown", width="stretch")
c2.download_button("⬇ HTML report (print to PDF)", to_html(report_md, "FinPilot AI Report"),
                   file_name="finpilot_report.html", mime="text/html", width="stretch")
exp_df = pd.DataFrame({"Category": list(p.expenses), "Monthly amount (INR)": list(p.expenses.values())})
c3.download_button("⬇ Expenses (CSV)", exp_df.to_csv(index=False), file_name="expenses.csv", mime="text/csv", width="stretch")
st.caption("Tip: open the HTML report in your browser and choose Print > Save as PDF.")
with st.container(border=True):
    st.markdown(report_md)
