# 🤝 Contributing to KrishiSaathi

Thank you for your interest in contributing to **KrishiSaathi** — an AI-powered agricultural advisory system built for Indian farmers.

---

## 👥 Team

We are a team of 4 passionate developers from India, building KrishiSaathi for the **AWS AI for Bharat Hackathon 2026** under the track *AI for Rural Innovation & Sustainable Systems*.

### Core Team

<table>
  <tr>
    <td align="center">
      <strong>Shashidhar Reddy N</strong><br/>
      <em>Team Lead & Full-Stack Developer</em><br/>
      Multi-agent architecture, RAG pipeline, backend services, deployment<br/><br/>
      <a href="https://linkedin.com/in/reddynalamari">
        <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Vishnu Preshitha M</strong><br/>
      <em>AI/ML Engineer</em><br/>
      Agent design, LLM prompt engineering, knowledge base curation<br/><br/>
      <a href="https://linkedin.com/in/vishnupreshitham">
        <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Pranavi P</strong><br/>
      <em>Frontend & UX Developer</em><br/>
      Streamlit UI, theme system, user experience, accessibility<br/><br/>
      <a href="https://linkedin.com/in/pranavip">
        <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Sai Shiva P</strong><br/>
      <em>Data & Integration Engineer</em><br/>
      Supabase setup, API integrations, testing, documentation<br/><br/>
      <a href="https://linkedin.com/in/saishivap">
        <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/>
      </a>
    </td>
  </tr>
</table>

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **Git**
- API keys for: Google Gemini, Groq, OpenWeatherMap
- Supabase project (free tier)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/smechello/KrishiSaathi-AI-Hackathon.git
cd KrishiSaathi-AI-Hackathon

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Ingest knowledge base (first time only)
python scripts/ingest_knowledge_base.py

# 6. Run the app
streamlit run frontend/app.py
```

---

## 📁 Project Structure

```
backend/
├── agents/          # 5 specialist agents + supervisor
├── knowledge_base/  # RAG engine + JSON documents
├── services/        # LLM, Supabase, memory, weather, etc.
├── config.py        # Centralised configuration
└── main.py          # KrishiSaathi facade

frontend/
├── app.py           # Main chat page
├── components/      # Reusable UI (auth, sidebar, theme)
└── pages/           # Feature pages (Crop Doctor, Market, etc.)

docs/                # Project documentation
scripts/             # Utility scripts (ingest, test, verify)
tests/               # Unit & integration tests
```

---

## 🔀 Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable release |
| `shashi` | Active development branch |
| `feature/*` | Feature branches (merge into `shashi`) |

### Workflow

1. Create a feature branch from `shashi`:
   ```bash
   git checkout shashi
   git pull origin shashi
   git checkout -b feature/your-feature-name
   ```

2. Make changes, commit with descriptive messages:
   ```bash
   git add .
   git commit -m "feat: add crop rotation logic to soil agent"
   ```

3. Push and open a Pull Request targeting `shashi`.

---

## ✍️ Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `style:` | Formatting, CSS, no code change |
| `refactor:` | Code restructuring |
| `test:` | Adding or updating tests |
| `chore:` | Build, config, or dependency updates |

**Examples:**
```
feat: add memory engine with Supabase persistence
fix: resolve nested expander crash on Streamlit Cloud
docs: add architecture and deployment guides
chore: update requirements.txt with new dependencies
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run integration tests
python scripts/test_integration.py
```

### Test Structure

| File | Coverage |
|------|----------|
| `tests/test_agents.py` | Agent classification & response |
| `tests/test_rag.py` | RAG engine queries & embeddings |
| `tests/test_services.py` | LLM, Supabase, weather services |
| `scripts/test_integration.py` | End-to-end query flow |

---

## 📝 Code Style

- **Python**: Follow PEP 8 with type hints (`from __future__ import annotations`)
- **Docstrings**: Google-style docstrings for all public functions
- **Imports**: Use absolute imports from project root (`from backend.config import Config`)
- **Line length**: 120 characters max
- **Formatting**: Black-compatible formatting preferred

---

## 📄 Adding Knowledge Base Documents

To add new agricultural data to the RAG knowledge base:

1. Create or update a JSON file in `backend/knowledge_base/documents/` or `backend/data/`
2. Follow the existing structure (list of records with descriptive text fields)
3. Add the mapping to `COLLECTION_MAP` in `rag_engine.py`
4. Run the ingest script:
   ```bash
   python scripts/ingest_knowledge_base.py
   ```
5. Alternatively, use the **Admin Console → Knowledge Base** tab for live ingestion

---

## 🐛 Reporting Issues

When reporting bugs, include:

1. **Steps to reproduce** the issue
2. **Expected vs actual** behavior
3. **Environment** (OS, Python version, browser)
4. **Error logs** (from terminal or browser console)
5. **Screenshots** if applicable

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](../LICENSE).

---

<div align="center">

**🌾 Built with ❤️ for Indian Farmers**

*KrishiSaathi — Because Every Farmer Deserves a Team of AI Experts*

</div>
