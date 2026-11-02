"""SIP / goal projections and age + risk based asset allocation."""

from __future__ import annotations

from typing import Dict, List

# Assumed long-term annual returns (illustrative, NOT guaranteed)
EXPECTED_RETURN = {"Low": 0.07, "Medium": 0.10, "High": 0.12}
DEFAULT_INFLATION = 0.06


def sip_future_value(monthly: float, annual_rate: float, years: int) -> float:
    """Future value of a monthly SIP (invested at start of each month)."""
    n = years * 12
    r = annual_rate / 12
    if n <= 0:
        return 0.0
    if r == 0:
        return monthly * n
    return monthly * (((1 + r) ** n - 1) / r) * (1 + r)


def lumpsum_future_value(amount: float, annual_rate: float, years: int) -> float:
    return amount * (1 + annual_rate / 12) ** (years * 12)


def required_monthly_sip(
    target: float, annual_rate: float, years: int, current_savings: float = 0.0
) -> float:
    """Monthly SIP needed to reach `target` after `years`."""
    remaining = target - lumpsum_future_value(current_savings, annual_rate, years)
    if remaining <= 0:
        return 0.0
    factor = sip_future_value(1.0, annual_rate, years)
    return remaining / factor


def inflation_adjusted(amount: float, years: int, inflation: float = DEFAULT_INFLATION) -> float:
    """Today's purchasing power of `amount` received after `years`."""
    return amount / (1 + inflation) ** years


def projection_series(
    monthly: float, annual_rate: float, years: int, current_savings: float = 0.0
) -> List[Dict[str, float]]:
    """Year-by-year corpus growth: invested amount vs. projected value."""
    rows = []
    for y in range(0, years + 1):
        invested = current_savings + monthly * 12 * y
        value = sip_future_value(monthly, annual_rate, y) + lumpsum_future_value(
            current_savings, annual_rate, y
        )
        rows.append({"year": y, "invested": invested, "value": value})
    return rows


def suggest_allocation(age: int, risk_level: str) -> Dict[str, int]:
    """Age + risk based asset allocation (percentages summing to 100)."""
    equity = 100 - age
    equity += {"Low": -20, "Medium": 0, "High": 15}[risk_level]
    equity = int(max(15, min(80, equity)))
    gold = 10
    liquid = 5
    debt = 100 - equity - gold - liquid
    return {
        "Equity (Index / Mutual Funds)": equity,
        "Debt (PPF / FD / Bonds)": debt,
        "Gold": gold,
        "Liquid / Emergency": liquid,
    }


def goal_plan(
    goal_amount: float,
    years: int,
    risk_level: str,
    current_savings: float,
    available_monthly: float,
) -> Dict[str, float]:
    """Summarise how feasible a goal is with the user's current surplus."""
    rate = EXPECTED_RETURN[risk_level]
    needed = required_monthly_sip(goal_amount, rate, years, current_savings)
    projected = sip_future_value(max(available_monthly, 0), rate, years) + lumpsum_future_value(
        current_savings, rate, years
    )
    return {
        "rate": rate,
        "required_sip": needed,
        "available_monthly": available_monthly,
        "projected_corpus": projected,
        "shortfall": max(goal_amount - projected, 0.0),
        "on_track": projected >= goal_amount,
        "goal_today_value": inflation_adjusted(goal_amount, years),
    }
