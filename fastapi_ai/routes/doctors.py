# MediAI - Doctor Recommendation Routes
import csv
import os
import re
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Query
from models.schemas import DoctorRecommendationRequest

router = APIRouter(tags=["Doctors"])

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "rag_pipeline",
    "data",
)

DEMO_DOCTORS = [
    {"id": 1, "source": "demo", "doctor_name": "Dr. Rahim Ahmed", "specialization": "Cardiologist", "hospital": "Dhaka Medical College", "location": "Dhaka", "availability": "Mon-Fri"},
    {"id": 2, "source": "demo", "doctor_name": "Dr. Nasrin Islam", "specialization": "Medicine Specialist", "hospital": "Square Hospital", "location": "Dhaka", "availability": "Sun-Thu"},
    {"id": 3, "source": "demo", "doctor_name": "Dr. Karim Hossain", "specialization": "Neurologist", "hospital": "BIRDEM General Hospital", "location": "Dhaka", "availability": "Mon-Wed"},
    {"id": 4, "source": "demo", "doctor_name": "Dr. Fatema Begum", "specialization": "Pediatrician", "hospital": "Shishu Hospital", "location": "Chittagong", "availability": "Sat-Thu"},
    {"id": 5, "source": "demo", "doctor_name": "Dr. Arif Siddiqui", "specialization": "Dermatologist", "hospital": "Apollo Hospital", "location": "Dhaka", "availability": "Mon-Sat"},
    {"id": 6, "source": "demo", "doctor_name": "Dr. Tariq Rahman", "specialization": "Gastroenterologist", "hospital": "Labaid Specialized", "location": "Dhaka", "availability": "Mon-Thu"},
]

STOPWORDS = {
    "a", "about", "after", "also", "am", "an", "and", "are", "as", "at", "be",
    "been", "but", "by", "can", "days", "do", "for", "from", "had", "has",
    "have", "having", "i", "in", "is", "it", "my", "of", "on", "or", "past",
    "the", "this", "to", "with",
}

SPECIALTY_FIXES = {
    "internal medcine": "Medicine Specialist",
    "internal medicine": "Internal Medicine Specialist",
    "general physician": "Medicine Specialist",
    "gastroenterologist": "Gastroenterologist",
    "rheumatologists": "Rheumatologist",
    "rheumatologist": "Rheumatologist",
    "otolaryngologist": "Otolaryngologists (ENT)",
    "tuberculosis": "Respiratory Specialist",
}

SPECIALTY_ALIASES = {
    "Medicine Specialist": ["medicine specialist", "general physician", "internal medicine", "internal medcine", "family medicine", "general medicine"],
    "Cardiologist": ["cardiologist", "cardiac", "cardiology", "heart"],
    "Dermatologist": ["dermatologist", "skin", "dermatology"],
    "Endocrinologist": ["endocrinologist", "diabetes", "thyroid", "hormone"],
    "Gastroenterologist": ["gastroenterologist", "gastro", "stomach", "abdominal", "digestive", "gerd", "ulcer"],
    "Gynecologist & Obstetrician": ["gynecologist", "gynaecologist", "obstetrician", "pregnancy", "urinary tract infection"],
    "Hepatologist": ["hepatologist", "hepatitis", "liver", "jaundice"],
    "Neurologist": ["neurologist", "neuromedicine", "migraine", "headache", "brain", "seizure", "paralysis", "vertigo"],
    "Otolaryngologists (ENT)": ["otolaryngologist", "otolaryngologists", "ent", "ear", "nose", "throat", "cold"],
    "Pediatrician": ["pediatrician", "paediatrician", "child", "children", "neonatologist"],
    "Pulmonologist": ["pulmonologist", "respiratory specialist", "respiratory", "asthma", "pneumonia", "breathing", "lung"],
    "Rheumatologist": ["rheumatologist", "rheumatologists", "arthritis", "joint"],
    "Orthopedic Surgeon": ["orthopedic", "orthopedist", "bone", "fracture", "spine"],
    "Urologist": ["urologist", "urinary", "kidney stone", "prostate"],
    "Nephrologist": ["nephrologist", "kidney", "renal"],
    "Psychiatrist": ["psychiatrist", "mental", "depression", "anxiety"],
    "Ophthalmologist": ["ophthalmologist", "eye", "vision"],
    "Dentist": ["dentist", "dental", "tooth", "oral"],
    "Oncologist": ["oncologist", "cancer", "tumor", "tumour"],
    "Hematologist": ["hematologist", "blood", "anemia", "platelet"],
}

