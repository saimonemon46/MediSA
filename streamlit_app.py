# import streamlit as st
# import requests

# API_BASE = "http://localhost:8000"


# # ==================================================
# # API Helpers
# # ==================================================

# def start_session():
#     res = requests.post(f"{API_BASE}/start")
#     res.raise_for_status()
#     return res.json()


# def send_message(session_id, user_input):
#     payload = {
#         "session_id": session_id,
#         "user_input": user_input,
#     }
#     res = requests.post(f"{API_BASE}/chat", json=payload)
#     res.raise_for_status()
#     return res.json()


# # ==================================================
# # UI Helpers
# # ==================================================

# def render_messages():
#     for msg in st.session_state.messages:
#         role = msg["role"]
#         content = msg["content"]

#         if role == "agent":
#             st.chat_message("assistant").write(content)
#         elif role == "system":
#             st.chat_message("assistant").markdown(f"*{content}*")
#         else:
#             st.chat_message("assistant").write(content)


# # ==================================================
# # Session State
# # ==================================================

# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "session_id" not in st.session_state:
#     st.session_state.session_id = None

# if "awaiting_input" not in st.session_state:
#     st.session_state.awaiting_input = False

# if "done" not in st.session_state:
#     st.session_state.done = False


# # ==================================================
# # UI
# # ==================================================

# st.set_page_config(
#     page_title="Medical Triage Assistant",
#     layout="centered"
# )

# st.title("🩺 AI Medical Triage Assistant")


# # --------------------------------------------------
# # Start session (only once)
# # --------------------------------------------------

# if st.session_state.session_id is None:
#     with st.spinner("Starting triage session..."):
#         data = start_session()

#         st.session_state.session_id = data["session_id"]
#         st.session_state.awaiting_input = data["awaiting_input"]
#         st.session_state.messages.extend(data["messages"])


# # --------------------------------------------------
# # Render conversation (always)
# # --------------------------------------------------

# render_messages()


# # --------------------------------------------------
# # User input
# # --------------------------------------------------

# if not st.session_state.done and st.session_state.awaiting_input:
#     user_text = st.chat_input("Type your response")

#     if user_text:
#         # Show user message immediately
#         st.chat_message("user").write(user_text)

#         with st.spinner("Thinking..."):
#             data = send_message(
#                 st.session_state.session_id,
#                 user_text
#             )

#         # Update state strictly from backend
#         st.session_state.messages.extend(data["messages"])
#         st.session_state.awaiting_input = data["awaiting_input"]
#         st.session_state.done = data["done"]

#         # Force UI refresh so next question appears
#         st.rerun()


# # --------------------------------------------------
# # End state
# # --------------------------------------------------

# if st.session_state.done:
#     st.success("Triage session completed.")





import streamlit as st
import requests
from typing import Dict, Any, Optional

# ==================================================
# Configuration
# ==================================================

API_BASE_URL = "http://localhost:8000"  # Change to your API URL

st.set_page_config(
    page_title="AI Medical Triage",
    page_icon="🏥",
    layout="centered"
)

# ==================================================
# Helper Functions
# ==================================================

def start_session(initial_symptoms: str) -> Optional[Dict[str, Any]]:
    """Start a new triage session"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/start-session",
            json={"initial_symptoms": initial_symptoms}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error starting session: {str(e)}")
        return None

def submit_answer(session_id: str, answer: str) -> Optional[Dict[str, Any]]:
    """Submit an answer to the current question"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/answer",
            json={"session_id": session_id, "answer": answer}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error submitting answer: {str(e)}")
        return None

def want_doctor(session_id: str, wants: bool) -> Optional[Dict[str, Any]]:
    """Indicate whether user wants to see a doctor"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/want-doctor",
            json={"session_id": session_id, "want_doctor": wants}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def find_doctors(session_id: str, location: str) -> Optional[Dict[str, Any]]:
    """Find doctors based on location"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/find-doctors",
            json={"session_id": session_id, "location": location}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error finding doctors: {str(e)}")
        return None

