#!/usr/bin/env python
"""Ingest all knowledge-base JSON documents into ChromaDB.

This is a standalone script you can run manually whenever the knowledge base
files change.  It will:

  1. Validate all JSON sources before touching the database.
  2. (Optionally) wipe existing collections so you get a clean re-index.
  3. Load every JSON file from BOTH directories:
        backend/knowledge_base/documents/   (5 files, ~160 records)
        backend/data/                        (3 files, ~58 records)
  4. Flatten each record into readable text.
  5. Generate embeddings via Google Gemini Embedding API (gemini-embedding-001).
  6. Upsert everything into persistent ChromaDB collections under data/chroma_db/

Usage
-----
    # From the project root  (KrishiSaathi-AI-Hackathon/)
    python -m scripts.ingest_knowledge_base            # incremental upsert
    python -m scripts.ingest_knowledge_base --fresh     # wipe & re-ingest
    python -m scripts.ingest_knowledge_base --dry-run   # validate only, no DB writes
    python -m scripts.ingest_knowledge_base --collection crop_diseases  # single collection
    python -m scripts.ingest_knowledge_base --list      # show available collections

The script is safe to re-run — ChromaDB upsert uses deterministic IDs, so
duplicate entries are never created.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

# ── Make sure the project root is on sys.path so `backend.*` imports work ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.knowledge_base.rag_engine import (  # noqa: E402
    COLLECTION_MAP,
    ROOT_KEY_MAP,
    RAGEngine,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Validation ─────────────────────────────────────────────────────────

def find_json_file(filename: str) -> str | None:
    """Locate a JSON file across both source directories."""
    for subdir in ["backend/knowledge_base/documents", "backend/data"]:
        path = os.path.join(PROJECT_ROOT, subdir, filename)
        if os.path.exists(path):
            return path
    return None


def validate_sources() -> tuple[dict[str, dict], list[str]]:
    """Validate all JSON source files.

    Returns (file_info, errors) where file_info maps filename → {path, count, ok}.
    """
    file_info: dict[str, dict] = {}
    errors: list[str] = []

    for filename, collection_name in COLLECTION_MAP.items():
        filepath = find_json_file(filename)
        info = {"path": filepath, "collection": collection_name, "count": 0, "ok": False}

        if filepath is None:
            errors.append(f"  ✗ {filename:<30s}  FILE NOT FOUND")
            file_info[filename] = info
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as exc:
            errors.append(f"  ✗ {filename:<30s}  INVALID JSON: {exc}")
            file_info[filename] = info
            continue

        # Extract records
        root_key = ROOT_KEY_MAP.get(filename)
        if root_key is None:
            records = raw if isinstance(raw, list) else []
        else:
            records = raw.get(root_key, []) if isinstance(raw, dict) else []

        if not records:
            errors.append(f"  ✗ {filename:<30s}  EMPTY (no records found)")
            file_info[filename] = info
            continue

        # Check that records are dicts
        bad = sum(1 for r in records if not isinstance(r, dict))
        if bad:
            errors.append(f"  ✗ {filename:<30s}  {bad} records are not objects")
            file_info[filename] = info
            continue

        info["count"] = len(records)
        info["ok"] = True
        file_info[filename] = info

    return file_info, errors


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest knowledge base into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m scripts.ingest_knowledge_base            # full ingestion\n"
            "  python -m scripts.ingest_knowledge_base --fresh     # wipe + re-ingest\n"
            "  python -m scripts.ingest_knowledge_base --dry-run   # validate only\n"
            "  python -m scripts.ingest_knowledge_base --collection crop_diseases\n"
        ),
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Delete all existing collections before ingesting (clean re-index).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate all JSON sources without writing to ChromaDB.",
    )
    parser.add_argument(
        "--collection", type=str, default=None,
        help="Ingest only a specific collection (e.g., crop_diseases, mandi_prices).",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_collections",
        help="List all available collections and their source files, then exit.",
    )
    parser.add_argument(
        "--docs-dir", type=str, default=None,
        help="Override the documents directory.",
    )
    args = parser.parse_args()

    print()
    print("=" * 65)
    print("  KrishiSaathi — Knowledge Base Ingestion Pipeline")
    print("=" * 65)
    print()

    # ── List mode ──────────────────────────────────────────────────────
    if args.list_collections:
        print(f"  {'Collection':<25s}  {'Source File':<35s}  {'Root Key'}")
        print(f"  {'─' * 25}  {'─' * 35}  {'─' * 15}")
        for filename, col_name in COLLECTION_MAP.items():
            root = ROOT_KEY_MAP.get(filename) or "(bare list)"
            path = find_json_file(filename)
            status = "✓" if path else "✗"
            relpath = os.path.relpath(path, PROJECT_ROOT) if path else "NOT FOUND"
            print(f"  {col_name:<25s}  {status} {relpath:<33s}  {root}")
        print()
        return

    # ── Step 1: Validate all sources ───────────────────────────────────
    print("Step 1/4: Validating JSON sources ...")
    file_info, errors = validate_sources()

    total_records = sum(info["count"] for info in file_info.values())
    valid_files = sum(1 for info in file_info.values() if info["ok"])

    print(f"\n  {'File':<35s}  {'Collection':<25s}  {'Records':>8s}  Status")
    print(f"  {'─' * 35}  {'─' * 25}  {'─' * 8}  {'─' * 8}")
    for filename, info in file_info.items():
        status = "✓ OK" if info["ok"] else "✗ FAIL"
        relpath = os.path.relpath(info["path"], PROJECT_ROOT) if info["path"] else "NOT FOUND"
        print(f"  {relpath:<35s}  {info['collection']:<25s}  {info['count']:>8d}  {status}")
    print(f"  {'─' * 35}  {'─' * 25}  {'─' * 8}  {'─' * 8}")
    print(f"  {'TOTAL':<35s}  {valid_files} valid files{' ' * 13}  {total_records:>8d}")
    print()

    if errors:
        print("  ⚠ Validation warnings:")
        for e in errors:
            print(f"    {e}")
        print()

    if total_records == 0:
        print("  ✗ No valid records found. Aborting.")
        sys.exit(1)

    # ── Dry-run exit ───────────────────────────────────────────────────
    if args.dry_run:
        print("  --dry-run: Validation complete. No data was written.")
        print()
        return

    # ── Step 2: Initialise engine ──────────────────────────────────────
    print("Step 2/4: Initialising RAG engine ...")
    engine = RAGEngine()

    # ── Step 3: Optionally wipe + ingest ───────────────────────────────
    if args.fresh:
        print("\nStep 3/4: Clean re-index (--fresh) ...")
        if args.collection:
            # Only delete the targeted collection
            try:
                engine._client.delete_collection(args.collection)
                print(f"  ✓ Deleted collection: {args.collection}")
            except Exception:
                print(f"  (collection {args.collection} did not exist)")
        else:
            engine.delete_all()
            print("  ✓ All existing collections deleted.")
    else:
        print("\nStep 3/4: Incremental upsert (existing data preserved) ...")

    # Pre-ingestion stats
    pre_stats = engine.collection_stats()

    start = time.time()

    if args.collection:
        # Targeted single-collection ingestion
        # Find the filename for this collection
        target_files = {fn: cn for fn, cn in COLLECTION_MAP.items() if cn == args.collection}
        if not target_files:
            print(f"  ✗ Unknown collection: {args.collection}")
            print(f"    Available: {', '.join(sorted(set(COLLECTION_MAP.values())))}")
            sys.exit(1)
        print(f"\n  Ingesting only: {args.collection}")
        stats = engine.ingest_documents(documents_dir=args.docs_dir)
        # Filter stats to only the target
        stats = {k: v for k, v in stats.items() if k == args.collection}
    else:
        stats = engine.ingest_documents(documents_dir=args.docs_dir)

    elapsed = time.time() - start

    # ── Step 4: Report ─────────────────────────────────────────────────
    post_stats = engine.collection_stats()

    print(f"\nStep 4/4: Ingestion Report")
    print(f"  {'─' * 60}")
    print(f"  {'Collection':<25s}  {'Before':>8s}  {'Ingested':>10s}  {'After':>8s}")
    print(f"  {'─' * 25}  {'─' * 8}  {'─' * 10}  {'─' * 8}")
    grand_total = 0
    for col_name in sorted(set(COLLECTION_MAP.values())):
        before = pre_stats.get(col_name, 0)
        ingested = stats.get(col_name, 0)
        after = post_stats.get(col_name, 0)
        grand_total += after
        marker = "  ← NEW" if before == 0 and after > 0 else ""
        print(f"  {col_name:<25s}  {before:>8d}  {ingested:>10d}  {after:>8d}{marker}")
    print(f"  {'─' * 25}  {'─' * 8}  {'─' * 10}  {'─' * 8}")
    print(f"  {'TOTAL':<25s}  {sum(pre_stats.values()):>8d}  {sum(stats.values()):>10d}  {grand_total:>8d}")
    print(f"\n  Time elapsed: {elapsed:.1f}s")
    print(f"  ChromaDB path: {engine._persist_dir}")
    print()

    # ── Sanity check ───────────────────────────────────────────────────
    print("Running sanity check queries ...")
    try:
        _sanity_check(engine)
    except Exception:
        print("  ⚠ Re-loading engine from disk for sanity check ...")
        engine = RAGEngine()
        _sanity_check(engine)

    print()
    print("=" * 65)
    print(f"  ✅ Ingestion complete!  {grand_total} documents across "
          f"{len([v for v in post_stats.values() if v > 0])} collections")
    print("=" * 65)
    print()


def _sanity_check(engine: RAGEngine) -> None:
    """Run test queries to verify the index is working."""
    test_queries = [
        ("tomato leaf spots", ["crop_diseases"]),
        ("Rythu Bandhu eligibility", ["government_schemes"]),
        ("red soil management tips", ["soil_data"]),
        ("rice market price Warangal", ["market_data"]),
        ("SRI method water saving", ["farming_practices"]),
        ("kharif season rice sowing", ["crop_calendar"]),
        ("cotton price Adilabad", ["mandi_prices"]),
        ("PM KISAN documents required", ["schemes_database"]),
    ]
    passed = 0
    for query, collections in test_queries:
        results = engine.query(query, collection_names=collections, n_results=2)
        if results:
            top = results[0]
            dist = top["distance"]
            snippet = top["document"][:70].replace("\n", " ")
            print(f"  ✓ \"{query}\"  →  dist={dist:.4f}  →  {snippet}...")
            passed += 1
        else:
            print(f"  ✗ \"{query}\"  →  NO RESULTS (collection may be empty)")
    print(f"\n  Sanity check: {passed}/{len(test_queries)} queries returned results")


if __name__ == "__main__":
    main()
