# MediAI - Document Analysis Routes
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from models.schemas import DocumentAnalysisRequest
from models.llm_client import chat_json
from prompts.templates import DOCUMENT_ANALYSIS_SYSTEM, DOCUMENT_ANALYSIS_USER

router = APIRouter(tags=["Documents"])

try:
    import pytesseract
    from PIL import Image

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pdfplumber

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def _clean(value) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").replace("\ufffd", "").split())


def _as_list(value):
    if isinstance(value, list):
        return [_clean(item) for item in value if _clean(item)]
    if isinstance(value, str) and value.strip():
        return [_clean(value)]
    return []


def _resolve_upload_path(base_dir: str, file_path: str) -> str:
    backend_dir = os.path.abspath(os.path.join(base_dir, "backend_php"))
    upload_root = os.path.abspath(os.path.join(backend_dir, "uploads"))
    full_path = os.path.abspath(os.path.join(backend_dir, file_path or ""))
    if full_path == upload_root or full_path.startswith(upload_root + os.sep):
        return full_path
    return ""


def extract_text_from_file(file_path: str) -> tuple[str, str, str]:
    if not os.path.exists(file_path):
        return "", "missing", "File was not found."

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf" and PDF_AVAILABLE:
        try:
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            text = "\n".join(text_parts).strip()
            return text, "pdfplumber", "" if text else "No selectable text was found in the PDF."
        except Exception as exc:
            return "", "pdfplumber", str(exc)

    if ext in (".jpg", ".jpeg", ".png") and OCR_AVAILABLE:
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img).strip()
            return text, "tesseract", "" if text else "OCR did not find readable text."
        except Exception as exc:
            return "", "tesseract", str(exc)

    if ext == ".pdf" and not PDF_AVAILABLE:
        return "", "unavailable", "PDF text extraction dependency is not installed."
    if ext in (".jpg", ".jpeg", ".png") and not OCR_AVAILABLE:
        return "", "unavailable", "OCR dependency is not installed."
    return "", "unsupported", "Unsupported document type."


def _normalise_medications(value) -> list[dict]:
    if not isinstance(value, list):
        return []

    medications = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name") or item.get("medicine_name") or item.get("medication"))
        if not name:
            continue
        medications.append(
            {
                "name": name,
                "dosage": _clean(item.get("dosage") or item.get("dose")),
                "frequency": _clean(item.get("frequency")),
                "duration": _clean(item.get("duration")),
                "instructions": _clean(item.get("instructions") or item.get("notes")),
                "route": _clean(item.get("route")),
            }
        )
    return medications


def _normalise_lab_results(value) -> list[dict]:
    if not isinstance(value, list):
        return []

    labs = []
    for item in value:
        if not isinstance(item, dict):
            continue
        test = _clean(item.get("test") or item.get("name"))
        if not test:
            continue
        labs.append(
            {
                "test": test,
                "value": _clean(item.get("value")),
                "unit": _clean(item.get("unit")),
                "reference_range": _clean(item.get("reference_range") or item.get("range")),
                "flag": _clean(item.get("flag") or item.get("status")),
            }
        )
    return labs


def _extract_prescription_medications(raw_text: str) -> list[dict]:
    lower = raw_text.lower()
    start = lower.find("medication prescribed")
    if start < 0:
        start = lower.find("medicine")
    if start < 0:
        return []

    section = raw_text[start:]
    end_markers = ["\nadvice", "\nfollow up", "\nfollow-up", "\nthis prescription", "\ndoctor", "\nreg."]
    end_positions = [section.lower().find(marker) for marker in end_markers if section.lower().find(marker) > 0]
    if end_positions:
        section = section[: min(end_positions)]

    route_pattern = r"(Oral|Injection|Injectable|Topical|IV|IM|SC|Subcutaneous|Inhalation|Other)"
    duration_pattern = r"(\d+\s*(?:day|days|week|weeks|month|months))"
    dose_unit_pattern = r"(\d+(?:,\d{3})*(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|units?|ng/ml|ngiml)|-)"
    freq_pattern = (
        r"((?:\d+\s*)?(?:tablet|tab|capsule|cap|spoon|drop|drops|ml)\s+"
        r"(?:once|twice|thrice|daily|weekly|monthly|every|as needed|if needed|[0-9]).*)"
    )

    medications = []
    seen = set()
    for raw_line in section.splitlines():
        line = _clean(raw_line)
        if not line or re.search(r"^(s\.?no|medicine|strength|dosage|duration|route|instructions)\b", line, re.I):
            continue
        if not re.match(r"^\d+\s*\|?\s*", line):
            continue

        line = re.sub(r"^\d+\s*\|?\s*", "", line).strip()
        line = re.sub(r"^(tab|tablet|cap|capsule|syp|syrup|inj|injection)\.?\s+", "", line, flags=re.I)

        tail_match = re.search(duration_pattern + r"\s+" + route_pattern + r"\s*(.*)$", line, re.I)
        if not tail_match:
            continue

        duration = _clean(tail_match.group(1))
        route = _clean(tail_match.group(2))
        instructions = _clean(tail_match.group(3))
        before_tail = line[: tail_match.start()].strip(" -|")

        freq_match = re.search(freq_pattern, before_tail, re.I)
        if freq_match:
            frequency = _clean(freq_match.group(1))
            name_strength = before_tail[: freq_match.start()].strip(" -|")
        else:
            frequency = ""
            name_strength = before_tail

        dosage = ""
        dose_matches = list(re.finditer(dose_unit_pattern, name_strength, re.I))
        if dose_matches:
            dose_match = dose_matches[-1]
            dosage = _clean(dose_match.group(1))
            name = _clean(name_strength[: dose_match.start()])
        else:
            name = _clean(name_strength)

        # OCR can turn "60,000 IU" into "60,000 1". Keep the medicine instead of
        # dropping the row; the raw line remains available in instructions.
        name = re.sub(r"\s+\d+(?:,\d{3})?\s+\d+$", "", name).strip()
        if not name:
            continue

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        medications.append(
            {
                "name": name[:80],
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration,
                "instructions": instructions,
                "route": route,
            }
        )

    return medications


