import pytest

from src.projections import (
    goal_plan,
    inflation_adjusted,
    lumpsum_future_value,
    projection_series,
    required_monthly_sip,
    sip_future_value,
    suggest_allocation,
)


def test_sip_future_value_known_value():
    # Rs 10,000/month, 12% p.a., 10 years -> about Rs 23.2 lakh (annuity-due)
    fv = sip_future_value(10000, 0.12, 10)
    assert fv == pytest.approx(2_323_391, rel=0.01)


def test_zero_rate_sip():
    assert sip_future_value(1000, 0.0, 2) == 24000


def test_required_sip_roundtrip():
    sip = required_monthly_sip(5_000_000, 0.10, 15, current_savings=100000)
    total = sip_future_value(sip, 0.10, 15) + lumpsum_future_value(100000, 0.10, 15)
    assert total == pytest.approx(5_000_000, rel=1e-6)


def test_required_sip_zero_when_already_enough():
    assert required_monthly_sip(100000, 0.10, 10, current_savings=1_000_000) == 0


def test_inflation_adjustment():
    assert inflation_adjusted(1000, 1, 0.06) == pytest.approx(1000 / 1.06)


def test_projection_series_shape():
    s = projection_series(5000, 0.10, 5, 10000)
    assert len(s) == 6
    assert s[0]["value"] == pytest.approx(10000)
    assert s[-1]["value"] > s[-1]["invested"]


@pytest.mark.parametrize("age", [20, 35, 50, 70])
@pytest.mark.parametrize("risk", ["Low", "Medium", "High"])
def test_allocation_sums_to_100(age, risk):
    alloc = suggest_allocation(age, risk)
    assert sum(alloc.values()) == 100
    assert all(v >= 0 for v in alloc.values())


def test_higher_risk_means_more_equity():
    low = suggest_allocation(30, "Low")
    high = suggest_allocation(30, "High")
    assert list(high.values())[0] > list(low.values())[0]


def test_goal_plan_on_track_flag():
    plan = goal_plan(1_000_000, 10, "Medium", 0, 20000)
    assert plan["on_track"] and plan["shortfall"] == 0
    plan = goal_plan(50_000_000, 5, "Medium", 0, 1000)
    assert not plan["on_track"] and plan["shortfall"] > 0
