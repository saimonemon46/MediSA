class ConfidenceEngine:
    def calculate(self, state: dict) -> float:

        # -------------------------------
        # 1. Symptom coverage
        # -------------------------------
        symptom_count = len(set(state.get("collected_symptoms", [])))
        if symptom_count == 0:
            symptom_score = 0.0
        elif symptom_count == 1:
            symptom_score = 0.6
        else:
            symptom_score = 1.0

        # -------------------------------
        # 2. Follow-up adequacy
        # -------------------------------
        followups = state.get("followup_count", 0)
        if followups <= 1:
            followup_score = 0.4
        elif followups <= 3:
            followup_score = 0.7
        else:
            followup_score = 1.0

        # -------------------------------
        # 3. Severity clarity
        # -------------------------------
        severity_score = 1.0 if state.get("severity_level") else 0.0

        # -------------------------------
        # 4. Consistency check
        # -------------------------------
        consistency_score = 1.0
        if state.get("severity_level") == "high" and followups < 2:
            consistency_score = 0.6

        # -------------------------------
        # 5. Raw confidence
        # -------------------------------
        raw_confidence = (
            symptom_score * 0.4 +
            followup_score * 0.3 +
            severity_score * 0.2 +
            consistency_score * 0.1
        )

        # -------------------------------
        # 6. Information coverage cap
        # -------------------------------
        coverage = state.get("info_coverage", {})
        if not coverage:
            return round(raw_confidence * 0.5, 2)

        coverage_ratio = sum(1 for v in coverage.values() if v) / len(coverage)

        final_confidence = min(raw_confidence, coverage_ratio)
        return round(final_confidence, 2)
