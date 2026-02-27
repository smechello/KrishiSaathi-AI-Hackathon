#!/usr/bin/env python3
"""Check existing users and fix first admin account."""
import sys, os
sys.path.insert(0, "/home/ubuntu/KrishiSaathi-AI-Hackathon")
os.chdir("/home/ubuntu/KrishiSaathi-AI-Hackathon")
from dotenv import load_dotenv
load_dotenv()

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

# Show all users
cur.execute("SELECT id, email, full_name, email_verified, created_at FROM profiles ORDER BY created_at")
rows = cur.fetchall()
print("Current users:")
for r in rows:
    print(f"  id={r[0][:12]}... email={r[1]} name={r[2]} verified={r[3]}")

# Check if nalamarishashidharreddy@gmail.com exists
cur.execute("SELECT id FROM profiles WHERE email = %s", ("nalamarishashidharreddy@gmail.com",))
existing = cur.fetchone()
if existing:
    print(f"\nnalamarishashidharreddy@gmail.com already exists (id={existing[0][:12]}...)")
    print("Updating password to '12345678' and marking verified...")
    import bcrypt
    pw_hash = bcrypt.hashpw("12345678".encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE profiles SET password_hash = %s, email_verified = true, full_name = 'Shashidhar Reddy' WHERE email = %s",
                (pw_hash, "nalamarishashidharreddy@gmail.com"))
    print("Done!")
else:
    print("\nCreating nalamarishashidharreddy@gmail.com...")
    import bcrypt, uuid
    uid = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw("12345678".encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO profiles (id, full_name, email, password_hash, email_verified) VALUES (%s, %s, %s, %s, true)",
                (uid, "Shashidhar Reddy", "nalamarishashidharreddy@gmail.com", pw_hash))
    print(f"Created with id={uid[:12]}...")

# Ensure pranavi is verified too
cur.execute("UPDATE profiles SET email_verified = true WHERE email = 'pranavi@gmail.com'")
print("Ensured pranavi@gmail.com is verified.")

# Final state
print("\nFinal users:")
cur.execute("SELECT id, email, full_name, email_verified FROM profiles ORDER BY created_at")
for r in cur.fetchall():
    print(f"  {r[1]} - {r[2]} (verified={r[3]})")

cur.close()
conn.close()
