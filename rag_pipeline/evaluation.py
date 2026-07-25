"""Dataset-grounded benchmark creation, validation, and retrieval evaluation for MediSA."""
from __future__ import annotations
import csv, hashlib, json, re, time, uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from rag_pipeline.federated_retriever import retrieve_federated
from rag_pipeline.hospital_loader import hospital_statistics, load_hospital_corpora
from rag_pipeline.hospital_partition import DATA_DIR, canonical_specialty, normalise_text, row_value
from rag_pipeline.rag_engine import load_knowledge_documents, retrieve

BASE_DIR = Path(__file__).parent.parent
BENCHMARK_PATH = BASE_DIR / "rag_pipeline" / "data" / "retrieval_benchmark.json"
RESULTS_DIR = BASE_DIR / "rag_pipeline" / "evaluation_results"


def dataset_document_id(text: str) -> str:
    """Stable source-entity ID used by both retrieval architectures for evaluation."""
    value = str(text or "")
    patterns = [(r"(?:Disease|Disease pattern|Patient symptom description suggests):\s*([^.;]+)", "disease"), (r"Symptom:\s*([^.;]+)", "symptom"), (r"(?:Hospital|Hospital facility):\s*([^.;]+)", "hospital")]
    for pattern, kind in patterns:
        match = re.search(pattern, value, re.I)
        if match:
            return f"{kind}:{normalise_text(match.group(1))}"
    digest = hashlib.sha256(normalise_text(value).encode("utf-8")).hexdigest()[:16]
    return f"passage:{digest}"


def _read_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with path.open(encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle))


def _shared_ids() -> tuple[set[str], dict[str, dict[str, Any]]]:
    traditional = {dataset_document_id(text) for text in load_knowledge_documents()}
    frag_docs: dict[str, dict[str, Any]] = {}
    for corpus in load_hospital_corpora().values():
        for doc in corpus["documents"]:
            frag_docs.setdefault(dataset_document_id(doc.text), {"hospital": doc.hospital_name, "metadata": doc.metadata})
    return traditional & set(frag_docs), frag_docs


def build_initial_benchmark(target_size: int = 36) -> dict[str, Any]:
    """Create dataset-grounded queries only when the evidence exists in both pipelines."""
    shared, frag_docs = _shared_ids()
    items: list[dict[str, Any]] = []
    used: set[str] = set()
    for row in _read_csv("Disease_Specialist.csv"):
        disease, specialist = row_value(row, "disease", "name"), row_value(row, "specialist", "recommended_specialist")
        doc_id = f"disease:{normalise_text(disease)}"
        if not disease or not specialist or doc_id not in shared or doc_id in used:
            continue
        source = frag_docs[doc_id]
        items.append({"query_id": f"Q{len(items)+1:03d}", "query": f"Which specialist is recommended for {disease}?", "category": "doctor_recommendation", "relevant_document_ids": [doc_id], "expected_hospital": source["hospital"], "expected_department": None, "expected_specialist": specialist, "expected_answer": None})
        used.add(doc_id)
        if len(items) >= 24:
            break
    for row in _read_csv("symptoms.csv"):
        symptom = row_value(row, "symptom")
        doc_id = f"symptom:{normalise_text(symptom)}"
        if not symptom or doc_id not in shared or doc_id in used:
            continue
        source = frag_docs[doc_id]
        items.append({"query_id": f"Q{len(items)+1:03d}", "query": f"What healthcare information does MediSA contain for the symptom {symptom}?", "category": "symptom_triage", "relevant_document_ids": [doc_id], "expected_hospital": source["hospital"], "expected_department": None, "expected_specialist": source["metadata"].get("specialist") or None, "expected_answer": None})
        used.add(doc_id)
        if len(items) >= target_size:
            break
    return {"version": 1, "description": "Preliminary retrieval benchmark generated from actual MediSA CSV records shared by Traditional RAG and FRAG. Binary relevance only.", "relevance": "binary", "items": items}


def ensure_benchmark() -> dict[str, Any]:
    if not BENCHMARK_PATH.exists():
        BENCHMARK_PATH.write_text(json.dumps(build_initial_benchmark(), indent=2), encoding="utf-8")
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


