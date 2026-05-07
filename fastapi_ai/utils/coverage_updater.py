def update_info_coverage(state: dict, user_input: str) -> None:
    text = user_input.lower()
    coverage = state.get("info_coverage", {})
    info_state = state.get("info_state", {})

    # -------------------------
    # Duration
    # -------------------------
    if any(k in text for k in [
        "minute", "minutes", "min",
        "hour", "hours", "hr",
        "day", "days", "week", "weeks",
        "month", "months", "year", "years",
        "ago", "since", "for"
    ]):
        coverage["duration"] = True
        info_state["duration"] = True   # 🔒 LOCK IT

    # -------------------------
    # Progression
    # -------------------------
    if any(k in text for k in [
        "change", "changed", "worse", "better",
        "same", "spreading", "darker", "lighter",
        "swollen", "inflamed"
    ]):
        coverage["progression"] = True
        info_state["progression"] = True  # 🔒 LOCK IT

    # -------------------------
    # Sensation
    # -------------------------
    if any(k in text for k in [
        "itch", "itching", "pain", "burning",
        "hurting", "throbbing"
    ]):
        coverage["sensation"] = True
        info_state["sensation"] = True  # 🔒 LOCK IT

    # -------------------------
    # Context (trigger/exposure)
    # -------------------------
    if any(k in text for k in [
        "soap", "cream", "medicine", "food",
        "after", "before", "used"
    ]):
        coverage["context"] = True
        info_state["context"] = True  # 🔒 LOCK IT

    # -------------------------
    # Associated discomfort
    # -------------------------
    if any(k in text for k in [
        "fever", "nausea", "dizziness",
        "swelling", "itching"
    ]):
        coverage["associated_discomfort"] = True
        info_state["associated_discomfort"] = True  # 🔒 LOCK IT

    # -------------------------
    # Red flags (unchanged)
    # -------------------------
    if not any(neg in text for neg in ["no ", "not ", "never "]):
        if any(k in text for k in [
            "shortness of breath", "difficulty breathing",
            "chest pain", "fainting",
            "unconscious", "bleeding"
        ]):
            coverage["red_flags"] = True

    state["info_coverage"] = coverage
    state["info_state"] = info_state
