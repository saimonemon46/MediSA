# ==================================================
# Imports
# ==================================================

from langgraph.graph import StateGraph

from services.symptom_extractor import SymptomExtractor
from services.severity_engine import SeverityEngine
from services.question_generator import generate_followup
from services.guidance_generator import generate_guidance
from services.doctor_service import DoctorService
from services.confidence_engine import ConfidenceEngine
from services.info_state_updater import update_info_state
from services.disease_specialist_mapper import DiseaseSpecialistMapper

from agents.decision_agent import decide_next, doctor_decision

from utils.coverage_updater import update_info_coverage
from utils.followup_policy import next_missing_dimension
from utils.triage_reasoning import generate_triage_reasoning
from utils.confidence_bucket import confidence_bucket


# ==================================================
# Setup / Services
# ==================================================

extractor = SymptomExtractor()
severity_engine = SeverityEngine()
confidence_engine = ConfidenceEngine()
doctor_service = DoctorService()
_mapper = DiseaseSpecialistMapper()

MAX_FOLLOWUPS = 12


# ==================================================
# Nodes
# ==================================================

def opening_node(state):
    print("Agent: What symptom are you currently experiencing?")
    user_input = input("You: ")

    state["conversation_history"] = [user_input]
    state["collected_symptoms"] = extractor.extract(user_input)

    state["asked_questions"] = []
    state["followup_count"] = 0
    state["stop_flag"] = False

    state["info_state"] = {
        "onset": None,
        "duration": None,
        "progression": None,
        "sensation": None,
        "context": None,
        "associated_discomfort": None,
    }

    return state


# --------------------------------------------------

def followup_node(state):
    state["followup_count"] += 1

    # Hard stop
    if state["followup_count"] >= MAX_FOLLOWUPS:
        state["stop_flag"] = True
        return state

    # Update extracted info
    update_info_state(state)

    dimension = next_missing_dimension(state["info_state"])
    if dimension is None:
        state["stop_flag"] = True
        return state

    # Pre-lock dimension
    state["current_dimension"] = dimension
    state["info_state"][dimension] = True

    question = generate_followup(dimension, state)

    if question.strip() == "STOP":
        state["stop_flag"] = True
        return state

    if question in state["asked_questions"]:
        state["stop_flag"] = True
        return state

    state["asked_questions"].append(question)
    print("Agent:", question)

    user_input = input("You: ")
    state["conversation_history"].append(user_input)

    state["collected_symptoms"].extend(
        extractor.extract(user_input)
    )

    update_info_coverage(state, user_input)
    state["stop_flag"] = False

    return state


# --------------------------------------------------

def should_continue(state):
    if next_missing_dimension(state["info_state"]) is None:
        return "decide"
    return "followup"


# --------------------------------------------------

def severity_node(state):
    score, level = severity_engine.calculate(state["collected_symptoms"])

    state["severity_score"] = score
    state["severity_level"] = level
    state["confidence_score"] = confidence_engine.calculate(state)

    return state


# --------------------------------------------------

def low_severity_node(state):
    print("\nTriage reasoning:")
    for r in generate_triage_reasoning(state):
        print(f"- {r}")

    print("\nTriage summary:")
    for k, v in state["info_coverage"].items():
        print(f"- {k}: {'✓' if v else '✗'}")

    if state.get("confidence_score") is not None:
        score = state["confidence_score"]
        bucket = confidence_bucket(score)
        print(f"\nTriage confidence: {bucket} ({score})")
        print("(Reflects information completeness and internal consistency, not a diagnosis.)")

    print("\nAgent: Here is some general guidance based on what you shared:\n")
    print(generate_guidance(state))

    choice = input("\nAgent: Would you like to see a relevant doctor near you? (yes/no)\nYou: ")
    state["want_doctor"] = choice.lower().startswith("y")

    return state


# --------------------------------------------------

