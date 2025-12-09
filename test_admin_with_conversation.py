#!/usr/bin/env python3
"""Test admin commands with conversation ID and provider tracking."""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

def test_game_command(command, conversation_id=None, provider="gemini"):
    """Test a game command with optional conversation context."""
    payload = {
        "command": command,
        "experience": "wylding-woods",
        "user_context": {"role": "admin", "user_id": "admin@gaia.dev"}
    }
    
    # Add conversation ID if provided
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    # Add provider preference if supported
    if provider:
        payload["provider"] = provider
    
    print(f"\n{'='*70}")
    print(f"Command: {command}")
    if conversation_id:
        print(f"Conversation ID: {conversation_id}")
    if provider:
        print(f"Provider: {provider}")
    print(f"{'='*70}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/game/command",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        result = response.json()
        
        # Pretty print response
        print(json.dumps(result, indent=2))
        
        # Show narrative if present
        if result.get("narrative"):
            print(f"\n📋 {result['narrative']}")
        
        # Return conversation ID for chaining
        return result.get("conversation_id")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test sequence with conversation continuity
print("╔═══════════════════════════════════════════════════════════════════╗")
print("║    Admin Commands with Conversation ID & Gemini Provider         ║")
print("╚═══════════════════════════════════════════════════════════════════╝")

# Test 1: Stats (start new conversation)
conv_id = test_game_command("@stats", provider="gemini")

# Test 2: List waypoints (continue conversation)
conv_id = test_game_command("@list waypoints", conversation_id=conv_id, provider="gemini")

# Test 3: List locations (continue conversation)
conv_id = test_game_command("@list locations waypoint_28a", conversation_id=conv_id, provider="gemini")

# Test 4: List sublocations (continue conversation)
conv_id = test_game_command("@list sublocations waypoint_28a clearing", conversation_id=conv_id, provider="gemini")

print(f"\n{'='*70}")
print(f"✅ Test sequence complete!")
print(f"Final conversation ID: {conv_id}")
print(f"{'='*70}")
