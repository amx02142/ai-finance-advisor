"""Statement Analyzer: upload, auto-categorise, forecast, recurring payments, anomalies, AI insights."""

import streamlit as st

from src import charts, llm
from src.advisor import ask_advisor
from src.config import ROOT
from src.fmt import inr
from src.forecast import forecast_series, trend_label
from src.state import current_ctx
from src.transactions import (
    ALL_CATEGORIES, UNCAT, ai_categorize, average_monthly_expenses, average_monthly_income,
    average_monthly_investing, categorize_df, category_pivot, detect_anomalies, detect_recurring,
    load_statement, monthly_expenses, rule_based_insights,
)
from src.ui import kpis, page_header

ctx = current_ctx()
SAMPLE_FILE = ROOT / "data" / "sample_statement.csv"

page_header("Statement Analyzer",
            "Upload a bank statement to auto-categorise spending, spot subscriptions and forecast the next 3 months.")


def apply_statement(avg_expenses: dict, avg_income: float) -> None:
    for cat, value in avg_expenses.items():
        st.session_state[f"e_{cat}"] = int(round(value / 100.0) * 100)
    if avg_income > 0:
        st.session_state["income"] = int(round(avg_income / 500.0) * 500)
    st.session_state["applied"] = True


if st.session_state.pop("applied", False):
    st.success("Statement averages were applied to your profile (see the sidebar).")

up_col, sample_col = st.columns([4, 1], vertical_alignment="bottom")
uploaded = up_col.file_uploader("Bank statement (CSV or Excel)", type=["csv", "xlsx", "xls"])
if sample_col.button("Load sample data", width="stretch"):
    st.session_state["stmt"] = categorize_df(load_statement(SAMPLE_FILE))
    st.session_state["stmt_id"] = "sample"
    st.rerun()

if uploaded is not None and st.session_state.get("stmt_id") != f"{uploaded.name}:{uploaded.size}":
    try:
        st.session_state["stmt"] = categorize_df(load_statement(uploaded))
        st.session_state["stmt_id"] = f"{uploaded.name}:{uploaded.size}"
        st.rerun()
    except Exception as exc:
        st.error(f"Could not read the statement: {exc}")

with st.expander("Supported statement format"):
    st.markdown(
        "Columns are detected automatically: **Date**, **Description / Narration / Particulars** and either "
        "**Debit + Credit** (or Withdrawal + Deposit) columns or a single **Amount** column with a Dr/Cr type. "
        "Your data stays in this browser session; only a compact summary is sent to Gemini when you use an AI button."
    )

stmt = st.session_state.get("stmt")
if stmt is None:
    st.info("No statement loaded yet. Click **Load sample data** for a demo, or upload your own file.")
    st.stop()

spend = monthly_expenses(stmt)
avg_exp, avg_inc = average_monthly_expenses(stmt), average_monthly_income(stmt)
kpis([
    ("Transactions", f"{len(stmt):,}", f"{stmt['month'].nunique()} months", "off"),
    ("Avg monthly income", inr(avg_inc)),
    ("Avg monthly spend", inr(spend.mean())),
    ("Avg monthly investing", inr(average_monthly_investing(stmt))),
])
st.write("")

n_uncat = int((stmt["category"] == UNCAT).sum())
if n_uncat:
    w1, w2 = st.columns([4, 1], vertical_alignment="center")
    w1.warning(f"{n_uncat} transactions could not be categorised automatically.")
    if w2.button("✦ Categorise with AI", disabled=not ctx.ai_on, width="stretch",
                 help=None if ctx.ai_on else "Add GEMINI_API_KEY to your .env file."):
        with st.spinner("Gemini is categorising…"):
            try:
                new_df, _ = ai_categorize(stmt, ctx.key.key)
                st.session_state["stmt"] = new_df
                st.rerun()
            except Exception as exc:
                st.error(f"AI categorisation failed: {llm.friendly_error(exc)}")

st.button("Apply these averages to my profile", type="primary", on_click=apply_statement, args=(avg_exp, avg_inc))

st.markdown("#### Expense forecast (next 3 months)")
forecast = forecast_series(spend, horizon=3)
nxt = forecast.iloc[0]
kpis([
    (f"Expected spend ({nxt['month']})", inr(nxt["forecast"]), f"{inr(nxt['lower'])} - {inr(nxt['upper'])}", "off"),
    ("Spending trend", trend_label(spend)),
    ("Expected savings next month", inr(avg_inc - nxt["forecast"])),
])
c1, c2 = st.columns(2, gap="large")
c1.plotly_chart(charts.spend_trend(spend, forecast), width="stretch")
c2.plotly_chart(charts.category_stack(category_pivot(stmt)), width="stretch")

r1, r2 = st.columns(2, gap="large")
with r1:
    st.markdown("#### Recurring payments")
    recurring = detect_recurring(stmt)
    if len(recurring):
        show = recurring.assign(avg_amount=recurring["avg_amount"].map(inr))
        show.columns = ["Merchant", "Category", "Avg / month", "Months"]
        st.dataframe(show, hide_index=True, width="stretch", height=300)
    else:
        st.caption("No recurring payments found.")
with r2:
    st.markdown("#### Unusual expenses")
    anomalies = detect_anomalies(stmt)
    if len(anomalies):
        show = anomalies.assign(spend=anomalies["spend"].map(inr), date=anomalies["date"].dt.strftime("%d %b %Y"))
        show.columns = ["Date", "Description", "Category", "Amount", "Z"]
        st.dataframe(show, hide_index=True, width="stretch")
    else:
        st.caption("No unusual expenses detected.")

st.markdown("#### Insights")
if st.button("✦ Get deep insights from Gemini", disabled=not ctx.ai_on):
    with st.spinner("Analysing your statement…"):
        answer, mode = ask_advisor(
            "Analyse my bank statement: give the top 3 insights, where I can save money (with INR amounts) "
            "and 3 concrete actions.", ctx.profile, ctx.analysis, ctx.plan, api_key=ctx.key.key,
            extra_context=ctx.stmt_context, model=ctx.model)
    st.session_state["stmt_ai"] = answer if mode == "ai" else None
    if mode != "ai":
        st.warning("Gemini was unavailable; showing the rule-based insights.")
with st.container(border=True):
    st.markdown(st.session_state.get("stmt_ai") or rule_based_insights(stmt, forecast))

with st.expander("Review transactions and fix categories"):
    view = stmt[["date", "description", "amount", "category"]].copy()
    view["date"] = view["date"].dt.date
    edited = st.data_editor(
        view, hide_index=True, width="stretch", num_rows="fixed", height=340, key="tx_editor",
        disabled=["date", "description", "amount"],
        column_config={"category": st.column_config.SelectboxColumn("category", options=ALL_CATEGORIES, required=True),
                       "amount": st.column_config.NumberColumn("amount", format="₹%.0f")},
    )
    if list(edited["category"]) != list(stmt["category"]):
        fixed = stmt.copy()
        fixed["category"] = edited["category"].values
        st.session_state["stmt"] = fixed
        st.session_state.pop("stmt_ai", None)
