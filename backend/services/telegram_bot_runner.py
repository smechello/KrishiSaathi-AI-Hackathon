#!/usr/bin/env python3
"""KrishiSaathi Telegram Bot — standalone runner.

Usage:
    python -m backend.services.telegram_bot_runner
    # or
    python backend/services/telegram_bot_runner.py
"""

import os
import sys

# Ensure project root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services.telegram_bot import run_bot

if __name__ == "__main__":
    run_bot()
