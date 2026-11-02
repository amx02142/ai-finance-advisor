"""India income-tax calculator: Old vs New regime (individuals below 60, salaried).

Slabs as published for FY 2026-27 (AY 2027-28). Surcharge (income > Rs 50 lakh) is NOT included.
This is an estimate for planning - always verify with the latest Income Tax Department rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

INF = float("inf")
CESS = 0.04

NEW_SLABS = [(400_000, 0.0), (800_000, 0.05), (1_200_000, 0.10), (1_600_000, 0.15),
             (2_000_000, 0.20), (2_400_000, 0.25), (INF, 0.30)]
OLD_SLABS = [(250_000, 0.0), (500_000, 0.05), (1_000_000, 0.20), (INF, 0.30)]

NEW_STD_DEDUCTION = 75_000
OLD_STD_DEDUCTION = 50_000
NEW_REBATE_LIMIT, NEW_REBATE_MAX = 1_200_000, 60_000
OLD_REBATE_LIMIT, OLD_REBATE_MAX = 500_000, 12_500

CAP_80C = 150_000
CAP_80CCD_1B = 50_000
CAP_80D = 100_000
CAP_HOME_LOAN_INTEREST = 200_000


@dataclass
class Deductions:
    """Old-regime deductions (annual, Rs)."""

    sec_80c: float = 0.0
    sec_80d: float = 0.0
    nps_80ccd_1b: float = 0.0
    hra_exempt: float = 0.0
    home_loan_interest: float = 0.0
    other: float = 0.0
    employer_nps: float = 0.0  # 80CCD(2): allowed in both regimes


@dataclass
class TaxResult:
    regime: str
    gross_income: float
    deductions: float
    taxable_income: float
    slab_tax: float
    rebate: float
    cess: float
    total_tax: float

    @property
    def effective_rate(self) -> float:
        return self.total_tax / self.gross_income * 100 if self.gross_income else 0.0

    @property
    def monthly_take_home(self) -> float:
        return (self.gross_income - self.total_tax) / 12


def slab_tax(taxable: float, slabs) -> float:
    tax, prev = 0.0, 0.0
    for limit, rate in slabs:
        if taxable > prev:
            tax += (min(taxable, limit) - prev) * rate
        prev = limit
    return tax


def new_regime_tax(gross: float, employer_nps: float = 0.0) -> TaxResult:
    deductions = NEW_STD_DEDUCTION + employer_nps
    taxable = max(gross - deductions, 0.0)
    tax = slab_tax(taxable, NEW_SLABS)
    if taxable <= NEW_REBATE_LIMIT:
        rebate = min(tax, NEW_REBATE_MAX)
    else:  # marginal relief just above the rebate limit
        rebate = max(tax - (taxable - NEW_REBATE_LIMIT), 0.0)
    after_rebate = tax - rebate
    cess = after_rebate * CESS
    return TaxResult("New", gross, deductions, taxable, tax, rebate, cess, after_rebate + cess)


def old_regime_tax(gross: float, d: Optional[Deductions] = None) -> TaxResult:
    d = d or Deductions()
    deductions = (
        OLD_STD_DEDUCTION
        + d.hra_exempt
        + min(d.sec_80c, CAP_80C)
        + min(d.nps_80ccd_1b, CAP_80CCD_1B)
        + min(d.sec_80d, CAP_80D)
        + min(d.home_loan_interest, CAP_HOME_LOAN_INTEREST)
        + d.other
        + d.employer_nps
    )
    taxable = max(gross - deductions, 0.0)
    tax = slab_tax(taxable, OLD_SLABS)
    rebate = min(tax, OLD_REBATE_MAX) if taxable <= OLD_REBATE_LIMIT else 0.0
    after_rebate = tax - rebate
    cess = after_rebate * CESS
    return TaxResult("Old", gross, deductions, taxable, tax, rebate, cess, after_rebate + cess)


def compare_regimes(gross: float, d: Optional[Deductions] = None) -> Dict[str, object]:
    d = d or Deductions()
    new = new_regime_tax(gross, d.employer_nps)
    old = old_regime_tax(gross, d)
    better = "New" if new.total_tax <= old.total_tax else "Old"
    return {
        "new": new,
        "old": old,
        "better": better,
        "saving": abs(new.total_tax - old.total_tax),
    }


def breakeven_deductions(gross: float, step: int = 10_000, limit: int = 1_000_000) -> Optional[int]:
    """Smallest extra old-regime deductions (beyond standard deduction) at which Old beats New."""
    new_tax = new_regime_tax(gross).total_tax
    for extra in range(0, limit + step, step):
        if old_regime_tax(gross, Deductions(other=extra)).total_tax < new_tax:
            return extra
    return None
