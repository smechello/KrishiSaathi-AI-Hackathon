"""KrishiSaathi Memory Engine — Mem0-inspired long-term user memory.

Architecture inspired by mem0 (https://github.com/mem0ai/mem0):
  - **Fact Extraction**: LLM extracts structured facts from every conversation turn
  - **Categories**: personal, farming, crops, location, equipment, preferences, experiences
  - **Deduplication**: new facts are compared against existing; duplicates merged, conflicts resolved
  - **Semantic Search**: memories retrieved by embedding cosine similarity (Gemini embeddings)
  - **Memory Injection**: relevant memories injected into every LLM prompt for personalisation
  - **Importance Scoring**: memories scored 1-10; decayed over time, boosted on access
  - **Short-term + Long-term**: conversation buffer (session) + persistent store (Supabase)
  - **Memory Management**: view, search, delete individual memories

Usage::

    from backend.services.memory_engine import MemoryEngine

    mem = MemoryEngine(user_id="uuid-here")
    mem.add_from_conversation(user_msg, assistant_msg)      # extract & store facts
    context = mem.get_memory_context(query)                 # retrieve relevant memories
    all_memories = mem.get_all()                             # list everything
    mem.delete(memory_id)                                    # remove one
    mem.search("cotton crop")                               # semantic search
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from backend.config import Config

logger = logging.getLogger(__name__)

# ── Optional imports ────────────────────────────────────────────────────
_supabase_ok = False
try:
    from supabase import create_client, Client
    _supabase_ok = True
except ImportError:
    Client = None  # type: ignore

_genai_ok = False
try:
    import google.generativeai as genai
    _genai_ok = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

MEMORY_CATEGORIES = [
    "personal",       # name, age, family size, education
    "location",       # village, district, state, taluk
    "farming",        # farm size, irrigation type, farming style
    "crops",          # current/past crops, crop rotation, varieties
    "equipment",      # tractor, sprayer, drip irrigation, etc.
    "livestock",      # cattle, poultry, etc.
    "soil",           # soil type, pH, nutrient status
    "preferences",    # preferred language, advisory style, organic/chemical
    "experience",     # years of farming, past problems, successes
    "financial",      # budget, loans, insurance, subsidy status
]

EXTRACTION_PROMPT = """You are a memory extraction system for KrishiSaathi, an AI farming advisor.

Analyse the following conversation between a farmer and the AI assistant.
Extract ALL factual information about the farmer that should be remembered for future conversations.

RULES:
1. Extract ONLY facts explicitly stated or strongly implied by the farmer's message
2. Do NOT extract facts from the assistant's response (those are advice, not user facts)
3. Each fact should be a single, clear, self-contained statement
4. Assign a category from: {categories}
5. Score importance 1-10 (10 = critical farming decision info, 1 = trivial)
6. If the farmer asks about a specific crop/location, that's a fact about their interest

Return a JSON array of objects. If no new facts, return [].
Format:
[
  {{"fact": "The farmer grows cotton in 5 acres", "category": "crops", "importance": 8}},
  {{"fact": "The farmer is from Karimnagar district", "category": "location", "importance": 9}}
]

CONVERSATION:
Farmer: {user_message}
Assistant: {assistant_message}

Extract facts (JSON array only, no explanation):"""

DEDUP_PROMPT = """You are a memory deduplication system.

Compare NEW_FACT against EXISTING_MEMORIES.
Determine if the new fact:
- "new": genuinely new information not covered by any existing memory
- "duplicate": same information already stored (skip it)
- "update": updates/corrects/expands an existing memory (return the ID to update)

Return JSON:
{{"action": "new"|"duplicate"|"update", "update_id": null|"memory_id", "merged_fact": null|"updated text"}}

EXISTING_MEMORIES:
{existing}

NEW_FACT: {new_fact}

