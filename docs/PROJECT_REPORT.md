# FinPilot AI - Project Report

## 1. Abstract
Most people cannot afford a human financial advisor and rely on generic advice that ignores their own numbers.
**FinPilot AI** is a web application that combines deterministic financial engines (budgeting, SIP maths, Monte Carlo,
tax, debt and FIRE planning) with Google Gemini to deliver personalised, explainable guidance. Bank statements are
categorised automatically, spending is forecast, and a streaming AI copilot answers questions using the user's real
data. The system degrades gracefully to a rule-based advisor when no API key or network is available.

## 2. Problem statement
- Users do not know how much to save, invest or borrow.
- Advisors are expensive; generic internet advice is not personal.
- Existing budgeting apps show data but do not plan, simulate or explain.

## 3. Objectives
1. Analyse the budget (50/30/20) and score financial health.
2. Turn raw bank statements into categories, recurring payments, anomalies and a forecast.
3. Plan goals with probabilistic simulation instead of a single optimistic number.
4. Support decisions: tax regime, debt payoff strategy, FIRE age, affordability of a purchase.
5. Provide a conversational AI that is grounded in the user's data and always safe to run offline.

## 4. Architecture
```
Streamlit UI (top navigation, 7 pages)  <-- session state (profile, statement, settings)
        |
        v
   Deterministic engines (src/)                     Gemini layer (src/llm.py, advisor.py)
   budget - transactions - forecast - projections   stream() / generate() with model fallback
   simulation - tax - debt - fire - affordability   structured JSON action plan, AI categorisation
        |                                                   |
        +---------------> context builder <-----------------+
                                |
              no key or API error -> rule-based advisor (offline mode)
```
Design principle: **numbers come from tested Python code; the LLM explains and advises on top of them.**

## 5. Key algorithms
| Module | Method |
|---|---|
| Health score | savings rate (40) + emergency fund (30) + debt burden (20) + wants discipline (10) |
| SIP | FV = P x [((1+r)^n - 1)/r] x (1+r); required SIP by inversion |
| Monte Carlo | 2,000 paths; monthly return ~ N(mu/12, sigma/sqrt(12)); step-up SIP; P10/P50/P90 and goal probability |
| Forecast | least-squares trend damped by 60%, 80% band from residual deviation |
| Categorisation | word-boundary keyword engine, Gemini JSON classification for unknown merchants, editable by user |
| Recurring / anomalies | same merchant in >= 3 months with CV <= 0.25; per-category z-score > 2.5 and > 2x median |
| Tax | slab engine, 87A rebate, marginal relief, break-even search for the Old regime |
| Debt | month-by-month simulation; avalanche (highest rate) vs snowball (smallest balance) vs minimum, payments roll over |
| FIRE | corpus needed = inflated expenses / withdrawal rate; bisection for required monthly investment; earliest FI age; Coast FIRE |
| Affordability | EMI formula; before/after DTI, savings rate, emergency fund, health score; verdict rules |

## 6. AI design
- **Grounding:** every prompt contains a compact snapshot of profile, goal, statement summary and forecast.
- **Structured output:** the action plan is requested as JSON, validated (priority, title, detail) and rendered as cards;
  invalid output triggers the offline plan.
- **Streaming:** copilot answers stream token by token (`generate_content_stream`).
- **Resilience:** model chain `gemini-3.5-flash -> gemini-2.5-flash -> gemini-2.5-pro`; authentication errors stop the chain
  and show an actionable message; every AI feature has an offline fallback.
- **Safety:** no stock tips or guaranteed returns; transaction text is treated as untrusted data (prompt-injection
  hygiene); AI text is HTML-escaped before rendering; disclaimer on every page.
- **Transparency:** the "What the copilot can see" panel shows exactly what is sent.

## 7. Security and privacy
The API key is read from `.env` / environment on the server, masked in the UI, never logged and git-ignored. No database:
data lives in the browser session. Only summaries are sent to Gemini and only when an AI action is triggered.

## 8. Testing
82 pytest tests cover maths (round-trip checks such as zero-volatility Monte Carlo = closed-form SIP), parsing,
categorisation, forecasting, tax edge cases, debt conservation of money, FIRE inversion, affordability verdicts, key
discovery and a **mocked Gemini client** (model fallback, streaming, JSON validation, error handling). A Playwright
smoke test opens all pages in a real browser and fails on any Streamlit exception; the `.env` flow was verified end to end.

## 9. Limitations
Illustrative return assumptions; tax estimate excludes surcharge and other income; no live market or bank integration;
categorisation of unusual merchants depends on the AI or manual correction.

## 10. Future scope
Bank-statement PDF parsing, account aggregation, portfolio tracking with live prices, multi-user login with a database,
voice assistant, goal alerts by email/WhatsApp.

## 11. Viva questions
**What is the role of AI if calculations are in Python?** Python guarantees correct, testable numbers; Gemini explains,
prioritises and answers follow-up questions in natural language using those numbers.

**What if the API is down or there is no key?** Every AI feature falls back to a rule-based engine, so the app never breaks.

**Why Monte Carlo?** Markets are uncertain; a probability of success is more honest than one fixed projected value.

**Avalanche vs snowball?** Avalanche minimises total interest; snowball clears small debts first for motivation.

**How do you protect the API key?** `.env` outside source control, server-side only, masked in the UI.
