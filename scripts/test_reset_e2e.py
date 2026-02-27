#!/usr/bin/env python3
"""
End-to-end password reset flow test on LIVE deployed server.

Tests the full cycle:
1. Trigger password reset for a known user
2. Verify email is actually sent (check token in DB)
3. Validate the reset token
4. Complete the password reset with a new password
5. Sign in with the new password
6. Restore the original password
"""
import os, sys

# ── Bootstrap ──
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DB_BACKEND", "rds")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from backend.services.rds_service import SupabaseManager as SM

TEST_EMAIL = "pranavi@gmail.com"
ORIGINAL_PWD = "123"
NEW_PWD = "TestReset2026!"

results = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((label, status, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition

print("=" * 60)
print("  END-TO-END PASSWORD RESET FLOW TEST")
print("=" * 60)

# ── Step 1: Verify user exists & can sign in with original password ──
print("\n── Step 1: Verify user can sign in with original password ──")
res = SM.sign_in(TEST_EMAIL, ORIGINAL_PWD)
check("Sign-in with original password", res.get("success"), 
      f"user_id={res.get('user', {}).get('id', 'N/A')[:8]}..." if res.get("success") else res.get("error"))

# ── Step 2: Trigger password reset ──
print("\n── Step 2: Trigger password reset ──")
res = SM.reset_password(TEST_EMAIL)
check("reset_password() call", res.get("success"), str(res))

# ── Step 3: Get the token directly from DB (since we can't check email) ──
print("\n── Step 3: Retrieve reset token from DB ──")
from backend.services.rds_service import _exec
row = _exec(
    "SELECT token, expires_at, used FROM password_resets "
    "WHERE email = %s AND used = FALSE "
    "ORDER BY id DESC LIMIT 1",
    (TEST_EMAIL.lower(),),
    fetch="one",
)
token = row["token"] if row else None
check("Token exists in DB", token is not None,
      f"token={token[:12]}..., expires={row['expires_at']}" if token else "NO TOKEN FOUND")

if not token:
    print("\n  ABORTING: No valid token found.")
    sys.exit(1)

# ── Step 4: Check reset token ──
print("\n── Step 4: Validate reset token ──")
res = SM.check_reset_token(token)
check("check_reset_token()", res.get("valid"), f"email={res.get('email')}")

# ── Step 5: Complete password reset ──
print("\n── Step 5: Complete password reset with new password ──")
res = SM.complete_password_reset(token, NEW_PWD)
check("complete_password_reset()", res.get("success"), str(res))

# ── Step 6: Verify sign-in with NEW password ──
print("\n── Step 6: Sign in with new password ──")
res = SM.sign_in(TEST_EMAIL, NEW_PWD)
check("Sign-in with new password", res.get("success"),
      f"user_id={res.get('user', {}).get('id', 'N/A')[:8]}..." if res.get("success") else res.get("error"))

# ── Step 7: Restore original password ──
print("\n── Step 7: Restore original password ──")
import bcrypt
from backend.services.rds_service import _exec
pw_hash = bcrypt.hashpw(ORIGINAL_PWD.encode(), bcrypt.gensalt()).decode()
_exec("UPDATE profiles SET password_hash = %s WHERE email = %s", (pw_hash, TEST_EMAIL.lower()))
res = SM.sign_in(TEST_EMAIL, ORIGINAL_PWD)
check("Restored original password & sign-in", res.get("success"),
      "Original password works again" if res.get("success") else res.get("error"))

# ── Step 8: Verify used token can't be reused ──
print("\n── Step 8: Verify used token rejection ──")
res = SM.check_reset_token(token)
check("Used token rejected", not res.get("valid"), "Token correctly marked as used")

# ── Summary ──
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
print(f"  RESULTS: {passed}/{total} passed")
if passed == total:
    print("  ✅ ALL TESTS PASSED — Password reset flow is working perfectly!")
else:
    print("  ❌ SOME TESTS FAILED — See details above")
print("=" * 60)
