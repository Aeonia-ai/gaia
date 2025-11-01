#!/usr/bin/env python3
"""
Direct test of waypoint lookup methods (no HTTP required).

This script tests the waypoint lookup functionality by directly
instantiating the KB Agent and calling the lookup methods.
"""

import sys
import os
import asyncio
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.services.kb.kb_agent import KBIntelligentAgent
from app.services.llm.chat_service import ChatService
from app.shared.config import settings

def print_section(title):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

async def setup_locations_file():
    """
    Ensure locations.json exists in the KB.

    For this test, we'll check if the file exists in the container.
    If not, you'll need to copy sample-locations.json to the KB directory.
    """
    kb_path = getattr(settings, 'KB_PATH', '/kb')
    locations_file = f"{kb_path}/experiences/wylding-woods/locations.json"

    print(f"📂 Checking for locations file at: {locations_file}")

    if os.path.exists(locations_file):
        print(f"   ✅ File exists")
        return True
    else:
        print(f"   ❌ File not found!")
        print(f"\n   To create it, run:")
        print(f"   docker compose exec kb-service mkdir -p /kb/experiences/wylding-woods")
        print(f"   docker compose cp sample-locations.json kb-service:/kb/experiences/wylding-woods/locations.json")
        return False

async def test_exact_match(agent):
    """Test exact name matching."""
    print_section("TEST 1: Exact Name Match (_find_waypoint_by_name)")

    test_cases = [
        ("Dream Weaver's Clearing", True),
        ("woander store area", True),  # case-insensitive test
        ("Jason's Office", True),
        ("NonExistent Location", False)  # should fail
    ]

    results = []
    for name, should_find in test_cases:
        print(f"🔍 Searching: '{name}'")

        try:
            waypoint = await agent._find_waypoint_by_name(
                experience="wylding-woods",
                friendly_name=name
            )

            if waypoint:
                print(f"   ✅ Found: {waypoint['waypoint_id']}")
                print(f"      Name: \"{waypoint.get('name')}\"")
                print(f"      GPS: {waypoint.get('gps', {}).get('latitude')}, "
                      f"{waypoint.get('gps', {}).get('longitude')}")
                results.append((name, True, waypoint['waypoint_id']))
            else:
                print(f"   ❌ Not found")
                results.append((name, False, None))

        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            results.append((name, False, str(e)))

        print()

    return results

async def test_fuzzy_match(agent):
    """Test fuzzy matching."""
    print_section("TEST 2: Fuzzy Matching (_find_waypoint_fuzzy)")

    test_cases = [
        "store",      # partial match
        "clearing",   # common word
        "fairy",      # description match
        "woander",    # specific match
        "office",     # Jason's Office
        "magical"     # description keyword
    ]

    results = []
    for term in test_cases:
        print(f"🔍 Fuzzy search: '{term}'")

        try:
            matches = await agent._find_waypoint_fuzzy(
                experience="wylding-woods",
                search_term=term
            )

            if matches:
                print(f"   ✅ Found {len(matches)} match(es):")
                for i, match in enumerate(matches[:3], 1):  # Show top 3
                    print(f"      {i}. {match['waypoint_id']}: \"{match.get('name')}\"")
                    print(f"         Score: {match.get('match_score')}, "
                          f"Reason: {match.get('match_reason')}")
                results.append((term, len(matches), matches[0]['waypoint_id']))
            else:
                print(f"   ❌ No matches")
                results.append((term, 0, None))

        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            results.append((term, 0, str(e)))

        print()

    return results

async def test_semantic_resolution(agent):
    """Test LLM-based semantic resolution."""
    print_section("TEST 3: Semantic Resolution (_resolve_location_semantically)")

    # Check if LLM service is available
    if not agent.llm_service:
        print("⚠️  LLM service not available - skipping semantic tests")
        return []

    test_cases = [
        "the place where the Dream Weaver lives",
        "I'm at the store where Woander sells magical items",
        "the mystical clearing with fairies",
        "Jason's home office where he codes",
        "a random nonexistent place that doesn't match anything"
    ]

    results = []
    for phrase in test_cases:
        print(f"🔍 Resolving: '{phrase}'")

        try:
            result = await agent._resolve_location_semantically(
                experience="wylding-woods",
                user_location_phrase=phrase
            )

            waypoint_id = result.get("waypoint_id")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")

            if waypoint_id:
                waypoint_data = result.get("waypoint_data", {})
                print(f"   ✅ Resolved: {waypoint_id}")
                print(f"      Name: \"{waypoint_data.get('name')}\"")
                print(f"      Confidence: {confidence:.2f}")
                print(f"      Reasoning: {reasoning}")
                results.append((phrase, waypoint_id, confidence))
            else:
                print(f"   ❌ Could not resolve")
                print(f"      Reasoning: {reasoning}")
                results.append((phrase, None, 0.0))

        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            results.append((phrase, None, str(e)))

        print()

    return results

async def main():
    """Run all tests."""
    print("╔═════════════════════════════════════════════════════════════════════╗")
    print("║       WAYPOINT LOOKUP DIRECT TEST - Wylding Woods                  ║")
    print("║  Tests: Exact Match, Fuzzy Search, Semantic Resolution            ║")
    print("╚═════════════════════════════════════════════════════════════════════╝")

    # Check if locations file exists
    file_exists = await setup_locations_file()
    if not file_exists:
        print("\n⚠️  Cannot run tests - locations.json not found")
        sys.exit(1)

    # Initialize KB Agent
    print("\n🤖 Initializing KB Agent...")

    try:
        # Create LLM service for semantic resolution
        llm_service = ChatService()

        # Create KB Agent
        auth_principal = {
            "user_id": "test@example.com",
            "role": "admin",
            "auth_type": "api_key"
        }

        agent = KBIntelligentAgent(
            llm_service=llm_service,
            auth_principal=auth_principal
        )

        print("   ✅ Agent initialized\n")

        # Run tests
        exact_results = await test_exact_match(agent)
        fuzzy_results = await test_fuzzy_match(agent)
        semantic_results = await test_semantic_resolution(agent)

        # Summary
        print_section("TEST SUMMARY")

        print(f"✅ Exact Match Tests: {sum(1 for _, found, _ in exact_results if found)}/{len(exact_results)} passed")
        print(f"✅ Fuzzy Match Tests: {sum(1 for _, count, _ in fuzzy_results if count > 0)}/{len(fuzzy_results)} found matches")
        print(f"✅ Semantic Tests: {sum(1 for _, wid, _ in semantic_results if wid)}/{len(semantic_results)} resolved")

        print("\n" + "="*70)
        print("USAGE IN PRODUCTION")
        print("="*70)
        print("""
These methods can be used in admin commands and player interactions:

# 1. Admin command with friendly name:
@inspect waypoint "Jason's Office"
  → Calls: agent._find_waypoint_by_name("wylding-woods", "Jason's Office")
  → Returns waypoint_42 data

# 2. Player chat with partial name:
"I'm at the store"
  → Calls: agent._find_waypoint_fuzzy("wylding-woods", "store")
  → Returns: [waypoint_28a_store, ...]

# 3. Natural language resolution:
"Take me to where Woander sells magical items"
  → Calls: agent._resolve_location_semantically(...)
  → Returns: waypoint_28a_store with 0.95 confidence
        """)

    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
