#!/usr/bin/env python3
# ============================================================
# MediAI — RAG Index Builder
# Run this script once to build the FAISS vector index
# from the CSV knowledge base files.
#
# Usage:
#   cd medical_triage
#   python rag_pipeline/build_index.py
#   python rag_pipeline/build_index.py --force   (rebuild)
# ============================================================

import sys
import os
import argparse

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rag_pipeline.rag_engine import build_index, retrieve, format_context


def main():
    parser = argparse.ArgumentParser(description="Build MediAI RAG vector index")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--test",  action="store_true", help="Test retrieval after building")
    args = parser.parse_args()

    print("=" * 60)
    print("MediAI RAG Index Builder")
    print("=" * 60)

    build_index(force=args.force)

    if args.test:
        print("\n--- Test retrieval ---")
        test_queries = [
            "high fever and severe headache",
            "chest pain and shortness of breath",
            "persistent cough",
            "cardiologist in Dhaka",
        ]
        for q in test_queries:
            print(f"\nQuery: {q}")
            docs = retrieve(q, top_k=3)
            for d in docs:
                print(f"  -> {d[:100]}...")

    print("\nDone.")


if __name__ == "__main__":
    main()
