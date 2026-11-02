"""Browser smoke test: starts the app, visits every page, fails on any Streamlit exception.

Usage:  python scripts/smoke_test.py [--shots]   (needs: pip install playwright && playwright install chromium)
"""
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
PORT = 8791
TAKE_SHOTS = "--shots" in sys.argv
errors = []


def check(page, label):
    page.wait_for_timeout(1800)
    n = page.locator('[data-testid="stException"]').count()
    if n:
        errors.append(f"{label}: {n} exception(s): {page.locator('[data-testid=stException]').first.inner_text()[:300]}")
    print(("FAIL " if n else "ok   ") + label)


def shot(page, name, height=None):
    if TAKE_SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.set_viewport_size({"width": 1440, "height": height or 2000})
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SHOTS / name))
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(500)


def go(page, title):
    page.get_by_role("link", name=re.compile(title)).first.click()
    page.wait_for_timeout(1500)


server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"), "--server.headless", "true",
                           "--server.port", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}/_stcore/health", timeout=2)
            break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"http://localhost:{PORT}", wait_until="networkidle")
        page.get_by_text("Financial Overview").first.wait_for(timeout=60000)
        check(page, "overview"); shot(page, "1_overview.png")
        side = page.locator('section[data-testid="stSidebar"]').inner_text()
        print("sidebar AI status ->", "Connected" if "Connected" in side else "Offline mode" if "Offline mode" in side else "?")

        go(page, "Statement Analyzer")
        page.get_by_role("button", name="Load sample data").click()
        page.get_by_text("Expense forecast").first.wait_for(timeout=60000)
        check(page, "statement"); shot(page, "2_statement.png")
        page.get_by_role("button", name=re.compile("Apply these averages")).click()
        page.wait_for_timeout(2000)
        check(page, "statement apply")

        go(page, "Goals")
        page.get_by_text("Monte Carlo simulator").first.wait_for(timeout=60000)
        check(page, "goals"); shot(page, "3_goals.png")

        go(page, "Planning Lab")
        page.get_by_text("Pay off debt faster").first.wait_for(timeout=60000)
        check(page, "lab: debt"); shot(page, "4_lab_debt.png")
        page.get_by_role("tab", name="FIRE planner").click(); check(page, "lab: fire"); shot(page, "5_lab_fire.png")
        page.get_by_role("tab", name="Purchase analyzer").click(); check(page, "lab: purchase"); shot(page, "6_lab_purchase.png")

        go(page, "Tax Planner")
        page.get_by_text("Old vs New regime").first.wait_for(timeout=60000)
        check(page, "tax"); shot(page, "7_tax.png")
        salary = page.get_by_label("Annual gross salary")
        salary.fill("2500000"); salary.press("Enter"); page.wait_for_timeout(2000)
        go(page, "Overview"); go(page, "Tax Planner")
        page.wait_for_timeout(1500)
        kept = page.get_by_label("Annual gross salary").input_value()
        print("tax salary after navigating away and back:", kept)
        if kept.replace(",", "") != "2500000":
            errors.append(f"tax input did not persist across pages (got {kept})")

        go(page, "AI Copilot")
        page.get_by_text("Ask anything about your money").first.wait_for(timeout=60000)
        page.get_by_role("button", name="How big should my emergency fund be?").click()
        page.get_by_text("Emergency fund").nth(1).wait_for(timeout=90000)
        check(page, "copilot"); shot(page, "8_copilot.png")

        go(page, "Reports")
        page.get_by_text("Download a complete").first.wait_for(timeout=60000)
        check(page, "reports"); shot(page, "9_reports.png")
        for label in ("Markdown report", "HTML report", "Expenses (CSV)"):
            if page.get_by_role("button", name=re.compile(re.escape(label))).count() == 0:
                errors.append(f"missing download button: {label}")
        browser.close()
finally:
    server.terminate()

print("\nRESULT:", "ALL PAGES OK" if not errors else "\n".join(errors))
sys.exit(1 if errors else 0)
