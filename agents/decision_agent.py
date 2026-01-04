def decide_next(state):
    # If high severity → emergency
    if state["severity_level"] == "high":
        return "emergency"

    # If questioning is not done → continue loop
    if not state.get("stop_flag", False):
        return "continue"

    # Questioning done + not high severity
    return "doctor"

