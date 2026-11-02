"""Tax Planner: Old vs New regime comparison."""

import streamlit as st

from src import charts
from src.fmt import inr
from src.state import TAX_DEFAULTS, current_ctx, sticky_number, tax_inputs
from src.tax import breakeven_deductions, compare_regimes
from src.ui import page_header, verdict_box

current_ctx()
page_header("Tax Planner", "Old vs New regime for FY 2026-27 (salaried, age below 60).")
st.caption("Surcharge is not included. This is an estimate - verify against the latest Income Tax Department "
           "rules before filing.")

left, right = st.columns([1, 2], gap="large")
with left:
    with st.container(border=True):
        st.markdown("**Income and deductions (₹ per year)**")
        sticky_number("Annual gross salary", "tax_gross", TAX_DEFAULTS["tax_gross"], min_value=0, step=50_000)
        sticky_number("80C - PPF / ELSS / EPF / LIC (max 1.5L)", "tax_80c", TAX_DEFAULTS["tax_80c"], min_value=0, step=10_000)
        sticky_number("80D - health insurance", "tax_80d", TAX_DEFAULTS["tax_80d"], min_value=0, step=5_000)
        sticky_number("NPS 80CCD(1B) (max 50K)", "tax_nps", TAX_DEFAULTS["tax_nps"], min_value=0, step=10_000)
        sticky_number("HRA exemption", "tax_hra", TAX_DEFAULTS["tax_hra"], min_value=0, step=10_000)
        sticky_number("Home loan interest (max 2L)", "tax_home", TAX_DEFAULTS["tax_home"], min_value=0, step=10_000)
        sticky_number("Other deductions", "tax_other", TAX_DEFAULTS["tax_other"], min_value=0, step=10_000)
        sticky_number("Employer NPS 80CCD(2)", "tax_emp_nps", TAX_DEFAULTS["tax_emp_nps"], min_value=0, step=10_000)

gross, ded = tax_inputs()
result = compare_regimes(gross, ded)
new_r, old_r = result["new"], result["old"]

with right:
    if result["saving"] == 0:
        verdict_box("Your tax is the same under both regimes.", "success")
    else:
        verdict_box(f"{result['better']} Regime is better - you save {inr(result['saving'])} per year.", "success")
    c1, c2 = st.columns(2)
    for col, r in ((c1, new_r), (c2, old_r)):
        with col.container(border=True):
            st.markdown(f"**{r.regime} Regime**")
            st.metric("Total tax", inr(r.total_tax))
            st.caption(f"Taxable income: {inr(r.taxable_income)}  \nEffective rate: {r.effective_rate:.1f}%  \n"
                       f"Monthly take-home: {inr(r.monthly_take_home)}")
    st.plotly_chart(charts.tax_compare_bar(new_r, old_r), width="stretch")
    breakeven = breakeven_deductions(gross)
    if breakeven is None:
        st.info("At this income the Old regime does not beat the New regime with any realistic deduction level.")
    else:
        st.info(f"The Old regime wins only if your extra deductions (above the standard deduction) exceed about "
                f"{inr(breakeven)}.")
