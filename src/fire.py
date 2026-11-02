"""FIRE (Financial Independence, Retire Early) planner."""

from __future__ import annotations

from typing import Dict, List, Optional

MAX_AGE = 85


def _simulate(years: int, corpus: float, monthly: float, annual_return: float, step_up: float) -> List[float]:
    """Corpus at the end of each year 0..years (SIP at the start of every month, optional yearly step-up)."""
    r = annual_return / 12
    values = [corpus]
    contribution = monthly
    for year in range(years):
        if year > 0:
            contribution *= 1 + step_up
        for _ in range(12):
            corpus = (corpus + contribution) * (1 + r)
        values.append(corpus)
    return values


def fire_number(monthly_expenses_today: float, years: int, inflation: float, withdrawal_rate: float) -> float:
    """Corpus needed at retirement so that `withdrawal_rate` of it covers inflated expenses."""
    return monthly_expenses_today * 12 * (1 + inflation) ** years / withdrawal_rate


def fire_plan(
    current_age: int,
    retire_age: int,
    monthly_expenses_today: float,
    current_corpus: float,
    monthly_investment: float,
    annual_return: float = 0.10,
    inflation: float = 0.06,
    withdrawal_rate: float = 0.035,
    step_up: float = 0.0,
) -> Dict:
    if retire_age <= current_age:
        raise ValueError("Retirement age must be greater than your current age.")
    if withdrawal_rate <= 0 or monthly_expenses_today <= 0:
        raise ValueError("Withdrawal rate and expenses must be positive.")
    years = retire_age - current_age
    horizon = max(MAX_AGE - current_age, years)
    path = _simulate(horizon, current_corpus, monthly_investment, annual_return, step_up)

    series = []
    fi_age: Optional[int] = None
    for y, value in enumerate(path):
        target = fire_number(monthly_expenses_today, y, inflation, withdrawal_rate)
        series.append({"age": current_age + y, "corpus": value, "target": target})
        if fi_age is None and value >= target:
            fi_age = current_age + y

    target_at_retire = fire_number(monthly_expenses_today, years, inflation, withdrawal_rate)
    projected = path[years]

    required = 0.0
    if projected < target_at_retire:
        low, high = 0.0, max(target_at_retire / max(years * 12, 1), 1.0) * 2
        for _ in range(60):  # bisection on the monthly investment
            mid = (low + high) / 2
            if _simulate(years, current_corpus, mid, annual_return, step_up)[-1] >= target_at_retire:
                high = mid
            else:
                low = mid
        required = high

    return {
        "years_to_retire": years,
        "expenses_at_retirement_monthly": monthly_expenses_today * (1 + inflation) ** years,
        "fire_number": target_at_retire,
        "projected_corpus": projected,
        "gap": max(target_at_retire - projected, 0.0),
        "on_track": projected >= target_at_retire,
        "required_monthly": required,
        "fi_age": fi_age,
        # corpus needed today that would grow to the target with no further contributions
        "coast_number": target_at_retire / (1 + annual_return) ** years,
        "series": series[: years + 1] if fi_age is None or fi_age <= retire_age else series[: (fi_age - current_age) + 1],
    }