def validate_benchmark(benchmark: dict[str, Any]) -> dict[str, Any]:
    shared, frag_docs = _shared_ids()
    valid_hospitals = {record["name"] for record in hospital_statistics().values()}
    specialists = {canonical_specialty(row_value(row, "specialist", "recommended_specialist", "specialization")) for filename in ("Disease_Specialist.csv", "doctors.csv") for row in _read_csv(filename)}
    valid_departments = {normalise_text(str(doc["metadata"].get("specialist") or "")) for doc in frag_docs.values() if doc["metadata"].get("specialist")}
    valid, invalid = [], []
    for item in benchmark.get("items", []):
        problems = []
        if not item.get("query") or not item.get("query_id"): problems.append("query_id and query are required")
        missing = [doc_id for doc_id in item.get("relevant_document_ids", []) if doc_id not in shared]
        if not item.get("relevant_document_ids"): problems.append("at least one relevant_document_id is required")
        if missing: problems.append("unknown or non-shared document IDs: " + ", ".join(missing))
        if item.get("expected_hospital") and item["expected_hospital"] not in valid_hospitals: problems.append("expected hospital does not exist")
        specialist = canonical_specialty(item.get("expected_specialist") or "")
        if specialist and specialist not in specialists: problems.append("expected specialist does not exist")
        if item.get("expected_department") and (not isinstance(item["expected_department"], str) or normalise_text(item["expected_department"]) not in valid_departments): problems.append("expected department does not exist")
        (invalid if problems else valid).append({"item": item, "problems": problems} if problems else item)
    return {"valid_items": valid, "invalid_items": invalid, "shared_document_count": len(shared), "fragment_document_count": len(frag_docs)}


def _metrics(retrieved: list[str], relevant: set[str], k: int) -> dict[str, Any]:
    hits = [doc_id for doc_id in retrieved[:k] if doc_id in relevant]
    precision = len(hits) / k
    recall = len(hits) / len(relevant) if relevant else None
    first = next((index + 1 for index, doc_id in enumerate(retrieved[:k]) if doc_id in relevant), None)
    reciprocal_rank = 1 / first if first else 0.0
    dcg = sum(1 / __import__("math").log2(index + 2) for index, doc_id in enumerate(retrieved[:k]) if doc_id in relevant)
    ideal = sum(1 / __import__("math").log2(index + 2) for index in range(min(k, len(relevant))))
    return {"relevant_hits": hits, "precision_at_k": precision, "recall_at_k": recall, "reciprocal_rank": reciprocal_rank, "ndcg_at_k": dcg / ideal if ideal else None, "hit_rate_at_k": 1.0 if hits else 0.0}


def _aggregate(rows: list[dict[str, Any]], system: str) -> dict[str, Any]:
    fields = ["precision_at_k", "recall_at_k", "reciprocal_rank", "ndcg_at_k", "hit_rate_at_k", "latency_ms"]
    values = {field: [row[system][field] for row in rows if row[system].get(field) is not None] for field in fields}
    return {field: (sum(items) / len(items) if items else None) for field, items in values.items()}


def run_benchmark(k: int = 5) -> dict[str, Any]:
    if k < 1 or k > 25: raise ValueError("K must be between 1 and 25")
    validation = validate_benchmark(ensure_benchmark())
    rows = []
    for item in validation["valid_items"]:
        start = time.perf_counter(); traditional_ids = list(dict.fromkeys(dataset_document_id(text) for text in retrieve(item["query"], top_k=k))); traditional_latency = (time.perf_counter()-start)*1000
        start = time.perf_counter(); frag = retrieve_federated(item["query"], hospital_top_k=k, final_top_k=k); frag_ids = list(dict.fromkeys(dataset_document_id(str(doc.get("text", ""))) for doc in frag["fused_evidence"])); frag_latency = (time.perf_counter()-start)*1000
        relevant = set(item["relevant_document_ids"])
        traditional = _metrics(traditional_ids, relevant, k) | {"retrieved_document_ids": traditional_ids, "latency_ms": round(traditional_latency, 3)}
        federated = _metrics(frag_ids, relevant, k) | {"retrieved_document_ids": frag_ids, "latency_ms": round(frag_latency, 3)}
        rows.append({"query_id": item["query_id"], "query": item["query"], "category": item["category"], "traditional_rag": traditional, "frag": federated})
    categories = {}
    for category in sorted({row["category"] for row in rows}):
        selected = [row for row in rows if row["category"] == category]
        categories[category] = {"query_count": len(selected), "traditional_rag": _aggregate(selected, "traditional_rag"), "frag": _aggregate(selected, "frag")}
    result = {"run_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "benchmark_size": len(rows), "k": k, "ground_truth": "dataset-labeled", "relevance": "binary", "configuration": {"traditional": "combined/global corpus retrieval", "frag": "independent hospital retrieval + existing fusion/reranking", "embedding_model": "all-MiniLM-L6-v2", "answer_generation": "excluded"}, "traditional_rag": _aggregate(rows, "traditional_rag"), "frag": _aggregate(rows, "frag"), "category_metrics": categories, "per_query_results": rows, "invalid_benchmark_items": validation["invalid_items"]}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (RESULTS_DIR / f"{result['run_id']}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def latest_results() -> dict[str, Any] | None:
    path = RESULTS_DIR / "latest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None