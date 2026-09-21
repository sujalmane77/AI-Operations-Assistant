"""
Streamlit chat frontend for the AI Operations Assistant.
Run the FastAPI backend first (uvicorn app.main:app --reload), then:
    streamlit run frontend/streamlit_app.py
"""
import uuid
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="AI Operations Assistant", page_icon="🤖", layout="wide")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of (role, content, trace)

st.title("🤖 AI Operations Assistant")
st.caption(f"Session: `{st.session_state.session_id}`")

with st.sidebar:
    st.header("Session")
    st.write(f"ID: `{st.session_state.session_id}`")
    if st.button("New session"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.chat_history = []
        st.rerun()

    if st.button("View full session log"):
        try:
            resp = requests.get(f"{API_BASE}/sessions/{st.session_state.session_id}/logs", timeout=10)
            resp.raise_for_status()
            logs = resp.json()
            st.subheader("Execution Log")
            if not logs:
                st.info("No logs yet for this session.")
            else:
                st.dataframe(logs, width="stretch")
        except Exception as e:
            st.error(f"Could not fetch logs: {e}")

for role, content, trace in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(content)
        if role == "assistant" and trace:
            with st.expander("Agent trace (retrieval, tool calls, reasoning)"):
                for step in trace:
                    st.json(step)

user_input = st.chat_input("Ask something operational...")

if user_input:
    st.session_state.chat_history.append(("user", user_input, None))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/chat",
                    json={"session_id": st.session_state.session_id, "message": user_input},
                    timeout=180,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["answer"]
                trace = data["steps"]
            except Exception as e:
                answer = f"Error contacting backend: {e}"
                trace = []

        st.markdown(answer)
        if trace:
            with st.expander("Agent trace (retrieval, tool calls, reasoning)"):
                for step in trace:
                    st.json(step)

    st.session_state.chat_history.append(("assistant", answer, trace))
