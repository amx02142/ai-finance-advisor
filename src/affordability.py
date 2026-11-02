"""Big-purchase / new-loan affordability check."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict

from .budget import FinanceProfile, analyze_budget
from .debt import emi
from .fmt import inr


def assess_purchase(
    profile: FinanceProfile,
    price: float,
    down_payment: float,
    loan_rate: float,
    tenor_years: int,
    running_cost: float = 0.0,
) -> Dict:
    """Compare the user's finances before and after buying something on a loan.

    loan_rate is a decimal (0.095 = 9.5%). running_cost is extra monthly cost (fuel, insurance, upkeep).
    """
    if price <= 0:
        raise ValueError("Price must be greater than zero.")
    if not 0 <= down_payment <= price:
        raise ValueError("Down payment must be between 0 and the price.")
    if tenor_years < 1 and price > down_payment:
        raise ValueError("Loan tenor must be at least 1 year.")

    before = analyze_budget(profile)
    loan = price - down_payment
    monthly_emi = emi(loan, loan_rate, int(tenor_years * 12)) if loan > 0 else 0.0
    total_interest = monthly_emi * tenor_years * 12 - loan if loan > 0 else 0.0

    after_profile = deepcopy(profile)
    after_profile.expenses["EMI / Debt"] = after_profile.expenses.get("EMI / Debt", 0.0) + monthly_emi
    after_profile.expenses["Other"] = after_profile.expenses.get("Other", 0.0) + running_cost
    after_profile.current_savings = max(profile.current_savings - down_payment, 0.0)
    after = analyze_budget(after_profile)

    cash_short = max(down_payment - profile.current_savings, 0.0)
    if cash_short > 0 or after.savings < 0 or after.debt_to_income > 0.40:
        verdict, tone = "Not advisable right now", "error"
    elif after.debt_to_income > 0.30 or after.savings_pct < 10 or after.emergency_months_covered < 3:
        verdict, tone = "Stretch - proceed carefully", "warning"
    else:
        verdict, tone = "Comfortably affordable", "success"

    reasons = []
    if cash_short > 0:
        reasons.append(f"Your savings are short of the down payment by {inr(cash_short)}.")
    if after.savings < 0:
        reasons.append("Monthly expenses would exceed income after this purchase.")
    if after.debt_to_income > 0.40:
        reasons.append(f"EMIs would take {after.debt_to_income * 100:.0f}% of income (limit 40%).")
    elif after.debt_to_income > 0.30:
        reasons.append(f"EMIs would take {after.debt_to_income * 100:.0f}% of income (comfort zone is below 30%).")
    if after.emergency_months_covered < 3 and cash_short == 0:
        reasons.append(f"Emergency fund would drop to {after.emergency_months_covered:.1f} months of expenses.")
    if not reasons:
        reasons.append("EMI, savings rate and emergency fund all stay in healthy ranges.")

    return {
        "loan": loan,
        "emi": monthly_emi,
        "total_interest": total_interest,
        "total_cost": price + total_interest + running_cost * tenor_years * 12,
        "before": before,
        "after": after,
        "verdict": verdict,
        "tone": tone,
        "reasons": reasons,
        "cash_short": cash_short,
    }
