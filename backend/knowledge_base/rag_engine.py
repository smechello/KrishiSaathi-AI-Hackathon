"""RAG Engine - Retrieval Augmented Generation using ChromaDB.

Uses Google Gemini Embedding API (gemini-embedding-001) for embeddings
and ChromaDB as the local persistent vector store.

Pipeline:
    User Query → Generate Embedding (Gemini) → Search ChromaDB (top-k)
    → Return relevant context → Inject into Agent prompt → Gemini responds
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import chromadb
import google.generativeai as genai

from backend.config import Config

logger = logging.getLogger(__name__)

# ── Mapping of JSON files to ChromaDB collection names ───────────────
COLLECTION_MAP: dict[str, str] = {
    "crop_diseases.json": "crop_diseases",
    "farming_practices.json": "farming_practices",
    "government_schemes.json": "government_schemes",
    "market_data.json": "market_data",
    "soil_data.json": "soil_data",
}

# Top-level JSON key inside each file that holds the list of records
ROOT_KEY_MAP: dict[str, str] = {
    "crop_diseases.json": "crop_diseases",
    "farming_practices.json": "farming_practices",
    "government_schemes.json": "schemes",
    "market_data.json": "market_data",
    "soil_data.json": "soils",
}


class RAGEngine:
    """Retrieval-Augmented Generation engine backed by ChromaDB + Gemini embeddings."""

    def __init__(self, persist_dir: str | None = None) -> None:
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing — cannot initialise RAG engine.")
        genai.configure(api_key=Config.GEMINI_API_KEY)

        self._persist_dir = persist_dir or self._default_chroma_path()
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._embed_model = Config.EMBEDDING_MODEL  # "models/gemini-embedding-001"
        logger.info("RAGEngine initialised  →  ChromaDB at %s", self._persist_dir)

    # ── public API ─────────────────────────────────────────────────────

    def ingest_documents(self, documents_dir: str | None = None) -> dict[str, int]:
        """Load every JSON knowledge-base file, chunk it, embed it, and upsert
        into the corresponding ChromaDB collection.

        Returns a dict mapping collection name → number of documents ingested.
        """
        docs_dir = documents_dir or self._default_documents_path()
        stats: dict[str, int] = {}

        for filename, collection_name in COLLECTION_MAP.items():
            filepath = os.path.join(docs_dir, filename)
            if not os.path.exists(filepath):
                logger.warning("Skipping missing file: %s", filepath)
                continue

            with open(filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)

            root_key = ROOT_KEY_MAP.get(filename, "data")
            records: list[dict[str, Any]] = raw.get(root_key, [])
            if not records:
                logger.warning("No records under key '%s' in %s", root_key, filename)
                continue

            chunks = self._records_to_chunks(records, collection_name)
            count = self._upsert_chunks(collection_name, chunks)
            stats[collection_name] = count
            logger.info("  ✓ %s  →  %d chunks ingested", collection_name, count)

        return stats

    def query(
        self,
        query_text: str,
        collection_names: list[str] | None = None,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search one or more collections and return the top-k relevant chunks.

        Each result dict has keys: collection, id, document, metadata, distance.
        """
        if collection_names is None:
            collection_names = list(COLLECTION_MAP.values())

        query_embedding = self._embed_text(query_text)
        results: list[dict[str, Any]] = []

        for col_name in collection_names:
            try:
                collection = self._client.get_collection(col_name)
            except Exception:
                logger.debug("Collection '%s' not found — skipping.", col_name)
                continue

            hits = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            for idx in range(len(hits["ids"][0])):
                results.append(
                    {
                        "collection": col_name,
                        "id": hits["ids"][0][idx],
                        "document": hits["documents"][0][idx],
                        "metadata": hits["metadatas"][0][idx],
                        "distance": hits["distances"][0][idx],
                    }
                )

        # Sort all results across collections by distance (lower = better)
        results.sort(key=lambda r: r["distance"])
        return results[:n_results]

    def get_relevant_context(
        self,
        query_text: str,
        collection_names: list[str] | None = None,
        n_results: int = 5,
        max_chars: int = 4000,
    ) -> str:
        """Convenience wrapper: returns a single formatted string ready to inject
        into an LLM prompt, capped at *max_chars* characters.
        """
        hits = self.query(query_text, collection_names, n_results)
        if not hits:
            return ""

        parts: list[str] = []
        total = 0
        for h in hits:
            doc = h["document"]
            source = h["metadata"].get("source", h["collection"])
            entry = f"[Source: {source}]\n{doc}"
            if total + len(entry) > max_chars:
                break
            parts.append(entry)
            total += len(entry)

        return "\n\n---\n\n".join(parts)

    def collection_stats(self) -> dict[str, int]:
        """Return {collection_name: document_count} for every collection."""
        stats: dict[str, int] = {}
        for col_name in COLLECTION_MAP.values():
            try:
                col = self._client.get_collection(col_name)
                stats[col_name] = col.count()
            except Exception:
                stats[col_name] = 0
        return stats

    def delete_all(self) -> None:
        """Delete every collection (useful for re-ingestion)."""
        for col_name in COLLECTION_MAP.values():
            try:
                self._client.delete_collection(col_name)
                logger.info("Deleted collection: %s", col_name)
            except Exception:
                pass

    # ── private helpers ────────────────────────────────────────────────

    def _embed_text(self, text: str, max_retries: int = 3) -> list[float]:
        """Generate an embedding vector via Google Gemini Embedding API with retry."""
        for attempt in range(1, max_retries + 1):
            try:
                result = genai.embed_content(
                    model=self._embed_model,
                    content=text,
                    task_type="retrieval_query",
                )
                return result["embedding"]
            except Exception as exc:
                err_msg = str(exc)
                if ("429" in err_msg or "ResourceExhausted" in err_msg) and attempt < max_retries:
                    wait = 2 ** attempt * 10
                    logger.warning("  ⏳ Rate-limited on query embed — retrying in %ds", wait)
                    time.sleep(wait)
                else:
                    raise
        return []  # unreachable, satisfies type checker

    def _embed_texts_batch(
        self,
        texts: list[str],
        task_type: str = "retrieval_document",
        batch_size: int = 20,
        max_retries: int = 5,
    ) -> list[list[float]]:
        """Embed a batch of texts with automatic rate-limit retry.

        Gemini free-tier allows ~100 embed requests/min.  Each text in a
        batch counts as one request, so we use small batches (default 20)
        with a pause between them.  If a 429 (ResourceExhausted) is
        returned we back off exponentially and retry.
        """
        embeddings: list[list[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(texts), batch_size)):
            batch = texts[i : i + batch_size]
            attempt = 0

            while True:
                try:
                    result = genai.embed_content(
                        model=self._embed_model,
                        content=batch,
                        task_type=task_type,
                    )
                    embeddings.extend(result["embedding"])
                    break  # success → move to next batch
                except Exception as exc:
                    attempt += 1
                    err_msg = str(exc)
                    if ("429" in err_msg or "ResourceExhausted" in err_msg) and attempt <= max_retries:
                        wait = min(2 ** attempt * 15, 120)  # 15 s, 30 s, 60 s, 120 s …
                        logger.warning(
                            "  ⏳ Rate-limited (batch %d/%d) — retrying in %ds (attempt %d/%d)",
                            batch_idx + 1, total_batches, wait, attempt, max_retries,
                        )
                        time.sleep(wait)
                    else:
                        raise

            # Pause between batches to stay under free-tier RPM quota
            if i + batch_size < len(texts):
                time.sleep(2)

        return embeddings

    def _records_to_chunks(
        self, records: list[dict[str, Any]], collection_name: str
    ) -> list[dict[str, Any]]:
        """Convert raw JSON records into chunks suitable for embedding.

        Each chunk = {id, text, metadata}.
        """
        chunks: list[dict[str, Any]] = []

        for rec in records:
            rec_id = rec.get("id", "")
            text = self._flatten_record(rec)
            metadata = {
                "source": collection_name,
                "record_id": rec_id,
            }

            # Add key filterable metadata depending on collection type
            if collection_name == "crop_diseases":
                metadata["crop"] = rec.get("crop", "")
                metadata["category"] = rec.get("category", "")
                metadata["severity"] = rec.get("severity", "")
            elif collection_name == "farming_practices":
                metadata["category"] = rec.get("category", "")
                metadata["season"] = rec.get("season", "")
            elif collection_name == "government_schemes":
                metadata["category"] = rec.get("category", "")
                metadata["name"] = rec.get("name", "")
            elif collection_name == "market_data":
                metadata["crop"] = rec.get("crop", "")
                metadata["category"] = rec.get("category", "")
            elif collection_name == "soil_data":
                metadata["type"] = rec.get("type", "")

            chunks.append({"id": rec_id or f"{collection_name}_{len(chunks)}", "text": text, "metadata": metadata})

        return chunks

    def _flatten_record(self, record: dict[str, Any]) -> str:
        """Convert a JSON record into a readable text block for embedding."""
        parts: list[str] = []
        for key, value in record.items():
            if key == "id":
                continue
            label = key.replace("_", " ").title()
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                value_str = "; ".join(f"{k}: {v}" for k, v in value.items())
            else:
                value_str = str(value)
            parts.append(f"{label}: {value_str}")
        return "\n".join(parts)

    def _upsert_chunks(self, collection_name: str, chunks: list[dict[str, Any]]) -> int:
        """Embed texts and upsert into ChromaDB collection."""
        if not chunks:
            return 0

        collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        logger.info("  Embedding %d chunks for '%s' ...", len(texts), collection_name)
        embeddings = self._embed_texts_batch(texts)

        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    # ── path helpers ───────────────────────────────────────────────────

    @staticmethod
    def _default_chroma_path() -> str:
        """Return the default persistent ChromaDB directory."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "chroma_db",
        )

    @staticmethod
    def _default_documents_path() -> str:
        """Return the default knowledge-base documents directory."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base",
            "documents",
        )
