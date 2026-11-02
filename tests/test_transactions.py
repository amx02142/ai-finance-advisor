from pathlib import Path

import pandas as pd
import pytest

from src.transactions import (
    INCOME, INVEST, UNCAT, average_monthly_expenses, average_monthly_income, categorize_description,
    categorize_df, detect_anomalies, detect_recurring, load_statement, monthly_expenses, normalize_statement,
    rule_based_insights, build_statement_context,
)

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_statement.csv"


@pytest.fixture(scope="module")
def stmt():
    return categorize_df(load_statement(SAMPLE))


@pytest.mark.parametrize("desc,amount,expected", [
    ("SWIGGY ORDER 12345", -300, "Dining Out"),
    ("NETFLIX.COM", -649, "Subscriptions"),
    ("UPI-LANDLORD RENT", -16000, "Rent / Home Loan"),
    ("SIP GROWW MUTUAL FUND", -5000, INVEST),
    ("SALARY CREDIT", 50000, INCOME),
    ("UPI-RAMESH KUMAR", -500, UNCAT),
    ("SCHOLARSHIP FEES", -500, UNCAT),  # 'ola' must not match inside 'scholarship'
    ("UBER TRIP", -200, "Transport"),
])
def test_categorize_description(desc, amount, expected):
    assert categorize_description(desc, amount) == expected


def test_normalize_debit_credit_columns():
    raw = pd.DataFrame({"Txn Date": ["01/05/2026", "02/05/2026"], "Narration": ["SALARY", "SWIGGY"],
                        "Withdrawal Amt.": ["", "1,250.50"], "Deposit Amt.": ["50,000", ""]})
    df = normalize_statement(raw)
    assert list(df["amount"]) == [50000, -1250.5]
    assert df["month"].iloc[0] == "2026-05"


def test_normalize_single_amount_with_type():
    raw = pd.DataFrame({"Date": ["01-05-2026", "03-05-2026"], "Description": ["A", "B"],
                        "Amount": [100, 250], "Type": ["CR", "DR"]})
    assert list(normalize_statement(raw)["amount"]) == [100, -250]


def test_normalize_rejects_bad_input():
    with pytest.raises(ValueError):
        normalize_statement(pd.DataFrame({"foo": [1], "bar": [2]}))
    with pytest.raises(ValueError):
        normalize_statement(pd.DataFrame())


def test_sample_statement_loads_and_totals(stmt):
    assert stmt["month"].nunique() == 6
    assert len(monthly_expenses(stmt)) == 6
    assert 55000 < average_monthly_income(stmt) < 65000
    avg = average_monthly_expenses(stmt)
    assert avg["Rent / Home Loan"] == pytest.approx(14000)
    assert avg["Subscriptions"] > 2000


def test_recurring_and_anomalies(stmt):
    names = " ".join(detect_recurring(stmt)["merchant"]).lower()
    assert "netflix" in names and "rent" in names
    anomalies = detect_anomalies(stmt)
    assert any("CROMA" in d for d in anomalies["description"])


def test_text_summaries(stmt):
    assert "Spending insights" in rule_based_insights(stmt)
    assert "BANK STATEMENT SUMMARY" in build_statement_context(stmt)
