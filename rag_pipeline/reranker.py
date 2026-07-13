"""Semantic and lexical reranking utilities for FRAG evidence."""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List

import numpy as np

from rag_pipeline.rag_engine import embed

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "of", "on", "or", "that", "the", "to", "with",
    "my", "i", "am", "this", "these", "those", "then", "than",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _cosine_scores(query: str, texts: List[str]) -> List[float] | None:
    vectors = embed([query] + texts)
    if vectors is None or len(vectors) != len(texts) + 1:
        return None
    qvec = vectors[0]
    dvecs = vectors[1:]
    qnorm = np.linalg.norm(qvec)
    dnorms = np.linalg.norm(dvecs, axis=1)
    denom = qnorm * dnorms
    denom[denom == 0] = 1.0
    return ((dvecs @ qvec) / denom).astype(float).tolist()


def lexical_similarity(query: str, text: str) -> float:
    q = _tokens(query)
    d = _tokens(text)
    if not q or not d:
        return 0.0
    overlap = len(q & d)
    return overlap / math.sqrt(len(q) * len(d))


class EvidenceReranker:
    """Rerank merged evidence using semantic similarity with safe fallback."""

    def rerank(self, query: str, evidence: Iterable[Dict[str, object]], limit: int = 12) -> List[Dict[str, object]]:
        items = [dict(item) for item in evidence if str(item.get("text", "")).strip()]
        if not items:
            return []

        texts = [str(item["text"]) for item in items]
        semantic_scores = _cosine_scores(query, texts)
        for index, item in enumerate(items):
            lexical = lexical_similarity(query, texts[index])
            semantic = semantic_scores[index] if semantic_scores is not None else lexical
            retrieval_score = float(item.get("score") or 0.0)
            source_bonus = 0.04 if item.get("hospital_id") == "national" else 0.0
            item["semantic_score"] = round(float(semantic), 6)
            item["lexical_score"] = round(float(lexical), 6)
            item["fusion_score"] = round((0.72 * semantic) + (0.18 * lexical) + (0.10 * retrieval_score) + source_bonus, 6)

        items.sort(key=lambda item: item["fusion_score"], reverse=True)
        return items[:limit]
