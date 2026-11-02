"""Plotly chart builders."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go

from .budget import BudgetAnalysis

PALETTE = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16"]


def _layout(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=20, r=20, t=60, b=70),
        legend=dict(orientation="h", yanchor="top", y=-0.2),
    )
    return fig


def expense_pie(expenses: Dict[str, float]) -> go.Figure:
    data = {k: v for k, v in expenses.items() if v > 0}
    fig = go.Figure(
        go.Pie(
            labels=list(data.keys()),
            values=list(data.values()),
            hole=0.45,
            marker=dict(colors=PALETTE),
            textinfo="percent",
        )
    )
    return _layout(fig, "Monthly Expense Breakdown")


def rule_comparison_bar(analysis: BudgetAnalysis) -> go.Figure:
    cats = ["Needs", "Wants", "Savings"]
    actual = [analysis.needs_pct, analysis.wants_pct, max(analysis.savings_pct, 0)]
    ideal = [50, 30, 20]
    fig = go.Figure()
    fig.add_bar(name="Your actual", x=cats, y=actual, marker_color=PALETTE[0],
                text=[f"{v:.0f}%" for v in actual], textposition="outside")
    fig.add_bar(name="Ideal (50/30/20)", x=cats, y=ideal, marker_color=PALETTE[1],
                text=[f"{v}%" for v in ideal], textposition="outside")
    fig.update_layout(barmode="group", yaxis_title="% of income")
    return _layout(fig, "50/30/20 Rule: Actual vs Ideal")


def allocation_donut(allocation: Dict[str, int]) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=list(allocation.keys()),
            values=list(allocation.values()),
            hole=0.5,
            marker=dict(colors=PALETTE[1:]),
            textinfo="percent",
        )
    )
    fig.update_layout(showlegend=True)
    return _layout(fig, "Suggested Asset Allocation")


def projection_line(series: List[Dict[str, float]], goal_amount: float) -> go.Figure:
    years = [r["year"] for r in series]
    fig = go.Figure()
    fig.add_scatter(x=years, y=[r["value"] for r in series], name="Projected value",
                    mode="lines", line=dict(color=PALETTE[1], width=3), fill="tozeroy",
                    fillcolor="rgba(16,185,129,0.12)")
    fig.add_scatter(x=years, y=[r["invested"] for r in series], name="Amount invested",
                    mode="lines", line=dict(color=PALETTE[0], width=2, dash="dash"))
    fig.add_hline(y=goal_amount, line_dash="dot", line_color=PALETTE[3],
                  annotation_text="Goal", annotation_position="top left")
    fig.update_layout(xaxis_title="Years", yaxis_title="Amount (₹)")
    return _layout(fig, "Wealth Projection")


def health_gauge(score: int) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(suffix="/100"),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color="#1F2937"),
                steps=[
                    dict(range=[0, 40], color="#FCA5A5"),
                    dict(range=[40, 60], color="#FCD34D"),
                    dict(range=[60, 80], color="#A7F3D0"),
                    dict(range=[80, 100], color="#34D399"),
                ],
            ),
        )
    )
    _layout(fig, "Financial Health Score", height=300)
    fig.update_layout(margin=dict(l=40, r=60, t=60, b=10))
    return fig


# ------------------------------------------------------------------ advanced charts
def spend_trend(history, forecast) -> go.Figure:
    """Monthly spend bars + forecast line with confidence band."""
    fig = go.Figure()
    fig.add_bar(x=list(history.index), y=list(history.values), name="Actual spend",
                marker_color=PALETTE[0])
    if forecast is not None and len(forecast):
        x = [history.index[-1]] + list(forecast["month"])
        mid = [history.values[-1]] + list(forecast["forecast"])
        upper = [history.values[-1]] + list(forecast["upper"])
        lower = [history.values[-1]] + list(forecast["lower"])
        fig.add_scatter(x=x, y=upper, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=x, y=lower, mode="lines", line=dict(width=0), fill="tonexty",
                        fillcolor="rgba(245,158,11,0.18)", name="80% range", hoverinfo="skip")
        fig.add_scatter(x=x, y=mid, mode="lines+markers", name="Forecast",
                        line=dict(color=PALETTE[2], width=3, dash="dash"))
    fig.update_layout(yaxis_title="Spend (₹)", xaxis_title=None, xaxis_type="category")
    return _layout(fig, "Monthly Spend & Forecast")


def category_stack(pivot) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        fig.add_bar(x=list(pivot.index), y=list(pivot[col]), name=col,
                    marker_color=PALETTE[i % len(PALETTE)])
    fig.update_layout(barmode="stack", yaxis_title="Spend (₹)", xaxis_type="category",
                      legend=dict(orientation="v", x=1.02, y=1))
    return _layout(fig, "Category-wise Spend by Month", height=400)


def tax_compare_bar(new_result, old_result) -> go.Figure:
    labels = ["New Regime", "Old Regime"]
    fig = go.Figure()
    fig.add_bar(x=labels, y=[new_result.total_tax, old_result.total_tax],
                marker_color=[PALETTE[0], PALETTE[2]],
                text=[f"₹{new_result.total_tax:,.0f}", f"₹{old_result.total_tax:,.0f}"],
                textposition="outside")
    top = max(new_result.total_tax, old_result.total_tax)
    fig.update_layout(yaxis_title="Annual tax (₹)", showlegend=False,
                      yaxis_range=[0, top * 1.2 if top > 0 else 1])
    return _layout(fig, "Total Tax Payable", height=330)


def monte_carlo_fan(summary: dict, goal_amount: float) -> go.Figure:
    years = list(range(len(summary["p50"])))
    fig = go.Figure()
    fig.add_scatter(x=years, y=summary["p90"], mode="lines", line=dict(width=0),
                    showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=years, y=summary["p10"], mode="lines", line=dict(width=0), fill="tonexty",
                    fillcolor="rgba(37,99,235,0.15)", name="10th-90th percentile")
    fig.add_scatter(x=years, y=summary["p50"], mode="lines", name="Median outcome",
                    line=dict(color=PALETTE[0], width=3))
    fig.add_scatter(x=years, y=summary["invested"], mode="lines", name="Amount invested",
                    line=dict(color=PALETTE[1], width=2, dash="dash"))
    fig.add_hline(y=goal_amount, line_dash="dot", line_color=PALETTE[3],
                  annotation_text="Goal", annotation_position="top left")
    fig.update_layout(xaxis_title="Years", yaxis_title="Portfolio value (₹)")
    return _layout(fig, "Monte Carlo: 2,000 possible futures", height=400)


def final_histogram(final_values, goal_amount: float) -> go.Figure:
    fig = go.Figure(go.Histogram(x=final_values, nbinsx=40, marker_color=PALETTE[4]))
    fig.add_vline(x=goal_amount, line_dash="dot", line_color=PALETTE[3],
                  annotation_text="Goal", annotation_position="top")
    fig.update_layout(xaxis_title="Final corpus (₹)", yaxis_title="Simulations", showlegend=False)
    return _layout(fig, "Distribution of Final Corpus", height=330)


# ------------------------------------------------------------------ planning-lab charts
def debt_balance_lines(history) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(history.columns):
        fig.add_scatter(x=list(history.index), y=list(history[col]), name=col, mode="lines",
                        line=dict(width=3, color=PALETTE[i % len(PALETTE)]), stackgroup=None)
    fig.update_layout(xaxis_title="Months", yaxis_title="Outstanding balance (₹)")
    return _layout(fig, "Debt balance over time", height=380)


def debt_strategy_bars(results: dict) -> go.Figure:
    labels, interest, colors = [], [], []
    names = {"minimum": "Minimum only", "snowball": "Snowball", "avalanche": "Avalanche"}
    for i, key in enumerate(("minimum", "snowball", "avalanche")):
        r = results[key]
        if r["converged"]:
            labels.append(f"{names[key]}<br>{r['months']} months")
            interest.append(r["total_interest"])
            colors.append([PALETTE[3], PALETTE[2], PALETTE[1]][i])
    fig = go.Figure(go.Bar(x=labels, y=interest, marker_color=colors,
                           text=[f"₹{v:,.0f}" for v in interest], textposition="outside"))
    fig.update_layout(yaxis_title="Total interest paid (₹)", showlegend=False,
                      yaxis_range=[0, max(interest) * 1.2 if interest else 1])
    return _layout(fig, "Total interest by strategy", height=380)


def fire_chart(series, retire_age: int) -> go.Figure:
    ages = [r["age"] for r in series]
    fig = go.Figure()
    fig.add_scatter(x=ages, y=[r["target"] for r in series], name="FIRE target (inflation-adjusted)",
                    mode="lines", line=dict(color=PALETTE[3], width=2, dash="dot"))
    fig.add_scatter(x=ages, y=[r["corpus"] for r in series], name="Projected corpus", mode="lines",
                    line=dict(color=PALETTE[1], width=3), fill="tozeroy", fillcolor="rgba(16,185,129,0.12)")
    fig.add_vline(x=retire_age, line_dash="dash", line_color=PALETTE[0],
                  annotation_text="Retirement", annotation_position="top left")
    fig.update_layout(xaxis_title="Age", yaxis_title="Amount (₹)")
    return _layout(fig, "Path to financial independence", height=400)


def before_after_bars(before, after) -> go.Figure:
    cats = ["Savings rate %", "EMI share of income %", "Emergency fund (months)"]
    b = [before.savings_pct, before.debt_to_income * 100, before.emergency_months_covered]
    a = [after.savings_pct, after.debt_to_income * 100, after.emergency_months_covered]
    fig = go.Figure()
    fig.add_bar(name="Before", x=cats, y=b, marker_color=PALETTE[0], text=[f"{v:.1f}" for v in b], textposition="outside")
    fig.add_bar(name="After purchase", x=cats, y=a, marker_color=PALETTE[2], text=[f"{v:.1f}" for v in a], textposition="outside")
    fig.update_layout(barmode="group")
    return _layout(fig, "Impact on your finances", height=360)