KEYWORD_SPECIALTY_RULES = [
    ({"chest", "heart", "palpitation", "pressure"}, "Cardiologist"),
    ({"rash", "skin", "itching", "acne", "scaly"}, "Dermatologist"),
    ({"headache", "migraine", "seizure", "dizziness", "vertigo"}, "Neurologist"),
    ({"cough", "breath", "breathing", "asthma", "pneumonia", "lung"}, "Pulmonologist"),
    ({"abdominal", "stomach", "vomiting", "nausea", "diarrhea", "gerd", "jaundice"}, "Gastroenterologist"),
    ({"joint", "arthritis", "swelling"}, "Rheumatologist"),
    ({"pregnancy", "period", "uterus", "urinary"}, "Gynecologist & Obstetrician"),
    ({"child", "baby", "infant"}, "Pediatrician"),
    ({"fever", "fatigue", "infection", "dengue", "malaria", "typhoid"}, "Medicine Specialist"),
]


def _normalise_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def _clean(value) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("\ufeff", "").replace("\ufffd", "").split())


def _param(value) -> str:
    return value if isinstance(value, str) else ""


def _bounded_limit(value: int) -> int:
    try:
        return max(1, min(60, int(value)))
    except (TypeError, ValueError):
        return 24


def _conversation_to_text(conversation: Any) -> str:
    if not conversation:
        return ""
    if isinstance(conversation, str):
        return _clean(conversation)
    if not isinstance(conversation, list):
        return ""

    parts = []
    for item in conversation:
        if isinstance(item, dict):
            item_parts = []
            for key in ("question", "answer", "role", "content", "text", "message"):
                value = _clean(item.get(key))
                if value:
                    item_parts.append(value)
            if item_parts:
                parts.append(" ".join(item_parts))
        else:
            value = _clean(item)
            if value:
                parts.append(value)
    return " ".join(parts)


def _report_field(report: Any, *names: str) -> str:
    if not isinstance(report, dict):
        return ""
    for name in names:
        value = report.get(name)
        if isinstance(value, list):
            cleaned = [_clean(item) for item in value if _clean(item)]
            if cleaned:
                return ", ".join(cleaned)
        value = _clean(value)
        if value:
            return value
    return ""


def _normalise_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


def _tokens(value: str) -> Set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", _normalise_text(value)) if token not in STOPWORDS and len(token) > 2}


def _row_value(row: dict, *names: str) -> str:
    wanted = {_normalise_header(name) for name in names}
    for key, value in row.items():
        if _normalise_header(key) in wanted:
            return _clean(value)
    return ""


def _read_csv(filename: str) -> List[dict]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def _parse_experience(value: str) -> float:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0.0


def _canonical_specialty(value: str) -> str:
    cleaned = _clean(value).strip(" .,-")
    key = _normalise_text(cleaned)
    if key in SPECIALTY_FIXES:
        return SPECIALTY_FIXES[key]
    for canonical, aliases in SPECIALTY_ALIASES.items():
        alias_keys = [_normalise_text(alias) for alias in aliases]
        if key == _normalise_text(canonical) or key in alias_keys:
            return canonical
    return cleaned


def _expand_specialties(specialties: List[str]) -> List[str]:
    expanded = []
    seen = set()
    for specialty in specialties:
        canonical = _canonical_specialty(specialty)
        values = [canonical] + SPECIALTY_ALIASES.get(canonical, [])
        for value in values:
            key = _normalise_text(value)
            if key and key not in seen:
                expanded.append(value)
                seen.add(key)
    return expanded


@lru_cache(maxsize=1)
def load_doctors_from_csv() -> List[dict]:
    doctors = []
    for i, row in enumerate(_read_csv("doctors.csv")):
        doctor_name = _row_value(row, "doctor_name", "doctor name", "name")
        specialization = _canonical_specialty(_row_value(row, "specialization", "speciality", "specialty"))
        hospital = _row_value(row, "hospital", "chamber")
        location = _row_value(row, "location")
        availability = _row_value(row, "availability")
        education = _row_value(row, "education")
        experience = _row_value(row, "experience")
        focus_areas = _row_value(row, "concentration", "focus_areas", "focus areas")
        contact = _row_value(row, "contact", "phone", "mobile")

        if not doctor_name and not specialization:
            continue

        doctors.append({
            "id": i + 1,
            "source": "csv",
            "doctor_name": doctor_name or "Unknown doctor",
            "specialization": specialization or "Medicine Specialist",
            "hospital": hospital,
            "location": location,
            "availability": availability,
            "education": education,
            "experience": experience,
            "experience_years": _parse_experience(experience),
            "focus_areas": focus_areas,
            "contact": contact,
        })
    return doctors


@lru_cache(maxsize=1)
def load_disease_specialists() -> Dict[str, str]:
    mapping = {}
    for row in _read_csv("Disease_Specialist.csv"):
        disease = _row_value(row, "disease", "name")
        specialist = _canonical_specialty(_row_value(row, "specialist", "recommended_specialist"))
        if disease and specialist:
            mapping[disease] = specialist
    return mapping


