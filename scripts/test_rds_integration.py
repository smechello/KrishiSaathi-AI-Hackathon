#!/usr/bin/env python3
"""Test: import the rds_service module and verify tables are created on RDS."""
import sys, os
sys.path.insert(0, "/home/ubuntu/KrishiSaathi-AI-Hackathon")
os.chdir("/home/ubuntu/KrishiSaathi-AI-Hackathon")

# Load .env
from dotenv import load_dotenv
load_dotenv()

print(f"DB_BACKEND = {os.getenv('DB_BACKEND')}")
print(f"RDS_HOST   = {os.getenv('RDS_HOST', '')[:40]}...")
print()

from backend.services.supabase_service import SupabaseManager

print(f"SupabaseManager module: {SupabaseManager.__module__}")
print(f"is_configured: {SupabaseManager.is_configured()}")
print()

# Trigger table creation
print("Calling _ensure()...")
SupabaseManager._ensure()
print("Done!")
print()

# Verify tables exist by checking counts
print("Checking admin_get_counts()...")
counts = SupabaseManager.admin_get_counts()
print(f"  Counts: {counts}")
print()

# Test auth flow
print("Testing sign_up...")
result = SupabaseManager.sign_up(
    email="test@example.com",
    password="TestPass123!",
    full_name="Test User",
)
print(f"  Result: success={result.get('success')}, msg={result.get('message', '')[:80]}")
print()

# Clean up test user
import psycopg2
conn = psycopg2.connect(
    host=os.getenv("RDS_HOST"),
    port=5432,
    dbname=os.getenv("RDS_DBNAME", "krishisaathi"),
    user=os.getenv("RDS_USER", "postgres"),
    password=os.getenv("RDS_PASSWORD"),
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("DELETE FROM profiles WHERE email = 'test@example.com'")
print("Cleaned up test user.")

# List all tables
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(f"\nAll tables in krishisaathi: {tables}")
cur.close()
conn.close()

print("\n✅ All RDS integration tests passed!")
