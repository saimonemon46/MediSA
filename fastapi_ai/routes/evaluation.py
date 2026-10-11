"""Research evaluation endpoints that orchestrate MediSA's existing retrieval pipelines."""
from __future__ import annotations
import os
import sys
import re
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException
from models.schemas import EvaluationComparisonRequest
from rag_pipeline.frag_engine import build_frag_context
from rag_pipeline.hospital_loader import hospital_statistics, load_national_documents
from rag_pipeline.rag_engine import format_context, load_knowledge_documents, retrieve
from rag_pipeline.reranker import lexical_similarity

router = APIRouter(prefix="/evaluation", tags=["Research Evaluation"])
SYSTEM_PROMPT = """You are MediSA, a cautious healthcare research decision-support assistant. Use only supplied evidence. Do not diagnose with certainty, prescribe treatment, or replace emergency care. For chest pain, breathing difficulty, stroke signs, severe bleeding, confusion, or loss of consciousness, advise urgent emergency evaluation."""

def _title(text: str) -> str:
    match = re.search(r"(?:Disease|Symptom|Hospital facility|Patient symptom description suggests|Disease pattern):\s*([^.;]+)", text, re.I)
    return match.group(1).strip() if match else text[:92].strip() + ("..." if len(text) > 92 else "")

def _traditional_documents(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    documents = retrieve(query, top_k=top_k)
    return [{"rank": i, "document_id": f"traditional:{i}", "title": _title(text), "text": text, "hospital": "Combined MediSA knowledge base", "department": None, "retrieval_score": round(lexical_similarity(query, text), 6), "reranking_score": None} for i, text in enumerate(documents, 1)]

def _frag_documents(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output = []
    for rank, item in enumerate(evidence, 1):
        metadata = item.get("metadata") or {}
        output.append({"rank": rank, "document_id": item.get("doc_id"), "title": metadata.get("disease") or metadata.get("symptom") or metadata.get("facility") or _title(str(item.get("text", ""))), "text": item.get("text", ""), "hospital": item.get("hospital_name") or item.get("hospital_id"), "hospital_id": item.get("hospital_id"), "department": metadata.get("specialist"), "retrieval_score": item.get("score"), "reranking_score": item.get("fusion_score"), "source_type": item.get("source_type")})
    return output

def _answer(query: str, context: str) -> str:
    try:
        from models.llm_client import chat
        answer = chat(SYSTEM_PROMPT, f"Question: {query}\n\nEvidence:\n{context}\n\nGive a concise, safety-conscious research response.", max_tokens=550)
        if answer and "unable to generate" not in answer.lower():
            return answer
    except Exception:
        pass
    return "Answer generation is unavailable because the configured LLM could not be reached. Retrieved evidence is shown below for research inspection."


@router.get("/dataset-status")
async def dataset_status():
    """Actual corpus counts; benchmark quality metrics require labeled ground truth."""
    hospitals = hospital_statistics()
    return {
        "traditional_rag_documents": len(load_knowledge_documents()),
        "hospital_partitions": list(hospitals.values()),
        "national_reference_documents": len(load_national_documents()),
        "benchmark_metrics_available": False,
        "benchmark_note": "No labeled relevance or answer-quality benchmark is configured yet.",
    }
@router.post("/compare")
async def compare(req: EvaluationComparisonRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")
    try:
        start = time.perf_counter()
        traditional_docs = _traditional_documents(query)
        traditional_answer = _answer(query, format_context([item["text"] for item in traditional_docs]))
        traditional_latency = round((time.perf_counter() - start) * 1000, 2)
        start = time.perf_counter()
        frag_retrieval = build_frag_context(query, top_k_per_hospital=5, final_top_k=10)
        frag_docs = _frag_documents(frag_retrieval["fused_evidence"])
        frag_answer = _answer(query, frag_retrieval["context"])
        frag_latency = round((time.perf_counter() - start) * 1000, 2)
        hospitals = []
        for hospital_id, documents in frag_retrieval["per_hospital"].items():
            name = documents[0].get("hospital_name") if documents else hospital_id
            hospitals.append({"hospital_id": hospital_id, "hospital_name": name or hospital_id, "documents_retrieved": len(documents), "top_retrieval_score": max((item.get("score") or 0 for item in documents), default=None), "documents": _frag_documents(documents)})
        return {"query": query, "traditional_rag": {"answer": traditional_answer, "retrieved_documents": traditional_docs, "latency_ms": traditional_latency, "metrics": {"faithfulness": None, "answer_relevance": None}}, "frag": {"answer": frag_answer, "searched_hospitals": hospitals, "retrieved_documents": [doc for hospital in hospitals for doc in hospital["documents"]], "reranked_documents": frag_docs, "latency_ms": frag_latency, "metrics": {"faithfulness": None, "answer_relevance": None}, "fusion_method": "Weighted semantic + lexical fusion reranking"}}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison could not run: {exc}")

from rag_pipeline.evaluation import ensure_benchmark, latest_results, run_benchmark, validate_benchmark
from models.schemas import EvaluationRunRequest

@router.get("/benchmark")
async def benchmark_status():
    validation = validate_benchmark(ensure_benchmark())
    return {"benchmark_size": len(validation["valid_items"]), "invalid_items": validation["invalid_items"], "shared_document_count": validation["shared_document_count"], "relevance": "binary", "ground_truth": "dataset-labeled"}

@router.post("/run")
async def run_retrieval_evaluation(req: EvaluationRunRequest):
    try:
        return run_benchmark(req.k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Benchmark evaluation could not run: {exc}")

@router.get("/results")
async def evaluation_results():
    result = latest_results()
    if result is None:
        raise HTTPException(status_code=404, detail="No completed evaluation run exists yet.")
    return result
