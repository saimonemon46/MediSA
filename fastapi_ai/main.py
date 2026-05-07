# ============================================================
# MediAI — FastAPI AI Service
# Main application entry point
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.triage import router as triage_router
from routes.documents import router as docs_router
from routes.doctors import router as doctors_router
from routes.symptom_images import router as symptom_images_router
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


@app.get("/")
async def root():
    return {
        "service": "MediAI AI Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "POST /generate-questions",
            "POST /generate-report",
            "POST /analyze-document",
            "POST /analyze-symptom-image",
            "GET  /doctor-recommendation",
            "POST /doctor-recommendation",
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
