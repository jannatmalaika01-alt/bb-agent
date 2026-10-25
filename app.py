import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/chat"
WELCOME = "Hi! I'm the Big Brains AI Support Agent. How can I help you today?"

st.set_page_config(page_title="Big Brains AI Support Agent", page_icon="🧠")

# Header
st.title("🧠 Big Brains AI Support Agent")
st.caption("Ask me about refunds, shipping, payments and more.")

# Chat history lives in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "agent", "text": WELCOME}]

# Sidebar
with st.sidebar:
    st.header("Big Brains Support")
    st.write("Powered by Gemini + FastAPI")
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = [{"role": "agent", "text": WELCOME}]
        st.rerun()

# Show history
for m in st.session_state.messages:
    role = "user" if m["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(m["text"])

# New message
if prompt := st.chat_input("Type your question..."):
    prior = st.session_state.messages[1:]  # skip welcome message
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    API_URL,
                    json={"message": prompt, "history": prior},
                    timeout=60,
                )
                if res.status_code == 200:
                    reply = res.json()["reply"]
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "agent", "text": reply})
                else:
                    detail = res.json().get("detail", "Server error")
                    st.error(f"Sorry, something went wrong: {detail}")
            except requests.exceptions.ConnectionError:
                st.error("Can't reach the backend. Is uvicorn running on port 8000?")
            except requests.exceptions.Timeout:
                st.error("The request timed out. Please try again.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")