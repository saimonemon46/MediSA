# AGENTS.md — MediSA Developer & Agent Guide

## Architecture Overview
MediSA is an AI-powered medical triage, federated RAG, and healthcare assistant platform.
The tech stack consists of:
- **Frontend**: Next.js (React) application with dark medical UI, conversational triage, document upload, doctor booking, and research evaluation dashboards.
- **Backend**: Django REST backend (`backend_django/`) handling authentication, health profiles, appointments, reports, medications, and medical document records.
- **AI Microservice**: FastAPI service (`fastapi_ai/`) running LangGraph orchestration, multi-turn patient state tracking, diagnostic ranking, prescription OCR, Gemini vision analysis, and Federated RAG (FRAG).
- **Dual RAG Engine**: Traditional FAISS vector store + Federated RAG across Bangladeshi hospital partitions (`rag_pipeline/`).

## Key Directories & Entry Points
- `backend_django/`: Django project root (`manage.py`, `medisa_core/`, API endpoints matching `/api/...`)
- `fastapi_ai/main.py`: FastAPI microservice entry point (Port 8000)
- `frontend_next/`: Next.js frontend application (Port 3000)
- `rag_pipeline/`: Traditional & federated RAG implementations, vector indices, and hospital corpora
- `test_enhancements.py`: Comprehensive test suite for patient state and diagnostic ranking
- `docker-compose.yml`: Multi-container orchestration (Next.js, Django, FastAPI, MariaDB/PostgreSQL)

## Standard Commands
- Run AI Service: `uvicorn main:app --app-dir fastapi_ai --host 0.0.0.0 --port 8000 --reload`
- Run Django Backend: `python manage.py runserver 0.0.0.0:8082` (inside `backend_django`)
- Run Next.js Frontend: `npm run dev` (inside `frontend_next`)
- Run Unit Tests: `python test_enhancements.py`
