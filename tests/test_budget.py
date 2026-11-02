import pytest

from src.budget import FinanceProfile, analyze_budget


def make_profile(**overrides):
    base = dict(
        age=28,
        monthly_income=50000,
        expenses={
            "Rent / Home Loan": 15000,
            "Groceries & Food": 7000,
            "Transport": 3000,
            "Dining Out": 5000,
            "Shopping": 5000,
        },
        risk_level="Medium",
        goal_name="Retirement",
        goal_amount=5_000_000,
        goal_years=20,
        current_savings=150000,
    )
    base.update(overrides)
    return FinanceProfile(**base)


def test_totals_and_split():
    a = analyze_budget(make_profile())
    assert a.needs == 25000
    assert a.wants == 10000
    assert a.total_expenses == 35000
    assert a.savings == 15000
    assert a.savings_pct == pytest.approx(30.0)
    assert a.needs_pct == pytest.approx(50.0)
    assert a.wants_pct == pytest.approx(20.0)


def test_emergency_fund_months():
    a = analyze_budget(make_profile())
    assert a.emergency_months_covered == pytest.approx(150000 / 35000)
    assert a.emergency_target == 35000 * 6


def test_health_score_bounds_and_ordering():
    good = analyze_budget(make_profile(current_savings=500000))
    bad = analyze_budget(
        make_profile(expenses={"Rent / Home Loan": 30000, "EMI / Debt": 25000, "Shopping": 10000},
                     current_savings=0)
    )
    assert 0 <= bad.health_score <= good.health_score <= 100
    assert bad.health_label == "Critical"
    assert any("exceeds income" in f for f in bad.flags)


def test_negative_savings_flagged():
    a = analyze_budget(make_profile(monthly_income=20000))
    assert a.savings < 0
    assert a.flags


@pytest.mark.parametrize(
    "kwargs",
    [
        {"monthly_income": 0},
        {"age": 5},
        {"risk_level": "Crazy"},
        {"goal_years": 0},
        {"current_savings": -1},
    ],
)
def test_invalid_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        analyze_budget(make_profile(**kwargs))
