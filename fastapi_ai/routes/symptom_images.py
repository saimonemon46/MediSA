# MediAI - Symptom Image Analysis Routes
import base64
import json
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile

from prompts.templates import SYMPTOM_IMAGE_ANALYSIS_SYSTEM, SYMPTOM_IMAGE_ANALYSIS_USER

load_dotenv()

router = APIRouter(tags=["Symptom Images"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
GEMINI_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").replace("\ufffd", "").split())


def _extract_json(raw: str) -> dict:
    raw = _clean(raw)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
    return {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_clean(item) for item in value if _clean(item)]
    if isinstance(value, str) and value.strip():
        return [_clean(value)]
    return []


def _normalise_result(result: dict, fallback_note: str = "") -> dict:
    result = result if isinstance(result, dict) else {}
    observations = _as_list(result.get("visible_observations") or result.get("observations"))
    red_flags = _as_list(result.get("red_flags"))
    return {
        "image_type": _clean(result.get("image_type")) or "unclear",
        "visible_observations": observations,
        "possible_relevance": _clean(result.get("possible_relevance")) or fallback_note,
        "red_flags": red_flags,
        "image_quality": _clean(result.get("image_quality")) or "unclear",
        "confidence": _clean(result.get("confidence")) or "low",
        "needs_clinician_review": bool(result.get("needs_clinician_review", True)),
        "model": _clean(result.get("model")) or ("gemini" if GEMINI_API_KEY else "local_fallback"),
        "disclaimer": "Image review is supportive only and cannot diagnose a condition. Seek urgent care for severe or rapidly worsening symptoms.",
    }


async def _analyze_with_gemini(image_bytes: bytes, mime_type: str) -> dict:
    if not GEMINI_API_KEY:
        return {}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": SYMPTOM_IMAGE_ANALYSIS_SYSTEM + "\n\n" + SYMPTOM_IMAGE_ANALYSIS_USER},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
    data = response.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    result = _extract_json(text)
    if result:
        result["model"] = GEMINI_MODEL
    return result


def _fallback_analysis(filename: str, mime_type: str) -> dict:
    name = filename.lower()
    if any(word in name for word in ("rash", "skin", "itch", "allergy")):
        image_type = "rash"
    elif any(word in name for word in ("cut", "wound", "injury", "infect", "pus")):
        image_type = "cut/wound"
    elif any(word in name for word in ("burn", "scald")):
        image_type = "burn"
    elif any(word in name for word in ("swelling", "swollen")):
        image_type = "swelling"
    else:
        image_type = "unclear"

    return {
        "image_type": image_type,
        "visible_observations": [
            "The image was received, but no configured vision model was available for detailed visual interpretation."
        ],
        "possible_relevance": "The uploaded image should be reviewed by a clinician or analyzed again after configuring GEMINI_API_KEY.",
        "red_flags": [],
        "image_quality": "unclear",
        "confidence": "low",
        "needs_clinician_review": True,
        "model": "local_fallback",
    }


@router.post("/analyze-symptom-image")
async def analyze_symptom_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WEBP symptom images are supported.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large. Maximum size is 8MB.")

    result = {}
    if GEMINI_API_KEY:
        try:
            result = await _analyze_with_gemini(image_bytes, file.content_type or "image/jpeg")
        except Exception:
            result = {}

    if not result:
        result = _fallback_analysis(file.filename or "symptom-image", file.content_type or "")

    return _normalise_result(result)


@router.post("/analyze-symptom-image-for-triage")
async def analyze_symptom_image_for_triage(file: UploadFile = File(...)):
    """
    Analyzes a symptom image in the context of medical triage assessment.
    Returns structured analysis to be included in triage reports and assessment recommendations.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WEBP symptom images are supported.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large. Maximum size is 8MB.")

    result = {}
    if GEMINI_API_KEY:
        try:
            result = await _analyze_with_gemini(image_bytes, file.content_type or "image/jpeg")
        except Exception:
            result = {}

    if not result:
        result = _fallback_analysis(file.filename or "symptom-image", file.content_type or "")

    # Enhanced response for triage context
    normalized = _normalise_result(result)
    return {
        **normalized,
        "analysis_context": "triage",
        "assessment_flag": "red" if normalized.get("red_flags") else ("yellow" if "needs_clinician_review" in result else "green")
    }