# ==================================================
# Session State Initialization
# ==================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "stage" not in st.session_state:
    st.session_state.stage = "start"
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "triage_results" not in st.session_state:
    st.session_state.triage_results = None
if "current_question" not in st.session_state:
    st.session_state.current_question = None

# ==================================================
# UI Components
# ==================================================

def display_conversation():
    """Display the conversation history"""
    for msg in st.session_state.conversation:
        if msg["role"] == "agent":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])
        else:
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])

def display_triage_results(results: Dict[str, Any]):
    """Display triage assessment results"""
    st.divider()
    
    # Triage Reasoning
    if results.get("triage_reasoning"):
        st.subheader("📋 Triage Reasoning")
        for reason in results["triage_reasoning"]:
            st.write(f"• {reason}")
    
    # Triage Summary
    if results.get("triage_summary"):
        st.subheader("📊 Information Summary")
        cols = st.columns(4)
        summary = results["triage_summary"]
        items = list(summary.items())
        for idx, (key, value) in enumerate(items):
            with cols[idx % 4]:
                icon = "✓" if value else "✗"
                st.metric(key.replace("_", " ").title(), icon)
    
    # Confidence Score
    if results.get("confidence_score") is not None:
        st.subheader("🎯 Triage Confidence")
        score = results["confidence_score"]
        bucket = results.get("confidence_bucket", "Unknown")
        
        st.progress(score)
        st.write(f"**{bucket}** ({score:.1f})")
        st.caption("Reflects information completeness and internal consistency, not a diagnosis.")
    
    st.divider()

