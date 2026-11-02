import pytest

from src.affordability import assess_purchase
from src.budget import FinanceProfile
from src.debt import compare_strategies, emi, payoff_schedule
from src.fire import fire_number, fire_plan

DEBTS = [
    {"name": "Card", "balance": 100_000, "rate_pct": 36.0, "min_payment": 4_000},
    {"name": "Personal", "balance": 250_000, "rate_pct": 14.0, "min_payment": 8_000},
    {"name": "Car", "balance": 400_000, "rate_pct": 9.5, "min_payment": 9_000},
]


def test_emi_formula():
    assert emi(1_000_000, 0.10, 120) == pytest.approx(13_215.07, abs=0.5)
    assert emi(120_000, 0.0, 12) == 10_000
    assert emi(0, 0.1, 12) == 0
    with pytest.raises(ValueError):
        emi(1000, 0.1, 0)


def test_single_loan_schedule_matches_emi_math():
    loan = [{"name": "L", "balance": 500_000, "rate_pct": 10.0, "min_payment": emi(500_000, 0.10, 60)}]
    res = payoff_schedule(loan, 0, "avalanche")
    assert res["converged"] and res["months"] == 60
    assert res["total_interest"] == pytest.approx(emi(500_000, 0.10, 60) * 60 - 500_000, rel=1e-4)


def test_avalanche_beats_snowball_beats_minimum():
    res = compare_strategies(DEBTS, 5_000)
    assert res["avalanche"]["total_interest"] <= res["snowball"]["total_interest"] < res["minimum"]["total_interest"]
    assert res["avalanche"]["months"] < res["minimum"]["months"]
    assert res["interest_saved"] > 0 and res["months_saved"] > 0
    assert res["avalanche"]["payoff_order"][0][0] == "Card"      # highest rate cleared first
    assert res["snowball"]["payoff_order"][0][0] == "Card"        # smallest balance is the card too
    assert (res["avalanche"]["history"].iloc[-1] == 0).all()


def test_money_is_conserved():
    res = payoff_schedule(DEBTS, 3_000, "snowball")
    assert res["total_paid"] == pytest.approx(sum(d["balance"] for d in DEBTS) + res["total_interest"])


def test_non_convergent_minimum_payments():
    res = payoff_schedule([{"name": "X", "balance": 100_000, "rate_pct": 36.0, "min_payment": 1_000}], 0, "minimum", max_months=120)
    assert not res["converged"] and res["months"] is None


def test_debt_validation():
    with pytest.raises(ValueError):
        payoff_schedule([], 0)
    with pytest.raises(ValueError):
        payoff_schedule([{"name": "x", "balance": -1, "rate_pct": 5, "min_payment": 100}], 0)


def test_fire_number_and_plan():
    assert fire_number(50_000, 0, 0.06, 0.04) == pytest.approx(15_000_000)
    plan = fire_plan(30, 55, 50_000, 500_000, 40_000, 0.10, 0.06, 0.035, 0.05)
    assert plan["years_to_retire"] == 25 and plan["series"][0]["age"] == 30 and plan["series"][-1]["age"] >= 55
    assert plan["on_track"] == (plan["projected_corpus"] >= plan["fire_number"])


def test_fire_required_monthly_closes_the_gap():
    plan = fire_plan(30, 50, 60_000, 200_000, 5_000, 0.10, 0.06, 0.035, 0.0)
    assert not plan["on_track"] and plan["required_monthly"] > 5_000
    again = fire_plan(30, 50, 60_000, 200_000, plan["required_monthly"], 0.10, 0.06, 0.035, 0.0)
    assert again["projected_corpus"] == pytest.approx(again["fire_number"], rel=1e-3)


def test_fire_validation():
    with pytest.raises(ValueError):
        fire_plan(40, 40, 50_000, 0, 0)


def _profile(**over):
    base = dict(age=30, monthly_income=100_000,
                expenses={"Rent / Home Loan": 25_000, "Groceries & Food": 10_000, "Insurance": 2_000, "Shopping": 10_000},
                risk_level="Medium", goal_name="Retirement", goal_amount=5_000_000, goal_years=20, current_savings=900_000)
    base.update(over)
    return FinanceProfile(**base)


def test_purchase_comfortable_vs_not_advisable():
    ok = assess_purchase(_profile(), 800_000, 300_000, 0.09, 5, 2_000)
    assert ok["tone"] == "success" and ok["emi"] == pytest.approx(emi(500_000, 0.09, 60))
    bad = assess_purchase(_profile(monthly_income=60_000), 3_000_000, 100_000, 0.10, 5, 5_000)
    assert bad["tone"] == "error" and bad["after"].debt_to_income > 0.4
    assert assess_purchase(_profile(current_savings=50_000), 800_000, 300_000, 0.09, 5)["cash_short"] == 250_000


def test_purchase_validation_and_cash_purchase():
    with pytest.raises(ValueError):
        assess_purchase(_profile(), 0, 0, 0.09, 5)
    with pytest.raises(ValueError):
        assess_purchase(_profile(), 100_000, 200_000, 0.09, 5)
    cash = assess_purchase(_profile(), 100_000, 100_000, 0.09, 1)
    assert cash["emi"] == 0 and cash["total_interest"] == 0
