# 📚 KrishiSaathi — Documentation Index

> Complete documentation for the KrishiSaathi AI-Powered Multi-Agent Agricultural Intelligence System.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System architecture, data flow, component design |
| [**API_REFERENCE.md**](API_REFERENCE.md) | Internal Python API — agents, services, RAG engine |
| [**USER_GUIDE.md**](USER_GUIDE.md) | End-user guide for farmers and users |
| [**DEPLOYMENT.md**](DEPLOYMENT.md) | Local setup and Streamlit Cloud deployment |
| [**SUPABASE_SETUP.md**](SUPABASE_SETUP.md) | Database tables, RLS policies, SQL scripts |
| [**CONTRIBUTING.md**](CONTRIBUTING.md) | Team profiles, branch strategy, coding standards |
| [**SECURITY.md**](SECURITY.md) | Security architecture, privacy, compliance |
| [**CHANGELOG.md**](CHANGELOG.md) | Version history and release notes |

---

## For Different Audiences

### 👨‍🌾 Farmers / End Users
→ Start with [**USER_GUIDE.md**](USER_GUIDE.md)

### 👩‍💻 Developers / Contributors
→ Start with [**CONTRIBUTING.md**](CONTRIBUTING.md), then [**ARCHITECTURE.md**](ARCHITECTURE.md) and [**API_REFERENCE.md**](API_REFERENCE.md)

### 🚀 Deployers / DevOps
→ Start with [**DEPLOYMENT.md**](DEPLOYMENT.md) and [**SUPABASE_SETUP.md**](SUPABASE_SETUP.md)

### 🏆 Hackathon Judges
→ See the [**README.md**](../README.md) for project overview, then [**ARCHITECTURE.md**](ARCHITECTURE.md) for deep-dive

---

## Project Overview

**KrishiSaathi** is a Multi-Agent AI Agricultural Advisory System designed for Indian farmers, built for the AWS AI for Bharat Hackathon 2026.

### Key Numbers

| Metric | Value |
|--------|-------|
| Specialist AI Agents | 6 (Supervisor + 5 domain experts) |
| RAG Documents | 218 across 8 collections |
| Supported Languages | 12 Indian languages |
| LLM Models | Groq (Llama 3.3-70B) + Gemini (fallback) |
| Memory Categories | 10 per-user memory types |
| Admin Console Tabs | 7 management panels |
| Frontend Pages | 6 (Chat + 5 specialist pages + Admin) |

### Tech Stack

- **Frontend:** Streamlit 1.45
- **LLM:** Groq Cloud (primary) + Google Gemini (fallback)
- **Embeddings:** Gemini Embedding API (768-dim)
- **Vector Store:** ChromaDB 1.4
- **Auth & DB:** Supabase (PostgreSQL + Auth)
- **Weather:** OpenWeatherMap API
- **Deployment:** Streamlit Community Cloud
- **Language:** Python 3.12+

---

## Repository Root Docs

These documents are in the repository root (not `docs/`):

| File | Description |
|------|-------------|
| [README.md](../README.md) | Project overview, problem statement, architecture |
| [design.md](../design.md) | Detailed system design (hackathon submission) |
| [requirements.md](../requirements.md) | Functional & technical requirements specification |
| [LICENSE](../LICENSE) | MIT License |

---

<div align="center">

**🌾 KrishiSaathi — Because Every Farmer Deserves a Team of AI Experts**

</div>
