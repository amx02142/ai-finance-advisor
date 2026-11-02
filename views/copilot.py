"""AI Copilot: streaming chat grounded in the user's own financial data."""

import streamlit as st

from src import llm
from src.advisor import SUGGESTED_PROMPTS, stream_advisor
from src.state import current_ctx
from src.ui import page_header, source_pill

ctx = current_ctx()
page_header("AI Copilot", "Ask anything about your money - answers use your real numbers.")

st.session_state.setdefault("chat", [])
mode = "ai" if ctx.ai_on else "offline"
info_col, clear_col = st.columns([5, 1], vertical_alignment="center")
info_col.markdown(
    source_pill(mode, ctx.model if ctx.ai_on else None)
    + ('  <span class="muted">Statement data included in context</span>' if ctx.stmt_context else ""),
    unsafe_allow_html=True,
)
if clear_col.button("Clear chat", width="stretch", disabled=not st.session_state["chat"]):
    st.session_state["chat"] = []
    st.rerun()

if not ctx.ai_on:
    st.info("Gemini is not connected, so the copilot answers common topics offline. Add `GEMINI_API_KEY` to the "
            "project's `.env` file, save it and refresh the page for full AI answers.")

with st.expander("What the copilot can see"):
    st.code(ctx.full_context(), language="text")

pending = None
cols = st.columns(3)
for i, prompt in enumerate(SUGGESTED_PROMPTS):
    if cols[i % 3].button(prompt, key=f"sp_{i}", width="stretch"):
        pending = prompt

for msg in st.session_state["chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = pending or st.chat_input("Ask about budgeting, investing, loans, tax…")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        answer = st.write_stream(stream_advisor(
            question, ctx.profile, ctx.analysis, ctx.plan, history=st.session_state["chat"],
            api_key=ctx.key.key, extra_context=ctx.stmt_context, model=ctx.model))
        if ctx.ai_on and llm.LAST_MODEL:
            st.caption(f"Answered by {llm.LAST_MODEL}")
    st.session_state["chat"] += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
