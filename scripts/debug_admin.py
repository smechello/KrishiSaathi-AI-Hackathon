#!/usr/bin/env python3
import sys, os
sys.path.insert(0, "/home/ubuntu/KrishiSaathi-AI-Hackathon")
os.chdir("/home/ubuntu/KrishiSaathi-AI-Hackathon")
from dotenv import load_dotenv
load_dotenv(override=True)

print("ADMIN_MAILS env:", repr(os.getenv("ADMIN_MAILS")))
print("ADMIN_EMAILS env:", repr(os.getenv("ADMIN_EMAILS")))

from backend.config import Config
print("Config.ADMIN_EMAILS:", Config.ADMIN_EMAILS)
print("pranavi check:", "pranavi@gmail.com" in Config.ADMIN_EMAILS)
print("shashi check:", "nalamarishashidharreddy@gmail.com" in Config.ADMIN_EMAILS)
