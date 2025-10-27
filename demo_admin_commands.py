#!/usr/bin/env python3
"""
Live demonstration of admin commands with visual output.
Shows the complete hierarchy: waypoints → locations → sublocations → items
"""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def cmd(command, desc=""):
    """Execute admin command and show narrative."""
    print(f"\n{'▶'*35}")
    if desc:
        print(f"📌 {desc}")
    print(f"💻 Command: {command}")
    print(f"{'▶'*35}")
    
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {"role": "admin", "user_id": "demo@gaia.dev"}
        },
        timeout=30
    )
    
    result = response.json()
    if result.get("narrative"):
        print(f"\n{result['narrative']}\n")
    return result

print("╔═════════════════════════════════════════════════════════════════════╗")
print("║                   ADMIN COMMANDS LIVE DEMO                          ║")
print("║              Exploring the Wylding Woods World                      ║")
print("╚═════════════════════════════════════════════════════════════════════╝")

# 1. World Overview
cmd("@stats", "Step 1: Get world statistics")

# 2. Top Level - Waypoints
cmd("@list waypoints", "Step 2: List all waypoints")

# 3. Mid Level - Locations within waypoint
cmd("@list locations waypoint_28a", "Step 3: Explore waypoint_28a locations")

# 4. Bottom Level - Sublocations with GRAPH STRUCTURE
cmd("@list sublocations waypoint_28a clearing", 
    "Step 4: Show navigation graph for 'clearing' location")

# 5. Content - Items in world
cmd("@list items", "Step 5: List all items in world")

# 6. Specific Query - Items at location
cmd("@list items at waypoint_28a clearing shelf_1", 
    "Step 6: What's on shelf_1?")

# 7. Templates
cmd("@list templates", "Step 7: Available content templates")

print("\n" + "═"*70)
print("✨ DEMO COMPLETE!")
print("═"*70)
print("\n🎯 Key Takeaways:")
print("  • Admin commands provide instant, structured world access")
print("  • Graph-based navigation shown in exits arrays")
print("  • Hierarchical structure: waypoint → location → sublocation")
print("  • Items tracked at sublocation level")
print("  • No LLM needed - direct file access for speed")
print("\n📚 See ADMIN_COMMANDS_QUICKREF.md for full syntax")
print("═"*70 + "\n")
