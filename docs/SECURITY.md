# 🔐 KrishiSaathi — Security & Privacy

> Security architecture, data privacy practices, and compliance for the KrishiSaathi platform.

---

## Table of Contents

1. [Security Overview](#1-security-overview)
2. [Authentication](#2-authentication)
3. [Authorization & Access Control](#3-authorization--access-control)
4. [Data Protection](#4-data-protection)
5. [API Key Management](#5-api-key-management)
6. [Infrastructure Security](#6-infrastructure-security)
7. [Privacy Policy](#7-privacy-policy)
8. [Compliance](#8-compliance)
9. [Incident Response](#9-incident-response)
10. [Security Checklist](#10-security-checklist)

---

## 1. Security Overview

KrishiSaathi implements a defense-in-depth approach to security:

```
┌───────────────────────────────────────────────┐
│ Layer 1: Authentication (Supabase Auth)       │
│   Email/password with JWT tokens              │
├───────────────────────────────────────────────┤
│ Layer 2: Authorization (RLS + Admin Checks)   │
│   Row-Level Security on every table           │
├───────────────────────────────────────────────┤
│ Layer 3: Transport (HTTPS/TLS)                │
│   All traffic encrypted in transit            │
├───────────────────────────────────────────────┤
│ Layer 4: Data at Rest                         │
│   Supabase encrypts stored data               │
├───────────────────────────────────────────────┤
│ Layer 5: Secret Management                    │
│   .env locally, st.secrets on cloud           │
└───────────────────────────────────────────────┘
```

---

## 2. Authentication

### 2.1 Supabase Auth

KrishiSaathi uses **Supabase Authentication** (built on GoTrue) for user identity:

| Feature | Implementation |
|---------|---------------|
| Method | Email + Password |
| Token format | JWT (JSON Web Token) |
| Token storage | Streamlit session state (server-side) |
| Session duration | Configurable (default: 1 week) |
| Password minimum | 6 characters |
| Email confirmation | Configurable in Supabase Dashboard |

### 2.2 Auth Flow

```
1. User submits email + password
2. Supabase validates credentials
3. Returns JWT access_token + refresh_token
4. Tokens stored in st.session_state (server-side, never in browser localStorage)
5. Every page call checks require_auth() before rendering
6. On sign-out, tokens are cleared from session state
```

### 2.3 Auth Gate

Every page is protected by `require_auth()`:

```python
from frontend.components.auth import require_auth

user = require_auth()  # Redirects to login if not authenticated
if not user:
    st.stop()
```

---

## 3. Authorization & Access Control

### 3.1 Row-Level Security (RLS)

Every Supabase table has RLS enabled with policies ensuring users can only access their own data:

| Table | Policy | Rule |
|-------|--------|------|
| `profiles` | Select/Update own | `auth.uid() = id` |
| `chat_history` | Select/Insert own | `auth.uid() = user_id` |
| `memories` | Select/Insert/Delete own | `auth.uid() = user_id` |
| `admin_settings` | Select/Update (admin only) | Service role or admin email check |

### 3.2 Admin Access

Admin functionality is restricted by email whitelist:

```python
# In backend/config.py
ADMIN_EMAILS = ["admin@example.com"]

# In frontend — checked on every admin page render
def is_admin() -> bool:
    user = st.session_state.get("user", {})
    return user.get("email", "") in Config.ADMIN_EMAILS
```

Admin capabilities:
- View all users and their activity
- Access all chat logs and memories
- Modify system configuration
- Manage knowledge base
- Delete user data

### 3.3 Principle of Least Privilege

- Regular users: Can only read/write their own profile, chats, and memories
- Admins: Can read all data, modify config; determined by email whitelist
- Service role key: Only used server-side, never exposed to frontend

---

## 4. Data Protection

### 4.1 Data in Transit

| Path | Encryption |
|------|-----------|
| Browser → Streamlit Cloud | HTTPS (TLS 1.2+) |
| Streamlit → Supabase | HTTPS (TLS 1.2+) |
| Streamlit → Groq API | HTTPS (TLS 1.2+) |
| Streamlit → Google Gemini API | HTTPS (TLS 1.2+) |
| Streamlit → OpenWeatherMap API | HTTPS |

### 4.2 Data at Rest

| Store | Encryption |
|-------|-----------|
| Supabase (PostgreSQL) | AES-256 at rest (Supabase managed) |
| ChromaDB (local/in-memory) | Not encrypted (ephemeral on cloud) |
| Streamlit session state | In-memory only (server-side) |

### 4.3 Data Collected

| Data Type | Purpose | Stored Where | Retention |
|-----------|---------|-------------|-----------|
| Email, name | Authentication | Supabase `profiles` | Until account deletion |
| Location, phone | Personalization | Supabase `profiles` | Until account deletion |
| Chat messages | Conversation history | Supabase `chat_history` | Until user clears or admin deletes |
| Memory facts | Personalized responses | Supabase `memories` | Until user clears |
| Crop photos | Disease diagnosis | Not stored permanently | Session-only |

### 4.4 Data NOT Collected

- Browsing history outside KrishiSaathi
- Device identifiers or fingerprints
- IP addresses (Streamlit Cloud handles routing)
- Payment or banking information
- Aadhaar or government ID numbers

---

## 5. API Key Management

### 5.1 Key Storage

| Environment | Method | Security |
|-------------|--------|----------|
| Local development | `.env` file | Added to `.gitignore`, never committed |
| Streamlit Cloud | `st.secrets` | Encrypted, accessible only to app owner |
| CI/CD | GitHub Secrets | Encrypted repository secrets |

### 5.2 Keys Used

| Key | Service | Scope |
|-----|---------|-------|
| `GEMINI_API_KEY` | Google AI Studio | Embeddings, vision, fallback LLM |
| `GROQ_API_KEY` | Groq Cloud | Primary LLM inference |
| `OPENWEATHER_API_KEY` | OpenWeatherMap | Weather data (read-only) |
| `SUPABASE_URL` | Supabase | Project URL (public) |
| `SUPABASE_KEY` | Supabase | Anon JWT key (public, RLS-protected) |

### 5.3 Key Rotation

- API keys can be rotated in the respective service dashboards
- Update `.env` (local) and `st.secrets` (cloud) after rotation
- App restarts automatically pick up new keys

---

## 6. Infrastructure Security

### 6.1 Streamlit Cloud

- Managed by Streamlit Inc. (Snowflake)
- **Ephemeral containers**: No persistent local storage
- **HTTPS enforced**: All traffic encrypted
- **No SSH access**: Immutable infrastructure
- **Auto-restart**: App restarts on crash or config change

### 6.2 Supabase

- Hosted on AWS infrastructure
- PostgreSQL with **RLS enforced** at the database level
- **Automatic backups** (daily, managed by Supabase)
- **Point-in-time recovery** available on paid plans
- **SOC 2 Type II compliant**

### 6.3 Third-Party APIs

| Service | Security Certification |
|---------|----------------------|
| Groq Cloud | SOC 2, encrypted inference |
| Google Gemini | Google Cloud security (ISO 27001, SOC 2) |
| OpenWeatherMap | Standard API security |

---

## 7. Privacy Policy

### 7.1 Data Usage

- User data is used **exclusively** for providing agricultural advisory services
- **No data is sold** to third parties
- **No advertising** or tracking
- Chat data may be used to improve response quality (anonymized)

### 7.2 User Rights

Users have the right to:

| Right | How to Exercise |
|-------|----------------|
| **Access** | View all your data in the app (profile, chats, memories) |
| **Correction** | Update your profile anytime via sidebar |
| **Deletion** | Clear chat history via sidebar; request full deletion via admin |
| **Portability** | Contact admin for data export |
| **Withdraw consent** | Delete account (contact admin) |

### 7.3 Data Sharing

Data is shared only with:
- **LLM providers** (Groq, Google): Query text sent for processing (not stored by providers beyond API processing)
- **OpenWeatherMap**: City name for weather queries
- **No other third parties**

---

## 8. Compliance

### 8.1 Indian Regulatory Framework

| Regulation | Status | Notes |
|-----------|--------|-------|
| IT Act 2000 | ✅ Compliant | Reasonable security practices implemented |
| Digital Personal Data Protection Act 2023 | ✅ Designed for compliance | Purpose limitation, data minimization, consent-based |
| RBI data localization (if applicable) | ✅ | No payment data collected |

### 8.2 International Standards

| Standard | Status |
|----------|--------|
| OWASP Top 10 | Addressed via Supabase managed infrastructure |
| Data minimization (GDPR principle) | ✅ Only essential data collected |
| Right to be forgotten | ✅ Deletion available |

---

## 9. Incident Response

### 9.1 If a Security Issue is Discovered

1. **Report** to the team lead immediately (see [CONTRIBUTING.md](CONTRIBUTING.md))
2. **Assess** impact scope (data affected, users affected)
3. **Contain** — rotate compromised API keys, disable affected services
4. **Fix** — patch the vulnerability
5. **Notify** — inform affected users if data was compromised
6. **Document** — record the incident and remediation steps

### 9.2 Contact for Security Issues

For security concerns, contact the team lead:

- **Shashidhar Reddy N** — [LinkedIn](https://linkedin.com/in/reddynalamari)

---

## 10. Security Checklist

### Pre-Deployment

- [x] All API keys stored in `.env` / `st.secrets` (never hardcoded)
- [x] `.env` listed in `.gitignore`
- [x] Supabase RLS enabled on all tables
- [x] Admin access restricted by email whitelist
- [x] `require_auth()` gate on every page
- [x] HTTPS enforced (Streamlit Cloud default)
- [x] No sensitive data in error messages or logs
- [x] `SUPABASE_KEY` is the anon JWT key (not service role)

### Ongoing

- [ ] Rotate API keys periodically
- [ ] Monitor Supabase usage dashboard for anomalies
- [ ] Review admin access list quarterly
- [ ] Update dependencies for security patches (`pip install --upgrade`)
- [ ] Review Streamlit Cloud logs for errors

---

*Last updated: February 2026*
