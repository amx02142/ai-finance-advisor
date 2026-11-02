"""Generate data/sample_statement.csv - 6 months of realistic bank transactions (Apr-Sep 2026)."""
import csv
import random
from datetime import date
from pathlib import Path

rng = random.Random(7)
OUT = Path(__file__).resolve().parent.parent / "data" / "sample_statement.csv"
MONTHS = [(2026, m) for m in range(4, 10)]
rows = []  # (date, description, debit, credit)


def d(y, m, day):
    return date(y, m, min(day, 28))


for y, m in MONTHS:
    rows.append((d(y, m, 1), "SALARY CREDIT ACME TECH PVT LTD", 0, 58000))
    if m == 6:
        rows.append((d(y, m, 15), "BONUS CREDIT ACME TECH", 0, 8000))
    rows.append((d(y, m, 3), "UPI-LANDLORD RENT", 14000, 0))
    rows.append((d(y, m, 5), "BAJAJ FINSERV EMI", 3500, 0))
    rows.append((d(y, m, 6), "HDFC LIFE INSURANCE PREMIUM", 1500, 0))
    rows.append((d(y, m, 7), "SIP GROWW MUTUAL FUND", 5000, 0))
    rows.append((d(y, m, 2), "NETFLIX.COM", 649, 0))
    rows.append((d(y, m, 2), "SPOTIFY INDIA", 119, 0))
    rows.append((d(y, m, 4), "GOOGLE ONE", 130, 0))
    rows.append((d(y, m, 8), "CULT.FIT GYM MEMBERSHIP", 1500, 0))
    rows.append((d(y, m, 9), "AIRTEL BROADBAND BILL", 999, 0))
    rows.append((d(y, m, 10), "JIO RECHARGE", 349, 0))
    rows.append((d(y, m, 12), "BSES ELECTRICITY BILL", rng.randint(1200, 2400), 0))
    for _ in range(rng.randint(5, 7)):
        shop = rng.choice(["BIGBASKET", "BLINKIT", "DMART", "ZEPTO"])
        rows.append((d(y, m, rng.randint(1, 28)), f"{shop} ORDER", rng.randint(300, 1500), 0))
    for _ in range(rng.randint(4, 6)):
        rows.append((d(y, m, rng.randint(1, 28)), "SWIGGY ORDER", rng.randint(150, 600), 0))
    for _ in range(rng.randint(3, 5)):
        rows.append((d(y, m, rng.randint(1, 28)), "ZOMATO ORDER", rng.randint(200, 700), 0))
    for _ in range(rng.randint(2, 3)):
        rows.append((d(y, m, rng.randint(1, 28)), "STARBUCKS COFFEE", rng.randint(250, 500), 0))
    for _ in range(rng.randint(5, 8)):
        rows.append((d(y, m, rng.randint(1, 28)), "UBER TRIP", rng.randint(150, 400), 0))
    for _ in range(2):
        rows.append((d(y, m, rng.randint(1, 28)), "INDIAN OIL PETROL PUMP", rng.randint(800, 1200), 0))
    rows.append((d(y, m, 14), "DELHI METRO RECHARGE", 500, 0))
    for _ in range(rng.randint(1, 3)):
        rows.append((d(y, m, rng.randint(1, 28)), "AMAZON PAY INDIA", rng.randint(400, 3000), 0))
    rows.append((d(y, m, rng.randint(1, 28)), "MYNTRA DESIGNS", rng.randint(800, 2500), 0))
    for _ in range(rng.randint(1, 2)):
        rows.append((d(y, m, rng.randint(1, 28)), "APOLLO PHARMACY", rng.randint(200, 900), 0))
    rows.append((d(y, m, rng.randint(1, 28)), "BOOKMYSHOW TICKETS", rng.randint(500, 900), 0))
    for _ in range(2):  # unknown merchants -> good for AI categorisation
        rows.append((d(y, m, rng.randint(1, 28)), f"UPI-{rng.choice(['RAMESH KUMAR', 'SURESH STORES', 'ANITA TAILORS'])}",
                     rng.randint(500, 2000), 0))
    rows.append((d(y, m, rng.randint(1, 28)), "ATM WDL CASH", 2000, 0))

rows.append((d(2026, 7, 18), "MAKEMYTRIP FLIGHT BOOKING", 6200, 0))
rows.append((d(2026, 8, 20), "CROMA ELECTRONICS LAPTOP", 18000, 0))  # anomaly
rows.append((d(2026, 5, 22), "CLINIC DR SHARMA", 800, 0))
rows.append((d(2026, 9, 11), "CLINIC DR SHARMA", 800, 0))

rows.sort(key=lambda r: r[0])
balance = 45000
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Description", "Debit", "Credit", "Balance"])
    for dt, desc, debit, credit in rows:
        balance += credit - debit
        w.writerow([dt.strftime("%d/%m/%Y"), desc, debit or "", credit or "", balance])
print(f"wrote {len(rows)} rows -> {OUT}")
