
def next_missing_dimension(info_state: dict) -> str | None:
    for k, v in info_state.items():
        if v is None:
            return k
    return None
