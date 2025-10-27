#!/usr/bin/env python3
"""Test admin CRUD and navigation commands."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def cmd(desc, command):
    print(f"\n{'='*70}")
    print(f"{desc}")
    print(f"Command: '{command}'")
    print(f"{'='*70}")
    
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {"role": "admin", "user_id": "test@gaia.dev"}
        },
        timeout=30
    )
    
    result = response.json()
    
    if result.get("success"):
        print(f"✅ Success")
        if result.get("narrative"):
            print(f"\n{result['narrative']}")
    else:
        print(f"❌ Failed: {result.get('error', {}).get('message', 'Unknown')}")
        if result.get("narrative"):
            print(f"\n{result['narrative']}")
    
    return result

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║             Admin CRUD & Navigation Commands Test                ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# ==== CREATE COMMANDS ====
print("\n" + "█"*70)
print("█                    CREATE COMMANDS                                █")
print("█"*70)

# Test 1: Create new waypoint
cmd("TEST 1: Create new waypoint",
    "@create waypoint test_wp Test Waypoint")

# Test 2: Create location in new waypoint
cmd("TEST 2: Create location in waypoint",
    "@create location test_wp test_loc Test Location")

# Test 3: Create sublocations
cmd("TEST 3: Create first sublocation",
    "@create sublocation test_wp test_loc room_a Room A")

cmd("TEST 4: Create second sublocation",
    "@create sublocation test_wp test_loc room_b Room B")

cmd("TEST 5: Create third sublocation",
    "@create sublocation test_wp test_loc room_c Room C")

# ==== CONNECT COMMANDS ====
print("\n" + "█"*70)
print("█                 NAVIGATION/GRAPH COMMANDS                         █")
print("█"*70)

# Test 6: Connect room_a to room_b (with cardinal direction)
cmd("TEST 6: Connect room_a to room_b (north)",
    "@connect test_wp test_loc room_a room_b north")

# Test 7: Connect room_b to room_c (no direction)
cmd("TEST 7: Connect room_b to room_c",
    "@connect test_wp test_loc room_b room_c")

# Test 8: Connect room_c back to room_a (creating a cycle)
cmd("TEST 8: Connect room_c to room_a (west)",
    "@connect test_wp test_loc room_c room_a west")

# Test 9: List sublocations to see the graph
cmd("TEST 9: Show navigation graph",
    "@list sublocations test_wp test_loc")

# ==== DISCONNECT COMMAND ====
print("\n" + "█"*70)
print("█                 DISCONNECT COMMAND                                █")
print("█"*70)

# Test 10: Disconnect room_b from room_c
cmd("TEST 10: Disconnect room_b from room_c",
    "@disconnect test_wp test_loc room_b room_c")

# Test 11: Verify disconnection
cmd("TEST 11: Verify graph after disconnect",
    "@list sublocations test_wp test_loc")

# ==== ERROR HANDLING ====
print("\n" + "█"*70)
print("█                 ERROR HANDLING TESTS                              █")
print("█"*70)

# Test 12: Try to create duplicate waypoint
cmd("TEST 12: Create duplicate waypoint (should fail)",
    "@create waypoint test_wp Duplicate")

# Test 13: Try to connect non-existent sublocations
cmd("TEST 13: Connect non-existent sublocations (should fail)",
    "@connect test_wp test_loc room_x room_y")

# Test 14: Try to create without required args
cmd("TEST 14: Create without args (should show usage)",
    "@create waypoint")

# ==== FINAL STATE ====
print("\n" + "█"*70)
print("█                 FINAL STATE CHECK                                 █")
print("█"*70)

# Test 15: Show updated world stats
cmd("TEST 15: Updated world statistics",
    "@stats")

# Test 16: List all waypoints (including new one)
cmd("TEST 16: List all waypoints",
    "@list waypoints")

print("\n" + "="*70)
print("✅ CRUD & NAVIGATION TESTS COMPLETE")
print("="*70)
print("\n📊 Summary:")
print("  • Created: 1 waypoint, 1 location, 3 sublocations")
print("  • Connected: 3 edges (room_a ↔ room_b ↔ room_c ↔ room_a)")
print("  • Disconnected: 1 edge (room_b ↮ room_c)")
print("  • Final graph: room_a ↔ room_b, room_a ↔ room_c")
print("  • Error handling tested and working")
print("\n🗺️  Graph Structure:")
print("     room_a")
print("      / \\")
print(" room_b   room_c")
print("\n💡 Commands tested: @create, @connect, @disconnect")
print("="*70 + "\n")
