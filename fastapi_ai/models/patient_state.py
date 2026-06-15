# ============================================================
# MediAI — Patient State Management
# Structured patient memory system for conversation continuity
# ============================================================

from typing import TypedDict, List, Dict, Optional
from datetime import datetime
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for symptoms."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class SymptomEntry(TypedDict):
    """Structure for a recorded symptom."""
    name: str
    onset: Optional[str]  # e.g., "2 days ago", "sudden"
    severity: SeverityLevel
    duration: Optional[str]  # e.g., "3 days", "intermittent"
    frequency: Optional[str]  # e.g., "constant", "occasional"
    details: Optional[str]  # additional descriptive details
    mentioned_turn: int  # conversation turn when first mentioned


class RiskFactor(TypedDict):
    """Structure for recorded risk factors."""
    factor: str
    status: str  # e.g., "present", "absent", "unknown"
    details: Optional[str]
    mentioned_turn: int


class NegativeFinding(TypedDict):
    """Structure for symptoms/findings explicitly absent."""
    finding: str
    confirmation_turn: int  # when user confirmed absence


class MedicalHistory(TypedDict):
    """Structure for medical history items."""
    item: str
    type: str  # e.g., "condition", "allergy", "medication", "surgery"
    active: bool
    details: Optional[str]
    mentioned_turn: int


class ExposureHistory(TypedDict):
    """Structure for exposure history."""
    exposure: str
    type: str  # e.g., "covid", "illness_contact", "environmental"
    timing: Optional[str]  # e.g., "last week", "2 weeks ago"
    details: Optional[str]
    mentioned_turn: int


class DifferentialDiagnosis(TypedDict):
    """Structure for a ranked differential diagnosis."""
    condition: str
    confidence: float  # 0.0 to 1.0
    likelihood_category: str  # "high", "moderate", "low"
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    reasoning: str


class PatientState(TypedDict):
    """Comprehensive patient state for a conversation session."""
    session_id: str
    user_id: int
    
    # Core information
    primary_concern: Optional[str]
    chief_complaint: Optional[str]
    
    # Structured patient data
    symptoms: Dict[str, SymptomEntry]  # key: symptom name
    risk_factors: Dict[str, RiskFactor]  # key: risk factor name
    negative_findings: Dict[str, NegativeFinding]  # explicitly absent symptoms
    medical_history: Dict[str, MedicalHistory]  # past/current medical info
    exposure_history: Dict[str, ExposureHistory]  # known exposures
    
    # Information tracking
    asked_questions: List[str]  # questions already asked (to avoid repeats)
    answered_questions: Dict[str, str]  # question -> answer mapping
    information_gaps: List[str]  # critical missing information
    
    # Conversation metadata
    current_turn: int
    last_updated: str  # ISO format timestamp
    conversation_summary: Optional[str]
    
    # Diagnostic state
    preliminary_concerns: List[str]  # working hypotheses
    differential_diagnoses: List[DifferentialDiagnosis]
    confidence_level: float  # overall confidence in information collected
    
    # Flags
    requires_emergency_triage: bool
    red_flags_present: List[str]
    needs_clarification: bool


def create_empty_patient_state(session_id: str, user_id: int) -> PatientState:
    """Initialize an empty patient state."""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "primary_concern": None,
        "chief_complaint": None,
        "symptoms": {},
        "risk_factors": {},
        "negative_findings": {},
        "medical_history": {},
        "exposure_history": {},
        "asked_questions": [],
        "answered_questions": {},
        "information_gaps": [],
        "current_turn": 0,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "conversation_summary": None,
        "preliminary_concerns": [],
        "differential_diagnoses": [],
        "confidence_level": 0.0,
        "requires_emergency_triage": False,
        "red_flags_present": [],
        "needs_clarification": False,
    }


def has_question_been_asked(patient_state: PatientState, question: str) -> bool:
    """
    Check if a similar question has already been asked.
    Uses fuzzy matching on core question topics.
    """
    question_lower = question.lower()
    
    # Medical terms and their synonyms
    term_synonyms = {
        "fever": ["fever", "temperature", "hot", "heat", "high temp", "temp"],
        "cough": ["cough", "coughing", "mucus", "phlegm"],
        "covid": ["covid", "covid-19", "coronavirus", "sars-cov-2"],
        "duration": ["duration", "long", "how long", "since when", "when did", "started"],
        "severity": ["severe", "severity", "bad", "serious", "mild", "moderate", "scale", "1 to 10"],
        "onset": ["onset", "start", "started", "began", "suddenly", "gradual", "acute"],
        "medication": ["medication", "medicine", "drug", "taking", "treatment"],
        "allergy": ["allergy", "allergic", "allergies", "reaction"],
        "symptom": ["symptom", "symptoms", "signs", "problem", "issue", "condition"],
    }
    
    # Extract keywords from current question
    current_keywords = set()
    for synonym_group, terms in term_synonyms.items():
        for term in terms:
            if term in question_lower:
                current_keywords.add(synonym_group)
    
    # Check against previously asked questions
    for asked_q in patient_state["asked_questions"]:
        asked_q_lower = asked_q.lower()
        asked_keywords = set()
        
        for synonym_group, terms in term_synonyms.items():
            for term in terms:
                if term in asked_q_lower:
                    asked_keywords.add(synonym_group)
        
        # If there's significant overlap in keywords, consider it a repeat
        overlap = current_keywords & asked_keywords
        if overlap and len(overlap) >= 1:  # At least one matching keyword group
            return True
    
    return False


def get_known_symptoms_summary(patient_state: PatientState) -> str:
    """Generate a summary of known symptoms from patient state."""
    if not patient_state["symptoms"]:
        return "No symptoms recorded yet."
    
    symptom_list = []
    for symptom_name, symptom_data in patient_state["symptoms"].items():
        severity = symptom_data.get("severity", "unknown")
        duration = symptom_data.get("duration", "unknown duration")
        symptom_list.append(f"{symptom_name} ({severity}, {duration})")
    
    return ", ".join(symptom_list)


def get_known_risk_factors_summary(patient_state: PatientState) -> str:
    """Generate a summary of known risk factors."""
    if not patient_state["risk_factors"]:
        return "No risk factors recorded."
    
    present_factors = [
        name for name, data in patient_state["risk_factors"].items()
        if data.get("status") == "present"
    ]
    
    if not present_factors:
        return "No present risk factors."
    
    return ", ".join(present_factors)


def get_negative_findings_summary(patient_state: PatientState) -> str:
    """Generate a summary of negative findings."""
    if not patient_state["negative_findings"]:
        return "No negative findings recorded."
    
    finding_list = list(patient_state["negative_findings"].keys())
    return ", ".join(finding_list)
