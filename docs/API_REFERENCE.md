# 📖 KrishiSaathi — API Reference

> Internal Python API documentation for all backend modules, services and agents.

---

## Table of Contents

1. [KrishiSaathi (Facade)](#1-krishisaathi-facade)
2. [SupervisorAgent](#2-supervisoragent)
3. [Specialist Agents](#3-specialist-agents)
4. [RAGEngine](#4-ragengine)
5. [LLMHelper](#5-llmhelper)
6. [SupabaseManager](#6-supabasemanager)
7. [MemoryEngine](#7-memoryengine)
8. [WeatherService](#8-weatherservice)
9. [TranslationService](#9-translationservice)
10. [Config](#10-config)

---

## 1. KrishiSaathi (Facade)

**Module:** `backend.main`

The top-level entry point that boots all subsystems and exposes a single `ask()` method.

### Constructor

```python
KrishiSaathi()
```

Initialises the RAG engine (ChromaDB + Gemini embeddings) and creates the SupervisorAgent.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `ask` | `ask(query: str, user_id: str \| None = None, memory_context: str = "") → dict` | `{ response, intent, sources, agent_responses }` | Process a farmer query end-to-end |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `rag` | `RAGEngine \| None` | Direct access to the RAG engine |
| `supervisor` | `SupervisorAgent` | Direct access to the supervisor |

### Return Schema — `ask()`

```python
{
    "response": str,            # Final synthesized answer
    "intent": {                 # Classification result
        "primary_intent": str,
        "secondary_intent": str | None,
        "entities": dict,
        "confidence": float
    },
    "sources": list[str],       # Source labels (e.g., "crop_diseases")
    "agent_responses": dict     # Per-agent raw outputs
}
```

---

## 2. SupervisorAgent

**Module:** `backend.agents.supervisor_agent`

Orchestrates the entire query lifecycle: classify → route → synthesize.

### Constructor

```python
SupervisorAgent(rag_engine: RAGEngine | None = None)
```

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `classify_intent` | `classify_intent(user_query: str) → dict` | Intent JSON | Classify user intent and extract entities |
| `handle_query` | `handle_query(user_query: str, memory_context: str = "") → dict` | Full response dict | End-to-end query handling |

### Intent Categories

| Intent | Routed Agent |
|--------|-------------|
| `crop_disease` | CropDoctorAgent |
| `market_prices` | MarketAgent |
| `government_scheme` | SchemeAgent |
| `weather` | WeatherAgent |
| `soil` | SoilAgent |
| `general` | Direct LLM response |

---

## 3. Specialist Agents

All specialist agents share the same base interface.

### Common Interface

```python
class SpecialistAgent:
    def __init__(self, rag_engine: RAGEngine | None = None)
    def handle(self, query: str, entities: dict, **kwargs) → str
```

### Agent Details

#### CropDoctorAgent
**Module:** `backend.agents.crop_doctor_agent`

| Capability | Details |
|-----------|---------|
| RAG Collections | `crop_diseases`, `farming_practices` |
| Vision | Gemini multimodal for image analysis |
| Input | Text query + optional image (PIL / bytes) |

#### MarketAgent
**Module:** `backend.agents.market_agent`

| Capability | Details |
|-----------|---------|
| RAG Collections | `market_data`, `mandi_prices` |
| Data | Static mandi prices from JSON + RAG context |
| Features | Price lookup, market comparison, trend analysis |

#### SchemeAgent
**Module:** `backend.agents.scheme_agent`

| Capability | Details |
|-----------|---------|
| RAG Collections | `government_schemes`, `schemes_database` |
| Features | Eligibility check, scheme discovery, application guidance |

#### WeatherAgent
**Module:** `backend.agents.weather_agent`

| Capability | Details |
|-----------|---------|
| External API | OpenWeatherMap (current + 5-day forecast) |
| Features | Location-based forecasts, crop-specific advisories |

#### SoilAgent
**Module:** `backend.agents.soil_agent`

| Capability | Details |
|-----------|---------|
| RAG Collections | `soil_data` |
| Features | Soil health analysis, fertilizer recommendations, NPK guidance |

---

## 4. RAGEngine

**Module:** `backend.knowledge_base.rag_engine`

ChromaDB-backed retrieval engine with Gemini embeddings.

### Constructor

```python
RAGEngine(persist_dir: str | None = None)
```

- `persist_dir` defaults to `chromadb_data/` in the project root.

### Core Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `ingest_documents` | `ingest_documents(documents_dir: str \| None = None) → dict[str, int]` | `{ collection_name: doc_count }` | Bulk-load JSON files into ChromaDB |
| `query` | `query(collection_name: str, query_text: str, n_results: int = 5) → dict` | ChromaDB results | Query a single collection |
| `get_relevant_context` | `get_relevant_context(query: str, collections: list[str] \| None = None, n_results: int = 5) → str` | Formatted context string | Search across multiple collections |
| `collection_stats` | `collection_stats() → dict[str, int]` | `{ collection: count }` | Document counts per collection |
| `delete_all` | `delete_all() → None` | — | Delete all collections |

### Admin / CRUD Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add_json_documents` | `add_json_documents(collection_name: str, records: list[dict], root_key: str \| None = None) → int` | Count ingested | Add JSON records to a collection |
| `add_text_document` | `add_text_document(collection_name: str, text: str, doc_id: str \| None = None, metadata: dict \| None = None) → str` | doc_id | Add a single text document |
| `add_from_url` | `add_from_url(collection_name: str, url: str) → int` | Count ingested | Fetch URL content and ingest |
| `fetch_url_preview` | `fetch_url_preview(url: str) → dict` | `{ title, text_preview, length }` | Preview URL content before ingesting |
| `list_all_collections` | `list_all_collections() → list[dict]` | Collection metadata | List all ChromaDB collections with counts |
| `get_collection_sample` | `get_collection_sample(collection_name: str, n: int = 5) → list[dict]` | Sample documents | Get sample documents from a collection |
| `delete_collection_by_name` | `delete_collection_by_name(name: str) → bool` | Success flag | Delete an entire collection |

### Collection Map

| Source File | Collection Name |
|-------------|----------------|
| `crop_diseases.json` | `crop_diseases` |
| `farming_practices.json` | `farming_practices` |
| `government_schemes.json` | `government_schemes` |
| `market_data.json` | `market_data` |
| `soil_data.json` | `soil_data` |
| `crop_calendar.json` | `crop_calendar` |
| `mandi_prices.json` | `mandi_prices` |
| `schemes_database.json` | `schemes_database` |

---

## 5. LLMHelper

**Module:** `backend.services.llm_helper`

Dual-backend LLM service (Groq primary, Gemini fallback) with caching and retry logic.

### Singleton

Accessed via the module-level `llm` instance:

```python
from backend.services.llm_helper import llm

response = llm.generate("Your prompt", role="agent")
```

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `generate` | `generate(prompt: str \| list, role: str = "agent", temperature: float = 0.3, max_tokens: int = 2048) → str` | Response text | Generate LLM response with fallback chain |
| `model_map` | `model_map() → dict[str, str]` | `{ role: model_name }` | Current model assignments |
| `cache_stats` | `cache_stats() → dict[str, int]` | `{ hits, misses, size }` | Cache performance |
| `clear_cache` | `clear_cache() → None` | — | Clear response cache |
| `reload_config` | `reload_config() → None` | — | Reload config (after admin changes) |

### Roles

| Role | Default Model | Purpose |
|------|---------------|---------|
| `classifier` | `llama-3.1-8b-instant` | Fast intent classification |
| `agent` | `llama-3.3-70b-versatile` | Deep reasoning for agents |
| `synthesis` | `llama-3.1-8b-instant` | Response synthesis |

---

## 6. SupabaseManager

**Module:** `backend.services.supabase_service`

All-static class managing Supabase auth, profiles, chat history, and admin operations.

### Auth Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `sign_up` | `sign_up(email, password, full_name, location, phone) → dict` | Session data | Register a new user |
| `sign_in` | `sign_in(email, password) → dict` | Session data | Authenticate user |
| `sign_out` | `sign_out() → None` | — | Clear session |
| `reset_password` | `reset_password(email) → dict` | Status | Send password reset email |
| `restore_session` | `restore_session() → dict \| None` | Session or None | Restore from stored tokens |

### Profile Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_profile` | `get_profile(user_id) → dict \| None` | Profile data | Get user profile |
| `update_profile` | `update_profile(user_id, data) → bool` | Success | Update user profile |

### Chat History Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `save_message` | `save_message(user_id, role, content, metadata) → bool` | Success | Store a chat message |
| `load_messages` | `load_messages(user_id, limit) → list[dict]` | Messages | Load chat history |
| `clear_messages` | `clear_messages(user_id) → bool` | Success | Delete all messages for a user |

### Admin Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `admin_list_users` | `admin_list_users() → list[dict]` | User list | List all profiles |
| `admin_get_all_chat_history` | `admin_get_all_chat_history(user_id, limit) → list[dict]` | Chat logs | All chats (optionally filtered) |
| `admin_get_all_memories` | `admin_get_all_memories(user_id, limit) → list[dict]` | Memories | All memories (optionally filtered) |
| `admin_delete_user_data` | `admin_delete_user_data(user_id) → dict` | Deletion report | Delete all data for a user |
| `admin_get_counts` | `admin_get_counts() → dict` | `{ users, chats, memories }` | Dashboard counts |
| `load_admin_settings` | `load_admin_settings() → dict \| None` | Settings JSON | Load admin config from Supabase |
| `save_admin_settings` | `save_admin_settings(settings) → bool` | Success | Persist admin config to Supabase |

---

## 7. MemoryEngine

**Module:** `backend.services.memory_engine`

Mem0-inspired per-user memory system with LLM-based fact extraction.

### Constructor

```python
MemoryEngine(user_id: str)
```

### Public Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add_from_conversation` | `add_from_conversation(user_msg, assistant_msg) → list[dict]` | Stored memories | Extract and store facts from a conversation turn |
| `get_memory_context` | `get_memory_context(query, max_memories=5) → str` | Formatted context string | Get relevant memories for prompt injection |
| `search` | `search(query, top_k=10) → list[dict]` | Ranked memories | Semantic + keyword search across memories |
| `get_all` | `get_all(limit=100) → list[dict]` | All memories | Retrieve all stored memories |
| `get_by_category` | `get_by_category(category) → list[dict]` | Category memories | Filter by memory category |
| `delete` | `delete(memory_id) → bool` | Success | Delete a specific memory |
| `clear_all` | `clear_all() → bool` | Success | Delete all memories for user |
| `stats` | `stats() → dict` | Stats breakdown | Memory count by category |

### Memory Categories

`personal_info`, `location`, `crops`, `land`, `soil`, `livestock`, `equipment`, `financial`, `preferences`, `history`

### Helper Function

```python
from backend.services.memory_engine import get_memory_engine

engine = get_memory_engine(user_id)  # Cached per user_id via st.cache_resource
```

---

## 8. WeatherService

**Module:** `backend.services.weather_service`

OpenWeatherMap integration for current weather and 5-day forecasts.

### Key Functions

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `get_current_weather` | `city: str` | Weather dict | Current conditions |
| `get_forecast` | `city: str` | Forecast list | 5-day / 3-hour forecast |
| `format_weather_response` | `data: dict` | `str` | Human-readable weather summary |

---

## 9. TranslationService

**Module:** `backend.services.translation_service`

Multi-language translation using `deep-translator` (Google Translate backend).

### Singleton

```python
from backend.services.translation_service import translator
```

### Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `hi` | Hindi |
| `te` | Telugu |
| `ta` | Tamil |
| `kn` | Kannada |
| `mr` | Marathi |
| `bn` | Bengali |
| `gu` | Gujarati |
| `ml` | Malayalam |
| `pa` | Punjabi |
| `or` | Odia |
| `ur` | Urdu |

---

## 10. Config

**Module:** `backend.config`

Centralised configuration loaded from `.env` (local) or `st.secrets` (Streamlit Cloud), with optional admin overrides from Supabase.

### Key Configuration Values

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `GEMINI_API_KEY` | `str` | — | Google Gemini API key |
| `GROQ_API_KEY` | `str` | — | Groq Cloud API key |
| `OPENWEATHER_API_KEY` | `str` | — | OpenWeatherMap key |
| `SUPABASE_URL` | `str` | — | Supabase project URL |
| `SUPABASE_KEY` | `str` | — | Supabase anon JWT key |
| `LLM_BACKEND` | `str` | `"groq"` | Primary LLM backend |
| `GROQ_MODEL_CLASSIFIER` | `str` | `"llama-3.1-8b-instant"` | Classifier model |
| `GROQ_MODEL_AGENT` | `str` | `"llama-3.3-70b-versatile"` | Agent model |
| `GROQ_MODEL_SYNTHESIS` | `str` | `"llama-3.1-8b-instant"` | Synthesis model |
| `DEFAULT_LANGUAGE` | `str` | `"en"` | Default UI language |
| `ADMIN_EMAILS` | `list` | `[]` | Emails with admin access |

### Admin Override Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `load_admin_settings` | `load_admin_settings() → dict` | Load from Supabase → local cache fallback |
| `save_admin_settings` | `save_admin_settings(settings: dict) → bool` | Save to Supabase + local cache |
| `apply_admin_overrides` | `apply_admin_overrides() → None` | Apply loaded settings to Config class attrs |
| `get_current_admin_settings` | `get_current_admin_settings() → dict` | Current effective settings |

---

*Last updated: February 2026*
