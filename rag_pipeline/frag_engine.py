"""High-level FRAG orchestration for MediSA.

The engine supports the thesis pipeline:
symptoms -> independent hospital retrieval -> fusion -> consolidated context
-> LLM diagnosis -> cross-hospital doctor recommendation.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from rag_pipeline.federated_retriever import retrieve_federated
from rag_pipeline.hospital_loader import DoctorRecord, doctor_search_text, hospital_statistics, load_all_doctors
from rag_pipeline.hospital_partition import canonical_specialty, normalise_text
from rag_pipeline.reranker import lexical_similarity



DIAGNOSIS_SYSTEM_PROMPT = """You are MediSA-FRAG, a medical decision-support assistant.
Use only the provided consolidated federated evidence. Do not invent clinical
facts outside the evidence. Return cautious triage, not a definitive diagnosis.
If evidence is insufficient, say so and recommend clinician review."""

DIAGNOSIS_USER_TEMPLATE = """User symptoms:
{symptoms}

Consolidated federated medical evidence:
{context}

Return JSON with these fields:
possible_condition, confidence_score, urgency, explanation,
recommended_specialist, symptoms_listed, evidence_used, guidance."""


SPECIALTY_ALIASES = {
    "cardiology": ["cardiologist", "cardiac", "heart"],
    "medicine": ["medicine specialist", "general physician", "internal medicine", "general medicine"],
    "neurology": ["neurologist", "headache", "migraine", "seizure"],
    "dermatology": ["dermatologist", "skin", "rash"],
    "pulmonology": ["pulmonologist", "respiratory", "lung", "breathing", "cough"],
    "gastro": ["gastroenterologist", "digestive", "abdominal", "stomach"],
    "rheumatology": ["rheumatologist", "joint", "arthritis"],
    "gynecology": ["gynecologist", "gynaecologist", "obstetrician"],
    "pediatrics": ["pediatrician", "paediatrician", "child"],
    "urology": ["urologist", "urinary"],
    "nephrology": ["nephrologist", "kidney", "renal"],
    "ophthalmology": ["ophthalmologist", "eye", "vision"],
    "ent": ["otolaryngologist", "ear", "nose", "throat"],
    "endocrinology": ["endocrinologist", "diabetes", "thyroid"],
}


def build_frag_context(symptoms: str, answers: Optional[List[str]] = None, top_k_per_hospital: int = 5, final_top_k: int = 12) -> Dict[str, object]:
    query = " ".join([symptoms or ""] + [answer for answer in (answers or []) if answer])
    return retrieve_federated(query.strip(), hospital_top_k=top_k_per_hospital, final_top_k=final_top_k)


def diagnose_with_frag(symptoms: str, answers: Optional[List[str]] = None, image_analysis: Optional[dict] = None) -> Dict[str, object]:
    retrieval = build_frag_context(symptoms, answers)
    prompt_symptoms = symptoms
    if answers:
        prompt_symptoms += "\nFollow-up answers: " + " | ".join(answers)
    if image_analysis:
        prompt_symptoms += "\nImage context: " + json.dumps(image_analysis, ensure_ascii=True)
    try:
        from fastapi_ai.models.llm_client import chat_json
    except Exception:
        chat_json = None

    if chat_json is not None:
        result = chat_json(
            DIAGNOSIS_SYSTEM_PROMPT,
            DIAGNOSIS_USER_TEMPLATE.format(symptoms=prompt_symptoms, context=retrieval["context"]),
            max_tokens=1200,
        )
    else:
        result = {}

    if not result:
        result = _fallback_diagnosis(symptoms, retrieval["fused_evidence"])

    result.setdefault("confidence_score", _confidence_from_evidence(retrieval["fused_evidence"]))
    result.setdefault("urgency", _urgency_from_text(prompt_symptoms, retrieval["context"]))
    result.setdefault("recommended_specialist", _specialty_from_evidence(retrieval["fused_evidence"]))
    result["frag_retrieval"] = {
        "raw_evidence_count": retrieval["raw_evidence_count"],
        "fused_evidence_count": len(retrieval["fused_evidence"]),
        "per_hospital_counts": {hid: len(items) for hid, items in retrieval["per_hospital"].items()},
        "evidence": retrieval["fused_evidence"],
    }
    return result


def _fallback_diagnosis(symptoms: str, evidence: List[Dict[str, object]]) -> Dict[str, object]:
    condition = "Undetermined condition"
    specialist = "General Physician"
    for item in evidence:
        text = str(item.get("text", ""))
        disease_match = re.search(r"(?:Disease|Disease pattern|suggests):\s*([^.;]+)", text, re.I)
        spec_match = re.search(r"Recommended specialist:\s*([^.;]+)", text, re.I)
        if disease_match and condition == "Undetermined condition":
            condition = disease_match.group(1).strip()
        if spec_match:
            specialist = spec_match.group(1).strip()
            break
    return {
        "possible_condition": condition,
        "urgency": _urgency_from_text(symptoms, " ".join(str(item.get("text", "")) for item in evidence)),
        "recommended_specialist": specialist,
        "explanation": "Assessment is based on the highest-ranked federated evidence. A clinician should confirm the finding.",
        "guidance": "Seek professional medical advice, especially if symptoms worsen or red flags appear.",
        "symptoms_listed": [symptoms],
        "evidence_used": [item.get("doc_id") for item in evidence[:5]],
    }


def _confidence_from_evidence(evidence: List[Dict[str, object]]) -> float:
    if not evidence:
        return 0.25
    top_scores = [float(item.get("fusion_score") or item.get("semantic_score") or 0.0) for item in evidence[:5]]
    score = sum(top_scores) / len(top_scores)
    return round(max(0.25, min(0.92, 0.45 + score / 2)), 2)


def _urgency_from_text(symptoms: str, context: str) -> str:
    text = f"{symptoms} {context}".lower()
    high = ["chest pain", "shortness of breath", "severe bleeding", "confusion", "blue lips", "stroke", "loss of consciousness"]
    medium = ["high fever", "persistent fever", "severe headache", "rash", "dehydration", "vomiting"]
    if any(term in text for term in high):
        return "high"
    if any(term in text for term in medium):
        return "medium"
    return "low"


def _specialty_from_evidence(evidence: List[Dict[str, object]]) -> str:
    for item in evidence:
        specialist = (item.get("metadata") or {}).get("specialist")
        if specialist:
            return specialist
        match = re.search(r"Recommended specialist:\s*([^.;]+)", str(item.get("text", "")), re.I)
        if match:
            return match.group(1).strip()
    return "General Physician"


def _expanded_specialty_terms(specialty: str) -> List[str]:
    canonical = canonical_specialty(specialty)
    terms = {normalise_text(specialty), normalise_text(canonical)}
    for key, aliases in SPECIALTY_ALIASES.items():
        all_terms = {key, *aliases}
        if normalise_text(canonical) in {normalise_text(term) for term in all_terms}:
            terms.update(normalise_text(term) for term in all_terms)
    return [term for term in terms if term]


def _specialization_score(doctor: DoctorRecord, specialty: str) -> float:
    doctor_spec = normalise_text(doctor.specialization)
    terms = _expanded_specialty_terms(specialty)
    if any(term and (term in doctor_spec or doctor_spec in term) for term in terms):
        return 1.0
    blob = normalise_text(doctor.focus_areas)
    if any(term and term in blob for term in terms):
        return 0.65
    return 0.0


def recommend_doctors_frag(
    specialty: str,
    diagnosis: str = "",
    symptoms: str = "",
    city: str = "",
    limit: int = 10,
) -> Dict[str, object]:
    """Rank doctors across all hospitals regardless of source hospital."""
    doctors = load_all_doctors()
    query = " ".join(part for part in [specialty, diagnosis, symptoms] if part)
    city_norm = normalise_text(city)
    ranked = []

    for doctor in doctors:
        spec_score = _specialization_score(doctor, specialty)
        location_score = 1.0 if city_norm and city_norm in normalise_text(f"{doctor.location} {doctor.chamber}") else 0.0
        experience_score = min(1.0, doctor.experience_years / 25.0) if doctor.experience_years else 0.25
        semantic_score = lexical_similarity(query, doctor_search_text(doctor))
        total = (0.45 * spec_score) + (0.20 * location_score) + (0.15 * experience_score) + (0.20 * semantic_score)

        item = doctor.to_dict()
        item["match_score"] = round(total * 100, 2)
        item["score_breakdown"] = {
            "specialization_match": round(spec_score, 4),
            "city_location": round(location_score, 4),
            "experience": round(experience_score, 4),
            "semantic_relevance": round(semantic_score, 4),
        }
        item["match_reason"] = _doctor_reason(item["score_breakdown"], specialty, city)
        ranked.append(item)

    ranked.sort(key=lambda item: item["match_score"], reverse=True)
    return {
        "doctors": ranked[: max(1, min(60, int(limit or 10)))],
        "recommended_specialty": specialty,
        "diagnosis": diagnosis,
        "city": city,
        "hospital_statistics": hospital_statistics(),
    }


def _doctor_reason(breakdown: Dict[str, float], specialty: str, city: str) -> str:
    reasons = []
    if breakdown["specialization_match"] >= 0.9:
        reasons.append(f"strong {specialty} match")
    elif breakdown["specialization_match"] > 0:
        reasons.append("related clinical focus")
    if city and breakdown["city_location"] > 0:
        reasons.append(f"location match for {city}")
    if breakdown["experience"] >= 0.6:
        reasons.append("high experience")
    if breakdown["semantic_relevance"] > 0:
        reasons.append("assessment relevance")
    return "; ".join(reasons) or "general directory match"



