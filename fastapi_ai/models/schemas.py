# MediAI — Pydantic Models
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SymptomRequest(BaseModel):
    symptom: str = Field(..., description="Primary symptom description from user")
    user_id: int = Field(..., description="User ID from PHP backend")


class ConversationalRequest(BaseModel):
    session_id: str
    message: str
    user_id: int
    chat_history: List[Dict[str, str]] = []
    patient_state: Optional[Dict[str, Any]] = None  # NEW: patient state


class ReportRequest(BaseModel):
    session_id: str
    symptom: str
    answers: List[str] = []
    user_id: int
    chat_history: List[Dict[str, str]] = []
    image_analysis: Optional[Dict[str, Any]] = None
    patient_state: Optional[Dict[str, Any]] = None  # NEW: patient state


class DocumentAnalysisRequest(BaseModel):
    document_id: int
    file_path: str


class DoctorRecommendationRequest(BaseModel):
    specialization: Optional[str] = ""
    location: Optional[str] = ""
    symptom: Optional[str] = ""
    possible_condition: Optional[str] = ""
    report_text: Optional[str] = ""
    urgency: Optional[str] = ""
    conversation: List[Any] = Field(default_factory=list)
    report: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = 0
    limit: int = Field(default=24, ge=1, le=60)


class Medication(BaseModel):
    name: str
    dosage: Optional[str] = ""
    frequency: Optional[str] = ""
    duration: Optional[str] = ""
    instructions: Optional[str] = ""


class TriageReport(BaseModel):
    session_id: str
    possible_condition: str
    urgency: str  # low | medium | high
    recommended_specialist: str
    reasoning: str
    guidance: str
    symptoms_listed: List[str] = []
    generated_at: str
    # NEW: differential diagnoses
    differential_diagnoses: Optional[List[Dict[str, Any]]] = None
    # NEW: conversation summary
    conversation_summary: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseModel):
    session_id: str
    questions: List[str]
    context_summary: Optional[str] = ""


class DocumentAnalysisResult(BaseModel):
    document_type: str
    document_summary: Optional[str] = ""
    medications: List[Medication] = []
    diagnoses: List[str] = []
    lab_results: List[Dict[str, Any]] = []
    abnormal_findings: List[str] = []
    red_flags: List[str] = []
    follow_up: Optional[str] = ""
    recommended_specialist: Optional[str] = ""
    notes: Optional[str] = ""
    raw_text: Optional[str] = ""


# NEW: Diagnostic result model
class DifferentialDiagnosis(BaseModel):
    rank: int
    condition: str
    confidence: float  # 0.0 to 1.0
    likelihood_category: str  # "high", "moderate", "low"
    supporting_evidence: List[str]
    contradicting_evidence: Optional[List[str]] = []
    requires_emergency: bool = False
    reasoning: str


class EnhancedTriageReport(BaseModel):
    """Extended report format with differential diagnosis and summaries."""
    session_id: str
    user_id: int
    
    # Basic triage info
    possible_condition: str
    urgency: str
    recommended_specialist: str
    
    # NEW: Differential diagnosis
    differential_diagnoses: List[DifferentialDiagnosis]
    overall_diagnosis_confidence: float
    
    # Evidence and reasoning
    reasoning: str
    guidance: str
    
    # NEW: Conversation summary
    conversation_summary: Optional[str]
    chief_complaint: Optional[str]
    symptoms_present: List[str]
    symptoms_absent: Optional[List[str]] = []
    risk_factors: Optional[List[str]] = []
    
    # Emergency assessment
    requires_emergency_referral: bool = False
    emergency_flags: Optional[List[str]] = []
    
    # Metadata
    generated_at: str
    image_analysis: Optional[Dict[str, Any]] = None

