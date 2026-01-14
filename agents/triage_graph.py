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

# extractor = SymptomExtractor()
# severity_engine = SeverityEngine()
# confidence_engine = ConfidenceEngine()
# doctor_service = DoctorService()
# _mapper = DiseaseSpecialistMapper()

# MAX_FOLLOWUPS = 12


# # ==================================================
# # Nodes
# # ==================================================

# def opening_node(state):
#     print("Agent: What symptom are you currently experiencing?")
#     user_input = input("You: ")

#     state["conversation_history"] = [user_input]
#     state["collected_symptoms"] = extractor.extract(user_input)

#     state["asked_questions"] = []
#     state["followup_count"] = 0
#     state["stop_flag"] = False

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
#     state["followup_count"] += 1

#     # Hard stop
#     if state["followup_count"] >= MAX_FOLLOWUPS:
#         state["stop_flag"] = True
#         return state

#     # Update extracted info
#     update_info_state(state)

#     dimension = next_missing_dimension(state["info_state"])
#     if dimension is None:
#         state["stop_flag"] = True
#         return state

#     # Pre-lock dimension
#     state["current_dimension"] = dimension
#     state["info_state"][dimension] = True

#     question = generate_followup(dimension, state)

#     if question.strip() == "STOP":
#         state["stop_flag"] = True
#         return state

#     if question in state["asked_questions"]:
#         state["stop_flag"] = True
#         return state

#     state["asked_questions"].append(question)
#     print("Agent:", question)

#     user_input = input("You: ")
#     state["conversation_history"].append(user_input)

#     state["collected_symptoms"].extend(
#         extractor.extract(user_input)
#     )

#     update_info_coverage(state, user_input)
#     state["stop_flag"] = False

#     return state


# # --------------------------------------------------

# def should_continue(state):
#     if next_missing_dimension(state["info_state"]) is None:
#         return "decide"
#     return "followup"


# # --------------------------------------------------

# def severity_node(state):
#     score, level = severity_engine.calculate(state["collected_symptoms"])

#     state["severity_score"] = score
#     state["severity_level"] = level
#     state["confidence_score"] = confidence_engine.calculate(state)

#     return state


# # --------------------------------------------------

# def low_severity_node(state):
#     print("\nTriage reasoning:")
#     for r in generate_triage_reasoning(state):
#         print(f"- {r}")

#     print("\nTriage summary:")
#     for k, v in state["info_coverage"].items():
#         print(f"- {k}: {'✓' if v else '✗'}")

#     if state.get("confidence_score") is not None:
#         score = state["confidence_score"]
#         bucket = confidence_bucket(score)
#         print(f"\nTriage confidence: {bucket} ({score})")
#         print("(Reflects information completeness and internal consistency, not a diagnosis.)")

#     print("\nAgent: Here is some general guidance based on what you shared:\n")
#     print(generate_guidance(state))

#     choice = input("\nAgent: Would you like to see a relevant doctor near you? (yes/no)\nYou: ")
#     state["want_doctor"] = choice.lower().startswith("y")

#     return state


# # --------------------------------------------------

# def emergency_node(state):
#     print("\nTriage reasoning:")
#     for r in generate_triage_reasoning(state):
#         print(f"- {r}")

#     print(
#         "\nAgent: ⚠️ Your symptoms may indicate a serious condition.\n"
#         "This could require immediate medical attention."
#     )

#     print("\nTriage summary:")
#     for k, v in state["info_coverage"].items():
#         print(f"- {k}: {'✓' if v else '✗'}")

#     if state.get("confidence_score") is not None:
#         score = state["confidence_score"]
#         bucket = confidence_bucket(score)
#         print(
#             f"\nTriage confidence: {bucket} ({score})\n"
#             "(Reflects information completeness and internal consistency, not a diagnosis.)"
#         )

#     choice = input("Agent: Do you want to contact emergency services now? (yes/no)\nYou: ")
#     if choice.lower().startswith("y"):
#         print("\nAgent: Emergency number (Bangladesh): 999")
#     else:
#         print("\nAgent: Please seek medical care as soon as possible.")

