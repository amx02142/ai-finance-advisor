"""Number formatting helpers (Indian digit grouping)."""

from __future__ import annotations


def inr(amount: float) -> str:
    """Format a number as Indian Rupees with lakh/crore grouping: 1234567 -> ₹12,34,567."""
    sign = "-" if amount < 0 else ""
    digits = str(abs(int(round(amount))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{sign}₹{digits}"


def inr_compact(amount: float) -> str:
    """Short form for big numbers: ₹1.25 Cr, ₹48.5 L, otherwise the full value."""
    sign = "-" if amount < 0 else ""
    value = abs(amount)
    if value >= 1e7:
        return f"{sign}₹{value / 1e7:.2f} Cr"
    if value >= 1e5:
        return f"{sign}₹{value / 1e5:.2f} L"
    return inr(amount)


def pct(value: float, digits: int = 0) -> str:
    return f"{value:.{digits}f}%"
