"""FinPilot AI - AI-powered personal finance copilot.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src.config import APP_NAME, load_env

load_env()  # reads GEMINI_API_KEY from the project's .env file

st.set_page_config(page_title=f"{APP_NAME} | Personal Finance Copilot", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

from src.advisor import DISCLAIMER  # noqa: E402  (after set_page_config)
from src.state import build_ctx, init_state, render_sidebar  # noqa: E402
from src.ui import footer, inject_css  # noqa: E402

inject_css()
init_state()
render_sidebar()

try:
    st.session_state["_ctx"] = build_ctx()
except ValueError as err:
    st.error(f"Please fix your profile inputs: {err}")
    st.stop()

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/space_dashboard:", url_path="overview", default=True),
    st.Page("views/statement.py", title="Statement Analyzer", icon=":material/receipt_long:", url_path="statement"),
    st.Page("views/goals.py", title="Goals & Simulator", icon=":material/flag:", url_path="goals"),
    st.Page("views/lab.py", title="Planning Lab", icon=":material/science:", url_path="lab"),
    st.Page("views/tax.py", title="Tax Planner", icon=":material/calculate:", url_path="tax"),
    st.Page("views/copilot.py", title="AI Copilot", icon=":material/smart_toy:", url_path="copilot"),
    st.Page("views/reports.py", title="Reports", icon=":material/description:", url_path="reports"),
]
navigation = st.navigation(pages, position="top")
navigation.run()
footer(DISCLAIMER)
