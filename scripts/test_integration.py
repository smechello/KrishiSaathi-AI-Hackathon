"""Integration test — runs 5 queries through the full KrishiSaathi pipeline.

Usage:
    cd KrishiSaathi-AI-Hackathon
    python -m scripts.test_integration
"""

from __future__ import annotations

import logging
import sys
import time

# ── bootstrap ──────────────────────────────────────────────────────────
sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    from backend.main import KrishiSaathi

    app = KrishiSaathi()

    test_queries = [
        # (label, query)
        ("Crop Disease", "My tomato leaves have brown spots and are wilting. What disease is this?"),
        ("Government Scheme", "What is Rythu Bandhu scheme and how do I apply?"),
        ("Market Price", "What is the current rice price in Warangal mandi?"),
        ("Soil Health", "I have red soil in my farm near Mahbubnagar. Which crops are best?"),
        ("Weather Advisory", "What is the weather in Hyderabad and should I spray pesticides today?"),
    ]

    print("\n" + "=" * 70)
    print("  KrishiSaathi — Integration Test  (5 queries)")
    print("=" * 70)

    passed = 0
    for i, (label, query) in enumerate(test_queries):
        # Respect Gemini free-tier rate limit (5 RPM for LLM calls)
        if i > 0 and i % 2 == 0:
            wait = 5
            print(f"\n  ⏳ Pausing {wait}s for API rate-limit cooldown …")
            time.sleep(wait)

        print(f"\n{'─' * 60}")
        print(f"  [{label}]  {query}")
        print("─" * 60)

        t0 = time.time()
        try:
            result = app.ask(query)
            elapsed = time.time() - t0

            response = result.get("response", "")
            sources = result.get("sources", [])
            intent = result.get("intent", {}).get("primary_intent", "?")
            agents = result.get("intent", {}).get("routed_agents", [])

            print(f"  Intent  : {intent}  →  agents: {agents}")
            print(f"  Sources : {sources[:5]}")  # max 5
            print(f"  Time    : {elapsed:.1f}s")
            print(f"  Response: {response[:300]}{'…' if len(response) > 300 else ''}")

            if response and len(response) > 20:
                print("  ✅ PASS")
                passed += 1
            else:
                print("  ❌ FAIL — response too short")
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"  ❌ ERROR ({elapsed:.1f}s): {exc}")

    print(f"\n{'=' * 70}")
    print(f"  Results: {passed}/{len(test_queries)} passed")
    print("=" * 70)


if __name__ == "__main__":
    main()