def emergency_node(state):
    print("\nTriage reasoning:")
    for r in generate_triage_reasoning(state):
        print(f"- {r}")

    print(
        "\nAgent: ⚠️ Your symptoms may indicate a serious condition.\n"
        "This could require immediate medical attention."
    )

    print("\nTriage summary:")
    for k, v in state["info_coverage"].items():
        print(f"- {k}: {'✓' if v else '✗'}")

    if state.get("confidence_score") is not None:
        score = state["confidence_score"]
        bucket = confidence_bucket(score)
        print(
            f"\nTriage confidence: {bucket} ({score})\n"
            "(Reflects information completeness and internal consistency, not a diagnosis.)"
        )

    choice = input("Agent: Do you want to contact emergency services now? (yes/no)\nYou: ")
    if choice.lower().startswith("y"):
        print("\nAgent: Emergency number (Bangladesh): 999")
    else:
        print("\nAgent: Please seek medical care as soon as possible.")

    return state


# --------------------------------------------------

def ask_location_node(state):
    state["user_location"] = input("\nAgent: Please tell me your location (city/area):\nYou: ")
    return state


# --------------------------------------------------

def doctor_lookup_node(state):
    location = state.get("user_location", "")
    symptoms = state.get("collected_symptoms", [])

    if not location:
        print("\nAgent: Location was not provided.")
        return state

    specialist = _mapper.infer_specialist(symptoms)

    results = doctor_service.find(
        location=location,
        specialty=specialist,
        limit=3
    )

    if results.empty:
        print(
            f"\nAgent: No {specialist} doctors found in {location}. "
            "Showing general medicine doctors instead.\n"
        )
        results = doctor_service.find(location, specialty="Medicine", limit=3)

        if results.empty:
            print("\nAgent: No doctors were found for the provided location.")
            return state

    print("\nAgent: Doctors you may consider:\n")
    for _, row in results.iterrows():
        print(f"- Doctor Name: {row['Doctor Name']}")
        print(f"  Speciality: {row['Speciality']}")
        print(f"  Experience: {row['Experience']} years")
        print(f"  Chamber: {row['Chamber']}\n")

    return state


# --------------------------------------------------

def end_node(state):
    return state


# ==================================================
# Graph Definition
# ==================================================

graph = StateGraph(dict)

graph.add_node("opening", opening_node)
graph.add_node("followup", followup_node)
graph.add_node("severity", severity_node)
graph.add_node("low", low_severity_node)
graph.add_node("emergency", emergency_node)
graph.add_node("ask_location", ask_location_node)
graph.add_node("doctor_lookup", doctor_lookup_node)
graph.add_node("end", end_node)

graph.set_entry_point("opening")

graph.add_edge("opening", "followup")

graph.add_conditional_edges(
    "followup",
    should_continue,
    {"followup": "followup", "decide": "severity"}
)

graph.add_conditional_edges(
    "severity",
    decide_next,
    {"continue": "followup", "low": "low", "emergency": "emergency"}
)

graph.add_conditional_edges(
    "low",
    doctor_decision,
    {"ask_location": "ask_location", "end": "end"}
)

graph.add_edge("ask_location", "doctor_lookup")
graph.add_edge("doctor_lookup", "end")
graph.add_edge("emergency", "end")

app = graph.compile()




























# # ==================================================
# # Imports
# # ==================================================

# # ==================================================
# # Imports
# # ==================================================

# from langgraph.graph import StateGraph

# from services.symptom_extractor import SymptomExtractor
# from services.severity_engine import SeverityEngine
# from services.question_generator import generate_followup
# from services.guidance_generator import generate_guidance
# from services.doctor_service import DoctorService
# from services.confidence_engine import ConfidenceEngine
# from services.info_state_updater import update_info_state
# from services.disease_specialist_mapper import DiseaseSpecialistMapper

# from agents.decision_agent import decide_next, doctor_decision

# from utils.coverage_updater import update_info_coverage
# from utils.followup_policy import next_missing_dimension
# from utils.triage_reasoning import generate_triage_reasoning
# from utils.confidence_bucket import confidence_bucket


# # ==================================================
# # Setup / Services
# # ==================================================