#     return state


# # --------------------------------------------------

# def ask_location_node(state):
#     state["user_location"] = input("\nAgent: Please tell me your location (city/area):\nYou: ")
#     return state


# # --------------------------------------------------

# def doctor_lookup_node(state):
#     location = state.get("user_location", "")
#     symptoms = state.get("collected_symptoms", [])

#     if not location:
#         print("\nAgent: Location was not provided.")
#         return state

#     specialist = _mapper.infer_specialist(symptoms)

#     results = doctor_service.find(
#         location=location,
#         specialty=specialist,
#         limit=3
#     )

#     if results.empty:
#         print(
#             f"\nAgent: No {specialist} doctors found in {location}. "
#             "Showing general medicine doctors instead.\n"
#         )
#         results = doctor_service.find(location, specialty="Medicine", limit=3)

#         if results.empty:
#             print("\nAgent: No doctors were found for the provided location.")
#             return state

#     print("\nAgent: Doctors you may consider:\n")
#     for _, row in results.iterrows():
#         print(f"- Doctor Name: {row['Doctor Name']}")
#         print(f"  Speciality: {row['Speciality']}")
#         print(f"  Experience: {row['Experience']} years")
#         print(f"  Chamber: {row['Chamber']}\n")

#     return state


# # --------------------------------------------------

# def end_node(state):
#     return state


# # ==================================================
# # Graph Definition
# # ==================================================

# graph = StateGraph(dict)

# graph.add_node("opening", opening_node)
# graph.add_node("followup", followup_node)
# graph.add_node("severity", severity_node)
# graph.add_node("low", low_severity_node)
# graph.add_node("emergency", emergency_node)
# graph.add_node("ask_location", ask_location_node)
# graph.add_node("doctor_lookup", doctor_lookup_node)
# graph.add_node("end", end_node)

# graph.set_entry_point("opening")

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





# ==================================================
# Imports
# ==================================================

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
# State helpers
# ==================================================

def ensure_initialized(state):
    if state.get("_initialized"):
        return

    state["conversation_history"] = []
    state["collected_symptoms"] = []
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

    state["info_coverage"] = {
        "onset": False,
        "duration": False,
        "progression": False,
        "sensation": False,
        "context": False,
        "associated_discomfort": False,
    }

    # 🔴 NEW (critical)
    state["stage"] = "opening"
    state["awaiting_input"] = False


    state["_initialized"] = True



def consume_input(state):
    if "__user_input__" not in state:
        return None

    state["awaiting_input"] = False
    return state.pop("__user_input__")




# ==================================================
# Nodes
# ==================================================

def opening_node(state):
    ensure_initialized(state)

    # If opening already completed, skip entirely
    if state["stage"] != "opening":
        return state

    # Only ask when there is no user input yet
    if "__user_input__" not in state:
        print("Agent: What symptom are you currently experiencing?")
        return state

    # Consume user input
    user_input = consume_input(state)

    state["conversation_history"].append(user_input)
    state["collected_symptoms"].extend(extractor.extract(user_input))

    # Mark opening complete
    state["stage"] = "followup"

    return state



def followup_node(state):
    ensure_initialized(state)

    if state.get("stop_flag"):
        return state

    # 1️⃣ If user just answered, process input
    if "__user_input__" in state:
        user_input = consume_input(state)
        state["conversation_history"].append(user_input)
        state["collected_symptoms"].extend(extractor.extract(user_input))
        update_info_coverage(state, user_input)
        
            # ✅ MARK THE DIMENSION AS ANSWERED
        if state.get("current_dimension"):
            state["info_state"][state["current_dimension"]] = True

        state["awaiting_input"] = False  # allow progression

        # 🔴 CRITICAL FIX:
        # If all info is collected, STOP QA immediately
        if next_missing_dimension(state["info_state"]) is None:
            state["stop_flag"] = True
            return state

    # 2️⃣ If waiting for user input, do nothing
    if state.get("awaiting_input"):
        return state

    # 3️⃣ Safety: max followups
    if state["followup_count"] >= MAX_FOLLOWUPS:
        state["stop_flag"] = True
        return state

    # 4️⃣ Find next missing dimension
    dimension = next_missing_dimension(state["info_state"])
    if dimension is None:
        state["stop_flag"] = True
        return state

    # 5️⃣ Ask ONE question
    state["followup_count"] += 1
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

    # 6️⃣ Hard pause until next user response
    state["awaiting_input"] = True
    return state



