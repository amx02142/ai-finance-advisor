"""Monte Carlo simulation of SIP growth under market volatility."""

from __future__ import annotations

from typing import Dict

import numpy as np

# Assumed annual volatility (standard deviation of returns) by risk appetite
VOLATILITY = {"Low": 0.06, "Medium": 0.12, "High": 0.18}


def simulate_sip(
    monthly: float,
    years: int,
    current_savings: float,
    annual_return: float,
    annual_vol: float,
    step_up: float = 0.0,
    n_sims: int = 2000,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """Simulate `n_sims` random market paths.

    Each month: add the SIP, then apply a random return ~ Normal(mu/12, sigma/sqrt(12)).
    `step_up` raises the SIP by that fraction every 12 months.
    Returns yearly portfolio values (n_sims x years+1), final values and total invested.
    """
    if years < 1:
        raise ValueError("years must be >= 1")
    rng = np.random.default_rng(seed)
    months = years * 12
    returns = rng.normal(annual_return / 12, annual_vol / np.sqrt(12), size=(n_sims, months))
    returns = np.clip(returns, -0.9, None)

    value = np.full(n_sims, float(current_savings))
    yearly = np.zeros((n_sims, years + 1))
    yearly[:, 0] = value
    invested_by_year = np.zeros(years + 1)
    invested_by_year[0] = current_savings

    contribution = float(monthly)
    invested = float(current_savings)
    for m in range(months):
        if m > 0 and m % 12 == 0:
            contribution *= 1 + step_up
        value = (value + contribution) * (1 + returns[:, m])
        invested += contribution
        if (m + 1) % 12 == 0:
            yearly[:, (m + 1) // 12] = value
            invested_by_year[(m + 1) // 12] = invested

    return {"yearly": yearly, "final": value, "invested": invested_by_year}


def summarize(sim: Dict[str, np.ndarray], goal: float) -> Dict[str, object]:
    """Percentile bands per year plus the probability of reaching the goal."""
    yearly, final = sim["yearly"], sim["final"]
    return {
        "p10": np.percentile(yearly, 10, axis=0),
        "p50": np.percentile(yearly, 50, axis=0),
        "p90": np.percentile(yearly, 90, axis=0),
        "invested": sim["invested"],
        "prob_success": float((final >= goal).mean()),
        "final_p10": float(np.percentile(final, 10)),
        "final_p50": float(np.percentile(final, 50)),
        "final_p90": float(np.percentile(final, 90)),
        "worst": float(final.min()),
        "best": float(final.max()),
    }
