import json

import pytest

from src import advisor, llm
from src.advisor import (SUGGESTED_PROMPTS, ask_advisor, build_context, generate_action_plan, plan_to_markdown,
                         rule_based_plan, stream_advisor)
from src.budget import FinanceProfile, analyze_budget
from src.fmt import inr, inr_compact
from src.projections import goal_plan
from src.report import build_report, to_html
from tests.test_config_llm import FakeModels, fake_client


def setup(**over):
    base = dict(age=26, monthly_income=45000,
                expenses={"Rent / Home Loan": 14000, "Groceries & Food": 6000, "Shopping": 4000},
                risk_level="Medium", goal_name="Home", goal_amount=3_000_000, goal_years=10, current_savings=60000)
    base.update(over)
    profile = FinanceProfile(**base)
    analysis = analyze_budget(profile)
    plan = goal_plan(profile.goal_amount, profile.goal_years, profile.risk_level, profile.current_savings,
                     max(analysis.savings, 0))
    return profile, analysis, plan


def test_inr_formatting():
    assert [inr(x) for x in (0, 999, 1000, 123456, 12345678, -5000)] == \
        ["₹0", "₹999", "₹1,000", "₹1,23,456", "₹1,23,45,678", "-₹5,000"]
    assert inr_compact(25_000_000) == "₹2.50 Cr" and inr_compact(450_000) == "₹4.50 L" and inr_compact(5000) == "₹5,000"


def test_offline_answers():
    profile, analysis, plan = setup()
    text, mode = ask_advisor("How do I start a SIP?", profile, analysis, plan)
    assert mode == "offline" and "SIP" in text
    text, _ = ask_advisor("xyzzy?", profile, analysis, plan)
    assert "offline mode" in text and "health score" in text
    assert "".join(stream_advisor("emergency fund?", profile, analysis, plan)).startswith("**Emergency fund**")


def test_rule_based_plan_is_prioritised_and_specific():
    profile, analysis, plan = setup(expenses={"Rent / Home Loan": 30000, "EMI / Debt": 20000, "Shopping": 10000})
    result = rule_based_plan(profile, analysis, plan)
    priorities = [a["priority"] for a in result["actions"]]
    assert priorities == sorted(priorities, key={"High": 0, "Medium": 1, "Low": 2}.get)
    titles = " ".join(a["title"] for a in result["actions"])
    assert "deficit" in titles and "insurance" in titles.lower() and len(result["actions"]) <= 6
    assert "health score" in result["summary"]


def test_gemini_plan_json_and_validation(monkeypatch):
    profile, analysis, plan = setup()
    payload = {"summary": "Solid base.", "actions": [
        {"priority": "low", "title": "Rebalance yearly", "detail": "Do it.", "impact": "x", "timeframe": "1y"},
        {"priority": "HIGH", "title": "Boost SIP", "detail": "Raise to ₹10,000.", "impact": "y", "timeframe": "now"},
        {"title": "", "detail": "dropped"}]}
    monkeypatch.setattr(llm, "_client", fake_client(FakeModels(chunks=(json.dumps(payload),))))
    result, mode, err = generate_action_plan(profile, analysis, plan, api_key="k")
    assert mode == "ai" and err is None
    assert [a["priority"] for a in result["actions"]] == ["High", "Low"]
    assert "Boost SIP" in plan_to_markdown(result)


def test_bad_gemini_output_falls_back(monkeypatch):
    profile, analysis, plan = setup()
    monkeypatch.setattr(llm, "_client", fake_client(FakeModels(chunks=("this is not json",))))
    result, mode, err = generate_action_plan(profile, analysis, plan, api_key="k")
    assert mode == "offline" and err and result["actions"]


def test_gemini_failure_falls_back_for_chat(monkeypatch):
    profile, analysis, plan = setup()
    monkeypatch.setattr(llm, "_client", fake_client(FakeModels(fail_models={"gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"}, error="429 quota")))
    text, mode = ask_advisor("Emergency fund?", profile, analysis, plan, api_key="k")
    assert mode == "offline" and "unavailable" in text
    streamed = "".join(stream_advisor("Emergency fund?", profile, analysis, plan, api_key="k"))
    assert "unavailable" in streamed and "Emergency fund" in streamed


def test_stream_with_key_returns_model_text(monkeypatch):
    profile, analysis, plan = setup()
    monkeypatch.setattr(llm, "_client", fake_client(FakeModels(chunks=("Save ", "more."))))
    assert "".join(stream_advisor("Hi", profile, analysis, plan, api_key="k")) == "Save more."


def test_context_includes_numbers_and_statement():
    profile, analysis, plan = setup()
    ctx = build_context(profile, analysis, plan, extra="BANK STATEMENT SUMMARY")
    assert "Monthly income: ₹45,000" in ctx and "BANK STATEMENT SUMMARY" in ctx


def test_report_markdown_and_html():
    profile, analysis, plan = setup()
    md = build_report(profile, analysis, plan, rule_based_plan(profile, analysis, plan), statement_md="x", tax_md="y")
    assert md.startswith("# FinPilot AI") and "Action Plan" in md and "8. Tax Comparison" in md
    html = to_html(md)
    assert "<table>" in html and "<h1>" in html


def test_suggested_prompts_exist():
    assert len(SUGGESTED_PROMPTS) == 6