# ==================================================
# Routing
# ==================================================

def should_continue(state):
    # Stop only if waiting for input AND no new input is present
    if state.get("awaiting_input") and "__user_input__" not in state:
        return "end"

    if state.get("stop_flag"):
        return "end"

    if next_missing_dimension(state["info_state"]) is None:
        return "decide"

    return "followup"




def severity_node(state):
    if state.get("stop_flag"):
        return state

    score, level = severity_engine.calculate(state["collected_symptoms"])

    state["severity_score"] = score
    state["severity_level"] = level
    state["confidence_score"] = confidence_engine.calculate(state)

    return state


# ==================================================
# Outcome nodes
# ==================================================

def low_severity_node(state):
    if state.get("stop_flag"):
        return state

    print("\nTriage reasoning:")
    for r in generate_triage_reasoning(state):
        print(f"- {r}")

    print("\nTriage summary:")
    for k, v in state["info_coverage"].items():
        print(f"- {k}: {'✓' if v else '✗'}")

    score = state.get("confidence_score")
    if score is not None:
        bucket = confidence_bucket(score)
        print(f"\nTriage confidence: {bucket} ({score})")
        print("(Reflects information completeness and internal consistency, not a diagnosis.)")

    print("\nAgent: Here is some general guidance based on what you shared:\n")
    print(generate_guidance(state))

    # Ask doctor question once
    if not state.get("awaiting_input"):
        print("\nAgent: Would you like to see a relevant doctor near you? (yes/no)")
        state["awaiting_input"] = True
        return state

    # Consume answer on next turn
    choice = consume_input(state)
    if choice is None:
        return state

    state["awaiting_input"] = False   # ✅ CRITICAL FIX
    state["want_doctor"] = choice.lower().startswith("y")
    return state


def emergency_node(state):
    if state.get("stop_flag"):
        return state

    print("\nTriage reasoning:")
    for r in generate_triage_reasoning(state):
        print(f"- {r}")

    print("Agent: ⚠️ This may require urgent care.")

    choice = consume_input(state)
    if choice is None:
        return state

    if choice.lower().startswith("y"):
        print("Emergency number (Bangladesh): 999")

    return state


def ask_location_node(state):
    print("\nAgent: Please tell me your location (city/area):")

    location = consume_input(state)
    if location is None:
        return state

    state["user_location"] = location
    return state


def doctor_lookup_node(state):
    location = state.get("user_location", "")
    symptoms = state.get("collected_symptoms", [])

    specialist = _mapper.infer_specialist(symptoms)

    results = doctor_service.find(location, specialty=specialist, limit=3)

    print("\nAgent: Doctors you may consider:\n")
    for _, row in results.iterrows():
        print(f"- {row['Doctor Name']} ({row['Speciality']})")

    return state


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

graph.add_conditional_edges(
    "opening",
    lambda state: "followup" if state["stage"] == "followup" else "end",
    {"followup": "followup", "end": "end"}
)