def _heuristic_document_analysis(raw_text: str) -> dict:
    lower = raw_text.lower()
    doc_type = "Prescription" if re.search(r"\b(tab|tablet|cap|capsule|syp|syrup|inj|injection|mg|ml)\b", lower) else "Medical Document"
    if re.search(r"\b(hemoglobin|platelet|wbc|rbc|creatinine|glucose|cholesterol|tsh|alt|ast)\b", lower):
        doc_type = "Lab Report"
    if "medication prescribed" in lower or "prescription" in lower:
        doc_type = "Prescription"

    medications = _extract_prescription_medications(raw_text)
    if not medications:
        for line in raw_text.splitlines():
            clean_line = _clean(line)
            if not re.search(r"\b(mg|mcg|g|ml|tablet|tab|capsule|cap|syrup|inj)\b", clean_line, re.I):
                continue
            if re.search(r"\b(hemoglobin|platelet|wbc|rbc|creatinine|glucose|cholesterol|triglycerides|hdl|ldl|tsh|alt|ast|blood sugar|lipid profile)\b", clean_line, re.I):
                continue
            dose_match = re.search(r"(\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|iu|units?))", clean_line, re.I)
            name = re.sub(r"^\W*(tab|tablet|cap|capsule|syp|syrup|inj|injection)\.?\s*", "", clean_line, flags=re.I)
            name = re.split(r"\s+\d", name, maxsplit=1)[0].strip(" -:,")
            if name and dose_match:
                medications.append(
                    {
                        "name": name[:80],
                        "dosage": dose_match.group(1),
                        "frequency": "",
                        "duration": "",
                        "instructions": clean_line,
                        "route": "",
                    }
                )

    labs = []
    for line in raw_text.splitlines():
        clean_line = _clean(line)
        if not re.search(r"\b(hemoglobin|platelet|wbc|rbc|creatinine|glucose|cholesterol|tsh|alt|ast)\b", clean_line, re.I):
            continue
        value_match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*([a-zA-Z/%]+)?", clean_line)
        test = re.split(r"[-:0-9]", clean_line, maxsplit=1)[0].strip(" -:")
        if test and value_match:
            labs.append(
                {
                    "test": test[:80],
                    "value": value_match.group(1),
                    "unit": value_match.group(2) or "",
                    "reference_range": "",
                    "flag": "",
                }
            )

    return {
        "document_type": doc_type,
        "document_summary": "Text was extracted and parsed locally because the AI model was unavailable.",
        "medications": medications[:12],
        "diagnoses": [],
        "lab_results": labs[:20],
        "abnormal_findings": [],
        "red_flags": [],
        "follow_up": "",
        "recommended_specialist": "",
        "notes": raw_text[:700],
    }


def _normalise_analysis(result: dict, document_id: int, raw_text: str, method: str, extraction_error: str) -> dict:
    result = result if isinstance(result, dict) else {}
    return {
        "document_id": document_id,
        "document_type": _clean(result.get("document_type")) or "Medical Document",
        "document_summary": _clean(result.get("document_summary") or result.get("summary")),
        "medications": _normalise_medications(result.get("medications")),
        "diagnoses": _as_list(result.get("diagnoses")),
        "lab_results": _normalise_lab_results(result.get("lab_results") or result.get("labs")),
        "abnormal_findings": _as_list(result.get("abnormal_findings") or result.get("abnormalities")),
        "red_flags": _as_list(result.get("red_flags")),
        "follow_up": _clean(result.get("follow_up") or result.get("follow_up_instructions")),
        "recommended_specialist": _clean(result.get("recommended_specialist") or result.get("specialist")),
        "notes": _clean(result.get("notes")),
        "raw_text": raw_text[:5000],
        "extraction": {
            "method": method,
            "text_found": bool(raw_text.strip()),
            "error": extraction_error,
        },
        "needs_review": bool(extraction_error) or not bool(raw_text.strip()),
    }


@router.post("/analyze-document")
async def analyze_document(req: DocumentAnalysisRequest):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = _resolve_upload_path(base_dir, req.file_path)
    if not full_path:
        raise HTTPException(status_code=400, detail="Invalid document path")

    raw_text, method, extraction_error = extract_text_from_file(full_path)

    if not raw_text:
        return _normalise_analysis(
            {
                "document_type": "Unreadable Document",
                "document_summary": "No readable text could be extracted from this upload.",
                "notes": "Upload a clearer PDF/image or make sure OCR support is available for scanned prescriptions.",
            },
            req.document_id,
            raw_text,
            method,
            extraction_error,
        )

    try:
        result = chat_json(
            DOCUMENT_ANALYSIS_SYSTEM,
            DOCUMENT_ANALYSIS_USER.format(text=raw_text[:3000]),
        )
    except Exception:
        result = _heuristic_document_analysis(raw_text)

    local_meds = _extract_prescription_medications(raw_text)
    if local_meds and not _normalise_medications(result.get("medications")):
        result["medications"] = local_meds

    return _normalise_analysis(result, req.document_id, raw_text, method, extraction_error)
