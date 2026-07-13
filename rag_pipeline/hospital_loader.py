"""Load simulated hospital corpora for MediSA FRAG.

This module converts the existing CSV records into normalized evidence
documents and doctor objects. It does not create new source records; every
record is assigned to one logical hospital by hospital_partition.py.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List

from rag_pipeline.hospital_partition import (
    HOSPITAL_PROFILES,
    canonical_specialty,
    clean,
    national_knowledge_documents,
    normalise_text,
    partition_records,
    row_value,
)


@dataclass(frozen=True)
class EvidenceDocument:
    doc_id: str
    text: str
    hospital_id: str
    hospital_name: str
    source_type: str
    metadata: Dict[str, str]


@dataclass(frozen=True)
class DoctorRecord:
    doctor_id: str
    doctor_name: str
    specialization: str
    hospital_id: str
    hospital_name: str
    chamber: str
    location: str
    experience_years: float
    education: str
    availability: str
    focus_areas: str
    source: str = "frag_partition"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _parse_experience(value: str) -> float:
    import re

    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0.0


def _document_id(hospital_id: str, source_type: str, index: int) -> str:
    return f"{hospital_id}:{source_type}:{index}"


def _doc(hospital_id: str, hospital_name: str, source_type: str, index: int, text: str, **metadata: str) -> EvidenceDocument:
    return EvidenceDocument(
        doc_id=_document_id(hospital_id, source_type, index),
        text=" ".join(text.split()),
        hospital_id=hospital_id,
        hospital_name=hospital_name,
        source_type=source_type,
        metadata={key: clean(value) for key, value in metadata.items() if clean(value)},
    )


def _disease_docs(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[EvidenceDocument]:
    docs = []
    for index, row in enumerate(rows):
        disease = row_value(row, "name", "disease", "label")
        specialist = row_value(row, "specialist", "recommended_specialist")
        description = row_value(row, "description", "text")
        if not disease and not description:
            continue
        text = f"Disease: {disease}."
        if description:
            text += f" Description: {description}."
        if specialist:
            text += f" Recommended specialist: {specialist}."
        docs.append(_doc(hospital_id, hospital_name, "disease", index, text, disease=disease, specialist=specialist))
    return docs


def _symptom_pattern_docs(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[EvidenceDocument]:
    docs = []
    for index, row in enumerate(rows):
        disease = row_value(row, "disease", "label", "name")
        specialist = row_value(row, "recommended_specialist", "specialist")
        symptoms = [
            clean(value)
            for key, value in row.items()
            if key and key.lower().replace(" ", "_").startswith("symptom") and clean(value)
        ]
        if not disease and not symptoms:
            continue
        text = f"Disease pattern: {disease}. Symptoms: {', '.join(symptoms)}."
        if specialist:
            text += f" Recommended specialist: {specialist}."
        docs.append(_doc(hospital_id, hospital_name, "symptom_pattern", index, text, disease=disease, specialist=specialist))
    return docs


def _symptom_example_docs(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[EvidenceDocument]:
    docs = []
    for index, row in enumerate(rows):
        disease = row_value(row, "label", "disease")
        text_value = row_value(row, "text", "description")
        specialist = row_value(row, "recommended_specialist", "specialist")
        if not disease and not text_value:
            continue
        text = f"Patient symptom description suggests: {disease}. Description: {text_value}."
        if specialist:
            text += f" Recommended specialist: {specialist}."
        docs.append(_doc(hospital_id, hospital_name, "symptom_example", index, text, disease=disease, specialist=specialist))
    return docs


def _symptom_docs(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[EvidenceDocument]:
    docs = []
    for index, row in enumerate(rows):
        symptom = row_value(row, "symptom")
        related = row_value(row, "related_conditions", "conditions")
        severity = row_value(row, "severity")
        specialist = row_value(row, "recommended_specialist", "specialist")
        if not symptom:
            continue
        parts = [f"Symptom: {symptom}."]
        if related:
            parts.append(f"Related conditions: {related}.")
        if severity:
            parts.append(f"Severity: {severity}.")
        if specialist:
            parts.append(f"Recommended specialist: {specialist}.")
        docs.append(_doc(hospital_id, hospital_name, "symptom", index, " ".join(parts), symptom=symptom, specialist=specialist))
    return docs


def _hospital_docs(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[EvidenceDocument]:
    docs = []
    for index, row in enumerate(rows):
        name = row_value(row, "hospital_name", "hospital name", "hospital", "chamber")
        location = row_value(row, "location")
        emergency = row_value(row, "emergency_services", "emergency services")
        contact = row_value(row, "contact")
        if not name and not location:
            continue
        text = f"Hospital facility: {name}. Location: {location}. Emergency services: {emergency}. Contact: {contact}."
        docs.append(_doc(hospital_id, hospital_name, "facility", index, text, facility=name, location=location))
    return docs


def _doctor_records(rows: Iterable[dict], hospital_id: str, hospital_name: str) -> List[DoctorRecord]:
    doctors = []
    for index, row in enumerate(rows):
        name = row_value(row, "doctor_name", "doctor name", "name")
        specialization = canonical_specialty(row_value(row, "specialization", "speciality", "specialty"))
        chamber = row_value(row, "hospital", "chamber")
        location = row_value(row, "location")
        education = row_value(row, "education")
        availability = row_value(row, "availability")
        experience = row_value(row, "experience")
        focus = row_value(row, "concentration", "focus_areas", "focus areas")
        if not name and not specialization:
            continue
        doctors.append(
            DoctorRecord(
                doctor_id=f"{hospital_id}:doctor:{index}",
                doctor_name=name or "Unknown doctor",
                specialization=specialization or "medicine",
                hospital_id=hospital_id,
                hospital_name=hospital_name,
                chamber=chamber,
                location=location,
                experience_years=_parse_experience(experience),
                education=education,
                availability=availability,
                focus_areas=focus,
            )
        )
    return doctors


def load_hospital_corpora() -> Dict[str, Dict[str, object]]:
    """Return normalized hospital evidence and doctors for all partitions."""
    partitions = partition_records()
    corpora: Dict[str, Dict[str, object]] = {}

    for profile in HOSPITAL_PROFILES:
        hospital_id = profile.hospital_id
        data = partitions[hospital_id]
        hospital_name = profile.display_name
        docs: List[EvidenceDocument] = []
        docs.extend(_disease_docs(data["diseases"], hospital_id, hospital_name))
        docs.extend(_symptom_pattern_docs(data["symptom_patterns"], hospital_id, hospital_name))
        docs.extend(_symptom_example_docs(data["symptom_examples"], hospital_id, hospital_name))
        docs.extend(_symptom_docs(data["symptoms"], hospital_id, hospital_name))
        docs.extend(_hospital_docs(data["hospitals"], hospital_id, hospital_name))

        corpora[hospital_id] = {
            "profile": profile,
            "documents": docs,
            "doctors": _doctor_records(data["doctors"], hospital_id, hospital_name),
        }

    return corpora


def load_national_documents() -> List[EvidenceDocument]:
    """Return shared national medical references used as a separate corpus."""
    docs = []
    for index, text in enumerate(national_knowledge_documents()):
        docs.append(
            EvidenceDocument(
                doc_id=f"national:reference:{index}",
                text=text,
                hospital_id="national",
                hospital_name="National Medical Knowledge Base",
                source_type="national_reference",
                metadata={"scope": "national"},
            )
        )
    return docs


def load_all_doctors() -> List[DoctorRecord]:
    doctors: List[DoctorRecord] = []
    for corpus in load_hospital_corpora().values():
        doctors.extend(corpus["doctors"])
    return doctors


def doctor_search_text(doctor: DoctorRecord) -> str:
    return " ".join(
        part
        for part in [
            doctor.doctor_name,
            doctor.specialization,
            doctor.focus_areas,
            doctor.chamber,
            doctor.location,
            doctor.education,
            doctor.hospital_name,
        ]
        if part
    )


def hospital_statistics() -> Dict[str, Dict[str, object]]:
    corpora = load_hospital_corpora()
    return {
        hospital_id: {
            "name": corpus["profile"].display_name,
            "documents": len(corpus["documents"]),
            "doctors": len(corpus["doctors"]),
            "specialties": sorted(
                {
                    normalise_text(doctor.specialization)
                    for doctor in corpus["doctors"]
                    if doctor.specialization
                }
            ),
        }
        for hospital_id, corpus in corpora.items()
    }