@lru_cache(maxsize=1)
def load_condition_examples() -> List[dict]:
    examples = []
    for row in _read_csv("Symptom2Disease.csv"):
        label = _row_value(row, "label", "disease")
        text = _row_value(row, "text", "description")
        if label and text:
            examples.append({"condition": label, "tokens": _tokens(text), "source": "symptom_text"})

    for row in _read_csv("Original_Dataset.csv"):
        disease = _row_value(row, "disease")
        symptoms = " ".join(
            _clean(value)
            for key, value in row.items()
            if _normalise_header(key).startswith("symptom") and _clean(value)
        )
        if disease and symptoms:
            examples.append({"condition": disease, "tokens": _tokens(symptoms), "source": "symptom_pattern"})
    return examples


def _infer_conditions(assessment_text: str, possible_condition: str) -> List[str]:
    conditions = []
    seen = set()

    def add(condition: str):
        condition = _clean(condition)
        key = _normalise_text(condition)
        if condition and key and key not in seen:
            conditions.append(condition)
            seen.add(key)

    add(possible_condition)
    text_norm = _normalise_text(assessment_text)
    query_tokens = _tokens(assessment_text)

    for disease in load_disease_specialists().keys():
        disease_norm = _normalise_text(disease)
        disease_tokens = _tokens(disease)
        if disease_norm and disease_norm in text_norm:
            add(disease)
        elif disease_tokens and disease_tokens.issubset(query_tokens):
            add(disease)

    scored = []
    for example in load_condition_examples():
        overlap = query_tokens & example["tokens"]
        if len(overlap) >= 2:
            scored.append((len(overlap), example["condition"]))

    for _, condition in sorted(scored, reverse=True)[:5]:
        add(condition)

    return conditions[:6]


def _specialist_for_condition(condition: str) -> Optional[str]:
    condition_norm = _normalise_text(condition)
    for disease, specialist in load_disease_specialists().items():
        disease_norm = _normalise_text(disease)
        if condition_norm == disease_norm or disease_norm in condition_norm or condition_norm in disease_norm:
            return _canonical_specialty(specialist)
    return None


def _infer_specialties(
    specialization: str,
    assessment_text: str,
    possible_condition: str,
    conditions: List[str],
) -> List[str]:
    specialties = []
    seen = set()

    def add(specialty: str):
        specialty = _canonical_specialty(specialty)
        key = _normalise_text(specialty)
        if specialty and key and key not in seen:
            specialties.append(specialty)
            seen.add(key)

    add(specialization)
    for condition in conditions:
        add(_specialist_for_condition(condition) or "")

    text_tokens = _tokens(" ".join([assessment_text, possible_condition]))
    for keywords, specialty in KEYWORD_SPECIALTY_RULES:
        if text_tokens & keywords:
            add(specialty)

    if not specialties:
        add("Medicine Specialist")
    return specialties


def _matches_specialty(doctor_specialty: str, expanded_specialties: List[str]) -> bool:
    doctor_norm = _normalise_text(doctor_specialty)
    for specialty in expanded_specialties:
        spec_norm = _normalise_text(specialty)
        if not spec_norm:
            continue
        if spec_norm in doctor_norm or doctor_norm in spec_norm:
            return True
    return False


def _matching_specialty(doctor_specialty: str, specialties: List[str]) -> tuple:
    for index, specialty in enumerate(specialties):
        if _matches_specialty(doctor_specialty, _expand_specialties([specialty])):
            return specialty, index
    return "", -1


def _score_doctor(
    doctor: dict,
    specialties: List[str],
    conditions: List[str],
    assessment_text: str,
    location: str,
) -> dict:
    expanded_specialties = _expand_specialties(specialties)
    doctor_blob = " ".join([
        doctor.get("specialization", ""),
        doctor.get("focus_areas", ""),
        doctor.get("hospital", ""),
        doctor.get("location", ""),
        doctor.get("education", ""),
    ])
    doctor_tokens = _tokens(doctor_blob)
    assessment_tokens = _tokens(" ".join([assessment_text] + conditions))
    score = 0.0
    reasons = []

    matched_specialty, specialty_index = _matching_specialty(doctor.get("specialization", ""), specialties)
    if matched_specialty:
        score += 75 if specialty_index == 0 else 62
        reasons.append(f"Matches the recommended specialty: {matched_specialty}")
    else:
        specialty_tokens = _tokens(" ".join(expanded_specialties))
        overlap = specialty_tokens & doctor_tokens
        if overlap:
            score += min(35, len(overlap) * 8)
            reasons.append("Related specialty or clinical focus")

    clinical_overlap = assessment_tokens & doctor_tokens
    if clinical_overlap:
        score += min(30, len(clinical_overlap) * 4)
        terms = ", ".join(sorted(list(clinical_overlap))[:4])
        reasons.append(f"Focus areas overlap with assessment terms: {terms}")

    if location:
        loc_norm = _normalise_text(location)
        doctor_place = _normalise_text(" ".join([doctor.get("location", ""), doctor.get("hospital", "")]))
        if loc_norm and loc_norm in doctor_place:
            score += 18
            reasons.append(f"Available near {location}")
        else:
            score -= 10

    experience = float(doctor.get("experience_years") or 0)
    if experience:
        score += min(12, experience / 3)

    if not reasons:
        reasons.append("General match from the doctor directory")

    ranked = dict(doctor)
    ranked["match_score"] = round(max(score, 0), 1)
    ranked["match_reason"] = "; ".join(reasons[:2])
    return ranked