# # extractor = SymptomExtractor()
# # severity_engine = SeverityEngine()
# # confidence_engine = ConfidenceEngine()
# # doctor_service = DoctorService()
# # _mapper = DiseaseSpecialistMapper()

# MAX_FOLLOWUPS = 12


# # ==================================================
# # Helpers
# # ==================================================

# def say(state, role, message):
#     state.setdefault("ui_messages", []).append({
#         "role": role,
#         "content": message
#     })


# def get_user_input(state):
#     return state.pop("user_input", "").strip()


# def init_node(state):
#     state.setdefault("ui_messages", [])
#     state.setdefault("conversation_history", [])
#     state.setdefault("collected_symptoms", [])
#     state.setdefault("asked_questions", [])
#     state.setdefault("followup_count", 0)
#     state.setdefault("stop_flag", False)
#     state.setdefault("awaiting_input", False)
#     state.setdefault("info_state", {
#         "onset": None,
#         "duration": None,
#         "progression": None,
#         "sensation": None,
#         "context": None,
#         "associated_discomfort": None,
#     })
#     state.setdefault("info_coverage", {
#         "onset": False,
#         "duration": False,
#         "progression": False,
#         "sensation": False,
#         "context": False,
#         "associated_discomfort": False,
#     })
#     return state



# # ==================================================
# # Nodes
# # ==================================================

# def opening_node(state):
#     if state.get("opening_asked"):
#         return state

#     say(state, "agent", "What symptom are you currently experiencing?")
#     state["opening_asked"] = True

#     user_input = get_user_input(state)
#     if not user_input:
#         state["awaiting_input"] = True
#         return state

#     state["conversation_history"] = [user_input]
#     state["collected_symptoms"] = SymptomExtractor().extract(user_input)

#     state["asked_questions"] = []
#     state["followup_count"] = 0
#     state["stop_flag"] = False
#     state["awaiting_input"] = False

#     state["info_state"] = {
#         "onset": None,
#         "duration": None,
#         "progression": None,
#         "sensation": None,
#         "context": None,
#         "associated_discomfort": None,
#     }

#     return state



# # --------------------------------------------------

# def followup_node(state):
#     extractor = SymptomExtractor()
#     # 🚧 Guard against premature execution
#     if "info_state" not in state:
#         return state
#     state["followup_count"] += 1

#     if state["followup_count"] >= MAX_FOLLOWUPS:
#         state["stop_flag"] = True
#         return state

#     update_info_state(state)

#     dimension = next_missing_dimension(state["info_state"])
#     if dimension is None:
#         state["stop_flag"] = True
#         return state

#     state["current_dimension"] = dimension
#     state["info_state"][dimension] = True

#     question = generate_followup(dimension, state)

#     if question.strip() == "STOP" or question in state["asked_questions"]:
#         state["stop_flag"] = True
#         return state

#     state["asked_questions"].append(question)
#     say(state, "agent", question)

#     user_input = get_user_input(state)
#     if not user_input:
#         state["awaiting_input"] = True
#         return state

#     state["conversation_history"].append(user_input)
#     state["collected_symptoms"].extend(extractor.extract(user_input))

#     update_info_coverage(state, user_input)
#     state["awaiting_input"] = False
#     state["stop_flag"] = False

#     return state


# # --------------------------------------------------

# def should_continue(state):
#     # 🚧 Graph is waiting for first user input
#     if state.get("awaiting_input"):
#         return "followup"

#     # 🚧 Graph not initialized yet
#     if "info_state" not in state:
#         return "followup"

#     if next_missing_dimension(state["info_state"]) is None:
#         return "decide"

#     return "followup"



# # --------------------------------------------------

# def severity_node(state):
#     severity_engine = SeverityEngine()
#     confidence_engine = ConfidenceEngine()
#     score, level = severity_engine.calculate(state["collected_symptoms"])

#     state["severity_score"] = score
#     state["severity_level"] = level
#     state["confidence_score"] = confidence_engine.calculate(state)

#     return state


# # --------------------------------------------------

# def low_severity_node(state):
#     say(state, "agent", "Triage reasoning:")
#     for r in generate_triage_reasoning(state):
#         say(state, "system", f"- {r}")

