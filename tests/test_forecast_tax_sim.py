import numpy as np
import pandas as pd
import pytest

from src.forecast import forecast_series, trend_label
from src.projections import lumpsum_future_value, sip_future_value
from src.simulation import simulate_sip, summarize
from src.tax import Deductions, breakeven_deductions, compare_regimes, new_regime_tax, old_regime_tax, slab_tax, NEW_SLABS


def test_forecast_follows_trend():
    s = pd.Series([30000, 32000, 34000, 36000, 38000], index=["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"])
    f = forecast_series(s, 3)
    assert list(f["month"]) == ["2026-06", "2026-07", "2026-08"]
    assert f["forecast"].is_monotonic_increasing and f["forecast"].iloc[0] > 38000
    assert (f["lower"] <= f["forecast"]).all() and (f["forecast"] <= f["upper"]).all()
    assert "Rising" in trend_label(s)


def test_forecast_short_history_and_year_rollover():
    f = forecast_series(pd.Series([1000.0], index=["2026-12"]), 2)
    assert list(f["month"]) == ["2027-01", "2027-02"]
    with pytest.raises(ValueError):
        forecast_series(pd.Series(dtype=float))


def test_new_regime_known_values():
    assert new_regime_tax(1_275_000).total_tax == 0          # 12.75L gross -> 12L taxable -> rebate
    # taxable 14.25L: 20,000 + 40,000 + 2.25L x 15% = 93,750, plus 4% cess
    assert new_regime_tax(1_500_000).total_tax == pytest.approx(93_750 * 1.04)
    assert slab_tax(2_400_000, NEW_SLABS) == pytest.approx(300_000)


def test_new_regime_marginal_relief():
    # taxable just above 12L must never pay more than the income above 12L (+cess)
    r = new_regime_tax(1_200_000 + 75_000 + 10_000)
    assert r.total_tax <= 10_000 * 1.04 + 1e-6


def test_old_regime_and_comparison():
    r = old_regime_tax(1_000_000, Deductions(sec_80c=150_000, sec_80d=25_000))
    assert r.taxable_income == 1_000_000 - 50_000 - 150_000 - 25_000
    low = compare_regimes(600_000)
    assert low["better"] == "New" and low["new"].total_tax == 0
    heavy = compare_regimes(2_000_000, Deductions(sec_80c=150_000, nps_80ccd_1b=50_000, sec_80d=50_000,
                                                  hra_exempt=300_000, home_loan_interest=200_000))
    assert heavy["better"] == "Old"


def test_breakeven():
    assert breakeven_deductions(600_000) is None or breakeven_deductions(600_000) >= 0
    be = breakeven_deductions(2_000_000)
    assert be is not None and be > 0


def test_simulation_zero_vol_matches_formula():
    sim = simulate_sip(10_000, 10, 100_000, 0.10, 0.0, n_sims=5)
    expected = sip_future_value(10_000, 0.10, 10) + lumpsum_future_value(100_000, 0.10, 10)
    assert sim["final"][0] == pytest.approx(expected, rel=1e-9)


def test_simulation_stats_and_stepup():
    flat = simulate_sip(10_000, 10, 0, 0.10, 0.12)
    stepped = simulate_sip(10_000, 10, 0, 0.10, 0.12, step_up=0.10)
    assert stepped["invested"][-1] > flat["invested"][-1]
    sm = summarize(flat, goal=1e12)
    assert sm["prob_success"] == 0.0
    assert sm["final_p10"] <= sm["final_p50"] <= sm["final_p90"]
    assert summarize(flat, goal=0)["prob_success"] == 1.0
    assert np.isclose(flat["invested"][-1], 10_000 * 120)
