from langgraph.graph import StateGraph
from services.symptom_extractor import SymptomExtractor
from services.severity_engine import SeverityEngine
from services.question_generator import generate_followup
from agents.decision_agent import decide_next, doctor_decision
from services.guidance_generator import generate_guidance
from services.doctor_service import DoctorService
from services.confidence_engine import ConfidenceEngine
from utils.triage_reasoning import generate_triage_reasoning
from utils.confidence_bucket import confidence_bucket

from utils.coverage_updater import update_info_coverage
from services.info_state_updater import update_info_state
from utils.followup_policy import next_missing_dimension





# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

extractor = SymptomExtractor()
severity_engine = SeverityEngine()
confidence_engine = ConfidenceEngine()
doctor_service = DoctorService()

MAX_FOLLOWUPS = 6

# ------------------------------------------------------------------
# Nodes
# ------------------------------------------------------------------

def opening_node(state):
    print("Agent: What symptom are you currently experiencing?")
    user_input = input("You: ")

    state["conversation_history"] = [user_input]
    state["collected_symptoms"] = extractor.extract(user_input)
    state["asked_questions"] = []

    state["followup_count"] = 0
    state["stop_flag"] = False

    # ✅ Explicit information coverage
    state["info_state"] = {
        "onset": None,
        "duration": None,
        "progression": None,
        "sensation": None,
        "context": None,
        "associated_discomfort": None
    }


    return state


def followup_node(state):
    state["followup_count"] += 1

    # --------------------------------------------------
    # 1. Safety cap (hard stop)
    # --------------------------------------------------
    if state["followup_count"] >= MAX_FOLLOWUPS:
        state["stop_flag"] = True
        return state

    # --------------------------------------------------
    # 2. SYSTEM decides what is missing
    # --------------------------------------------------
    update_info_state(state)

    dimension = next_missing_dimension(state["info_state"])
    if dimension is None:
        state["stop_flag"] = True
        return state

    state["current_dimension"] = dimension
    state["info_state"][dimension] = True  # 🔒 PRE-LOCK DIMENSION


    question = generate_followup(dimension, state)


    # LLM should never control flow, but we guard anyway
    if question.strip() == "STOP":
        state["stop_flag"] = True
        return state

    # Absolute duplicate protection (last line of defense)
    if question in state["asked_questions"]:
        state["stop_flag"] = True
        return state

    state["asked_questions"].append(question)
    print("Agent:", question)

    # --------------------------------------------------
    # 4. User response
    # --------------------------------------------------
    user_input = input("You: ")
    state["conversation_history"].append(user_input)

    # --------------------------------------------------
    # 5. Update symptoms + coverage
    # --------------------------------------------------
    new_symptoms = extractor.extract(user_input)
    state["collected_symptoms"].extend(new_symptoms)

    update_info_coverage(state, user_input)

    state["stop_flag"] = False
    return state
    

from utils.followup_policy import next_missing_dimension

def should_continue(state):
    """
    Decide whether to continue follow-ups or move to severity decision.
    """

    if next_missing_dimension(state["info_state"]) is None:
        return "decide"

    return "followup"



def severity_node(state):
    score, level = severity_engine.calculate(state["collected_symptoms"])
    state["severity_score"] = score
    state["severity_level"] = level

    # Confidence now has real meaning
    state["confidence_score"] = confidence_engine.calculate(state)

    return state


def low_severity_node(state):
    # --------------------------------------------------
    # 1. Triage reasoning (NEW)
    # --------------------------------------------------
    reasoning = generate_triage_reasoning(state)

    print("\nTriage reasoning:")
    for r in reasoning:
        print(f"- {r}")

    # --------------------------------------------------
    # 2. Triage summary
    # --------------------------------------------------
    print("\nTriage summary:")
    for k, v in state["info_coverage"].items():
        print(f"- {k}: {'✓' if v else '✗'}")

    # --------------------------------------------------
    # 3. Confidence score
    # --------------------------------------------------
    # CONFIDENCE SCORE (with bucket)
    if state.get("confidence_score") is not None:
        score = state["confidence_score"]
        bucket = confidence_bucket(score)

        print(f"\nTriage confidence: {bucket} ({score})")
        print("(Reflects information completeness and internal consistency, not a diagnosis.)")


    # --------------------------------------------------
    # 4. Guidance (optional, non-diagnostic)
    # --------------------------------------------------
    guidance = generate_guidance(state)
    print("\nAgent: Here is some general guidance based on what you shared:\n")
    print(guidance)

    choice = input(
        "\nAgent: Would you like to see a relevant doctor near you? (yes/no)\nYou: "
    )

    state["want_doctor"] = choice.lower().startswith("y")
    return state


def emergency_node(state):
    # --------------------------------------------------
    # 1. TRIAGE REASONING (NEW)
    # --------------------------------------------------
    print("\nTriage reasoning:")
    for r in generate_triage_reasoning(state):
        print(f"- {r}")

    # --------------------------------------------------
    # 2. EMERGENCY WARNING
    # --------------------------------------------------
    print(
        "\nAgent: ⚠️ Your symptoms may indicate a serious condition.\n"
        "This could require immediate medical attention."
    )

    # --------------------------------------------------
    # 3. TRIAGE SUMMARY
    # --------------------------------------------------
    print("\nTriage summary:")
    for k, v in state["info_coverage"].items():
        print(f"- {k}: {'✓' if v else '✗'}")

    # --------------------------------------------------
    # 4. CONFIDENCE SCORE
    # --------------------------------------------------
    # CONFIDENCE SCORE (with bucket)
    if state.get("confidence_score") is not None:
        score = state["confidence_score"]
        bucket = confidence_bucket(score)

        print(
            f"\nTriage confidence: {bucket} ({score})\n"
            "(Reflects information completeness and internal consistency, not a diagnosis.)"
        )


    # --------------------------------------------------
    # 5. USER ACTION
    # --------------------------------------------------
    choice = input(
        "Agent: Do you want to contact emergency services now? (yes/no)\nYou: "
    )

    if choice.lower().startswith("y"):
        print("\nAgent: Emergency number (Bangladesh): 999")
    else:
        print("\nAgent: Please seek medical care as soon as possible.")

    return state



def ask_location_node(state):
    location = input("\nAgent: Please tell me your location (city/area):\nYou: ")
    state["user_location"] = location
    return state


def doctor_lookup_node(state):
    location = state.get("user_location", "")
    results = doctor_service.find(location, limit=3)

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


def end_node(state):
    return state

# ------------------------------------------------------------------
# Graph
# ------------------------------------------------------------------

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
    {
        "followup": "followup",
        "decide": "severity"
    }
)

graph.add_conditional_edges(
    "severity",
    decide_next,
    {
        "continue": "followup",
        "low": "low",
        "emergency": "emergency"
    }
)

graph.add_conditional_edges(
    "low",
    doctor_decision,
    {
        "ask_location": "ask_location",
        "end": "end"
    }
)

graph.add_edge("ask_location", "doctor_lookup")
graph.add_edge("doctor_lookup", "end")
graph.add_edge("emergency", "end")

app = graph.compile()
