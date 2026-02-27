#!/usr/bin/env python3
"""Create two admin user accounts in RDS."""
import sys, os
sys.path.insert(0, "/home/ubuntu/KrishiSaathi-AI-Hackathon")
os.chdir("/home/ubuntu/KrishiSaathi-AI-Hackathon")
from dotenv import load_dotenv
load_dotenv()

from backend.services.supabase_service import SupabaseManager

users = [
    ("nalamarishashidharreddy@gmail.com", "12345678", "Shashidhar Reddy"),
    ("pranavi@gmail.com", "123", "Pranavi"),
]

for email, pwd, name in users:
    print(f"\nCreating user: {email}")
    result = SupabaseManager.sign_up(email=email, password=pwd, full_name=name)
    print(f"  success={result.get('success')}, message={result.get('message', '')[:100]}")

print("\nDone! Verifying admin_list_users:")
all_users = SupabaseManager.admin_list_users()
for u in all_users:
    print(f"  {u.get('email')} - {u.get('full_name')} (id={u.get('id','')[:12]}...)")
