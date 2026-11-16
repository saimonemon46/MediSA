#!/usr/bin/env bash
set -e

echo "[MediSA AI] Initializing AI microservice..."

# Build RAG and FRAG indexes if not already created
if [ ! -f "/app/vector_store/mediai.faiss" ]; then
    echo "[MediSA AI] Building RAG and FRAG vector indexes (first-time init)..."
    python /app/rag_pipeline/build_index.py --force --frag || true
    echo "[MediSA AI] Vector indexes initialized."
else
    echo "[MediSA AI] Existing vector store found."
fi

echo "[MediSA AI] Starting FastAPI on 0.0.0.0:${PORT:-8000}..."
exec uvicorn fastapi_ai.main:app --host 0.0.0.0 --port ${PORT:-8000}
