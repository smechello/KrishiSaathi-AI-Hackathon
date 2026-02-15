# 🏗️ KrishiSaathi — System Architecture

> Comprehensive technical architecture of the KrishiSaathi AI-Powered Multi-Agent Agricultural Intelligence System.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Directory Structure](#2-directory-structure)
3. [Multi-Agent Orchestration](#3-multi-agent-orchestration)
4. [RAG Knowledge Base](#4-rag-knowledge-base)
5. [LLM Backend](#5-llm-backend)
6. [Authentication & User Management](#6-authentication--user-management)
7. [Memory Engine](#7-memory-engine)
8. [Frontend Layer](#8-frontend-layer)
9. [Data Flow](#9-data-flow)
10. [External Integrations](#10-external-integrations)
11. [Deployment Architecture](#11-deployment-architecture)

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Streamlit)                            │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 💬 Chat  │ │🌱CropDoctor│ │💰 Market │ │🏛️ Schemes│ │🌤️/🧪  ││
│  │   (Home) │ │  (Vision)  │ │  Prices  │ │  Advisor │ │Wtr/Soil││
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘ └────────┘│
│                    ┌──────────────┐                                │
│                    │ 🔒 Admin     │                                │
│                    │  Console     │                                │
│                    └──────────────┘                                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ Streamlit session / function calls
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND ORCHESTRATION                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              KrishiSaathi (Facade — main.py)                 │  │
│  │  • Boots RAG engine    • Creates SupervisorAgent             │  │
│  │  • Exposes ask(query)  • Injects memory context              │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │            SupervisorAgent (supervisor_agent.py)              │  │
│  │  1. Classify intent (LLM call)                               │  │
│  │  2. Route to specialist agent(s)                             │  │
│  │  3. Synthesize final response (LLM call)                     │  │
│  └──┬──────┬──────┬──────┬──────┬───────────────────────────────┘  │
│     │      │      │      │      │                                   │
│     ▼      ▼      ▼      ▼      ▼                                  │
│  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐                         │
│  │Crop  ││Market││Scheme││Weathr││ Soil │  ← 5 Specialist Agents  │
│  │Doctor││Agent ││Agent ││Agent ││Expert│                          │
│  └──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘                         │
│     └───────┴───────┴───┬───┴───────┘                              │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Services Layer                             │  │
│  │  • LLMHelper (Groq + Gemini dual backend)                   │  │
│  │  • RAGEngine (ChromaDB + Gemini embeddings)                  │  │
│  │  • MemoryEngine (Mem0-inspired user memory)                  │  │
│  │  • SupabaseManager (auth, persistence)                       │  │
│  │  • WeatherService, TranslationService, VoiceService          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌─────────┐ ┌──────────┐
   │ Supabase   │ │ChromaDB │ │ External │
   │ (Auth,     │ │ (Vector │ │  APIs    │
   │  Storage)  │ │  Store) │ │          │
   └────────────┘ └─────────┘ └──────────┘
```

---

## 2. Directory Structure

```
KrishiSaathi-AI-Hackathon/
├── .streamlit/
│   └── config.toml                 # Streamlit theme & server settings
├── backend/
│   ├── agents/
│   │   ├── supervisor_agent.py     # Intent classification & orchestration
│   │   ├── crop_doctor_agent.py    # Disease detection & treatment
│   │   ├── market_agent.py         # Mandi prices & forecasting
│   │   ├── scheme_agent.py         # Government scheme eligibility
│   │   ├── soil_agent.py           # Soil health & fertilizer plans
│   │   └── weather_agent.py        # Weather forecasts & farm advisories
│   ├── knowledge_base/
│   │   ├── rag_engine.py           # ChromaDB + Gemini embedding pipeline
│   │   └── documents/              # Source JSON knowledge files
│   │       ├── crop_diseases.json
│   │       ├── farming_practices.json
│   │       ├── government_schemes.json
│   │       ├── market_data.json
│   │       └── soil_data.json
│   ├── data/
│   │   ├── crop_calendar.json
│   │   ├── mandi_prices.json
│   │   └── schemes_database.json
│   ├── services/
│   │   ├── llm_helper.py           # Dual Groq/Gemini LLM backend
│   │   ├── supabase_service.py     # Auth, DB, admin operations
│   │   ├── memory_engine.py        # Per-user memory with fact extraction
│   │   ├── weather_service.py      # OpenWeatherMap integration
│   │   ├── translation_service.py  # Multi-language support
│   │   ├── voice_service.py        # TTS / speech services
│   │   └── database_service.py     # Legacy SQLite (superseded by Supabase)
│   ├── config.py                   # Centralised config (env + admin overrides)
│   └── main.py                     # KrishiSaathi facade class
├── frontend/
│   ├── app.py                      # Main Streamlit chat page
│   ├── assets/                     # Logos, images
│   ├── components/
│   │   ├── auth.py                 # Login / signup / password reset
│   │   ├── chat_interface.py       # Chat bubble rendering
│   │   ├── sidebar.py              # Navigation + language selector
│   │   └── theme.py                # KrishiSaathi dark/light theme
│   └── pages/
│       ├── 1_🌱_Crop_Doctor.py
│       ├── 2_💰_Market_Prices.py
│       ├── 3_🏛️_Government_Schemes.py
│       ├── 4_🌤️_Weather.py
│       ├── 5_🧪_Soil_Expert.py
│       └── 6_🔒_Admin.py
├── scripts/
│   ├── ingest_knowledge_base.py    # Bulk-load JSON → ChromaDB
│   ├── test_integration.py         # End-to-end smoke tests
│   └── verify_keys.py              # API key validation
├── tests/
│   ├── test_agents.py
│   ├── test_rag.py
│   └── test_services.py
├── docs/                           # ← You are here
├── .env                            # API keys (local only)
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT
└── README.md                       # Project overview
```

---

## 3. Multi-Agent Orchestration

### 3.1 SupervisorAgent

The central orchestrator that converts every user query into a structured response:

```
User Query
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. CLASSIFY INTENT                       │
│    LLM call → JSON:                      │
│    {                                     │
│      "primary_intent": "crop_disease",   │
│      "secondary_intent": "weather",      │
│      "entities": { "crop": "tomato" },   │
│      "confidence": 0.92                  │
│    }                                     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 2. ROUTE TO SPECIALIST(S)               │
│    • Primary → CropDoctorAgent          │
│    • Secondary → WeatherAgent (if any)  │
│    • RAG context injected into prompt   │
│    • Memory context injected            │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 3. SYNTHESIZE RESPONSE                  │
│    Combine specialist outputs →          │
│    Single farmer-friendly answer         │
│    with Markdown formatting              │
└──────────────────────────────────────────┘
```

### 3.2 Specialist Agents

| Agent | File | RAG Collections | External Data |
|-------|------|-----------------|---------------|
| **Crop Doctor** | `crop_doctor_agent.py` | `crop_diseases`, `farming_practices` | Gemini Vision (image analysis) |
| **Market Agent** | `market_agent.py` | `market_data`, `mandi_prices` | eNAM / static mandi data |
| **Scheme Agent** | `scheme_agent.py` | `government_schemes`, `schemes_database` | — |
| **Weather Agent** | `weather_agent.py` | — | OpenWeatherMap API |
| **Soil Expert** | `soil_agent.py` | `soil_data` | — |

Each agent follows the same contract:

```python
class SpecialistAgent:
    def __init__(self, rag_engine: RAGEngine | None = None)
    def handle(self, query: str, entities: dict, ...) -> str
```

### 3.3 Lazy Initialization

Child agents are created on first use (`_get_agent()` factory in SupervisorAgent), so startup only loads the RAG engine; actual agent imports happen on demand.

---

## 4. RAG Knowledge Base

### 4.1 Embedding Pipeline

```
JSON Source Files                  ChromaDB Collections
─────────────────                  ────────────────────
crop_diseases.json        →       crop_diseases       (40+ docs)
farming_practices.json    →       farming_practices   (35+ docs)
government_schemes.json   →       government_schemes  (30+ docs)
market_data.json          →       market_data         (25+ docs)
soil_data.json            →       soil_data           (20+ docs)
crop_calendar.json        →       crop_calendar       (25+ docs)
mandi_prices.json         →       mandi_prices        (20+ docs)
schemes_database.json     →       schemes_database    (23+ docs)
                                  ─────────────────────────────
                                  Total: 218 documents
```

### 4.2 Embedding Model

- **Model**: `gemini-embedding-001` (Google Gemini)
- **Dimensions**: 768
- **Rate Limiting**: Built-in sleep + retry with exponential back-off
- **Persistence**: ChromaDB stores embeddings on disk (`chromadb_data/`)

### 4.3 Query Flow

```python
# 1. Generate query embedding
embedding = genai.embed_content(model="models/gemini-embedding-001", content=query)

# 2. Search top-k similar documents
results = collection.query(query_embeddings=[embedding], n_results=5)

# 3. Format context for agent prompt
context = format_rag_results(results)
```

### 4.4 Admin Document Management

The Admin console (tab 5) supports live CRUD on the knowledge base:

- **Add JSON documents** to any collection
- **Add plain-text** documents with auto-embedding
- **Import from URL** (fetch + ingest)
- **Delete collections** entirely
- **Browse samples** from each collection

---

## 5. LLM Backend

### 5.1 Dual-Backend Architecture

```
                  ┌──────────────────┐
                  │   LLMHelper      │
                  │   (Singleton)    │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │   Groq      │          │   Gemini    │
       │  (Primary)  │          │ (Fallback)  │
       │  Free Tier  │          │  Free Tier  │
       └─────────────┘          └─────────────┘
```

### 5.2 Groq Configuration

| Role | Model | Purpose |
|------|-------|---------|
| Classifier | `llama-3.1-8b-instant` | Fast intent classification |
| Agent | `llama-3.3-70b-versatile` | Deep reasoning for specialist agents |
| Synthesis | `llama-3.1-8b-instant` | Response synthesis |

### 5.3 Fallback Chain

Each role has a 3-model fallback chain. If the primary model hits rate limits or errors, the system automatically tries the next model:

```
classifier: llama-3.1-8b-instant → llama-3.3-70b-versatile → llama-4-scout
agent:      llama-3.3-70b-versatile → llama-4-scout → llama-3.1-8b-instant
synthesis:  llama-3.1-8b-instant → llama-3.3-70b-versatile → llama-4-scout
```

If all Groq models fail → falls back to **Gemini 2.0 Flash**.

### 5.4 Caching & Rate Limiting

- **In-memory response cache** to avoid duplicate LLM calls
- **Retry with exponential back-off** on transient errors
- **Configurable via Admin Console** (model, temperature, max tokens)

---

## 6. Authentication & User Management

### 6.1 Supabase Auth

```
Login/Signup Page
       │
       ▼
┌─────────────────┐     ┌──────────────────┐
│ frontend/       │────▶│ Supabase Auth    │
│ components/     │     │ (email/password) │
│ auth.py         │     └────────┬─────────┘
│                 │              │
│ require_auth()  │              ▼
│ gate on every   │     ┌──────────────────┐
│ page            │     │ profiles table   │
└─────────────────┘     │ (RLS: own row)   │
                        └──────────────────┘
```

### 6.2 Row-Level Security (RLS)

Every table uses Supabase RLS so users can only access their own data:

| Table | Policy |
|-------|--------|
| `profiles` | `auth.uid() = id` |
| `chat_history` | `auth.uid() = user_id` |
| `memories` | `auth.uid() = user_id` |
| `admin_settings` | Admin-only (service role or specific emails) |

### 6.3 Admin Authorization

Admin access is determined by email matching against `ADMIN_EMAILS` in config:

```python
def is_admin() -> bool:
    user = st.session_state.get("user", {})
    return user.get("email", "") in Config.ADMIN_EMAILS
```

---

## 7. Memory Engine

### 7.1 Mem0-Inspired Architecture

```
User Message
     │
     ▼
┌────────────────────────────────┐
│  LLM Fact Extraction           │
│  "I grow rice in Nalgonda"     │
│  → { category: "crops",        │
│       fact: "grows rice",       │
│       location: "Nalgonda" }   │
└──────────────┬─────────────────┘
               │
               ▼
┌────────────────────────────────┐
│  Deduplication                 │
│  Semantic similarity check     │
│  against existing memories     │
└──────────────┬─────────────────┘
               │
               ▼
┌────────────────────────────────┐
│  Supabase `memories` table     │
│  • user_id, category, fact     │
│  • embedding (768-dim)         │
│  • importance_score            │
│  • created_at, accessed_at     │
└────────────────────────────────┘
```

### 7.2 Memory Categories

| # | Category | Example |
|---|----------|---------|
| 1 | `personal_info` | Name, family size |
| 2 | `location` | Village, district, state |
| 3 | `crops` | Crops grown, varieties |
| 4 | `land` | Farm size, irrigation type |
| 5 | `soil` | Soil type, pH, nutrients |
| 6 | `livestock` | Animals, breeds |
| 7 | `equipment` | Tractor, pump details |
| 8 | `financial` | Budget, loan status |
| 9 | `preferences` | Language, communication style |
| 10 | `history` | Past issues, seasons |

### 7.3 Context Injection

On each query, the top-k most relevant memories are injected into the agent prompt:

```
System: You are KrishiSaathi. Here is what you remember about this farmer:
- Grows rice and cotton in Nalgonda district
- Has 3 acres with borewell irrigation
- Prefers Telugu language
- Previously had issues with brown planthopper
```

---

## 8. Frontend Layer

### 8.1 Page Architecture

| Page | Route | Purpose |
|------|-------|---------|
| Home (Chat) | `app.py` | General multi-agent chat |
| Crop Doctor | `pages/1_🌱_Crop_Doctor.py` | Image upload + disease diagnosis |
| Market Prices | `pages/2_💰_Market_Prices.py` | Mandi prices & trends |
| Government Schemes | `pages/3_🏛️_Government_Schemes.py` | Scheme eligibility |
| Weather | `pages/4_🌤️_Weather.py` | Location-based forecasts |
| Soil Expert | `pages/5_🧪_Soil_Expert.py` | Soil analysis & recommendations |
| Admin | `pages/6_🔒_Admin.py` | 7-tab admin console |

### 8.2 Theme System

Custom KrishiSaathi theme with dark/light mode toggle:

- **Primary**: `#2E7D32` (Agricultural Green)
- **Secondary**: `#FF8F00` (Harvest Gold)
- **Accent**: `#1565C0` (Sky Blue)
- Dark mode with `#0E1117` background

### 8.3 Admin Console Tabs

| Tab | Features |
|-----|----------|
| 📊 Overview | User counts, chat stats, system health |
| 👥 Users | User list, profiles, activity |
| 💬 Chat Logs | All conversations (admin view) |
| 🧠 Memories | Per-user memory inspection |
| 📚 Knowledge Base | CRUD on RAG collections |
| ⚙️ Configuration | Live config editor (LLM model, temp, etc.) |
| 🔧 System | Cache clear, RAG stats, diagnostics |

---

## 9. Data Flow

### 9.1 Complete Query Lifecycle

```
1. User types message in Streamlit UI
   │
2. require_auth() verifies Supabase session
   │
3. MemoryEngine.recall(user_id, query) → memory context string
   │
4. KrishiSaathi.ask(query, user_id, memory_context)
   │
5. SupervisorAgent.classify_intent(query)
   │  └─ LLM call (Groq classifier) → { intent, entities }
   │
6. SupervisorAgent routes to specialist agent(s)
   │  ├─ Agent queries RAG (ChromaDB) for relevant docs
   │  ├─ Agent may call external APIs (weather, prices)
   │  └─ Agent generates response via LLM (Groq agent model)
   │
7. SupervisorAgent.synthesize(agent_outputs)
   │  └─ LLM call (Groq synthesis) → final answer
   │
8. MemoryEngine.memorize(user_id, query + response)
   │  └─ LLM extracts facts → embed → deduplicate → store
   │
9. SupabaseManager.save_chat(user_id, query, response)
   │
10. Display response in chat UI
```

---

## 10. External Integrations

| Service | Purpose | Endpoint |
|---------|---------|----------|
| **Supabase** | Auth, profiles, chat history, memories, admin settings | `tmkvxwglzzsxorunufok.supabase.co` |
| **Groq Cloud** | Primary LLM inference (Llama models) | `api.groq.com` |
| **Google Gemini** | Embeddings, vision, fallback LLM | `generativelanguage.googleapis.com` |
| **OpenWeatherMap** | Weather data (current + 5-day forecast) | `api.openweathermap.org` |
| **ChromaDB** | Local vector store (persisted to disk) | In-process (no network) |

---

## 11. Deployment Architecture

### 11.1 Streamlit Cloud

```
GitHub Repository (branch: shashi)
        │
        ▼ (auto-deploy on push)
┌────────────────────────────┐
│  Streamlit Community Cloud │
│  • Python 3.13             │
│  • Ephemeral filesystem    │
│  • Secrets via st.secrets  │
│  • ChromaDB in-memory mode │
└────────────────────────────┘
        │
        ├──▶ Supabase (persistent data)
        ├──▶ Groq Cloud (LLM)
        ├──▶ Google AI (embeddings)
        └──▶ OpenWeatherMap (weather)
```

### 11.2 Environment Variables

| Variable | Source (Local) | Source (Cloud) |
|----------|----------------|----------------|
| `GEMINI_API_KEY` | `.env` | `st.secrets` |
| `GROQ_API_KEY` | `.env` | `st.secrets` |
| `OPENWEATHER_API_KEY` | `.env` | `st.secrets` |
| `SUPABASE_URL` | `.env` | `st.secrets` |
| `SUPABASE_KEY` | `.env` | `st.secrets` |
| `ADMIN_EMAILS` | `.env` | `st.secrets` (JSON array) |

---

*Last updated: February 2026*
