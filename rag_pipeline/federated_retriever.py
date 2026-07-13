"""Federated retrieval over simulated hospital vector stores."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np

from rag_pipeline.fusion import format_consolidated_context, fuse_evidence
from rag_pipeline.hospital_loader import EvidenceDocument, load_hospital_corpora, load_national_documents
from rag_pipeline.rag_engine import RAG_AVAILABLE, embed
from rag_pipeline.reranker import lexical_similarity

try:
    import faiss
except ImportError:  # pragma: no cover - guarded by RAG_AVAILABLE at runtime
    faiss = None


BASE_DIR = Path(__file__).parent.parent
FRAG_STORE_DIR = BASE_DIR / "vector_store" / "frag"


class HospitalVectorStore:
    """Own vector database for one simulated hospital."""

    def __init__(self, hospital_id: str, documents: Iterable[EvidenceDocument]):
        self.hospital_id = hospital_id
        self.documents = list(documents)
        self.index = None
        self.store_dir = FRAG_STORE_DIR / hospital_id
        self.index_path = self.store_dir / "index.faiss"
        self.docs_path = self.store_dir / "docs.pkl"

    def ensure_loaded(self, force_rebuild: bool = False) -> None:
        if not RAG_AVAILABLE or faiss is None:
            return
        self.store_dir.mkdir(parents=True, exist_ok=True)
        if force_rebuild or not self.index_path.exists() or not self.docs_path.exists():
            self.build()
        self.index = faiss.read_index(str(self.index_path))
        with open(self.docs_path, "rb") as handle:
            self.documents = pickle.load(handle)

    def build(self) -> None:
        if not RAG_AVAILABLE or faiss is None or not self.documents:
            return
        self.store_dir.mkdir(parents=True, exist_ok=True)
        vectors = embed([doc.text for doc in self.documents])
        if vectors is None:
            return
        index = faiss.IndexFlatIP(vectors.shape[1])
        faiss.normalize_L2(vectors)
        index.add(vectors.astype("float32"))
        faiss.write_index(index, str(self.index_path))
        with open(self.docs_path, "wb") as handle:
            pickle.dump(self.documents, handle)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, object]]:
        if not self.documents:
            return []
        if not RAG_AVAILABLE or faiss is None:
            return self._keyword_search(query, top_k)
        self.ensure_loaded()
        if self.index is None:
            return self._keyword_search(query, top_k)
        qvec = embed([query])
        if qvec is None:
            return self._keyword_search(query, top_k)
        faiss.normalize_L2(qvec)
        scores, indices = self.index.search(qvec.astype("float32"), min(top_k, len(self.documents)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.documents):
                results.append(self._result(self.documents[idx], float(score)))
        return results

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, object]]:
        scored = [(lexical_similarity(query, doc.text), doc) for doc in self.documents]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._result(doc, score) for score, doc in scored[:top_k] if score > 0] or [
            self._result(doc, 0.0) for doc in self.documents[:top_k]
        ]

    @staticmethod
    def _result(doc: EvidenceDocument, score: float) -> Dict[str, object]:
        return {
            "doc_id": doc.doc_id,
            "text": doc.text,
            "hospital_id": doc.hospital_id,
            "hospital_name": doc.hospital_name,
            "source_type": doc.source_type,
            "metadata": doc.metadata,
            "score": round(float(score), 6),
        }


class FederatedRetriever:
    """Query each hospital independently, then fuse and rerank evidence."""

    def __init__(self, include_national: bool = True):
        corpora = load_hospital_corpora()
        self.hospital_stores = {
            hospital_id: HospitalVectorStore(hospital_id, corpus["documents"])
            for hospital_id, corpus in corpora.items()
        }
        self.national_store: Optional[HospitalVectorStore] = (
            HospitalVectorStore("national", load_national_documents()) if include_national else None
        )

    def build_indexes(self, force: bool = False) -> None:
        for store in self.hospital_stores.values():
            store.ensure_loaded(force_rebuild=force)
        if self.national_store:
            self.national_store.ensure_loaded(force_rebuild=force)

    def retrieve(self, query: str, hospital_top_k: int = 5, final_top_k: int = 12) -> Dict[str, object]:
        per_hospital: Dict[str, List[Dict[str, object]]] = {}
        raw_results: List[Dict[str, object]] = []

        for hospital_id, store in self.hospital_stores.items():
            results = store.search(query, top_k=hospital_top_k)
            per_hospital[hospital_id] = results
            raw_results.extend(results)

        if self.national_store:
            national_results = self.national_store.search(query, top_k=max(3, hospital_top_k))
            per_hospital["national"] = national_results
            raw_results.extend(national_results)

        fused = fuse_evidence(query, raw_results, limit=final_top_k)
        return {
            "query": query,
            "per_hospital": per_hospital,
            "raw_evidence_count": len(raw_results),
            "fused_evidence": fused,
            "context": format_consolidated_context(fused),
        }


_default_retriever: Optional[FederatedRetriever] = None


def get_federated_retriever() -> FederatedRetriever:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = FederatedRetriever(include_national=True)
    return _default_retriever


def retrieve_federated(query: str, hospital_top_k: int = 5, final_top_k: int = 12) -> Dict[str, object]:
    return get_federated_retriever().retrieve(query, hospital_top_k=hospital_top_k, final_top_k=final_top_k)
