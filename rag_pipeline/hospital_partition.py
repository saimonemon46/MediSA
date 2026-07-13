"""Partition existing MediSA CSV datasets into simulated hospitals.

The partitioner is deterministic and does not duplicate source records across
Hospital A, B, and C. It uses hospital/chamber names first, then specialty
alignment, and finally a stable hash fallback.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "rag_pipeline" / "data"


@dataclass(frozen=True)
class HospitalProfile:
    hospital_id: str
    display_name: str
    cities: tuple[str, ...]
    specialties: tuple[str, ...]
    hospital_keywords: tuple[str, ...]


HOSPITAL_PROFILES: tuple[HospitalProfile, ...] = (
    HospitalProfile(
        hospital_id="hospital_a",
        display_name="Hospital A - Metropolitan General Network",
        cities=("dhaka", "mirpur", "dhanmondi", "uttara"),
        specialties=("medicine", "general", "cardiology", "neurology", "emergency", "critical care", "pediatrics", "infectious", "fever"),
        hospital_keywords=("dhaka medical", "aalok", "square", "birdem", "popular"),
    ),
    HospitalProfile(
        hospital_id="hospital_b",
        display_name="Hospital B - Specialty Care Institute",
        cities=("dhaka", "gulshan", "banani", "mohakhali"),
        specialties=("gastro", "hepatology", "urology", "gynecology", "obstetric", "orthopedic", "surgery", "dermatology", "nutrition"),
        hospital_keywords=("labaid", "apollo", "evercare", "brb", "ibn sina"),
    ),
    HospitalProfile(
        hospital_id="hospital_c",
        display_name="Hospital C - Regional Clinical Consortium",
        cities=("chittagong", "sylhet", "rajshahi", "khulna", "barisal"),
        specialties=("pulmonology", "respiratory", "ent", "eye", "ophthalmology", "nephrology", "endocrinology", "oncology", "rheumatology"),
        hospital_keywords=("chittagong", "national", "chest", "eye", "ibrahim"),
    ),
)

SPECIALTY_SYNONYMS = {
    "cardiologist": "cardiology",
    "cardiac": "cardiology",
    "medicine specialist": "medicine",
    "general physician": "medicine",
    "internal medicine": "medicine",
    "neurologist": "neurology",
    "gastroenterologist": "gastro",
    "hepatologist": "hepatology",
    "dermatologist": "dermatology",
    "pulmonologist": "pulmonology",
    "respiratory specialist": "respiratory",
    "gynecologist": "gynecology",
    "gynaecologist": "gynecology",
    "obstetrician": "obstetric",
    "orthopedic": "orthopedic",
    "orthopaedic": "orthopedic",
    "urologist": "urology",
    "nephrologist": "nephrology",
    "endocrinologist": "endocrinology",
    "ophthalmologist": "ophthalmology",
    "ent": "ent",
    "rheumatologist": "rheumatology",
    "oncologist": "oncology",
    "pediatrician": "pediatrics",
    "paediatrician": "pediatrics",
    "allergist": "medicine",
}


def normalise_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def clean(value) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("\ufeff", "").replace("\ufffd", "").split())


def normalise_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def row_value(row: dict, *names: str) -> str:
    wanted = {normalise_header(name) for name in names}
    for key, value in row.items():
        if normalise_header(key) in wanted:
            return clean(value)
    return ""


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def canonical_specialty(value: str) -> str:
    text = normalise_text(value)
    if not text:
        return ""
    for alias, canonical in SPECIALTY_SYNONYMS.items():
        if alias in text:
            return canonical
    return text


def _stable_index(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % modulo


def _profile_score(profile: HospitalProfile, text: str, specialty: str, location: str) -> int:
    blob = normalise_text(text)
    specialty = canonical_specialty(specialty)
    location = normalise_text(location)
    score = 0
    for keyword in profile.hospital_keywords:
        if normalise_text(keyword) in blob:
            score += 8
    for city in profile.cities:
        if city and city in location:
            score += 3
    for profile_specialty in profile.specialties:
        profile_key = canonical_specialty(profile_specialty)
        if profile_key and (profile_key in specialty or specialty in profile_key):
            score += 5
        elif profile_key and profile_key in blob:
            score += 2
    return score


def assign_hospital(record: dict, record_type: str) -> str:
    """Assign a source record to one simulated hospital without duplication."""
    if record_type == "doctor":
        name = row_value(record, "doctor_name", "doctor name", "name")
        specialty = row_value(record, "specialization", "speciality", "specialty")
        hospital = row_value(record, "hospital", "chamber")
        location = row_value(record, "location")
        seed = "|".join([record_type, name, specialty, hospital, location])
        text = " ".join([hospital, location, specialty, row_value(record, "concentration", "focus_areas")])
    elif record_type == "disease":
        disease = row_value(record, "disease", "name", "label")
        specialty = row_value(record, "specialist", "recommended_specialist")
        text = " ".join([disease, specialty, row_value(record, "description", "text")])
        seed = "|".join([record_type, disease, specialty, text[:80]])
        location = ""
    else:
        text = " ".join(clean(v) for v in record.values())
        specialty = row_value(record, "specialist", "recommended_specialist", "specialization")
        location = row_value(record, "location")
        seed = "|".join([record_type, text[:160]])

    scored = [(_profile_score(profile, text, specialty, location), profile.hospital_id) for profile in HOSPITAL_PROFILES]
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return HOSPITAL_PROFILES[_stable_index(seed, len(HOSPITAL_PROFILES))].hospital_id


def _disease_specialist_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in read_csv(DATA_DIR / "Disease_Specialist.csv"):
        disease = normalise_text(row_value(row, "disease", "name"))
        specialist = row_value(row, "specialist", "recommended_specialist")
        if disease and specialist:
            mapping[disease] = specialist
    return mapping


def partition_records() -> Dict[str, dict]:
    """Return all hospital partitions and national KB documents as raw records."""
    partitions = {
        profile.hospital_id: {
            "profile": profile,
            "doctors": [],
            "diseases": [],
            "symptom_patterns": [],
            "symptom_examples": [],
            "symptoms": [],
            "hospitals": [],
        }
        for profile in HOSPITAL_PROFILES
    }
    disease_specialists = _disease_specialist_map()

    for row in read_csv(DATA_DIR / "doctors.csv"):
        partitions[assign_hospital(row, "doctor")]["doctors"].append(row)
    for row in read_csv(DATA_DIR / "hospitals.csv"):
        partitions[assign_hospital(row, "doctor")]["hospitals"].append(row)
    for row in read_csv(DATA_DIR / "diseases.csv"):
        disease_key = normalise_text(row_value(row, "name", "disease"))
        enriched = dict(row)
        if disease_key in disease_specialists:
            enriched["recommended_specialist"] = disease_specialists[disease_key]
        partitions[assign_hospital(enriched, "disease")]["diseases"].append(enriched)
    for row in read_csv(DATA_DIR / "Disease_Specialist.csv"):
        partitions[assign_hospital(row, "disease")]["diseases"].append(row)
    for row in read_csv(DATA_DIR / "Original_Dataset.csv"):
        disease_key = normalise_text(row_value(row, "disease"))
        enriched = dict(row)
        if disease_key in disease_specialists:
            enriched["recommended_specialist"] = disease_specialists[disease_key]
        partitions[assign_hospital(enriched, "disease")]["symptom_patterns"].append(row)
    for row in read_csv(DATA_DIR / "Symptom2Disease.csv"):
        disease_key = normalise_text(row_value(row, "label", "disease"))
        enriched = dict(row)
        if disease_key in disease_specialists:
            enriched["recommended_specialist"] = disease_specialists[disease_key]
        partitions[assign_hospital(enriched, "disease")]["symptom_examples"].append(row)
    for row in read_csv(DATA_DIR / "symptoms.csv"):
        partitions[assign_hospital(row, "symptom")]["symptoms"].append(row)
    return partitions


def national_knowledge_documents() -> List[str]:
    """Compact national reference corpus used by every FRAG run."""
    return [
        "National emergency protocol: chest pain, severe shortness of breath, stroke signs, severe bleeding, confusion, blue lips, or loss of consciousness require urgent emergency evaluation.",
        "WHO-style fever guidance: persistent high fever with severe headache, rash, bleeding, dehydration, neck stiffness, or altered mental status should be assessed promptly by a clinician.",
        "Drug interaction reference: patients taking anticoagulants, insulin, antihypertensives, steroids, or multiple chronic medicines need medication review before new treatment advice.",
        "Clinical safety reference: AI triage is decision support only and must not replace a licensed clinician, physical examination, diagnostic testing, or emergency care.",
        "Infection-control reference: cough, fever, sore throat, diarrhea, rash, and recent exposure history should be assessed with public-health precautions when contagious disease is possible.",
        "Referral reference: specialty recommendation should follow the dominant clinical system, urgency, patient location, and available doctor expertise across hospitals.",
    ]


def partition_summary() -> Dict[str, dict]:
    partitions = partition_records()
    return {
        hospital_id: {
            "name": data["profile"].display_name,
            "doctors": len(data["doctors"]),
            "diseases": len(data["diseases"]),
            "symptom_patterns": len(data["symptom_patterns"]),
            "symptom_examples": len(data["symptom_examples"]),
            "symptoms": len(data["symptoms"]),
            "hospital_records": len(data["hospitals"]),
        }
        for hospital_id, data in partitions.items()
    }
