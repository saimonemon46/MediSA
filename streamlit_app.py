import streamlit as st
import requests

# ==================================================
# Config
# ==================================================

API_BASE = "http://localhost:8000"

# ==================================================
# Page setup
# ==================================================

st.set_page_config(page_title="DOCTOR KOI", layout="centered")

st.title("🩺 DOCTOR KOI")
st.caption("AI Medical Triage Assistant")

# ==================================================
# Session state init
# ==================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "chat" not in st.session_state:
    st.session_state.chat = []

if "done" not in st.session_state:
    st.session_state.done = False

# 🔑 input widget counter (CRITICAL FIX)
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ==================================================
# Start consultation
# ==================================================

if st.session_state.session_id is None:
    if st.button("Start Consultation"):
        res = requests.post(f"{API_BASE}/start")

        if res.ok:
            data = res.json()
            st.session_state.session_id = data["session_id"]

            msg = data.get("agent_message", "").strip()
            if msg:
                st.session_state.chat.append(("Agent", msg))
        else:
            st.error("Failed to start consultation.")

# ==================================================
# Chat history
# ==================================================

for speaker, message in st.session_state.chat:
    if speaker == "Agent" and message.strip():
        # st.markdown("**Agent:**")
        for line in message.split("\n"):
            if line.strip():
                st.markdown(line)
    elif speaker == "You":
        st.markdown(f"**You:** {message}")

# ==================================================
# User input (ONE turn at a time)
# ==================================================

if st.session_state.session_id and not st.session_state.done:

    user_text = st.text_input(
        "Your response",
        key=f"input_{st.session_state.input_key}",  # ✅ NEW KEY EACH TURN
        placeholder="Type your answer here..."
    )

    if st.button("Send"):
        if not user_text.strip():
            st.warning("Please type a response.")
        else:
            # show user message
            st.session_state.chat.append(("You", user_text))

            payload = {
                "session_id": st.session_state.session_id,
                "message": user_text
            }

            res = requests.post(f"{API_BASE}/continue", json=payload)

            if res.ok:
                data = res.json()
            msg = data.get("agent_message")

            if msg:
                st.session_state.chat.append(("Agent", msg))


                st.session_state.done = data.get("done", False)
            else:
                st.error("Backend error.")

            # 🔑 advance input key → forces empty input next render
            st.session_state.input_key += 1
            st.rerun()

# ==================================================
# End state
# ==================================================

if st.session_state.done:
    st.success("Session ended.")
