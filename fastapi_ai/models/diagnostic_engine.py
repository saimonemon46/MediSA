# ============================================================
# MediAI — Diagnostic Ranking Engine
# Differential diagnosis ranking with evidence scoring
# ============================================================

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class DiagnosticScore:
    """Detailed scoring breakdown for a condition."""
    condition: str
    
    # Score components (0.0 to 1.0)
    symptom_match_score: float  # how many symptoms match
    risk_factor_score: float  # how many risk factors are present
    negative_finding_score: float  # impact of absent findings
    severity_coherence: float  # how well severity patterns fit
    exposure_history_score: float  # relevance of exposures
    overall_confidence: float  # combined score
    
    # Evidence
    matching_symptoms: List[str]
    matching_risk_factors: List[str]
    supporting_findings: List[str]  # could include lab values, images
    contradicting_findings: List[str]
    reasoning: str


class DiagnosticRankingEngine:
    """
    Engine for ranking differential diagnoses based on:
    - Symptom matches (positive findings)
    - Risk factors
    - Negative findings (absence of expected symptoms)
    - Severity patterns
    - Exposure history
    - Medical history context
    """
    
    def __init__(self):
        """Initialize the diagnostic engine with scoring weights."""
        # Weighting for different evidence types
        self.weights = {
            "symptom_match": 0.40,      # Most important
            "risk_factor": 0.20,        # Secondary
            "negative_finding": 0.15,   # Rules out conditions
            "severity_coherence": 0.10,
            "exposure_history": 0.10,
            "medical_history": 0.05,
        }
    
    def rank_diagnoses(
        self,
        symptoms_present: Dict[str, dict],
        symptoms_absent: Dict[str, str],
        risk_factors: Dict[str, dict],
        exposure_history: Dict[str, dict],
        medical_history: Dict[str, dict],
        preliminary_conditions: List[str],
        retrieved_context: str
    ) -> List[DiagnosticScore]:
        """
        Rank provided conditions based on collected evidence.
        
        Args:
            symptoms_present: {symptom_name: {severity, onset, duration, ...}}
            symptoms_absent: {symptom_name: confirmation_context}
            risk_factors: {factor_name: {status, details, ...}}
            exposure_history: {exposure_name: {type, timing, ...}}
            medical_history: {history_item: {type, status, ...}}
            preliminary_conditions: List of conditions to rank
            retrieved_context: Medical knowledge context from RAG
        
        Returns:
            List of DiagnosticScore objects ranked by confidence
        """
        scores = []
        
        for condition in preliminary_conditions:
            score = self._score_condition(
                condition,
                symptoms_present,
                symptoms_absent,
                risk_factors,
                exposure_history,
                medical_history,
                retrieved_context
            )
            scores.append(score)
        
        # Sort by overall confidence descending
        scores.sort(key=lambda x: x.overall_confidence, reverse=True)
        return scores
    
    def _score_condition(
        self,
        condition: str,
        symptoms_present: Dict[str, dict],
        symptoms_absent: Dict[str, str],
        risk_factors: Dict[str, dict],
        exposure_history: Dict[str, dict],
        medical_history: Dict[str, dict],
        context: str
    ) -> DiagnosticScore:
        """Score a single condition against available evidence."""
        
        # Extract condition-specific knowledge from context
        condition_info = self._extract_condition_info(condition, context)
        
        # Calculate component scores
        symptom_match_score = self._score_symptoms(
            symptoms_present,
            condition_info.get("typical_symptoms", [])
        )
        
        negative_finding_score = self._score_negative_findings(
            symptoms_absent,
            condition_info.get("red_flags", [])
        )
        
        risk_factor_score = self._score_risk_factors(
            risk_factors,
            condition_info.get("risk_factors", [])
        )
        
        exposure_score = self._score_exposure(
            exposure_history,
            condition_info.get("known_exposures", [])
        )
        
        severity_coherence = self._score_severity_coherence(
            symptoms_present,
            condition_info.get("typical_severity", "moderate")
        )
        
        # Calculate weighted overall confidence
        overall_confidence = (
            symptom_match_score * self.weights["symptom_match"] +
            risk_factor_score * self.weights["risk_factor"] +
            negative_finding_score * self.weights["negative_finding"] +
            severity_coherence * self.weights["severity_coherence"] +
            exposure_score * self.weights["exposure_history"]
        )
        
        # Get supporting/contradicting evidence
        matching_symptoms = self._get_matching_symptoms(
            symptoms_present,
            condition_info.get("typical_symptoms", [])
        )
        
        matching_risk_factors = self._get_matching_risk_factors(
            risk_factors,
            condition_info.get("risk_factors", [])
        )
        
        contradicting = self._get_contradicting_findings(
            symptoms_absent,
            condition_info.get("red_flags", [])
        )
        
        reasoning = self._generate_reasoning(
            condition,
            symptom_match_score,
            risk_factor_score,
            negative_finding_score,
            matching_symptoms,
            contradicting
        )
        
        return DiagnosticScore(
            condition=condition,
            symptom_match_score=min(1.0, symptom_match_score),
            risk_factor_score=min(1.0, risk_factor_score),
            negative_finding_score=negative_finding_score,
            severity_coherence=severity_coherence,
            exposure_history_score=min(1.0, exposure_score),
            overall_confidence=min(1.0, overall_confidence),
            matching_symptoms=matching_symptoms,
            matching_risk_factors=matching_risk_factors,
            supporting_findings=matching_symptoms + matching_risk_factors,
            contradicting_findings=contradicting,
            reasoning=reasoning
        )
    
    def _extract_condition_info(self, condition: str, context: str) -> Dict:
        """
        Extract condition-specific information from retrieved context.
        This is a simplified implementation; in production, use structured data.
        """
        # Normalize condition name for matching
        cond_lower = condition.lower()
        context_lower = context.lower()
        
        # Default structure
        info = {
            "typical_symptoms": [],
            "red_flags": [],
            "risk_factors": [],
            "known_exposures": [],
            "typical_severity": "moderate"
        }
        
        # Simple heuristics based on condition
        if "covid" in cond_lower or "sars-cov-2" in cond_lower or "coronavirus" in cond_lower:
            info["typical_symptoms"] = ["fever", "cough", "fatigue", "loss of taste", "loss of smell", "body ache"]
            info["red_flags"] = ["shortness of breath", "chest pain", "confusion"]
            info["risk_factors"] = ["age", "immunocompromised", "chronic disease", "exposure", "workplace"]
            info["known_exposures"] = ["covid", "coronavirus", "exposure", "contact"]
            info["typical_severity"] = "mild"  # Most cases are mild to moderate
        
        elif "influenza" in cond_lower or "flu" in cond_lower:
            info["typical_symptoms"] = ["fever", "cough", "body aches", "fatigue", "sore throat", "muscle pain"]
            info["red_flags"] = ["shortness of breath", "chest pain"]
            info["risk_factors"] = ["age extremes", "chronic disease", "immunocompromised"]
            info["typical_severity"] = "moderate"
        
        elif "cold" in cond_lower or "uri" in cond_lower or "upper respiratory" in cond_lower:
            info["typical_symptoms"] = ["cough", "sore throat", "runny nose", "fatigue", "congestion"]
            info["red_flags"] = ["high fever", "severe shortness of breath"]
            info["risk_factors"] = []
            info["typical_severity"] = "mild"
        
        elif "pneumonia" in cond_lower:
            info["typical_symptoms"] = ["cough", "fever", "fatigue", "shortness of breath", "chest pain"]
            info["red_flags"] = ["severe shortness of breath", "chest pain", "confusion", "cyanosis"]
            info["risk_factors"] = ["age extremes", "smoking", "immunocompromised", "chronic disease"]
            info["typical_severity"] = "moderate"
        
        elif "allergic" in cond_lower or "allergy" in cond_lower:
            info["typical_symptoms"] = ["itching", "sneezing", "runny nose", "rash", "swelling", "watery eyes"]
            info["red_flags"] = ["difficulty breathing", "swelling of throat", "anaphylaxis"]
            info["risk_factors"] = ["previous allergies", "family history", "exposure"]
            info["typical_severity"] = "mild"
        
        return info
    
    def _score_symptoms(
        self,
        symptoms_present: Dict[str, dict],
        typical_symptoms: List[str]
    ) -> float:
        """Score how well present symptoms match typical symptoms for condition."""
        if not typical_symptoms:
            return 0.5  # Neutral score if no typical symptoms defined
        
        if not symptoms_present:
            return 0.0  # No symptoms means poor match
        
        symptom_names_present = [name.lower() for name in symptoms_present.keys()]
        typical_lower = [s.lower() for s in typical_symptoms]
        
        # Count exact matches and partial matches
        exact_matches = 0
        partial_matches = 0
        
        for symptom in symptom_names_present:
            if symptom in typical_lower:
                exact_matches += 1
            else:
                # Check for partial matches (e.g., "dry cough" matches "cough")
                for typical in typical_lower:
                    if typical in symptom or symptom in typical:
                        partial_matches += 1
                        break
        
        # Score based on matches
        total_matches = exact_matches + (partial_matches * 0.7)
        score = total_matches / len(typical_symptoms) if typical_symptoms else 0.0
        
        return min(1.0, score)

    
    def _score_risk_factors(
        self,
        risk_factors: Dict[str, dict],
        typical_risk_factors: List[str]
    ) -> float:
        """Score presence of relevant risk factors."""
        if not typical_risk_factors:
            return 0.5
        
        if not risk_factors:
            return 0.3  # No risk factors is not necessarily bad
        
        present_factors = [
            name.lower() for name, data in risk_factors.items()
            if data.get("status") == "present"
        ]
        
        typical_lower = [f.lower() for f in typical_risk_factors]
        matches = sum(1 for factor in present_factors if factor in typical_lower)
        
        score = matches / len(typical_risk_factors) if typical_risk_factors else 0.0
        return score
    
    def _score_negative_findings(
        self,
        symptoms_absent: Dict[str, str],
        red_flags: List[str]
    ) -> float:
        """
        Score based on absent findings.
        High score if expected red flags are absent (supports diagnosis).
        Low score if absence of key symptoms makes diagnosis unlikely.
        """
        if not symptoms_absent:
            return 0.5  # Neutral if we don't know what's absent
        
        red_flags_lower = [rf.lower() for rf in red_flags]
        absent_symptoms_lower = [s.lower() for s in symptoms_absent.keys()]
        
        # Red flags that are present (bad for diagnosis)
        present_red_flags = sum(
            1 for absent in absent_symptoms_lower
            if not any(rf in absent for rf in red_flags_lower)
        )
        
        if not red_flags:
            return 0.7
        
        # Higher score if red flags are absent
        absent_red_flags = sum(
            1 for rf in red_flags_lower if rf in absent_symptoms_lower
        )
        
        score = absent_red_flags / len(red_flags) if red_flags else 0.5
        return score
    
    def _score_exposure(
        self,
        exposure_history: Dict[str, dict],
        known_exposures: List[str]
    ) -> float:
        """Score based on relevant exposures."""
        if not known_exposures:
            return 0.5
        
        if not exposure_history:
            return 0.3  # No known exposures is neutral
        
        exposure_names = [name.lower() for name in exposure_history.keys()]
        known_lower = [e.lower() for e in known_exposures]
        
        matches = sum(1 for exposure in exposure_names if exposure in known_lower)
        score = matches / len(known_exposures) if known_exposures else 0.0
        
        return score
    
    def _score_severity_coherence(
        self,
        symptoms_present: Dict[str, dict],
        typical_severity: str
    ) -> float:
        """Score how well symptom severities match expected pattern."""
        if not symptoms_present:
            return 0.5
        
        severity_map = {"mild": 1, "moderate": 2, "severe": 3, "unknown": 2}
        typical_severity_val = severity_map.get(typical_severity.lower(), 2)
        
        # Calculate average severity of present symptoms
        severities = []
        for symptom_data in symptoms_present.values():
            sev = symptom_data.get("severity", "unknown")
            severities.append(severity_map.get(sev.lower(), 2))
        
        if not severities:
            return 0.5
        
        avg_severity = sum(severities) / len(severities)
        
        # Score based on how close average is to typical
        difference = abs(avg_severity - typical_severity_val)
        score = 1.0 - (difference / 3.0)  # Normalize to 0-1
        
        return max(0.0, score)
    
    def _get_matching_symptoms(
        self,
        symptoms_present: Dict[str, dict],
        typical_symptoms: List[str]
    ) -> List[str]:
        """Get list of symptoms that match typical symptoms for condition."""
        symptom_names = set(name.lower() for name in symptoms_present.keys())
        typical_lower = set(s.lower() for s in typical_symptoms)
        
        matches = symptom_names.intersection(typical_lower)
        return [s for s in symptoms_present.keys() if s.lower() in matches]
    
    def _get_matching_risk_factors(
        self,
        risk_factors: Dict[str, dict],
        typical_risk_factors: List[str]
    ) -> List[str]:
        """Get list of present risk factors that match typical ones."""
        present = [
            name for name, data in risk_factors.items()
            if data.get("status") == "present"
        ]
        
        typical_lower = set(rf.lower() for rf in typical_risk_factors)
        matches = [rf for rf in present if rf.lower() in typical_lower]
        
        return matches
    
    def _get_contradicting_findings(
        self,
        symptoms_absent: Dict[str, str],
        red_flags: List[str]
    ) -> List[str]:
        """Get list of findings that contradict the diagnosis."""
        if not red_flags or not symptoms_absent:
            return []
        
        red_flags_lower = set(rf.lower() for rf in red_flags)
        absent_lower = set(s.lower() for s in symptoms_absent.keys())
        
        # Contradicting findings: expected red flags that are NOT present
        contradicting = [
            s for s in symptoms_absent.keys()
            if s.lower() not in red_flags_lower
        ]
        
        return contradicting[:3]  # Top 3 contradicting
    
    def _generate_reasoning(
        self,
        condition: str,
        symptom_score: float,
        risk_score: float,
        negative_score: float,
        matching_symptoms: List[str],
        contradicting: List[str]
    ) -> str:
        """Generate reasoning text for diagnosis score."""
        reasons = []
        
        if symptom_score > 0.7:
            reason = f"Strong symptom match: {', '.join(matching_symptoms[:3])}"
            reasons.append(reason)
        elif symptom_score > 0.4:
            reason = f"Moderate symptom match: {', '.join(matching_symptoms[:2])}"
            reasons.append(reason)
        else:
            reasons.append("Limited symptom overlap with typical presentation")
        
        if risk_score > 0.6:
            reasons.append("Relevant risk factors identified")
        
        if contradicting:
            reasons.append(f"Absence of {', '.join(contradicting[:2])} is less typical")
        
        return " ".join(reasons)
