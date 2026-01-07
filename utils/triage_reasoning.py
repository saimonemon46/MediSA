def generate_triage_reasoning(state):
    reasons = []

    symptoms = state.get("collected_symptoms", [])
    if symptoms:
        reasons.append(f"Symptom reported: {', '.join(set(symptoms))}")

    # Duration
    if state["info_coverage"].get("duration"):
        reasons.append("Duration information provided")
    else:
        reasons.append("Duration information limited")

    # Progression
    if state["info_coverage"].get("progression"):
        reasons.append("No rapid or concerning progression reported")
    else:
        reasons.append("Progression information incomplete")

    # Red flags
    if state["info_coverage"].get("red_flags"):
        reasons.append("No critical red-flag symptoms reported")
    else:
        reasons.append("Red-flag symptoms not present")

    # Severity
    severity_level = state.get("severity_level")
    if severity_level:
        reasons.append(f"Overall severity assessed as {severity_level}")

    return reasons
