# Supabase Setup Guide — KrishiSaathi

> Run the SQL below in the **Supabase SQL Editor** (Dashboard → SQL Editor → New Query) **before** starting the app.

---

## 1. Environment Variables

Add these to your `.env` file (project root) or Streamlit secrets:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key
```

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API → `anon` / `public` key |

---

## 2. Create Tables & RLS Policies

Copy-paste the entire block below into the SQL Editor and click **Run**.

```sql
-- ═══════════════════════════════════════════════════════════════════
--  KrishiSaathi — Supabase schema
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Profiles (extends auth.users) ──────────────────────────────

CREATE TABLE IF NOT EXISTS public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name       TEXT,
    preferred_language TEXT DEFAULT 'en',
    location        TEXT,
    phone           TEXT,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.profiles IS 'User profile data — one row per auth user.';

-- ── 2. Chat history ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.chat_history (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    sources     JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_user
    ON public.chat_history (user_id, created_at);

COMMENT ON TABLE public.chat_history IS 'Per-user chat messages — ordered by created_at.';

-- ═══════════════════════════════════════════════════════════════════
--  Row-Level Security (RLS)
-- ═══════════════════════════════════════════════════════════════════

-- profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- chat_history
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own chat"
    ON public.chat_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chat"
    ON public.chat_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own chat"
    ON public.chat_history FOR DELETE
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
--  Auto-create profile on sign-up (trigger)
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', '')
    );
    RETURN NEW;
END;
$$;

-- Drop if it already exists so the script is idempotent
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
```

---

## 2b. Admin RLS Policies

Admin users need to read **all** profiles, chat_history, and memories.
Create a helper function and add policies (replace the email list with your admin emails):

```sql
-- ═══════════════════════════════════════════════════════════════════
--  Admin helper function + read-all policies
-- ═══════════════════════════════════════════════════════════════════

-- Helper: returns TRUE if current user is an admin
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth.users
        WHERE id = auth.uid()
        AND email = ANY(ARRAY[
            'hiimamanenu@gmail.com'
            -- Add more admin emails here, comma-separated
        ])
    );
$$;

-- Admins can read ALL profiles
CREATE POLICY "Admins can read all profiles"
    ON public.profiles FOR SELECT
    USING (public.is_admin());

-- Admins can read ALL chat history
CREATE POLICY "Admins can read all chat"
    ON public.chat_history FOR SELECT
    USING (public.is_admin());

-- Admins can delete any chat history
CREATE POLICY "Admins can delete any chat"
    ON public.chat_history FOR DELETE
    USING (public.is_admin());

-- Admins can read ALL memories
CREATE POLICY "Admins can read all memories"
    ON public.memories FOR SELECT
    USING (public.is_admin());

-- Admins can delete any memories
CREATE POLICY "Admins can delete any memories"
    ON public.memories FOR DELETE
    USING (public.is_admin());
