# MediAI — Triage Routes
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from models.schemas import SymptomRequest, ReportRequest
from workflow import run_question_generation, run_report_generation

router = APIRouter(tags=["Triage"])


@router.post("/generate-questions")
async def generate_questions(req: SymptomRequest):
    """
    Step 1 of the triage pipeline.
    Accepts primary symptom, runs RAG retrieval, returns follow-up questions.
    """
    if not req.symptom.strip():
        raise HTTPException(status_code=400, detail="Symptom text is required")
    try:
        result = run_question_generation(
            symptom=req.symptom,
            user_id=req.user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-report")
async def generate_report(req: ReportRequest):
    """
    Step 2 of the triage pipeline.
    Accepts session ID, symptom, user answers, and optional image analysis.
    Runs full triage analysis via LangGraph and returns the report.
    """
    if not req.symptom.strip():
        raise HTTPException(status_code=400, detail="Symptom text is required")
    try:
        result = run_report_generation(
            session_id=req.session_id,
            symptom=req.symptom,
            answers=req.answers,
            user_id=req.user_id,
            image_analysis=req.image_analysis
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-answers")
async def submit_answers(req: ReportRequest):
    """Alias for /generate-report for compatibility."""
    return await generate_report(req)
