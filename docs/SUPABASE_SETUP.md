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

## 3. Supabase Auth Settings (Optional but Recommended)

In the Supabase Dashboard → **Authentication → Providers → Email**:

| Setting | Recommended Value | Why |
|---|---|---|
| **Confirm email** | ❌ Disabled (for hackathon) | Users can log in immediately after sign-up |
| **Secure email change** | ✅ Enabled | Standard security |
| **Minimum password length** | 6 | Default |

> For production, enable email confirmation and add rate limiting.

---

## 4. Verify Setup

After running the SQL, check:

1. **Tables** → `profiles` and `chat_history` appear under *Table Editor*
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