```

> **Important:** Update the email array in `is_admin()` whenever you add/remove admins.

---

## 3. Admin Settings Table (Cloud-persistent config)

This table stores admin dashboard settings (LLM config, API sources, etc.)
so they survive Streamlit Cloud redeploys.

```sql
-- ═══════════════════════════════════════════════════════════════════
--  Admin Settings — key-value config store
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.admin_settings (
    id          TEXT PRIMARY KEY DEFAULT 'global',
    settings    JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.admin_settings IS 'Admin dashboard config — single row, key=global.';

-- RLS: only admins can read/write
ALTER TABLE public.admin_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can read admin_settings"
    ON public.admin_settings FOR SELECT
    USING (public.is_admin());

CREATE POLICY "Admins can insert admin_settings"
    ON public.admin_settings FOR INSERT
    WITH CHECK (public.is_admin());

CREATE POLICY "Admins can update admin_settings"
    ON public.admin_settings FOR UPDATE
    USING (public.is_admin());
```

> **Note:** This table requires the `is_admin()` function from section 2b.
> Run section 2b first, then this section.

---

## 4. Memories Table (AI Memory System)

Run this SQL to enable the mem0-inspired memory system:

```sql
-- ═══════════════════════════════════════════════════════════════════
--  KrishiSaathi — Memories (mem0-inspired long-term user memory)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.memories (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'personal'
                    CHECK (category IN (
                        'personal', 'location', 'farming', 'crops',
                        'equipment', 'livestock', 'soil', 'preferences',
                        'experience', 'financial'
                    )),
    importance      SMALLINT NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    access_count    INT NOT NULL DEFAULT 0,
    embedding       TEXT,                          -- JSON-encoded float[] from Gemini
    metadata        JSONB DEFAULT '{}'::jsonb,     -- extensible key-value store
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memories_user
    ON public.memories (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_memories_category
    ON public.memories (user_id, category);

COMMENT ON TABLE public.memories IS 'Per-user long-term memories — extracted from conversations by AI.';

-- ── RLS ───────────────────────────────────────────────────────────

ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own memories"
    ON public.memories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own memories"
    ON public.memories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own memories"
    ON public.memories FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own memories"
    ON public.memories FOR DELETE
    USING (auth.uid() = user_id);
```

---

## 5. Supabase Auth Settings (Optional but Recommended)

In the Supabase Dashboard → **Authentication → Providers → Email**:

| Setting | Recommended Value | Why |
|---|---|---|
| **Confirm email** | ❌ Disabled | KrishiSaathi uses its own email service for verification |
| **Secure email change** | ✅ Enabled | Standard security |
| **Minimum password length** | 6 | Default |

> **Important:** If you are using the custom email service (Gmail SMTP),
> you must **disable** Supabase's built-in email confirmation so that
> users are created immediately and our own verification flow takes over.

---

## 6. Custom Email Service — Additional Tables

If you enable the custom Gmail SMTP email service (by setting
`EMAIL_ADDRESS`, `EMAIL_PASSWORD`, and `SUPABASE_SERVICE_KEY`), you need
these extra database objects.

### 6.1 Add columns to `profiles`

```sql
-- Email address + verification flag
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS email TEXT,
  ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false;

-- Grandfather existing users as verified
UPDATE public.profiles SET email_verified = true;
```

### 6.2 Email verification tokens

```sql
CREATE TABLE IF NOT EXISTS public.email_verifications (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.email_verifications ENABLE ROW LEVEL SECURITY;

-- Tokens are UUID-based and unguessable; permissive policies are safe
CREATE POLICY "email_verifications_select"
    ON public.email_verifications FOR SELECT USING (true);
CREATE POLICY "email_verifications_insert"
    ON public.email_verifications FOR INSERT WITH CHECK (true);
CREATE POLICY "email_verifications_delete"
    ON public.email_verifications FOR DELETE USING (true);
```

### 6.3 Password reset tokens

```sql
CREATE TABLE IF NOT EXISTS public.password_resets (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '1 hour'),
    used        BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.password_resets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "password_resets_select"
    ON public.password_resets FOR SELECT USING (true);
CREATE POLICY "password_resets_insert"
    ON public.password_resets FOR INSERT WITH CHECK (true);
CREATE POLICY "password_resets_update"
    ON public.password_resets FOR UPDATE USING (true);
```

### 6.4 Environment variables

Add these to your `.env` file (local) or Streamlit Cloud secrets:

| Variable | Description |
|---|---|
| `EMAIL_ADDRESS` | Gmail address (e.g. `krishisaathi@gmail.com`) |
| `EMAIL_PASSWORD` | **Gmail App Password** — *not* your regular password. Generate one at [Google App Passwords](https://myaccount.google.com/apppasswords) |
| `SUPABASE_SERVICE_KEY` | The **service_role** key from Supabase Dashboard → Settings → API. Used for admin operations (password updates, profile verification) |
| `APP_URL` | Your deployed app URL (defaults to `https://krishisaathi-ai-hackathon.streamlit.app`) |

> **Security note:** The `SUPABASE_SERVICE_KEY` bypasses Row Level Security.
> It is safe because Streamlit runs entirely server-side — the key is never
> exposed to the browser. Never use it in a client-side app.

---

## 7. Verify Setup

After running the SQL, check:

1. **Tables** → `profiles`, `chat_history`, `memories`, `admin_settings`, `email_verifications`, and `password_resets` appear under *Table Editor*
2. **Policies** → Each table shows its RLS policies under *Authentication → Policies*
3. **Trigger** → `on_auth_user_created` appears under *Database → Triggers*

Then start the app:

```bash
streamlit run frontend/app.py
```

You should see the login page. Create an account and start chatting!

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "relation profiles does not exist" | Run the SQL schema above |
| "new row violates RLS policy" | Check that RLS policies were created |
| Can't sign in after sign-up | Disable "Confirm email" in Auth settings |
| "Invalid API key" | Check `SUPABASE_KEY` is the **anon/public** key (not service_role) |
| "Please verify your email" after sign-up | Check your inbox (and spam) for the verification link |
| Verification email not arriving | Verify `EMAIL_ADDRESS` and `EMAIL_PASSWORD` are correct Gmail App Password credentials |
| "SUPABASE_SERVICE_KEY not configured" | Add the service_role key to `.env` / Streamlit secrets |
