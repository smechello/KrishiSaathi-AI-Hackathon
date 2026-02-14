"""Main backend entry point — KrishiSaathi orchestration layer.

Provides a single ``KrishiSaathi`` facade class that:
1. Initialises the RAG engine (ChromaDB + Gemini embeddings).
2. Creates the SupervisorAgent with RAG injected.
3. Exposes ``ask(query)`` for the frontend / CLI to call.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.config import Config
from backend.knowledge_base.rag_engine import RAGEngine
from backend.agents.supervisor_agent import SupervisorAgent

logger = logging.getLogger(__name__)


class KrishiSaathi:
    """Top-level application facade."""

    def __init__(self) -> None:
        logger.info("Initialising KrishiSaathi …")

        # 1. Boot RAG engine (loads persisted ChromaDB — no re-ingestion)
        try:
            self._rag = RAGEngine()
            stats = self._rag.collection_stats()
            total = sum(stats.values())
            logger.info("RAG engine ready  (%d documents across %d collections)", total, len(stats))
        except Exception as exc:
            logger.warning("RAG engine unavailable — running without knowledge base: %s", exc)
            self._rag = None  # type: ignore[assignment]

        # 2. Supervisor (creates child agents lazily with RAG injected)
        self._supervisor = SupervisorAgent(rag_engine=self._rag)
        logger.info("KrishiSaathi ready ✓")

    # ── public API ─────────────────────────────────────────────────────

    def ask(self, query: str, user_id: str | None = None, memory_context: str = "") -> dict[str, Any]:
        """Process a farmer query end-to-end.

        Parameters
        ----------
        query : str
            The farmer's question (in English).
        user_id : str | None
            Authenticated user ID (for memory personalisation).
        memory_context : str
            Pre-formatted memory context block to inject into prompts.

        Returns
        -------
        dict with keys:
            response  – final answer text (str)
            intent    – classification dict
            sources   – list of source labels
            agent_responses – per-agent raw results
        """
        return self._supervisor.handle_query(query, memory_context=memory_context)

    @property
    def rag(self) -> RAGEngine | None:
        """Expose RAG engine for direct access (e.g. admin tools)."""
        return self._rag

    @property
    def supervisor(self) -> SupervisorAgent:
        return self._supervisor


# ── CLI quick-test ─────────────────────────────────────────────────────

def _cli() -> None:
    """Interactive loop for quick testing from the terminal."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    app = KrishiSaathi()
    print("\n🌾 KrishiSaathi — AI Agricultural Advisory")
    print("Type a question (or 'quit' to exit)\n")

    while True:
        try:
            query = input("Farmer > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

        if not query or query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = app.ask(query)
        print(f"\n🤖 KrishiSaathi:\n{result['response']}")
        if result.get("sources"):
            print(f"\n📚 Sources: {', '.join(result['sources'])}")
        print("-" * 60)


if __name__ == "__main__":
    _cli()
