COVERAGE_PRIORITY = [
    "red_flags",
    "duration",
    "progression",
    "severity",
    "associated_symptoms"
]
def next_missing_coverage(info_coverage: dict) -> str | None:
    """
    Returns the highest-priority missing coverage key,
    or None if all coverage is complete.
    """
    for key in COVERAGE_PRIORITY:
        if not info_coverage.get(key, False):
            return key
    return None
