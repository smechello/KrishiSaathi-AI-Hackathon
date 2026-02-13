#!/usr/bin/env python
"""Ingest all knowledge-base JSON documents into ChromaDB.

This is a standalone script you can run manually whenever the knowledge base
files change.  It will:

  1. (Optionally) wipe existing collections so you get a clean re-index.
  2. Load every JSON file from  backend/knowledge_base/documents/
  3. Flatten each record into readable text.
  4. Generate embeddings via Google Gemini Embedding API (gemini-embedding-001).
  5. Upsert everything into persistent ChromaDB collections under  data/chroma_db/

Usage
-----
    # From the project root  (KrishiSaathi-AI-Hackathon/)
    python -m scripts.ingest_knowledge_base            # incremental upsert
    python -m scripts.ingest_knowledge_base --fresh     # wipe & re-ingest

The script is safe to re-run — ChromaDB upsert uses deterministic IDs, so
duplicate entries are never created.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# ── Make sure the project root is on sys.path so `backend.*` imports work ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.knowledge_base.rag_engine import RAGEngine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete all existing collections before ingesting (clean re-index).",
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Override the documents directory (default: backend/knowledge_base/documents/).",
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  KrishiSaathi — Knowledge Base Ingestion")
    print("=" * 60)
    print()

    # ── Initialise engine ──────────────────────────────────────────────
    logger.info("Initialising RAG engine ...")
    engine = RAGEngine()

    # ── Optionally wipe ────────────────────────────────────────────────
    if args.fresh:
        logger.info("--fresh flag set → deleting all existing collections ...")
        engine.delete_all()
        print("  ✓ Existing collections deleted.\n")

    # ── Pre-ingestion stats ────────────────────────────────────────────
    pre_stats = engine.collection_stats()
    logger.info("Pre-ingestion counts: %s", pre_stats)

    # ── Run ingestion ──────────────────────────────────────────────────
    start = time.time()
    logger.info("Starting document ingestion ...")
    stats = engine.ingest_documents(documents_dir=args.docs_dir)
    elapsed = time.time() - start

    # ── Post-ingestion report ──────────────────────────────────────────
    post_stats = engine.collection_stats()

    print()
    print("-" * 60)
    print("  Ingestion Report")
    print("-" * 60)
    total = 0
    for col_name, count in post_stats.items():
        ingested = stats.get(col_name, 0)
        total += count
        print(f"  {col_name:<25s}  {count:>4d} docs  (ingested {ingested} this run)")
    print("-" * 60)
    print(f"  TOTAL                       {total:>4d} docs")
    print(f"  Time elapsed                {elapsed:.1f}s")
    print("-" * 60)
    print()

    # ── Quick sanity query ─────────────────────────────────────────────
    #  After --fresh, the in-process HNSW index can fail.  We reload
    #  the engine from persisted data to work around this edge case.
    print("Running sanity check queries ...")
    try:
        _sanity_check(engine)
    except Exception:
        print("  ⚠ Re-loading engine from disk for sanity check ...")
        engine = RAGEngine()
        _sanity_check(engine)

    print()
    print("✅ Ingestion complete!  ChromaDB persisted at:")
    print(f"   {engine._persist_dir}")
    print()


def _sanity_check(engine: RAGEngine) -> None:
    """Run a few test queries to verify the index is working."""
    test_queries = [
        ("tomato leaf spots", ["crop_diseases"]),
        ("Rythu Bandhu eligibility", ["government_schemes"]),
        ("red soil management tips", ["soil_data"]),
        ("rice market price Warangal", ["market_data"]),
        ("SRI method water saving", ["farming_practices"]),
    ]
    for query, collections in test_queries:
        results = engine.query(query, collection_names=collections, n_results=2)
        if results:
            top = results[0]
            dist = top["distance"]
            snippet = top["document"][:80].replace("\n", " ")
            print(f"  ✓ \"{query}\"  →  dist={dist:.4f}  →  {snippet}...")
        else:
            print(f"  ✗ \"{query}\"  →  NO RESULTS (collection may be empty)")


if __name__ == "__main__":
    main()