graph.add_conditional_edges(
    "followup",
    should_continue,
    {"followup": "followup", "decide": "severity", "end": "end"}
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
























# from langgraph.graph import StateGraph

# from services.symptom_extractor import SymptomExtractor
# from services.severity_engine import SeverityEngine
# from services.question_generator import generate_followup
# from services.guidance_generator import generate_guidance
# from services.confidence_engine import ConfidenceEngine

# from utils.followup_policy import next_missing_dimension
# from utils.triage_reasoning import generate_triage_reasoning


# # =====================
# # Setup
# # =====================

# extractor = SymptomExtractor()
# severity_engine = SeverityEngine()
# confidence_engine = ConfidenceEngine()

# MAX_FOLLOWUPS = 6


# # =====================
# # Helpers
# # =====================

# def consume_input(state):
#     text = state.get("user_input")
#     state["user_input"] = None
#     return text


# def normalize_state(state):
#     state.setdefault("conversation_history", [])
#     state.setdefault("collected_symptoms", [])
#     state.setdefault("followup_count", 0)
#     state.setdefault("awaiting_input", False)
#     state.setdefault("info_state", {
#         "onset": None,
#         "duration": None,
#         "progression": None,
#         "sensation": None,
#         "context": None,
#         "associated_discomfort": None,
#     })
#     return state


# # =====================
# # Nodes
# # =====================

# def opening_node(state):
#     state = normalize_state(state)

#     if state["conversation_history"]:
#         return state

#     user_input = consume_input(state)

#     if not user_input:
#         state["agent_message"] = "What symptom are you currently experiencing?"
#         state["awaiting_input"] = True
#         return state

#     state["conversation_history"].append(user_input)
#     state["collected_symptoms"] = extractor.extract(user_input)
#     state["awaiting_input"] = False
#     return state


# def followup_node(state):
#     state = normalize_state(state)

#     # 🚫 ABSOLUTE GUARD: no symptom → no followups
#     if not state["collected_symptoms"]:
#         state["agent_message"] = "Please describe your main symptom first."
#         state["awaiting_input"] = True
#         return state

#     if state["followup_count"] >= MAX_FOLLOWUPS:
#         return state

#     dimension = next_missing_dimension(state["info_state"])
#     if dimension is None:
#         return state

#     user_input = consume_input(state)

#     # =========================
#     # AGENT ASKS QUESTION
#     # =========================
#     if not user_input:
#         symptom = state["collected_symptoms"][0]  # SAFE NOW

#         question = generate_followup(dimension, state)

#         # Force symptom specificity
#         if "this symptom" in question.lower():
#             question = question.replace("this symptom", f"the {symptom}")

#         state["agent_message"] = question
#         state["awaiting_input"] = True
#         return state   # 🔒 HARD STOP

#     # =========================
#     # USER ANSWERED
#     # =========================
#     state["conversation_history"].append(user_input)
#     state["collected_symptoms"].extend(extractor.extract(user_input))
#     state["info_state"][dimension] = True

#     state["followup_count"] += 1
#     state["awaiting_input"] = False
#     return state



# def severity_node(state):
#     score, level = severity_engine.calculate(state["collected_symptoms"])
#     state["severity_level"] = level
#     state["confidence_score"] = confidence_engine.calculate(state)
#     return state


# def low_severity_node(state):
#     state["agent_payload"] = {
#         "type": "low",
#         "reasoning": generate_triage_reasoning(state),
#         "confidence": state["confidence_score"],
#         "guidance": generate_guidance(state),
#     }
#     return state


# def end_node(state):
#     return state


# # =====================
# # Routing
# # =====================

# def route_after_opening(state):
#     if state.get("awaiting_input"):
#         return "end"
#     return "followup"


# def route_after_followup(state):
#     if state.get("awaiting_input"):
#         return "end"

#     if (
#         next_missing_dimension(state["info_state"]) is None
#         or state["followup_count"] >= MAX_FOLLOWUPS
#     ):
#         return "severity"

#     return "followup"


# def route_after_severity(state):
#     return "low"


# # =====================
# # Graph
# # =====================

# graph = StateGraph(dict)

# graph.add_node("opening", opening_node)
# graph.add_node("followup", followup_node)
# graph.add_node("severity", severity_node)
# graph.add_node("low", low_severity_node)
# graph.add_node("end", end_node)

# graph.set_entry_point("opening")

# graph.add_conditional_edges(
#     "opening",
#     route_after_opening,
#     {"followup": "followup", "end": "end"}
# )

# graph.add_conditional_edges(
#     "followup",
#     route_after_followup,
#     {"followup": "followup", "severity": "severity", "end": "end"}
# )

# graph.add_conditional_edges(
#     "severity",
#     route_after_severity,
#     {"low": "low"}
# )

# graph.add_edge("low", "end")

# app = graph.compile()
