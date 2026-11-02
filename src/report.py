"""Downloadable reports (Markdown and a print-ready HTML version)."""

from __future__ import annotations

from datetime import date
from typing import Dict

from .advisor import DISCLAIMER, plan_to_markdown
from .budget import BudgetAnalysis, FinanceProfile
from .config import APP_NAME
from .fmt import inr


def build_report(
    profile: FinanceProfile,
    analysis: BudgetAnalysis,
    plan: Dict[str, float],
    action_plan: Dict,
    statement_md: str = "",
    mc_md: str = "",
    tax_md: str = "",
    ai_source: str = "rule-based engine",
) -> str:
    rows = "\n".join(f"| {k} | {inr(v)} |" for k, v in profile.expenses.items() if v > 0)
    flags = "\n".join(f"- {f}" for f in analysis.flags) or "- No major red flags."
    sections = [
        f"# {APP_NAME} - Personal Finance Report",
        f"_Generated on {date.today().isoformat()}_",
        "## 1. Profile\n"
        f"- Age: {profile.age}\n- Monthly income: {inr(analysis.total_income)}\n- Risk appetite: {profile.risk_level}\n"
        f"- Goal: {profile.goal_name} - {inr(profile.goal_amount)} in {profile.goal_years} years\n"
        f"- Current savings and investments: {inr(profile.current_savings)}",
        f"## 2. Monthly Expenses\n| Category | Amount |\n|---|---|\n{rows}\n| **Total** | **{inr(analysis.total_expenses)}** |",
        "## 3. Budget Analysis\n"
        f"- Needs {analysis.needs_pct:.1f}% | Wants {analysis.wants_pct:.1f}% | Savings {analysis.savings_pct:.1f}%\n"
        f"- Monthly savings: {inr(analysis.savings)}\n"
        f"- Emergency fund: {analysis.emergency_months_covered:.1f} months (target 6)\n"
        f"- Debt-to-income: {analysis.debt_to_income * 100:.0f}%\n"
        f"- **Health score: {analysis.health_score}/100 ({analysis.health_label})**\n\n### Red flags\n{flags}",
        "## 4. Goal Plan\n"
        f"- Required SIP: {inr(plan['required_sip'])} per month (assumed return {plan['rate'] * 100:.0f}%)\n"
        f"- Projected corpus with the current surplus: {inr(plan['projected_corpus'])}\n"
        f"- Shortfall: {inr(plan['shortfall'])}\n- Status: {'On track' if plan['on_track'] else 'Needs adjustment'}",
        f"## 5. Action Plan _(source: {ai_source})_\n{plan_to_markdown(action_plan)}",
    ]
    for title, body in (("6. Bank Statement Insights", statement_md), ("7. Monte Carlo Simulation", mc_md),
                        ("8. Tax Comparison", tax_md)):
        if body:
            sections.append(f"## {title}\n{body}")
    sections.append(f"---\n_{DISCLAIMER}_")
    return "\n\n".join(sections) + "\n"


_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#0f172a;line-height:1.6}}
h1{{color:#4338ca;border-bottom:3px solid #6366f1;padding-bottom:8px}}h2{{color:#1e293b;margin-top:2rem}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{border:1px solid #e2e8f0;padding:8px 12px;text-align:left}}
th{{background:#eef2ff}}blockquote,em{{color:#64748b}}@media print{{body{{margin:0}}}}</style></head><body>{body}</body></html>"""


def to_html(markdown_text: str, title: str = "Finance Report") -> str:
    import markdown

    return _HTML.format(title=title, body=markdown.markdown(markdown_text, extensions=["tables"]))