def _recommend_doctors(
    specialization: str = "",
    location: str = "",
    symptom: str = "",
    possible_condition: str = "",
    report_text: str = "",
    urgency: str = "",
    conversation: Any = None,
    report: Any = None,
    limit: int = 24,
) -> dict:
    report_condition = _report_field(report, "possible_condition", "diagnosis", "condition")
    report_specialist = _report_field(report, "recommended_specialist", "specialist")
    report_urgency = _report_field(report, "urgency")
    report_symptoms = _report_field(report, "symptoms_listed", "symptoms")
    report_notes = " ".join(
        part
        for part in [
            _report_field(report, "reasoning"),
            _report_field(report, "guidance"),
            _report_field(report, "explanation"),
            _report_field(report, "notes"),
            _report_field(report, "diagnoses"),
        ]
        if part
    )
    conversation_text = _conversation_to_text(conversation)

    specialization = _param(specialization) or report_specialist
    location = _param(location)
    symptom = " ".join(part for part in [_param(symptom), report_symptoms, conversation_text] if part)
    possible_condition = _param(possible_condition) or report_condition
    report_text = " ".join(part for part in [_param(report_text), report_notes] if part)
    urgency = _param(urgency) or report_urgency
    limit = _bounded_limit(limit)

    doctors = load_doctors_from_csv() or DEMO_DOCTORS
    assessment_text = " ".join(
        _clean(part)
        for part in [symptom, possible_condition, report_text, urgency, conversation_text]
        if part
    )
    conditions = _infer_conditions(assessment_text, possible_condition or "")
    specialties = _infer_specialties(specialization or "", assessment_text, possible_condition or "", conditions)

    ranked = [
        _score_doctor(doctor, specialties, conditions, assessment_text, location or "")
        for doctor in doctors
    ]
    ranked.sort(key=lambda d: d.get("match_score", 0), reverse=True)

    useful = [doctor for doctor in ranked if doctor.get("match_score", 0) > 0]
    if not useful:
        useful = ranked

    return {
        "doctors": useful[:limit],
        "inferred_specialization": specialties[0] if specialties else "",
        "specialists_considered": specialties,
        "possible_conditions": conditions,
        "assessment_context": {
            "symptom": symptom or "",
            "possible_condition": possible_condition or "",
            "urgency": urgency or "",
            "location": location or "",
            "used_conversation": bool(conversation_text),
            "used_report": bool(report_text or report_condition or report_specialist),
        },
    }


@router.get("/doctor-recommendation")
async def doctor_recommendation(
    specialization: Optional[str] = Query(default=""),
    location: Optional[str] = Query(default=""),
    symptom: Optional[str] = Query(default=""),
    possible_condition: Optional[str] = Query(default=""),
    report_text: Optional[str] = Query(default=""),
    urgency: Optional[str] = Query(default=""),
    limit: int = Query(default=24, ge=1, le=60),
):
    """
    Returns doctor recommendations ranked by assessment context.

    The matcher accepts direct specialty/location search, plus symptom chat and
    report context. It normalizes the large CSV doctor schema before ranking.
    """
    return _recommend_doctors(
        specialization=specialization,
        location=location,
        symptom=symptom,
        possible_condition=possible_condition,
        report_text=report_text,
        urgency=urgency,
        limit=limit,
    )


@router.post("/doctor-recommendation")
async def doctor_recommendation_from_assessment(req: DoctorRecommendationRequest):
    """Returns ranked doctors from a full conversation/report payload."""
    return _recommend_doctors(
        specialization=req.specialization or "",
        location=req.location or "",
        symptom=req.symptom or "",
        possible_condition=req.possible_condition or "",
        report_text=req.report_text or "",
        urgency=req.urgency or "",
        conversation=req.conversation,
        report=req.report,
        limit=req.limit,
    )
