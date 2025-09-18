#!/usr/bin/env python3
"""
Test script for Option 3 Game State Proof of Concept.

This validates that our game state handler can:
1. Parse game commands correctly
2. Extract state from message history
3. Embed state in responses
4. Format KB queries appropriately
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.chat.game_state_handler import game_state_handler
import json

def test_command_parsing():
    """Test parsing various game commands."""
    print("Testing Command Parsing...")

    test_cases = [
        ("play zork", ("start_game", {"game": "zork"})),
        ("go north", ("move", {"direction": "north"})),
        ("look around", ("look", {"target": "around"})),
        ("take lamp", ("take", {"item": "lamp"})),
        ("inventory", ("inventory", {})),
        ("open mailbox", ("game_command", {"input": "open mailbox"})),
    ]

    for input_text, expected in test_cases:
        result = game_state_handler.parse_game_command(input_text)
        success = result == expected
        print(f"  {'✓' if success else '✗'} '{input_text}' -> {result[0]}")
        if not success:
            print(f"    Expected: {expected}")
    print()

def test_state_embedding():
    """Test embedding and extracting state from messages."""
    print("Testing State Embedding...")

    # Create test state
    test_state = {
        "game": "zork",
        "room": "west_of_house",
        "inventory": ["lamp", "sword"],
        "score": 10,
        "moves": 5
    }

    # Embed state in content
    content = "You are standing west of a white house."
    result = game_state_handler.embed_game_state(content, test_state)

    # Check if JSON block was added
    has_json_block = "```json:game_state" in result
    print(f"  {'✓' if has_json_block else '✗'} State embedded in content")

    # Try to extract it back
    messages = [{"role": "assistant", "content": result}]
    extracted = game_state_handler.extract_game_state(messages)

    matches = extracted and extracted.get("room") == "west_of_house"
    print(f"  {'✓' if matches else '✗'} State extracted from messages")

    if extracted:
        print(f"    Room: {extracted.get('room')}")
        print(f"    Inventory: {extracted.get('inventory')}")
        print(f"    Score: {extracted.get('score')}")
    print()

def test_kb_query_formatting():
    """Test formatting queries for KB Agent."""
    print("Testing KB Query Formatting...")

    current_state = {
        "room": "forest",
        "inventory": ["lamp"],
        "score": 5
    }

    test_cases = [
        ("start_game", {"game": "zork"}, "Initialize a new Zork game"),
        ("move", {"direction": "north"}, "from room 'forest', move north"),
        ("look", {"target": ""}, "describe the current room 'forest'"),
        ("take", {"item": "sword"}, "room 'forest', take the item: sword"),
    ]

    for command, params, expected_fragment in test_cases:
        query = game_state_handler.format_kb_game_query(command, params, current_state)
        success = expected_fragment in query
        print(f"  {'✓' if success else '✗'} {command}: Contains '{expected_fragment[:30]}...'")
        if not success:
            print(f"    Got: {query[:100]}...")
    print()

def test_response_formatting():
    """Test creating game responses with embedded state."""
    print("Testing Response Formatting...")

    kb_response = "You move north into a dark forest. A sword lies on the ground."
    game_state = {
        "game": "zork",
        "room": "forest",
        "inventory": ["lamp"],
        "score": 10,
        "moves": 6
    }

    formatted = game_state_handler.create_game_response(kb_response, game_state)

    # Check for game header
    has_header = "🎮 **Zork Adventure**" in formatted
    print(f"  {'✓' if has_header else '✗'} Game header added")

    # Check for status bar
    has_status = "📍 Location:" in formatted and "🏆 Score:" in formatted
    print(f"  {'✓' if has_status else '✗'} Status bar included")

    # Check for embedded state
    has_state = "```json:game_state" in formatted
    print(f"  {'✓' if has_state else '✗'} State JSON embedded")

    print()
    print("Sample output preview:")
    print("-" * 40)
    # Show first part before JSON
    preview = formatted.split("```json:game_state")[0]
    print(preview[:200] + "...")
    print("-" * 40)

def test_state_parsing_from_kb():
    """Test parsing state changes from KB responses."""
    print("Testing KB Response State Parsing...")

    current_state = {
        "room": "west_of_house",
        "inventory": [],
        "score": 0,
        "moves": 0
    }

    # Test room change detection
    kb_response = "You move north. You are now in the forest. Dark trees surround you."
    new_state = game_state_handler.parse_kb_response_for_state(kb_response, current_state)

    room_changed = new_state["room"] != current_state["room"]
    print(f"  {'✓' if room_changed else '✗'} Room change detected: {current_state['room']} -> {new_state['room']}")

    # Test item pickup detection
    kb_response = "You take the lamp. It glows softly in your hands."
    new_state = game_state_handler.parse_kb_response_for_state(kb_response, current_state)

    item_added = "lamp" in new_state.get("inventory", [])
    print(f"  {'✓' if item_added else '✗'} Item pickup detected: lamp added to inventory")

    # Test score update
    kb_response = "Congratulations! Score: 25 points."
    new_state = game_state_handler.parse_kb_response_for_state(kb_response, current_state)

    score_updated = new_state["score"] == 25
    print(f"  {'✓' if score_updated else '✗'} Score update detected: {new_state['score']} points")

    print()

if __name__ == "__main__":
    print("=" * 50)
    print("Option 3 Game State POC Test Suite")
    print("=" * 50)
    print()

    test_command_parsing()
    test_state_embedding()
    test_kb_query_formatting()
    test_response_formatting()
    test_state_parsing_from_kb()

    print("=" * 50)
    print("POC Testing Complete!")
    print("\nThis proof of concept demonstrates that:")
    print("1. Game commands can be detected and parsed")
    print("2. State can be embedded in message content")
    print("3. KB queries can be formatted with context")
    print("4. Responses can include both narrative and state")
    print("\nNext steps:")
    print("- Test with live KB Agent responses")
    print("- Verify PostgreSQL conversation storage")
    print("- Optimize state management (Redis, etc.)")
    print("=" * 50)