#!/usr/bin/env python3
"""
Test script for waypoint lookup methods.

Tests the three waypoint resolution methods:
1. Exact name match
2. Fuzzy matching
3. LLM-based semantic resolution
"""

import requests
import json
import sys
import asyncio

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_exact_match():
    """Test exact name matching."""
    print_section("TEST 1: Exact Name Match")

    test_cases = [
        "Dream Weaver's Clearing",
        "woander store area",  # lowercase test
        "The Fairy Grove",
        "NonExistent Location"  # should fail
    ]

    for name in test_cases:
        print(f"🔍 Looking for: '{name}'")

        # Call a test endpoint (we'll create this)
        payload = {
            "method": "find_waypoint_by_name",
            "experience": "wylding-woods",
            "friendly_name": name
        }

        try:
            response = requests.post(
                f"{BASE_URL}/test/waypoint-lookup",
                headers=HEADERS,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("waypoint_id"):
                    print(f"   ✅ Found: {result['waypoint_id']} - \"{result.get('name')}\"")
                else:
                    print(f"   ❌ Not found")
            else:
                print(f"   ⚠️  HTTP {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

def test_fuzzy_match():
    """Test fuzzy matching."""
    print_section("TEST 2: Fuzzy Matching")

    test_cases = [
        "store",      # partial match
        "clearing",   # common word
        "fairy",      # description match
        "woander"     # specific match
    ]

    for term in test_cases:
        print(f"🔍 Searching for: '{term}'")

        payload = {
            "method": "find_waypoint_fuzzy",
            "experience": "wylding-woods",
            "search_term": term
        }

        try:
            response = requests.post(
                f"{BASE_URL}/test/waypoint-lookup",
                headers=HEADERS,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                matches = result.get("matches", [])

                if matches:
                    print(f"   ✅ Found {len(matches)} match(es):")
                    for match in matches[:3]:  # Show top 3
                        print(f"      • {match['waypoint_id']}: \"{match.get('name')}\" "
                              f"(score: {match.get('match_score')}, {match.get('match_reason')})")
                else:
                    print(f"   ❌ No matches")
            else:
                print(f"   ⚠️  HTTP {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

def test_semantic_resolution():
    """Test LLM-based semantic resolution."""
    print_section("TEST 3: Semantic Resolution (LLM)")

    test_cases = [
        "the place where the Dream Weaver lives",
        "I'm at the store where Woander sells magical items",
        "the mystical grove with fairies",
        "a random unrelated place that doesn't exist"
    ]

    for phrase in test_cases:
        print(f"🔍 Resolving: '{phrase}'")

        payload = {
            "method": "resolve_location_semantically",
            "experience": "wylding-woods",
            "user_location_phrase": phrase
        }

        try:
            response = requests.post(
                f"{BASE_URL}/test/waypoint-lookup",
                headers=HEADERS,
                json=payload,
                timeout=30  # LLM call takes longer
            )

            if response.status_code == 200:
                result = response.json()
                waypoint_id = result.get("waypoint_id")
                confidence = result.get("confidence", 0.0)
                reasoning = result.get("reasoning", "")

                if waypoint_id:
                    waypoint_data = result.get("waypoint_data", {})
                    print(f"   ✅ Resolved: {waypoint_id} - \"{waypoint_data.get('name')}\"")
                    print(f"      Confidence: {confidence:.2f}")
                    print(f"      Reasoning: {reasoning}")
                else:
                    print(f"   ❌ Could not resolve")
                    print(f"      Reasoning: {reasoning}")
            else:
                print(f"   ⚠️  HTTP {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

def main():
    """Run all tests."""
    print("╔═════════════════════════════════════════════════════════════════════╗")
    print("║        WAYPOINT LOOKUP TEST SUITE - Wylding Woods                  ║")
    print("║   Tests: Exact Match, Fuzzy Search, Semantic Resolution           ║")
    print("╚═════════════════════════════════════════════════════════════════════╝")

    print("\n⚠️  Note: This requires a test endpoint at /test/waypoint-lookup")
    print("    If the endpoint doesn't exist, tests will fail.")
    print("    You can also test these methods directly in Python code.")

    # test_exact_match()
    # test_fuzzy_match()
    # test_semantic_resolution()

    print("\n" + "="*70)
    print("ALTERNATIVE: Direct Python Testing")
    print("="*70)
    print("""
To test these methods directly without HTTP endpoint:

```python
import asyncio
from app.services.kb.kb_agent import KBIntelligentAgent
from app.shared.config import settings

async def test_lookup():
    agent = KBIntelligentAgent(llm_service=None, auth_principal={})

    # Test 1: Exact match
    waypoint = await agent._find_waypoint_by_name(
        "wylding-woods",
        "Dream Weaver's Clearing"
    )
    print(f"Found: {waypoint}")

    # Test 2: Fuzzy match
    matches = await agent._find_waypoint_fuzzy(
        "wylding-woods",
        "store"
    )
    print(f"Matches: {len(matches)}")
    for m in matches:
        print(f"  - {m['waypoint_id']}: {m.get('name')}")

    # Test 3: Semantic (requires LLM)
    result = await agent._resolve_location_semantically(
        "wylding-woods",
        "the place where Woander sells items"
    )
    print(f"Resolved: {result}")

asyncio.run(test_lookup())
```

To make this work, you need a locations.json file at:
/kb/experiences/wylding-woods/locations.json
    """)

if __name__ == "__main__":
    main()
