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
