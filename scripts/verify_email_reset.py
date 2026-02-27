#!/usr/bin/env python3
"""Verify email + password reset config."""
import sys, os
sys.path.insert(0, "/home/ubuntu/KrishiSaathi-AI-Hackathon")
os.chdir("/home/ubuntu/KrishiSaathi-AI-Hackathon")
from dotenv import load_dotenv
load_dotenv()

from backend.config import Config
from backend.services.email_service import EmailService

print(f"EMAIL_ADDRESS: {Config.EMAIL_ADDRESS}")
print(f"EMAIL_PASSWORD: {'***' + Config.EMAIL_PASSWORD[-4:] if Config.EMAIL_PASSWORD else None}")
print(f"APP_URL: {Config.APP_URL}")
print(f"EmailService.is_configured(): {EmailService.is_configured()}")

# Test SMTP connection
if EmailService.is_configured():
    import smtplib
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
        server.quit()
        print("SMTP login: SUCCESS")
    except Exception as e:
        print(f"SMTP login: FAILED - {e}")

# Test reset token creation
from backend.services.supabase_service import SupabaseManager
result = SupabaseManager.create_password_reset("pranavi@gmail.com")
print(f"\ncreate_password_reset: token={result.get('token', 'NONE')[:12]}..., name={result.get('full_name')}")

# Verify check_reset_token
if result.get("token"):
    check = SupabaseManager.check_reset_token(result["token"])
    print(f"check_reset_token: {check}")
    # Clean up - mark as used
    from backend.services.rds_service import _exec
    _exec("DELETE FROM password_resets WHERE token = %s", (result["token"],))
    print("Test token cleaned up.")
