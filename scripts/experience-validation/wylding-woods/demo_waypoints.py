#!/usr/bin/env python3
"""
Quick demo of waypoint lookup functionality.

Shows how the three lookup methods work with real examples.
"""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"

def demo():
    """Run quick demonstration."""
    print("╔═════════════════════════════════════════════════════════════════════╗")
    print("║              WAYPOINT LOOKUP DEMONSTRATION                          ║")
    print("╚═════════════════════════════════════════════════════════════════════╝\n")

    print("✨ Three new methods added to KBIntelligentAgent:\n")

    print("1. _find_waypoint_by_name(experience, friendly_name)")
    print("   Purpose: Exact name match (case-insensitive)")
    print("   Example:")
    print("     Input:  'Jason\\'s Office'")
    print("     Output: waypoint_42 with full location data\n")

    print("2. _find_waypoint_fuzzy(experience, search_term)")
    print("   Purpose: Find waypoints by partial name or description keywords")
    print("   Example:")
    print("     Input:  'store'")
    print("     Output: [waypoint_28a_store] with match score 50\n")

    print("3. _resolve_location_semantically(experience, user_location_phrase)")
    print("   Purpose: Use LLM to understand natural language location references")
    print("   Example:")
    print("     Input:  'the place where Woander sells magical items'")
    print("     Output: waypoint_28a_store with 0.95 confidence\n")

    print("="*70)
    print("SAMPLE LOCATIONS IN TEST FILE")
    print("="*70)

    locations = [
        ("waypoint_28a", "Dream Weaver's Clearing"),
        ("waypoint_28a_store", "Woander Store Area"),
        ("waypoint_42", "Jason's Office")
    ]

    for wid, name in locations:
        print(f"  • {wid:25s} → \"{name}\"")

    print("\n" + "="*70)
    print("TESTING WITH GAME COMMANDS")
    print("="*70)

    print("\nThese methods enable friendly names in both admin and player commands:\n")

    print("Admin Example:")
    print("  @inspect waypoint \"Jason's Office\"")
    print("  → Resolves to waypoint_42")
    print("  → Shows full waypoint details\n")

    print("Player Example:")
    print("  Player: \"I'm at the store\"")
    print("  → Fuzzy match finds waypoint_28a_store")
    print("  → Game command executes at correct location\n")

    print("Chat Example:")
    print("  Player: \"Take me to where the Dream Weaver lives\"")
    print("  → LLM resolves to waypoint_28a")
    print("  → Navigation guidance provided\n")

    print("="*70)
    print("FILES CREATED")
    print("="*70)

    files = [
        ("app/services/kb/kb_agent.py", "Added 3 lookup methods (lines 830-1056)"),
        ("sample-locations.json", "Example locations for wylding-woods"),
        ("scripts/testing/wylding-woods/test_waypoint_lookup_direct.py", "Direct Python tests"),
        ("scripts/testing/wylding-woods/test_waypoint_lookup.py", "HTTP endpoint tests"),
        ("scripts/testing/wylding-woods/demo_waypoint_lookup.py", "This demo script")
    ]

    for filename, description in files:
        print(f"  ✅ {filename}")
        print(f"     {description}\n")

    print("="*70)
    print("NEXT STEPS")
    print("="*70)
    print("""
1. ✅ Methods are implemented and ready to use
2. ✅ Sample locations.json copied to KB service
3. ⏳ Integrate into admin commands (@inspect waypoint "name")
4. ⏳ Integrate into player command parser
5. ⏳ Add to execute_game_command tool for chat CLI
6. ⏳ Document naming conventions for waypoints

To test manually from Python:
    python3 scripts/testing/wylding-woods/test_waypoint_lookup_direct.py

To test specific lookups:
    # In Python
    from app.services.kb.kb_agent import KBIntelligentAgent
    agent = KBIntelligentAgent(...)
    result = await agent._find_waypoint_by_name("wylding-woods", "Jason's Office")
    """)

if __name__ == "__main__":
    demo()
