"""Debt maths: EMI formula and payoff strategies (avalanche, snowball, minimum-only)."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

STRATEGIES = ("avalanche", "snowball", "minimum")
_EPS = 0.005


def emi(principal: float, annual_rate: float, months: int) -> float:
    """Monthly instalment for a loan. `annual_rate` is a decimal (0.09 = 9%)."""
    if months <= 0:
        raise ValueError("Loan tenor must be at least one month.")
    if principal <= 0:
        return 0.0
    r = annual_rate / 12
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def _validate(debts: List[Dict]) -> None:
    if not debts:
        raise ValueError("Add at least one debt.")
    for d in debts:
        if d["balance"] <= 0 or d["min_payment"] <= 0 or d["rate_pct"] < 0:
            raise ValueError(f"Invalid values for '{d['name']}': balance and minimum payment must be positive.")


def payoff_schedule(debts: List[Dict], extra: float = 0.0, strategy: str = "avalanche", max_months: int = 600) -> Dict:
    """Simulate paying off several debts month by month.

    debts: [{"name", "balance", "rate_pct" (annual %), "min_payment"}]
    - avalanche: extra money goes to the highest interest rate first
    - snowball:  extra money goes to the smallest balance first
    - minimum:   only minimum payments (freed-up payments are NOT rolled over)
    For avalanche/snowball the total monthly outlay stays constant, so the minimum payment of a
    cleared debt automatically rolls into the next target.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")
    _validate(debts)
    state = [
        {"name": d["name"], "bal": float(d["balance"]), "rate": d["rate_pct"] / 100 / 12, "min": float(d["min_payment"])}
        for d in debts
    ]
    names = [s["name"] for s in state]
    monthly_budget = sum(s["min"] for s in state) + (extra if strategy != "minimum" else 0.0)

    history = [{n: s["bal"] for n, s in zip(names, state)}]
    total_interest = 0.0
    paid_off: Dict[str, int] = {}
    month = 0
    while any(s["bal"] > _EPS for s in state) and month < max_months:
        month += 1
        active = [s for s in state if s["bal"] > _EPS]
        for s in active:
            interest = s["bal"] * s["rate"]
            s["bal"] += interest
            total_interest += interest
        available = monthly_budget
        for s in active:
            pay = min(s["min"], s["bal"])
            s["bal"] -= pay
            available -= pay
        if strategy != "minimum" and available > _EPS:
            order = sorted(
                [s for s in state if s["bal"] > _EPS],
                key=(lambda s: -s["rate"]) if strategy == "avalanche" else (lambda s: s["bal"]),
            )
            for s in order:
                if available <= _EPS:
                    break
                pay = min(available, s["bal"])
                s["bal"] -= pay
                available -= pay
        for s in state:
            if s["bal"] <= _EPS:
                s["bal"] = 0.0
                paid_off.setdefault(s["name"], month)
        history.append({n: s["bal"] for n, s in zip(names, state)})

    converged = all(s["bal"] <= _EPS for s in state)
    principal = sum(d["balance"] for d in debts)
    frame = pd.DataFrame(history)
    frame.index.name = "month"
    return {
        "strategy": strategy,
        "converged": converged,
        "months": month if converged else None,
        "total_interest": total_interest,
        "total_paid": principal + total_interest,
        "payoff_order": sorted(paid_off.items(), key=lambda kv: kv[1]),
        "history": frame,
    }


def compare_strategies(debts: List[Dict], extra: float = 0.0) -> Dict:
    """Run all three strategies and report the savings versus paying only the minimums."""
    results = {s: payoff_schedule(debts, extra, s) for s in STRATEGIES}
    base, best = results["minimum"], results["avalanche"]
    saved_interest = saved_months = None
    if base["converged"] and best["converged"]:
        saved_interest = base["total_interest"] - best["total_interest"]
        saved_months = base["months"] - best["months"]
    return {**results, "interest_saved": saved_interest, "months_saved": saved_months}
