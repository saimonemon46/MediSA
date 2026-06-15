#!/usr/bin/env python
"""
Test file for MediSA Healthcare Triage Enhancements
Tests patient state tracking, memory management, and differential diagnosis ranking
"""
# -*- coding: utf-8 -*-

from fastapi_ai.models.patient_state import (
    create_empty_patient_state, has_question_been_asked,
    get_known_symptoms_summary, get_known_risk_factors_summary
)
from fastapi_ai.models.state_manager import PatientStateManager
from fastapi_ai.models.diagnostic_engine import DiagnosticRankingEngine


def test_patient_state_creation():
    """Test creating a new patient state."""
    print("\n=== Test 1: Patient State Creation ===")
    state = create_empty_patient_state("SESSION_001", user_id=123)
    assert state["session_id"] == "SESSION_001"
    assert state["user_id"] == 123
    assert state["symptoms"] == {}
    assert state["negative_findings"] == {}
    print("[PASS] Patient state created successfully")
    return state


def test_question_deduplication():
    """Test that questions are not repeated."""
    print("\n=== Test 2: Question Deduplication ===")
    state = create_empty_patient_state("SESSION_002", user_id=123)
    
    # Simulate asking a question about fever
    state["asked_questions"].append("Do you have a fever?")
    
    # Check if similar question would be asked
    similar_question = "Have you had a high temperature?"
    is_repeated = has_question_been_asked(state, similar_question)
    assert is_repeated, "Question deduplication failed"
    
    # Unrelated question should not be marked as repeat
    unrelated_question = "Do you have any allergies?"
    is_repeated = has_question_been_asked(state, unrelated_question)
    assert not is_repeated, "False positive in deduplication"
    
    print("[PASS] Question deduplication working correctly")


def test_state_management():
    """Test state manager operations."""
    print("\n=== Test 3: State Management ===")
    manager = PatientStateManager()
    
    # Create new state
    state = manager.initialize_state("SESSION_003", user_id=456)
    assert state["session_id"] == "SESSION_003"
    
    # Record questions
    state = manager.record_question(state, "Do you have a fever?")
    assert "Do you have a fever?" in state["asked_questions"]
    
    # Record Q&A
    state = manager.record_answer(state, "Do you have a fever?", "Yes, for 3 days")
    assert state["answered_questions"]["Do you have a fever?"] == "Yes, for 3 days"
    
    # Check readiness
    readiness = manager.get_conversation_readiness(state)
    assert "completeness_score" in readiness
    assert "is_ready_for_report" in readiness
    
    print("[PASS] State management operations working correctly")


def test_diagnostic_scoring():
    """Test diagnostic ranking engine."""
    print("\n=== Test 4: Diagnostic Ranking ===")
    engine = DiagnosticRankingEngine()
    
    # Simulate patient with COVID symptoms
    symptoms = {
        "fever": {"severity": "moderate", "onset": "3 days ago", "duration": "3 days"},
        "dry cough": {"severity": "moderate", "onset": "2 days ago", "duration": "2 days"},
        "fatigue": {"severity": "mild", "onset": "3 days ago", "duration": "3 days"},
    }
    
    negative_findings = {
        "shortness of breath": "confirmed absent",
    }
    
    risk_factors = {
        "workplace exposure": {"status": "present", "details": "COVID exposure at work"},
    }
    
    exposure_history = {
        "COVID exposure": {"type": "workplace", "timing": "last week"},
    }
    
    medical_history = {}
    
    preliminary = ["COVID-19", "Influenza", "Common Cold"]
    context = "COVID-19: respiratory infection with fever, cough, fatigue. Influenza: similar presentation."
    
    # Run scoring
    scores = engine.rank_diagnoses(
        symptoms,
        negative_findings,
        risk_factors,
        exposure_history,
        medical_history,
        preliminary,
        context
    )
    
    assert len(scores) > 0, "No diagnostic scores generated"
    
    # Check that top diagnosis is reasonable
    top_score = scores[0]
    print(f"\nTop Diagnosis: {top_score.condition}")
    print(f"  Overall Confidence: {top_score.overall_confidence:.2%}")
    print(f"  Matching Symptoms: {', '.join(top_score.matching_symptoms) if top_score.matching_symptoms else 'None'}")
    print(f"  Risk Factors: {', '.join(top_score.matching_risk_factors) if top_score.matching_risk_factors else 'None'}")
    
    # Print all rankings
    print("\nAll Rankings:")
    for i, score in enumerate(scores, 1):
        print(f"  {i}. {score.condition}: {score.overall_confidence:.2%}")
    
    # Verify that COVID is in top 3
    covid_names = [s.condition for s in scores[:3]]
    assert any("COVID" in name or "covid" in name.lower() for name in covid_names), \
        f"COVID-19 not in top 3: {covid_names}"
    
    print("[PASS] Diagnostic ranking working correctly")



def test_state_persistence():
    """Test converting state to/from dict."""
    print("\n=== Test 5: State Persistence ===")
    manager = PatientStateManager()
    
    # Create state with data
    state = manager.initialize_state("SESSION_005", 789)
    state["symptoms"]["fever"] = {
        "name": "fever",
        "onset": "2 days ago",
        "severity": "moderate",
        "duration": "2 days",
        "frequency": "continuous",
        "details": "High temperature",
        "mentioned_turn": 1
    }
    
    # Convert to dict
    state_dict = manager.to_dict(state)
    assert isinstance(state_dict, dict)
    assert state_dict["symptoms"]["fever"]["name"] == "fever"
    
    # Convert back from dict
    restored_state = manager.from_dict(state_dict)
    assert restored_state["symptoms"]["fever"]["severity"] == "moderate"
    
    print("[PASS] State persistence working correctly")


def test_symptom_summaries():
    """Test creating summaries from patient state."""
    print("\n=== Test 6: Symptom Summaries ===")
    state = create_empty_patient_state("SESSION_006", 999)
    
    # Add symptoms
    state["symptoms"]["fever"] = {
        "name": "fever",
        "onset": "3 days",
        "severity": "moderate",
        "duration": "3 days",
        "frequency": None,
        "details": None,
        "mentioned_turn": 1
    }
    state["symptoms"]["cough"] = {
        "name": "cough",
        "onset": "2 days",
        "severity": "mild",
        "duration": "2 days",
        "frequency": None,
        "details": None,
        "mentioned_turn": 2
    }
    
    # Test summaries
    symptoms_summary = get_known_symptoms_summary(state)
    assert "fever" in symptoms_summary
    assert "cough" in symptoms_summary
    assert "moderate" in symptoms_summary or "mild" in symptoms_summary
    
    print(f"Symptoms Summary: {symptoms_summary}")
    print("[PASS] Symptom summaries working correctly")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("MediSA Healthcare Triage - Enhancement Tests")
    print("="*60)
    
    try:
        test_patient_state_creation()
        test_question_deduplication()
        test_state_management()
        test_diagnostic_scoring()
        test_state_persistence()
        test_symptom_summaries()
        
        print("\n" + "="*60)
        print("[ALL TESTS PASSED]")
        print("="*60 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n[TEST FAILED]: {e}\n")
        return False
    except Exception as e:
        print(f"\n[ERROR]: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

