"""Budget analysis: 50/30/20 rule, savings rate, emergency fund and health score."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

# Expense categories grouped by the 50/30/20 rule
NEEDS = [
    "Rent / Home Loan",
    "Groceries & Food",
    "Utilities & Bills",
    "Transport",
    "EMI / Debt",
    "Insurance",
    "Health",
]
WANTS = [
    "Dining Out",
    "Shopping",
    "Entertainment",
    "Travel",
    "Subscriptions",
    "Other",
]

RISK_LEVELS = ("Low", "Medium", "High")


@dataclass
class FinanceProfile:
    """Everything the user tells us about their finances."""

    age: int
    monthly_income: float
    expenses: Dict[str, float] = field(default_factory=dict)
    risk_level: str = "Medium"
    goal_name: str = "Retirement"
    goal_amount: float = 5_000_000.0
    goal_years: int = 15
    current_savings: float = 0.0

    def validate(self) -> None:
        if self.monthly_income <= 0:
            raise ValueError("Monthly income must be greater than zero.")
        if not 16 <= self.age <= 100:
            raise ValueError("Age must be between 16 and 100.")
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"Risk level must be one of {RISK_LEVELS}.")
        if self.goal_years < 1:
            raise ValueError("Goal period must be at least 1 year.")
        if self.goal_amount < 0 or self.current_savings < 0:
            raise ValueError("Amounts cannot be negative.")
        if any(v < 0 for v in self.expenses.values()):
            raise ValueError("Expenses cannot be negative.")


@dataclass
class BudgetAnalysis:
    total_income: float
    total_expenses: float
    needs: float
    wants: float
    savings: float  # income - expenses (can be negative)
    needs_pct: float
    wants_pct: float
    savings_pct: float
    emergency_target: float
    emergency_months_covered: float
    debt_to_income: float
    health_score: int
    health_label: str
    ideal: Dict[str, float]
    flags: list = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def analyze_budget(profile: FinanceProfile) -> BudgetAnalysis:
    """Return a full budget analysis for the given profile."""
    profile.validate()
    income = profile.monthly_income

    needs = sum(v for k, v in profile.expenses.items() if k in NEEDS)
    # anything not recognised as a need counts as a want
    wants = sum(v for k, v in profile.expenses.items() if k not in NEEDS)
    total_expenses = needs + wants
    savings = income - total_expenses

    needs_pct = needs / income * 100
    wants_pct = wants / income * 100
    savings_pct = savings / income * 100

    emergency_target = total_expenses * 6
    if total_expenses > 0:
        months_covered = profile.current_savings / total_expenses
    else:
        months_covered = 12.0

    emi = profile.expenses.get("EMI / Debt", 0.0)
    dti = emi / income

    # --- Health score (0-100) ---
    # Savings rate: 40 pts (full marks at >= 20%)
    score = _clamp(savings_pct / 20, 0, 1) * 40
    # Emergency fund: 30 pts (full marks at >= 6 months)
    score += _clamp(months_covered / 6, 0, 1) * 30
    # Debt burden: 20 pts (full marks at DTI <= 20%, zero at >= 50%)
    score += _clamp((0.5 - dti) / 0.3, 0, 1) * 20
    # Wants discipline: 10 pts (full marks at <= 30%, zero at >= 60%)
    score += _clamp((60 - wants_pct) / 30, 0, 1) * 10
    health_score = int(round(score))

    if health_score >= 80:
        label = "Excellent"
    elif health_score >= 60:
        label = "Good"
    elif health_score >= 40:
        label = "Needs Improvement"
    else:
        label = "Critical"

    flags = []
    if savings < 0:
        flags.append("Spending exceeds income - you are running a monthly deficit.")
    elif savings_pct < 20:
        flags.append("Savings rate is below the 20% target.")
    if needs_pct > 50:
        flags.append("Needs exceed 50% of income.")
    if wants_pct > 30:
        flags.append("Wants exceed 30% of income.")
    if months_covered < 6:
        flags.append("Emergency fund covers less than 6 months of expenses.")
    if dti > 0.4:
        flags.append("EMI payments exceed 40% of income - high debt risk.")

    return BudgetAnalysis(
        total_income=income,
        total_expenses=total_expenses,
        needs=needs,
        wants=wants,
        savings=savings,
        needs_pct=needs_pct,
        wants_pct=wants_pct,
        savings_pct=savings_pct,
        emergency_target=emergency_target,
        emergency_months_covered=months_covered,
        debt_to_income=dti,
        health_score=health_score,
        health_label=label,
        ideal={"needs": income * 0.5, "wants": income * 0.3, "savings": income * 0.2},
        flags=flags,
    )
