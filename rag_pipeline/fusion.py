"""Evidence fusion for Federated RAG."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Dict, Iterable, List

from rag_pipeline.reranker import EvidenceReranker


def normalize_passage(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())
    return " ".join(cleaned.split())


def passage_key(text: str) -> str:
    return hashlib.sha256(normalize_passage(text).encode("utf-8", errors="ignore")).hexdigest()


def deduplicate_passages(evidence: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    """Remove duplicate passages while preserving all contributing sources."""
    grouped: Dict[str, Dict[str, object]] = {}
    source_map = defaultdict(list)

    for item in evidence:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        key = passage_key(text)
        source_map[key].append(
            {
                "hospital_id": item.get("hospital_id"),
                "hospital_name": item.get("hospital_name"),
                "source_type": item.get("source_type"),
                "doc_id": item.get("doc_id"),
            }
        )
        if key not in grouped or float(item.get("score") or 0.0) > float(grouped[key].get("score") or 0.0):
            grouped[key] = dict(item)

    deduped = []
    for key, item in grouped.items():
        item["dedupe_key"] = key
        item["source_count"] = len(source_map[key])
        item["sources"] = source_map[key]
        deduped.append(item)
    return deduped


def fuse_evidence(query: str, evidence: Iterable[Dict[str, object]], limit: int = 12) -> List[Dict[str, object]]:
    deduped = deduplicate_passages(evidence)
    return EvidenceReranker().rerank(query, deduped, limit=limit)


def format_consolidated_context(evidence: Iterable[Dict[str, object]]) -> str:
    items = list(evidence)
    if not items:
        return "No federated medical evidence retrieved."

    lines = []
    for index, item in enumerate(items, start=1):
        source = item.get("hospital_name") or item.get("hospital_id") or "Unknown source"
        source_type = item.get("source_type") or "evidence"
        score = item.get("fusion_score", item.get("semantic_score", item.get("score", "")))
        score_text = f", score={score}" if score != "" else ""
        lines.append(f"[{index}] Source: {source} ({source_type}{score_text})")
        lines.append(f"Evidence: {item.get('text')}")
    return "\n".join(lines)