def display_doctors(doctors_data: Dict[str, Any]):
    """Display doctor recommendations"""
    st.subheader(f"👨‍⚕️ Recommended Doctors - {doctors_data['specialist_type']}")
    
    if not doctors_data["doctors"]:
        st.warning("No doctors found for the provided location.")
        return
    
    for doctor in doctors_data["doctors"]:
        with st.container():
            st.markdown(f"**{doctor.get('Doctor Name', 'N/A')}**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"🏥 **Speciality:** {doctor.get('Speciality', 'N/A')}")
                st.write(f"📍 **Chamber:** {doctor.get('Chamber', 'N/A')}")
            with col2:
                st.write(f"⏱️ **Experience:** {doctor.get('Experience', 'N/A')} years")
            st.divider()

# ==================================================
# Main App
# ==================================================

st.title("🏥 DOCTOR KOI...")
st.caption("Get preliminary health guidance based on your symptoms")

# Start Stage
if st.session_state.stage == "start":
    st.write("### Welcome! Let's understand your symptoms.")
    st.info("⚠️ **Disclaimer:** This is not a replacement for professional medical advice. For emergencies, call 999.")
    
    with st.form("initial_symptoms_form"):
        initial_symptoms = st.text_area(
            "What symptom are you currently experiencing?",
            placeholder="E.g., rash on my face, headache, chest pain...",
            height=100
        )
        submitted = st.form_submit_button("Start Triage", type="primary", use_container_width=True)
        
        if submitted and initial_symptoms.strip():
            # Start session
            result = start_session(initial_symptoms)
            
            if result:
                st.session_state.session_id = result["session_id"]
                st.session_state.stage = result["stage"]
                st.session_state.current_question = result.get("question")
                st.session_state.conversation.append({
                    "role": "user",
                    "content": initial_symptoms
                })
                if result.get("question"):
                    st.session_state.conversation.append({
                        "role": "agent",
                        "content": result["question"]
                    })
                st.rerun()

# Followup Stage
elif st.session_state.stage == "followup":
    display_conversation()
    
    with st.form("answer_form", clear_on_submit=True):
        answer = st.text_input(
            "Your answer:",
            placeholder="Type your response here...",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Submit", type="primary")
        
        if submitted and answer.strip():
            st.session_state.conversation.append({
                "role": "user",
                "content": answer
            })
            
            # Submit answer
            result = submit_answer(st.session_state.session_id, answer)
            
            if result:
                st.session_state.stage = result["stage"]
                
                if result["stage"] == "followup" and result.get("question"):
                    st.session_state.current_question = result["question"]
                    st.session_state.conversation.append({
                        "role": "agent",
                        "content": result["question"]
                    })
                elif result["stage"] in ["low_severity", "emergency"]:
                    st.session_state.triage_results = result
                
                st.rerun()

# Low Severity Stage
elif st.session_state.stage == "low_severity":
    display_conversation()
    
    results = st.session_state.triage_results
    display_triage_results(results)
    
    # Guidance
    if results.get("guidance"):
        st.subheader("💡 General Guidance")
        st.write(results["guidance"])
        st.divider()
    
    # Ask about doctor
    st.write("### Would you like to see a relevant doctor near you?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Yes, find doctors", type="primary", use_container_width=True):
            want_doctor(st.session_state.session_id, True)
            st.session_state.stage = "ask_location"
            st.rerun()
    
    with col2:
        if st.button("No, I'm done", use_container_width=True):
            want_doctor(st.session_state.session_id, False)
            st.session_state.stage = "complete"
            st.rerun()

# Emergency Stage
elif st.session_state.stage == "emergency":
    display_conversation()
    
    results = st.session_state.triage_results
    
    st.error("⚠️ **Your symptoms may indicate a serious condition.**")
    st.warning("This could require immediate medical attention.")
    
    display_triage_results(results)
    
    st.write("### Do you want to contact emergency services now?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Yes, show emergency number", type="primary", use_container_width=True):
            st.success("🚨 **Emergency number (Bangladesh): 999**")
            st.session_state.stage = "complete"
    
    with col2:
        if st.button("No, I'll seek care soon", use_container_width=True):
            st.info("Please seek medical care as soon as possible.")
            st.session_state.stage = "complete"

# Ask Location Stage
elif st.session_state.stage == "ask_location":
    display_conversation()
    
    with st.form("location_form"):
        st.write("### Please tell me your location")
        location = st.text_input(
            "City or area:",
            placeholder="E.g., Dhaka, Chittagong, Sylhet...",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Find Doctors", type="primary", use_container_width=True)
        
        if submitted and location.strip():
            with st.spinner("Finding doctors near you..."):
                result = find_doctors(st.session_state.session_id, location)
                
                if result:
                    st.session_state.doctors_data = result
                    st.session_state.stage = "show_doctors"
                    st.rerun()

# Show Doctors Stage
elif st.session_state.stage == "show_doctors":
    display_conversation()
    
    if st.session_state.get("doctors_data"):
        display_doctors(st.session_state.doctors_data)
    
    st.session_state.stage = "complete"
    st.success("✅ Triage session complete!")
    
    if st.button("Start New Session", type="primary", use_container_width=True):
        # Clear session
        st.session_state.clear()
        st.rerun()

# Complete Stage
elif st.session_state.stage == "complete":
    display_conversation()
    
    st.success("✅ Session ended. Thank you for using AI Medical Triage!")
    st.info("Remember to follow up with healthcare professionals for proper diagnosis and treatment.")
    
    if st.button("Start New Session", type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================================================
# Sidebar
# ==================================================

with st.sidebar:
    st.header("ℹ️ About")
    st.write("This AI triage assistant helps assess your symptoms and provides preliminary guidance.")
    
    st.warning("**Important:** This tool does NOT provide medical diagnosis. Always consult healthcare professionals.")
    
    if st.session_state.session_id:
        st.divider()
        st.write("**Session Active**")
        st.caption(f"ID: {st.session_state.session_id[:8]}...")
        
        if st.button("Reset Session", type="secondary"):
            st.session_state.clear()
            st.rerun()
    
    st.divider()
    st.caption("Emergency: 999 (Bangladesh)")
    st.caption("Health Care (24/7): 16263(BD)")