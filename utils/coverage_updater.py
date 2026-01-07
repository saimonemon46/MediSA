def update_info_coverage(state: dict, user_input: str) -> None:
    """
    Update info_coverage flags based on the user's latest response.
    Uses transparent keyword heuristics (no ML, no LLM).
    """

    text = user_input.lower()
    coverage = state.get("info_coverage", {})

    # -------------------------
    # Duration
    # -------------------------
    if any(k in text for k in [
        "minute", "minutes", "min",
        "hour", "hours", "hr",
        "day", "days", "week", "weeks",
        "month", "months", "year", "years",
        "half", "ago", "since", "for",
        "today", "yesterday", "last night",
        "started", "began"
    ]):
        coverage["duration"] = True

    # -------------------------
    # Progression / change
    # -------------------------
    if any(k in text for k in [
        "change", "changed", "different",
        "worse", "worsening", "better", "improving",
        "same", "unchanged",
        "increasing", "decreasing",
        "spread", "spreading",
        "bigger", "larger", "smaller",
        "darker", "lighter", "color", "colour",
        "redder", "swollen", "inflamed"
    ]):
        coverage["progression"] = True

    # -------------------------
    # Severity / intensity
    # -------------------------
    if any(k in text for k in [
        "mild", "moderate", "severe",
        "intense", "bad",
        "pain", "hurting", "hurt",
        "burning", "throbbing",
        "scale", "out of", "/10", "rating", "rate"
    ]):
        coverage["severity"] = True

    # -------------------------
    # Red flags (presence, not screening)
    # -------------------------
    if not any(neg in text for neg in ["no ", "not ", "never "]):
        if any(k in text for k in [
            "shortness of breath", "difficulty breathing", "breathing problem",
            "chest pain", "tightness in chest",
            "faint", "fainted", "fainting",
            "unconscious", "collapse",
            "confusion", "seizure", "fits",
            "bleeding", "vomiting blood",
            "swelling", "swollen lips", "swollen tongue",
            "throat closing"
        ]):
            coverage["red_flags"] = True

    # -------------------------
    # Associated symptoms
    # -------------------------
    if any(k in text for k in [
        "also", "along with", "besides",
        "weak", "weakness", "nausea",
        "dizziness", "fever", "chills",
        "itching", "rash", "vomiting"
    ]):
        coverage["associated_symptoms"] = True

    state["info_coverage"] = coverage
