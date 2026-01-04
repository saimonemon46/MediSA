from langgraph.graph import StateGraph
from services.symptom_extractor import SymptomExtractor
from services.severity_engine import SeverityEngine
from services.question_generator import generate_followup
from agents.decision_agent import decide_next
from services.guidance_generator import generate_guidance

extractor = SymptomExtractor()
severity_engine = SeverityEngine()

MAX_FOLLOWUPS = 6

def followup_node(state):
    # increment follow-up count
    state["followup_count"] += 1

    # hard cap to prevent infinite loops
    if state["followup_count"] >= MAX_FOLLOWUPS:
        state["stop_flag"] = True
        return state

    question = generate_followup(state)

    # LLM says stop
    if question == "STOP":
        state["stop_flag"] = True
        return state

    print("Agent:", question)
    user_input = input("You: ")

    state["conversation_history"].append(user_input)

    # extract symptoms but DO NOT use this to stop
    new_symptoms = extractor.extract(user_input)
    state["collected_symptoms"].extend(new_symptoms)

    state["stop_flag"] = False
    return state


def opening_node(state):
    print("Agent: What symptom are you currently experiencing?")
    user_input = input("You: ")

    state["conversation_history"].append(user_input)
    state["collected_symptoms"] = extractor.extract(user_input)

    # Reset counters after symptom seed
    state["followup_count"] = 0
    state["last_symptom_count"] = len(state["collected_symptoms"])
    state["stop_flag"] = False

    return state


def should_continue(state):
    # If LLM explicitly said STOP → go to severity decision
    if state.get("stop_flag"):
        return "decide"

    # Otherwise keep asking follow-ups
    return "followup"

def severity_node(state):
    score, level = severity_engine.calculate(state["collected_symptoms"])
    state["severity_score"] = score
    state["severity_level"] = level
    return state



def low_severity_node(state):
    guidance = generate_guidance(state)
    print("\nAgent:", guidance)

    choice = input(
        "\nAgent: Would you like to see a relevant doctor near you? (yes/no)\nYou: "
    )

    state["want_doctor"] = choice.lower().startswith("y")
    return state



def emergency_node(state):
    print(
        "\nAgent: ⚠️ Your symptoms may indicate a serious condition.\n"
        "This could require immediate medical attention."
    )

    choice = input(
        "Agent: Do you want to contact emergency services now? (yes/no)\nYou: "
    )

    if choice.lower().startswith("y"):
        print("\nAgent: Emergency number (Bangladesh): 999")
        print("Please seek immediate medical help.")
    else:
        print("\nAgent: Understood. Please seek medical care as soon as possible.")

    return state




def end_node(state):
    return state

graph = StateGraph(dict)

graph.add_node("opening", opening_node)
graph.add_node("followup", followup_node)
graph.add_node("severity", severity_node)
graph.add_node("low", low_severity_node)
graph.add_node("emergency", emergency_node)
graph.add_node("end", end_node)


graph.set_entry_point("opening")


# After followup, ALWAYS go to severity
graph.add_edge("opening", "followup")
graph.add_edge("followup", "severity")

# After severity, either loop or end
graph.add_conditional_edges(
    "severity",
    decide_next,
    {
        "continue": "followup",
        "low": "low",
        "emergency": "emergency"
    }
)

graph.add_edge("low", "end")
graph.add_edge("emergency", "end")

app = graph.compile()
