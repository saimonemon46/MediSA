# ============================================================
# MediAI — FastAPI AI Service
# Main application entry point
# ============================================================

import os
import sys

# Ensure both fastapi_ai and project root are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.triage import router as triage_router
from routes.documents import router as docs_router
from routes.doctors import router as doctors_router
from routes.symptom_images import router as symptom_images_router
from routes.evaluation import router as evaluation_router
import uvicorn

app = FastAPI(
    title="MediAI AI Service",
    description="RAG-powered medical triage and health assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage_router)
app.include_router(docs_router)
app.include_router(doctors_router)
app.include_router(symptom_images_router)
app.include_router(evaluation_router)


@app.get("/")
async def root():
    return {
        "service": "MediAI AI Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "POST /generate-questions",
            "POST /process-message",
            "POST /generate-report",
            "POST /submit-answers",
            "POST /analyze-document",
            "POST /analyze-symptom-image",
            "POST /analyze-symptom-image-for-triage",
            "GET  /doctor-recommendation",
            "POST /doctor-recommendation",
            "GET  /evaluation/dataset-status",
            "POST /evaluation/compare",
            "GET  /evaluation/benchmark",
            "POST /evaluation/run",
            "GET  /evaluation/results",
            "GET  /health",
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
