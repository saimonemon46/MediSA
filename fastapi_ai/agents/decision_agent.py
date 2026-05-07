# def decide_next(state):
#     if state["severity_level"] == "high":
#         return "emergency"

#     if not state.get("stop_flag", False):
#         return "continue"

#     return "low"




# def doctor_decision(state):
#     return "ask_location" if state.get("want_doctor") else "end"



# agents/decision_agent.py

def decide_next(state):
    """
    Decide next step after severity calculation
    """
    if state.get("severity_level") == "high":
        return "emergency"

    return "low"


def doctor_decision(state):
    if state.get("want_doctor", False):
        return "ask_location"
    return "end"