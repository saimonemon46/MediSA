from langgraph.graph import StateGraph
from services.symptom_extractor import SymptomExtractor
from services.severity_engine import SeverityEngine
from services.question_generator import generate_followup
from agents.decision_agent import decide_next

extractor = SymptomExtractor()
severity_engine = SeverityEngine()

def followup_node(state):
    question = generate_followup(state)

    if question == "STOP":
        state["stop_flag"] = True
        return state

    print("Agent:", question)
    user_input = input("You: ")

    state["conversation_history"].append(user_input)
    state["collected_symptoms"] += extractor.extract(user_input)

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

def end_node(state):
    return state

graph = StateGraph(dict)

graph.add_node("followup", followup_node)
graph.add_node("severity", severity_node)
graph.add_node("end", end_node)

graph.set_entry_point("followup")

# After followup, ALWAYS go to severity
graph.add_edge("followup", "severity")

# After severity, either loop or end
graph.add_conditional_edges(
    "severity",
    decide_next,
    {
        "continue": "followup",   # keep asking
        "doctor": "end",
        "emergency": "end"
    }
)

app = graph.compile()