#     say(state, "agent", "Triage summary:")
#     for k, v in state["info_coverage"].items():
#         say(state, "system", f"- {k}: {'✓' if v else '✗'}")

#     if state.get("confidence_score") is not None:
#         score = state["confidence_score"]
#         bucket = confidence_bucket(score)
#         say(
#             state,
#             "system",
#             f"Triage confidence: {bucket} ({score})"
#         )

#     say(state, "agent", generate_guidance(state))
#     say(state, "agent", "Would you like to see a relevant doctor near you? (yes/no)")

#     choice = get_user_input(state)
#     if not choice:
#         state["awaiting_input"] = True
#         return state

#     state["want_doctor"] = choice.lower().startswith("y")
#     state["awaiting_input"] = False

#     return state


# # --------------------------------------------------

# def emergency_node(state):
#     say(state, "agent", "⚠️ Your symptoms may indicate a serious condition.")
#     say(state, "agent", "This could require immediate medical attention.")

#     say(state, "agent", "Do you want to contact emergency services now? (yes/no)")

#     choice = get_user_input(state)
#     if not choice:
#         state["awaiting_input"] = True
#         return state

#     if choice.lower().startswith("y"):
#         say(state, "agent", "Emergency number (Bangladesh): 999")
#     else:
#         say(state, "agent", "Please seek medical care as soon as possible.")

#     state["awaiting_input"] = False
#     return state


# # --------------------------------------------------

# def ask_location_node(state):
#     say(state, "agent", "Please tell me your location (city/area):")

#     location = get_user_input(state)
#     if not location:
#         state["awaiting_input"] = True
#         return state

#     state["user_location"] = location
#     state["awaiting_input"] = False
#     return state


# # --------------------------------------------------

# def doctor_lookup_node(state):
#     _mapper = DiseaseSpecialistMapper()
#     doctor_service = DoctorService()
#     location = state.get("user_location", "")
#     symptoms = state.get("collected_symptoms", [])

#     if not location:
#         say(state, "agent", "Location was not provided.")
#         return state

#     specialist = _mapper.infer_specialist(symptoms)
#     results = doctor_service.find(location, specialty=specialist, limit=3)

#     if results.empty:
#         results = doctor_service.find(location, specialty="Medicine", limit=3)
#         if results.empty:
#             say(state, "agent", "No doctors found for the provided location.")
#             return state

#     say(state, "agent", "Doctors you may consider:")
#     for _, row in results.iterrows():
#         say(
#             state,
#             "system",
#             f"{row['Doctor Name']} | {row['Speciality']} | "
#             f"{row['Experience']} yrs | {row['Chamber']}"
#         )

#     return state


# # --------------------------------------------------

# def end_node(state):
#     state["done"] = True
#     return state


# # ==================================================
# # Graph Definition
# # ==================================================
# graph = StateGraph(dict)

# graph.add_node("init", init_node)
# graph.add_node("opening", opening_node)
# graph.add_node("followup", followup_node)
# graph.add_node("severity", severity_node)
# graph.add_node("low", low_severity_node)
# graph.add_node("emergency", emergency_node)
# graph.add_node("ask_location", ask_location_node)
# graph.add_node("doctor_lookup", doctor_lookup_node)
# graph.add_node("end", end_node)

# graph.set_entry_point("init")
# graph.add_edge("init", "opening")


# graph.add_edge("opening", "followup")

# graph.add_conditional_edges(
#     "followup",
#     should_continue,
#     {"followup": "followup", "decide": "severity"}
# )

# graph.add_conditional_edges(
#     "severity",
#     decide_next,
#     {"continue": "followup", "low": "low", "emergency": "emergency"}
# )

# graph.add_conditional_edges(
#     "low",
#     doctor_decision,
#     {"ask_location": "ask_location", "end": "end"}
# )

# graph.add_edge("ask_location", "doctor_lookup")
# graph.add_edge("doctor_lookup", "end")
# graph.add_edge("emergency", "end")

# app = graph.compile()
