# 🚀 KrishiSaathi — Deployment Guide

> Step-by-step guide to deploy KrishiSaathi on Streamlit Community Cloud and run it locally.

---

## Table of Contents

1. [Local Development Setup](#1-local-development-setup)
2. [Environment Variables](#2-environment-variables)
3. [Knowledge Base Ingestion](#3-knowledge-base-ingestion)
4. [Supabase Setup](#4-supabase-setup)
5. [Streamlit Cloud Deployment](#5-streamlit-cloud-deployment)
6. [Post-Deployment Checklist](#6-post-deployment-checklist)
7. [Troubleshooting](#7-troubleshooting)
8. [Monitoring & Maintenance](#8-monitoring--maintenance)

---

## 1. Local Development Setup

### 1.1 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | 3.13 also supported |
| Git | Latest | For version control |
| pip | Latest | Comes with Python |

### 1.2 Installation

```bash
# Clone the repository
git clone https://github.com/smechello/KrishiSaathi-AI-Hackathon.git
cd KrishiSaathi-AI-Hackathon

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Running Locally

```bash
# Start the Streamlit app
streamlit run frontend/app.py

# The app will open at http://localhost:8501
```

---

## 2. Environment Variables

### 2.1 Required API Keys

Create a `.env` file in the project root:

```dotenv
# Google Gemini — embeddings, vision, fallback LLM
GEMINI_API_KEY=your_gemini_api_key

# Groq Cloud — primary LLM backend
GROQ_API_KEY=your_groq_api_key

# OpenWeatherMap — weather data
OPENWEATHER_API_KEY=your_openweather_api_key

# Supabase — auth & database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_jwt_anon_key

# Admin emails (JSON array)
ADMIN_EMAILS=["admin@example.com"]
```

### 2.2 Where to Get API Keys

| Service | Free Tier | Sign Up URL |
|---------|-----------|-------------|
| **Google AI Studio** (Gemini) | Free — generous limits | https://aistudio.google.com |
| **Groq Cloud** | Free developer plan — 30 RPM | https://console.groq.com |
| **OpenWeatherMap** | Free — 1M calls/month | https://openweathermap.org/api |
| **Supabase** | Free — 500 MB storage | https://supabase.com |

### 2.3 Important Notes

- `SUPABASE_KEY` must be the **JWT anon key** (starts with `eyJ...`), NOT the `sb_publishable_` key
- `ADMIN_EMAILS` is a JSON array: `["email1@example.com", "email2@example.com"]`
- Never commit `.env` to Git (it's in `.gitignore`)

---

## 3. Knowledge Base Ingestion

The RAG knowledge base must be built before the app can provide intelligent responses.

### 3.1 First-Time Ingestion

```bash
# Activate your virtual environment first, then:
python scripts/ingest_knowledge_base.py
```

This will:
1. Read all JSON files from `backend/knowledge_base/documents/` and `backend/data/`
2. Generate embeddings using Gemini (`gemini-embedding-001`)
3. Store vectors in ChromaDB (persisted to `chromadb_data/`)

### 3.2 Expected Output

```
Processing crop_diseases.json → crop_diseases collection ... 42 docs ✓
Processing farming_practices.json → farming_practices ... 35 docs ✓
Processing government_schemes.json → government_schemes ... 30 docs ✓
...
Total: 218 documents across 8 collections
```

### 3.3 Re-Ingestion

ChromaDB persists data to disk. You only need to re-ingest when:
- Knowledge base JSON files are updated
- The `chromadb_data/` directory is deleted
- Deploying to Streamlit Cloud (ephemeral filesystem)

> **Note:** On Streamlit Cloud, ChromaDB runs in-memory mode and re-ingests on each cold start.

---

## 4. Supabase Setup

Refer to the detailed guide: **[SUPABASE_SETUP.md](SUPABASE_SETUP.md)**

Quick summary of required tables:

| Table | Purpose |
|-------|---------|
| `profiles` | User profile data (extends auth.users) |
| `chat_history` | Per-user conversation storage |
| `memories` | Per-user memory facts (Mem0-style) |
| `admin_settings` | Admin configuration persistence |

All tables have **Row-Level Security (RLS)** enabled.

---

## 5. Streamlit Cloud Deployment

### 5.1 Prerequisites

- GitHub repository with the project code
- Streamlit Cloud account (free, sign in with GitHub)

### 5.2 Step-by-Step Deployment

#### Step 1: Push to GitHub

```bash
git add .
git commit -m "chore: prepare for deployment"
git push origin shashi
```

#### Step 2: Create Streamlit App

1. Go to https://share.streamlit.io
2. Click **"New app"**
3. Configure:
   - **Repository**: `smechello/KrishiSaathi-AI-Hackathon`
   - **Branch**: `shashi`
   - **Main file path**: `frontend/app.py`

#### Step 3: Configure Secrets

In the Streamlit Cloud dashboard, go to **Settings → Secrets** and add:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GROQ_API_KEY = "your_groq_api_key"
OPENWEATHER_API_KEY = "your_openweather_api_key"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
ADMIN_EMAILS = '["admin@example.com"]'
```

> **Critical:** `ADMIN_EMAILS` must be a string containing a JSON array (wrapped in single quotes in TOML). Streamlit auto-parses JSON arrays into Python lists — the app handles both formats.

#### Step 4: Deploy

Click **"Deploy!"** — Streamlit Cloud will:
1. Install dependencies from `requirements.txt`
2. Run `frontend/app.py`
3. Assign a URL: `https://your-app-name.streamlit.app`

### 5.3 Streamlit Cloud Considerations

| Aspect | Behavior |
|--------|----------|
| **Filesystem** | Ephemeral — wiped on every restart |
| **ChromaDB** | Runs in-memory, re-ingests on cold start |
| **Admin settings** | Stored in Supabase (not local JSON) |
| **Python version** | May differ from local (currently 3.13) |
| **Memory** | 1 GB limit on free tier |
| **Secrets** | Accessible via `st.secrets` |

### 5.4 Custom Domain (Optional)

In Streamlit Cloud settings → **General** → set custom URL slug.

---

## 6. Post-Deployment Checklist

- [ ] App loads without errors at the assigned URL
- [ ] Supabase login/signup works
- [ ] Chat produces AI responses (Groq LLM connected)
- [ ] Crop Doctor page accepts image uploads (Gemini Vision connected)
- [ ] Weather page returns forecasts (OpenWeatherMap connected)
- [ ] RAG knowledge base is populated (check Admin → System tab)
- [ ] Admin console is accessible for admin emails only
- [ ] Chat history persists across sessions (Supabase)
- [ ] Memory engine extracts and stores facts

---

## 7. Troubleshooting

### 7.1 Common Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError` | Missing dependency | Add to `requirements.txt` and redeploy |
| `KeyError: 'GEMINI_API_KEY'` | Missing secret | Add to Streamlit Cloud Secrets |
| `AttributeError: 'list' has no attribute 'startswith'` | `ADMIN_EMAILS` parsed as list | App already handles this — ensure latest code |
| `DuplicateWidgetID` | Streamlit widget key conflict | Add unique `key=` params |
| `OperationalError: database is locked` | SQLite on cloud | Use Supabase instead (already configured) |
| Supabase redirect to `localhost:3000` | Site URL not configured | Set Site URL in Supabase Dashboard → Auth |

### 7.2 Viewing Logs

- **Streamlit Cloud**: Click **"Manage app"** → **"Logs"** (bottom-right corner)
- **Local**: Logs print to the terminal running `streamlit run`

### 7.3 Force Reboot

In Streamlit Cloud dashboard → **Settings** → **"Reboot app"**

---

## 8. Monitoring & Maintenance

### 8.1 Admin Console

The built-in Admin Console (page 6) provides:

- **Overview**: User count, chat count, system health
- **System tab**: ChromaDB stats, cache management, agent diagnostics

### 8.2 Supabase Dashboard

Monitor at `https://supabase.com/dashboard`:

- **Auth**: Active users, sign-up rate
- **Database**: Table sizes, query performance
- **Storage**: Usage vs free-tier limits

### 8.3 API Usage Monitoring

| Service | Dashboard |
|---------|-----------|
| Groq | https://console.groq.com/usage |
| Google AI | https://aistudio.google.com |
| OpenWeatherMap | https://home.openweathermap.org/api_keys |

### 8.4 Updating the App

```bash
# Make changes locally
git add .
git commit -m "feat: your changes"
git push origin shashi

# Streamlit Cloud auto-deploys on push ✓
```

---

*Last updated: February 2026*
