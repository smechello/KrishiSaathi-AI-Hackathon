#!/usr/bin/env python3
"""Verification script for API keys and configuration."""

import os
import sys

import requests
from dotenv import load_dotenv
import google.generativeai as genai

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_gemini_api():
    """Test Gemini API key."""
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Say hello in Hindi")
        print("✅ Gemini API works:", response.text[:50].strip())
        return True
    except Exception as e:
        print("❌ Gemini API failed:", str(e))
        return False

def test_weather_api():
    """Test OpenWeatherMap API key."""
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q=Delhi&appid={os.getenv('OPENWEATHER_API_KEY')}",
            timeout=10,
        )
        if r.status_code == 200:
            print("✅ Weather API works: Status 200")
            return True
        else:
            print(f"❌ Weather API failed: Status {r.status_code}")
            return False
    except Exception as e:
        print("❌ Weather API failed:", str(e))
        return False

def test_config_import():
    """Test config module import."""
    try:
        from backend.config import Config
        if Config.GEMINI_API_KEY and Config.OPENWEATHER_API_KEY:
            print("✅ Config module works: API keys loaded")
            return True
        else:
            print("❌ Config module failed: API keys not loaded")
            return False
    except Exception as e:
        print("❌ Config module failed:", str(e))
        return False

def main():
    """Run all verification tests."""
    load_dotenv()

    print("🔍 Verifying KrishiSaathi API Keys and Configuration\n")

    results = []
    results.append(("Config Import", test_config_import()))
    results.append(("Gemini API", test_gemini_api()))
    results.append(("Weather API", test_weather_api()))

    print("\n📊 Summary:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check your configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