Decision (JSON only):"""

SHORT_TERM_LIMIT = 20   # max conversation turns kept in short-term buffer
MAX_MEMORY_INJECT = 12  # max memories injected into prompt
MEMORY_DECAY_DAYS = 90  # memories lose importance after this many days


# ═══════════════════════════════════════════════════════════════════════
#  MemoryEngine
# ═══════════════════════════════════════════════════════════════════════

class MemoryEngine:
    """Per-user memory store — short-term (session) + long-term (Supabase)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

        # Short-term conversation buffer (this session only)
        self._short_term: list[dict] = []

        # Embedding model
        self._embed_model = Config.EMBEDDING_MODEL

        # Supabase client (lazy, with auth tokens)
        self._client: Client | None = None

    # ── Supabase client ────────────────────────────────────────────────

    def _get_client(self) -> "Client | None":
        """Get authed Supabase client."""
        if not _supabase_ok or not getattr(Config, "SUPABASE_URL", None):
            return None
        if self._client is None:
            import streamlit as st
            self._client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            tokens = st.session_state.get("auth_tokens")
            if tokens:
                try:
                    self._client.auth.set_session(
                        tokens["access_token"], tokens["refresh_token"]
                    )
                except Exception:
                    pass
        return self._client

    # ═══════════════════════════════════════════════════════════════════
    #  Core: Extract → Deduplicate → Store
    # ═══════════════════════════════════════════════════════════════════

    def add_from_conversation(
        self,
        user_message: str,
        assistant_message: str,
    ) -> list[dict]:
        """Extract facts from a conversation turn and persist them.

        This is the main entry point — called after every exchange.
        Returns the list of newly stored memories.
        """
        # 1. Add to short-term buffer
        self._short_term.append({
            "role": "user", "content": user_message,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._short_term.append({
            "role": "assistant", "content": assistant_message,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._short_term) > SHORT_TERM_LIMIT * 2:
            self._short_term = self._short_term[-(SHORT_TERM_LIMIT * 2):]

        # 2. Extract facts via LLM
        facts = self._extract_facts(user_message, assistant_message)
        if not facts:
            return []

        # 3. Deduplicate against existing memories
        stored: list[dict] = []
        existing = self._load_existing_memories()

        for fact_obj in facts:
            fact_text = fact_obj.get("fact", "")
            category = fact_obj.get("category", "personal")
            importance = min(max(int(fact_obj.get("importance", 5)), 1), 10)

            if not fact_text:
                continue

            # Dedup check
            action_info = self._deduplicate(fact_text, existing)
            action = action_info.get("action", "new")

            if action == "duplicate":
                # Boost access count of existing memory
                update_id = action_info.get("update_id")
                if update_id:
                    self._boost_memory(update_id)
                continue

            if action == "update":
                update_id = action_info.get("update_id")
                merged = action_info.get("merged_fact", fact_text)
                if update_id and merged:
                    self._update_memory(update_id, merged, importance)
                    stored.append({"fact": merged, "category": category, "action": "updated"})
                continue

            # New memory
            embedding = self._embed(fact_text)
            mem = self._store_memory(fact_text, category, importance, embedding)
            if mem:
                stored.append({**mem, "action": "created"})
                existing.append(mem)  # so next fact in this batch can dedup against it

        return stored

    # ═══════════════════════════════════════════════════════════════════
    #  Retrieval: Semantic search + scoring
    # ═══════════════════════════════════════════════════════════════════

    def get_memory_context(self, query: str, max_memories: int = MAX_MEMORY_INJECT) -> str:
        """Build a memory context string for injection into LLM prompts.

        Combines:
        1. Semantic search (embedding similarity to query)
        2. Importance-weighted scoring with time decay
        3. Short-term conversation buffer summary

        Returns a formatted string ready to inject, or "" if no memories.
        """
        parts: list[str] = []

        # ── Long-term memories (semantic search) ───────────────────────
        relevant = self.search(query, top_k=max_memories)
        if relevant:
            mem_lines = []
            for m in relevant:
                cat = m.get("category", "")
                fact = m.get("content", "")
                score = m.get("_score", 0)
                mem_lines.append(f"  - [{cat}] {fact}")
            parts.append("Known facts about this farmer:\n" + "\n".join(mem_lines))

        # ── Short-term conversation context ────────────────────────────
        if self._short_term:
            recent = self._short_term[-6:]  # last 3 turns
            conv_lines = []
            for msg in recent:
                role = "Farmer" if msg["role"] == "user" else "KrishiSaathi"
                conv_lines.append(f"  {role}: {msg['content'][:200]}")
            parts.append("Recent conversation:\n" + "\n".join(conv_lines))

        if not parts:
            return ""

        return (
            "\n--- FARMER MEMORY (personalised context) ---\n"
            + "\n\n".join(parts)
            + "\n--- END MEMORY ---\n"
        )

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Semantic search over stored memories.

        Returns memories sorted by relevance score (descending).
        """
        client = self._get_client()
        if not client:
            return []

        query_embedding = self._embed(query)
        if not query_embedding:
            return self._keyword_search(query, top_k)

        try:
            # Fetch all user memories with embeddings for similarity calc
            res = (
                client.table("memories")
                .select("id, content, category, importance, access_count, embedding, created_at, updated_at")
                .eq("user_id", self.user_id)
                .execute()
            )
            if not res.data:
                return []

            # Compute cosine similarity + importance scoring
            scored: list[tuple[float, dict]] = []
            now = datetime.now(timezone.utc)

            for row in res.data:
                row_emb = row.get("embedding")
                if not row_emb:
                    continue
                if isinstance(row_emb, str):
                    row_emb = json.loads(row_emb)

                sim = self._cosine_similarity(query_embedding, row_emb)

                # Time decay: reduce score for old memories
                created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                days_old = (now - created).days
                decay = max(0.3, 1.0 - (days_old / MEMORY_DECAY_DAYS) * 0.5)

                # Composite score: similarity (60%) + importance (25%) + recency (15%)
                importance_norm = row.get("importance", 5) / 10.0
                access_boost = min(row.get("access_count", 0) / 20.0, 0.2)  # cap at 0.2
                score = (sim * 0.6) + (importance_norm * 0.25) + (decay * 0.15) + access_boost

                mem = {
                    "id": row["id"],
                    "content": row["content"],
                    "category": row.get("category", ""),
                    "importance": row.get("importance", 5),
                    "access_count": row.get("access_count", 0),
                    "created_at": row.get("created_at"),
                    "_score": round(score, 4),
                    "_similarity": round(sim, 4),
                }
                scored.append((score, mem))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = [m for _, m in scored[:top_k]]

            # Boost access count for retrieved memories
            for m in results[:5]:
                self._boost_memory(m["id"])

            return results

        except Exception as exc:
            logger.warning("Memory search failed: %s", exc)
            return []

    def get_all(self, limit: int = 100) -> list[dict]:
        """Return all memories for this user (newest first)."""
        client = self._get_client()
        if not client:
            return []
        try:
            res = (
                client.table("memories")
                .select("id, content, category, importance, access_count, created_at, updated_at")
                .eq("user_id", self.user_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning("get_all memories failed: %s", exc)
            return []

    def get_by_category(self, category: str) -> list[dict]:
        """Return memories filtered by category."""
        client = self._get_client()
        if not client:
            return []
        try:
            res = (
                client.table("memories")
                .select("id, content, category, importance, access_count, created_at")
                .eq("user_id", self.user_id)
                .eq("category", category)
                .order("importance", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning("get_by_category failed: %s", exc)
            return []

    def delete(self, memory_id: int) -> bool:
        """Delete a single memory by ID."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("memories").delete().eq("id", memory_id).eq("user_id", self.user_id).execute()
            return True
        except Exception as exc:
            logger.warning("delete memory failed: %s", exc)
            return False

    def clear_all(self) -> bool:
        """Delete ALL memories for this user."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("memories").delete().eq("user_id", self.user_id).execute()
            self._short_term.clear()
            return True
        except Exception as exc:
            logger.warning("clear_all memories failed: %s", exc)
            return False

    def stats(self) -> dict:
        """Return memory statistics."""
        client = self._get_client()
        if not client:
            return {"total": 0, "categories": {}}
        try:
            res = (
                client.table("memories")
                .select("category")
                .eq("user_id", self.user_id)
                .execute()
            )
            cats: dict[str, int] = {}
            for row in (res.data or []):
                c = row.get("category", "other")
                cats[c] = cats.get(c, 0) + 1
            return {"total": sum(cats.values()), "categories": cats}
        except Exception as exc:
            logger.warning("memory stats failed: %s", exc)
            return {"total": 0, "categories": {}}

    # ═══════════════════════════════════════════════════════════════════
    #  Internal: Fact extraction (LLM)
    # ═══════════════════════════════════════════════════════════════════

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> list[dict]:
        """Use LLM to extract factual memories from a conversation turn."""
        from backend.services.llm_helper import llm

        prompt = EXTRACTION_PROMPT.format(
            categories=", ".join(MEMORY_CATEGORIES),
            user_message=user_msg[:1500],
            assistant_message=assistant_msg[:1500],
        )

        try:
            raw = llm.generate(prompt, role="classifier", use_cache=False)
            parsed = self._safe_json_array(raw)
            if parsed:
                logger.info("Extracted %d facts from conversation", len(parsed))
            return parsed or []
        except Exception as exc:
            logger.warning("Fact extraction failed: %s", exc)
            return []

    def _deduplicate(self, new_fact: str, existing: list[dict]) -> dict:
        """Check if a fact is new, duplicate, or an update of existing."""
        if not existing:
            return {"action": "new"}

        # Quick embedding-based pre-filter: if very similar to any existing → candidate
        new_emb = self._embed(new_fact)
        candidates: list[dict] = []

        for mem in existing:
            mem_emb = mem.get("embedding")
            if mem_emb and new_emb:
                if isinstance(mem_emb, str):
                    mem_emb = json.loads(mem_emb)
                sim = self._cosine_similarity(new_emb, mem_emb)
                if sim > 0.75:  # high similarity threshold
                    candidates.append({**mem, "_sim": sim})

        if not candidates:
            return {"action": "new"}

        # If very high similarity (>0.92), it's a duplicate — no LLM needed
        best = max(candidates, key=lambda x: x["_sim"])
        if best["_sim"] > 0.92:
            return {"action": "duplicate", "update_id": str(best.get("id"))}

        # Moderate similarity — ask LLM
        from backend.services.llm_helper import llm

        existing_text = "\n".join(
            f'  [{m.get("id")}] ({m.get("category","")}) {m.get("content","")}'
            for m in candidates[:5]
        )
        prompt = DEDUP_PROMPT.format(existing=existing_text, new_fact=new_fact)

        try:
            raw = llm.generate(prompt, role="classifier", use_cache=False)
            parsed = self._safe_json_obj(raw)
            if parsed:
                return parsed
        except Exception:
            pass

        return {"action": "new"}

    # ═══════════════════════════════════════════════════════════════════
    #  Internal: Storage operations
    # ═══════════════════════════════════════════════════════════════════

    def _store_memory(
        self,
        content: str,
        category: str,
        importance: int,
        embedding: list[float] | None,
    ) -> dict | None:
        """Insert a new memory into Supabase."""
        client = self._get_client()
        if not client:
            return None
        try:
            row = {
                "user_id": self.user_id,
                "content": content,
                "category": category,
                "importance": importance,
                "access_count": 0,
                "embedding": json.dumps(embedding) if embedding else None,
            }
            res = client.table("memories").insert(row).execute()
            if res.data:
                stored = res.data[0]
                stored.pop("embedding", None)  # don't return embedding in results
                logger.info("Stored memory: [%s] %s (importance=%d)", category, content[:60], importance)
                return stored
        except Exception as exc:
            logger.warning("Store memory failed: %s", exc)
        return None

    def _update_memory(self, memory_id: str, new_content: str, importance: int) -> None:
        """Update an existing memory's content."""
        client = self._get_client()
        if not client:
            return
        try:
            client.table("memories").update({
                "content": new_content,
                "importance": importance,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", int(memory_id)).eq("user_id", self.user_id).execute()
            logger.info("Updated memory %s: %s", memory_id, new_content[:60])
        except Exception as exc:
            logger.warning("Update memory failed: %s", exc)

    def _boost_memory(self, memory_id: int | str) -> None:
        """Increment access_count + update timestamp (recency boost)."""
        client = self._get_client()
        if not client:
            return
        try:
            # Use RPC if available, otherwise read-modify-write
            res = (
                client.table("memories")
                .select("access_count")
                .eq("id", int(memory_id))
                .eq("user_id", self.user_id)
                .maybe_single()
                .execute()
            )
            if res.data:
                new_count = (res.data.get("access_count") or 0) + 1
                client.table("memories").update({
                    "access_count": new_count,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", int(memory_id)).execute()
        except Exception:
            pass  # non-critical

    def _load_existing_memories(self) -> list[dict]:
        """Load all memories for dedup comparison (with embeddings)."""
        client = self._get_client()
        if not client:
            return []
        try:
            res = (
                client.table("memories")
                .select("id, content, category, importance, embedding")
                .eq("user_id", self.user_id)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning("Load existing memories failed: %s", exc)
            return []

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Fallback text search when embeddings are not available."""
        client = self._get_client()
        if not client:
            return []
        try:
            # Simple ILIKE search
            res = (
                client.table("memories")
                .select("id, content, category, importance, access_count, created_at")
                .eq("user_id", self.user_id)
                .ilike("content", f"%{query[:50]}%")
                .limit(top_k)
                .execute()
            )
            return res.data or []
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════════════
    #  Internal: Embeddings
    # ═══════════════════════════════════════════════════════════════════

    def _embed(self, text: str) -> list[float] | None:
        """Generate embedding vector using Gemini."""
        if not _genai_ok or not Config.GEMINI_API_KEY:
            return None
        try:
            result = genai.embed_content(
                model=self._embed_model,
                content=text[:2000],
                task_type="SEMANTIC_SIMILARITY",
            )
            return result["embedding"]
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ═══════════════════════════════════════════════════════════════════
    #  Internal: JSON parsing helpers
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _safe_json_array(text: str) -> list[dict] | None:
        """Parse a JSON array from raw LLM output."""
        text = text.strip()
        # Strip markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting [...] from mixed output
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            try:
                result = json.loads(text[start : end + 1])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _safe_json_obj(text: str) -> dict | None:
        """Parse a JSON object from raw LLM output."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                result = json.loads(text[start : end + 1])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Module-level helper: get or create engine for current user
# ═══════════════════════════════════════════════════════════════════════

_engines: dict[str, MemoryEngine] = {}


def get_memory_engine(user_id: str) -> MemoryEngine:
    """Return (or create) a MemoryEngine for the given user."""
    if user_id not in _engines:
        _engines[user_id] = MemoryEngine(user_id)
    return _engines[user_id]
