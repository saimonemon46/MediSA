def decide_next(state):
    if state["severity_level"] == "high":
        return "emergency"

    if not state.get("stop_flag", False):
        return "continue"

    return "low"
