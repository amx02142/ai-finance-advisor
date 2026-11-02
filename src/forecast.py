"""Expense forecasting (damped linear trend with an 80% confidence band)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def forecast_series(monthly: pd.Series, horizon: int = 3) -> pd.DataFrame:
    """Forecast the next `horizon` months from a month-indexed Series ("YYYY-MM" labels).

    - fewer than 3 data points: flat forecast at the mean
    - otherwise: least-squares trend, damped (60%) so one odd month cannot run away
    Returns columns: month, forecast, lower, upper.
    """
    if len(monthly) == 0:
        raise ValueError("At least one month of data is required to forecast.")
    y = monthly.to_numpy(dtype=float)
    n = len(y)

    if n < 3:
        base = np.full(horizon, y.mean())
        sigma = y.std() if n > 1 else y.mean() * 0.10
        slope = 0.0
    else:
        x = np.arange(n)
        slope, intercept = np.polyfit(x, y, 1)
        fitted = intercept + slope * x
        sigma = float(np.std(y - fitted, ddof=2)) if n > 2 else 0.0
        base = fitted[-1] + 0.6 * slope * np.arange(1, horizon + 1)

    band = 1.28 * sigma  # ~80% interval
    forecast = np.maximum(base, 0.0)
    last = pd.Period(str(monthly.index[-1]), freq="M")
    months = [str(last + i) for i in range(1, horizon + 1)]
    frame = pd.DataFrame(
        {
            "month": months,
            "forecast": forecast,
            "lower": np.maximum(forecast - band, 0.0),
            "upper": forecast + band,
        }
    )
    frame.attrs["slope"] = float(slope)
    return frame


def trend_label(monthly: pd.Series) -> str:
    """Human readable trend of monthly spend."""
    if len(monthly) < 3:
        return "Not enough data"
    slope = np.polyfit(np.arange(len(monthly)), monthly.to_numpy(dtype=float), 1)[0]
    pct = slope / monthly.mean() * 100
    if pct > 3:
        return f"Rising (+{pct:.1f}% / month)"
    if pct < -3:
        return f"Falling ({pct:.1f}% / month)"
    return "Stable"
