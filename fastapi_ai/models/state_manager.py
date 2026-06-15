# ============================================================
# MediAI — State Management Module
# Manages patient state updates and question filtering
# ============================================================

from typing import Dict, List, Optional, Any
from fastapi_ai.models.patient_state import (
    PatientState, create_empty_patient_state, SymptomEntry,
    RiskFactor, NegativeFinding, MedicalHistory, ExposureHistory,
    DifferentialDiagnosis, has_question_been_asked
)
from fastapi_ai.models.llm_client import chat_json
from fastapi_ai.prompts.templates import (
    PATIENT_STATE_UPDATE_SYSTEM, PATIENT_STATE_UPDATE_USER,
    MISSING_INFO_ANALYSIS_SYSTEM, MISSING_INFO_ANALYSIS_USER
)
from datetime import datetime
import json


class PatientStateManager:
    """Manages patient state throughout a conversation session."""
    
    def __init__(self):
        """Initialize the state manager."""
        pass
    
    def initialize_state(self, session_id: str, user_id: int) -> PatientState:
        """Create a new patient state for a session."""
        return create_empty_patient_state(session_id, user_id)
    
    def update_state_from_message(
        self,
        patient_state: PatientState,
        user_message: str,
        last_question_asked: Optional[str] = None,
        turn_number: int = 1
    ) -> PatientState:
        """
        Update patient state based on user message.
        Extract symptoms, risk factors, negative findings, etc.
        """
        # Format previous state for LLM
        previous_state_str = self._format_state_for_llm(patient_state)
        
        # Call LLM to extract and update state
        prompt_user = PATIENT_STATE_UPDATE_USER.format(
            previous_state=previous_state_str,
            user_message=user_message,
            last_question=last_question_asked or "N/A"
        )
        
        try:
            result = chat_json(PATIENT_STATE_UPDATE_SYSTEM, prompt_user)
        except Exception as e:
            print(f"Error updating patient state: {e}")
            return patient_state
        
        # Process extracted information
        patient_state = self._integrate_extracted_info(patient_state, result, turn_number)
        
        # Update metadata
        patient_state["current_turn"] = turn_number
        patient_state["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        return patient_state
    
    def _format_state_for_llm(self, patient_state: PatientState) -> str:
        """Format patient state for LLM consumption."""
        lines = []
        
        lines.append("KNOWN INFORMATION:")
        
        if patient_state["primary_concern"]:
            lines.append(f"- Primary Concern: {patient_state['primary_concern']}")
        
        if patient_state["symptoms"]:
            lines.append("- Symptoms:")
            for symptom_name, data in patient_state["symptoms"].items():
                severity = data.get("severity", "unknown")
                onset = data.get("onset", "unknown")
                lines.append(f"  • {symptom_name}: {severity} severity, onset {onset}")
        
        if patient_state["risk_factors"]:
            present_factors = [
                name for name, data in patient_state["risk_factors"].items()
                if data.get("status") == "present"
            ]
            if present_factors:
                lines.append(f"- Risk Factors Present: {', '.join(present_factors)}")
        
        if patient_state["negative_findings"]:
            lines.append(f"- Symptoms NOT Present: {', '.join(patient_state['negative_findings'].keys())}")
        
        if patient_state["medical_history"]:
            lines.append("- Medical History:")
            for item_name, data in patient_state["medical_history"].items():
                status = "active" if data.get("active") else "past"
                lines.append(f"  • {item_name} ({status})")
        
        if patient_state["exposure_history"]:
            lines.append("- Known Exposures:")
            for exposure_name, data in patient_state["exposure_history"].items():
                timing = data.get("timing", "unknown timing")
                lines.append(f"  • {exposure_name}: {timing}")
        
        if patient_state["asked_questions"]:
            lines.append(f"- Questions Already Asked: {len(patient_state['asked_questions'])}")
        
        if not lines or len(lines) == 1:
            return "No patient information recorded yet."
        
        return "\n".join(lines)
    
    def _integrate_extracted_info(
        self,
        patient_state: PatientState,
        extracted: Dict[str, Any],
        turn_number: int
    ) -> PatientState:
        """Integrate extracted information into patient state."""
        
        # Add new symptoms
        for symptom_info in extracted.get("new_symptoms", []):
            symptom_name = symptom_info.get("name")
            if symptom_name:
                patient_state["symptoms"][symptom_name] = {
                    "name": symptom_name,
                    "onset": symptom_info.get("onset"),
                    "severity": symptom_info.get("severity", "unknown"),
                    "duration": symptom_info.get("duration"),
                    "frequency": symptom_info.get("frequency"),
                    "details": symptom_info.get("details"),
                    "mentioned_turn": turn_number
                }
        
        # Add new risk factors
        for rf_info in extracted.get("new_risk_factors", []):
            factor_name = rf_info.get("factor")
            if factor_name:
                patient_state["risk_factors"][factor_name] = {
                    "factor": factor_name,
                    "status": rf_info.get("status", "unknown"),
                    "details": rf_info.get("details"),
                    "mentioned_turn": turn_number
                }
        
        # Add negative findings
        for finding in extracted.get("negative_findings", []):
            if finding:
                patient_state["negative_findings"][finding] = {
                    "finding": finding,
                    "confirmation_turn": turn_number
                }
        
        # Add medical history items
        for hist_info in extracted.get("medical_history_items", []):
            item_name = hist_info.get("item")
            if item_name:
                patient_state["medical_history"][item_name] = {
                    "item": item_name,
                    "type": hist_info.get("type", "condition"),
                    "active": hist_info.get("active", False),
                    "details": hist_info.get("details"),
                    "mentioned_turn": turn_number
                }
        
        # Add exposure history
        for exp_info in extracted.get("exposure_history", []):
            exp_name = exp_info.get("exposure")
            if exp_name:
                patient_state["exposure_history"][exp_name] = {
                    "exposure": exp_name,
                    "type": exp_info.get("type", "other"),
                    "timing": exp_info.get("timing"),
                    "details": exp_info.get("details"),
                    "mentioned_turn": turn_number
                }
        
        # Check for red flags
        red_flags = extracted.get("red_flags", [])
        if red_flags:
            patient_state["red_flags_present"].extend(red_flags)
            patient_state["requires_emergency_triage"] = True
        
        # Check for contradictions
        contradictions = extracted.get("contradictions", [])
        if contradictions:
            patient_state["needs_clarification"] = True
        
        return patient_state
    
    def filter_questions(
        self,
        questions: List[str],
        patient_state: PatientState
    ) -> List[str]:
        """
        Filter out questions that have already been asked or are redundant.
        """
        filtered = []
        
        for question in questions:
            if not has_question_been_asked(patient_state, question):
                filtered.append(question)
        
        # If all questions were filtered, keep at least the first one
        if not filtered and questions:
            filtered = [questions[0]]
        
        # Ensure we always have questions to ask
        if not filtered:
            filtered = ["Do you have any other symptoms or concerns I should know about?"]
        
        return filtered[:6]  # Keep max 6 questions
    
    def get_missing_info(
        self,
        patient_state: PatientState,
        retrieved_context: str,
        preliminary_conditions: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze what critical information is still missing.
        """
        state_summary = self._format_state_for_llm(patient_state)
        
        conditions_str = ", ".join(preliminary_conditions[:3])
        
        prompt_user = MISSING_INFO_ANALYSIS_USER.format(
            patient_state_summary=state_summary,
            medical_context=retrieved_context[:1000],
            preliminary_conditions=conditions_str
        )
        
        try:
            result = chat_json(MISSING_INFO_ANALYSIS_SYSTEM, prompt_user)
            return result
        except Exception as e:
            print(f"Error analyzing missing info: {e}")
            return {
                "critical_missing_info": "Additional medical history",
                "priority": "YELLOW",
                "why_needed": "Help narrow down diagnosis",
                "suggested_question_focus": "medical history",
                "confidence_level": 0.5
            }
    
    def record_question(
        self,
        patient_state: PatientState,
        question: str
    ) -> PatientState:
        """Record a question that was asked to the user."""
        if question not in patient_state["asked_questions"]:
            patient_state["asked_questions"].append(question)
        return patient_state
    
    def record_answer(
        self,
        patient_state: PatientState,
        question: str,
        answer: str
    ) -> PatientState:
        """Record a Q&A pair."""
        patient_state["answered_questions"][question] = answer
        return patient_state
    
    def get_conversation_readiness(self, patient_state: PatientState) -> Dict[str, Any]:
        """
        Assess if we have enough information for report generation.
        """
        # Calculate information completeness score
        score = 0.0
        max_score = 5.0
        
        # Symptom information (0-1)
        if patient_state["symptoms"]:
            symptom_detail = sum(
                len([v for v in s.values() if v]) for s in patient_state["symptoms"].values()
            )
            score += min(1.0, symptom_detail / 10.0)
        
        # Risk factors (0-0.5)
        if patient_state["risk_factors"]:
            score += min(0.5, len(patient_state["risk_factors"]) / 5.0)
        
        # Medical history (0-0.5)
        if patient_state["medical_history"]:
            score += min(0.5, len(patient_state["medical_history"]) / 5.0)
        
        # Negative findings (0-1)
        if patient_state["negative_findings"]:
            score += min(1.0, len(patient_state["negative_findings"]) / 5.0)
        
        # Exposure history (0-1)
        if patient_state["exposure_history"]:
            score += min(1.0, len(patient_state["exposure_history"]) / 3.0)
        
        normalized_score = min(1.0, score / max_score)
        
        is_ready = (
            normalized_score > 0.6 or
            len(patient_state["asked_questions"]) >= 6
        )
        
        return {
            "completeness_score": normalized_score,
            "is_ready_for_report": is_ready,
            "information_count": (
                len(patient_state["symptoms"]) +
                len(patient_state["risk_factors"]) +
                len(patient_state["medical_history"])
            ),
            "questions_asked": len(patient_state["asked_questions"])
        }
    
    def to_dict(self, patient_state: PatientState) -> Dict[str, Any]:
        """Convert patient state to dictionary for transmission."""
        return dict(patient_state)
    
    def from_dict(self, data: Dict[str, Any]) -> PatientState:
        """Reconstruct patient state from dictionary."""
        # Ensure all required fields exist
        state = create_empty_patient_state(
            data.get("session_id", ""),
            data.get("user_id", 0)
        )
        state.update(data)
        return state
