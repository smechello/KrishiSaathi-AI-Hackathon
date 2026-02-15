# 📋 KrishiSaathi — Changelog

All notable changes to the KrishiSaathi project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### 🔧 Fixed

**Password Reset Flow**
- Added dedicated password reset page (`frontend/pages/Reset_Password.py`)
- Added `verify_recovery_token()` method to SupabaseManager for handling password reset tokens from email links
- Added `update_password()` method to SupabaseManager for updating user passwords
- Password reset emails now properly redirect to a dedicated reset page where users can set a new password
- Improved user experience with clear success/error messaging and automatic redirect after password update
- Updated documentation with password reset configuration instructions

---

## [1.0.0] — 2026-02-07

### 🎉 Initial Release — AWS AI for Bharat Hackathon 2026

#### Added

**Multi-Agent System**
- SupervisorAgent: Intent classification, routing, and response synthesis
- CropDoctorAgent: Disease detection with Gemini Vision + RAG knowledge base
- MarketAgent: Mandi price queries with regional market data
- SchemeAgent: Government scheme eligibility checking and application guidance
- WeatherAgent: Location-based forecasts via OpenWeatherMap API
- SoilAgent: Soil health analysis and fertilizer recommendations

**RAG Knowledge Base**
- ChromaDB vector store with 218 documents across 8 collections
- Gemini Embedding API (`gemini-embedding-001`) for 768-dim embeddings
- Collections: crop_diseases, farming_practices, government_schemes, market_data, soil_data, crop_calendar, mandi_prices, schemes_database
- Admin CRUD: add JSON, add text, import from URL, delete collections

**LLM Backend**
- Dual Groq/Gemini backend with automatic fallback
- Groq: `llama-3.3-70b-versatile` (agent), `llama-3.1-8b-instant` (classifier/synthesis)
- 3-model fallback chain per role
- Gemini 2.0 Flash as ultimate fallback
- In-memory response cache with cache stats

**Authentication & User Management**
- Supabase email/password authentication
- `require_auth()` gate on every page
- User profiles with location, language preference, phone
- Row-Level Security (RLS) on all tables
- Password reset via email

**Memory Engine (Mem0-Inspired)**
- LLM-based fact extraction from conversations
- 10 memory categories (personal_info, location, crops, land, soil, livestock, equipment, financial, preferences, history)
- Semantic search with Gemini embeddings
- Deduplication via cosine similarity
- Importance scoring and time decay
- Supabase persistence

**Frontend**
- Streamlit-based responsive UI with 6 pages
- KrishiSaathi branded theme (dark/light mode)
- Chat interface with message bubbles and Markdown rendering
- Language selector supporting 12 Indian languages
- Image upload for Crop Doctor
- Per-user chat history persistence

**Admin Console (7 tabs)**
- 📊 Overview: User counts, chat stats, system health
- 👥 Users: User list, profiles, activity breakdown
- 💬 Chat Logs: All conversations with filtering
- 🧠 Memories: Per-user memory inspection
- 📚 Knowledge Base: CRUD on RAG collections, URL import
- ⚙️ Configuration: Live config editor (LLM model, temperature, max tokens)
- 🔧 System: Cache management, RAG stats, diagnostics

**Deployment**
- Streamlit Cloud deployment at `krishisaathi-ai-hackathon.streamlit.app`
- Supabase persistence for admin settings (cloud-safe)
- Local JSON fallback for admin config
- Comprehensive `requirements.txt` with all dependencies

**Documentation**
- ARCHITECTURE.md — System architecture and data flow
- API_REFERENCE.md — Complete internal API docs
- CONTRIBUTING.md — Team profiles and contribution guide
- DEPLOYMENT.md — Local and cloud deployment guide
- SECURITY.md — Security architecture and privacy
- SUPABASE_SETUP.md — Database setup with SQL scripts
- USER_GUIDE.md — End-user documentation
- CHANGELOG.md — This file

**Infrastructure**
- `.env` + `st.secrets` dual config loading
- `.gitignore` for secrets, caches, virtual environments
- MIT License
- Scripts: `ingest_knowledge_base.py`, `test_integration.py`, `verify_keys.py`
- Tests: `test_agents.py`, `test_rag.py`, `test_services.py`

#### Fixed
- Nested expanders crash on Streamlit Cloud → replaced with `st.tabs`
- `st.secrets` auto-parsing JSON arrays → `isinstance(list)` guard
- `SUPABASE_KEY` wrong format → documented JWT requirement
- Supabase email redirect to `localhost:3000` → Site URL fix documented
- `TYPE_CHECKING` import pattern for Supabase `Client` type

---

## [0.1.0] — 2026-02-04

### 🏗️ Project Scaffolding

#### Added
- Initial project structure (`backend/`, `frontend/`, `scripts/`, `tests/`)
- `design.md` — Complete system design document
- `requirements.md` — Functional and technical requirements
- `README.md` — Project overview with architecture diagrams
- MIT License

---

*Last updated: February 2026*
