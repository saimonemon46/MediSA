def next_missing_dimension(info_state: dict, *, allow_resolution=False) -> str | None:
    """
    Returns the next missing information dimension.
    If allow_resolution=True, prioritizes clarification
    for resolved / stopped symptoms.
    """

    # Phase 1: normal missing fields
    for key, value in info_state.items():
        if value is None:
            return key

    # Phase 2: handled elsewhere
    return None



def needs_resolution_clarification(state: dict) -> bool:
    """
    Detects whether the symptom resolved and needs clarification.
    """
    text = " ".join(state.get("conversation_history", [])).lower()

    return any(word in text for word in [
        "stopped", "gone", "resolved", "disappeared",
        "no longer", "went away"
    ])
