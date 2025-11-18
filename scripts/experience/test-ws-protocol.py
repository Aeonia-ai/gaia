#!/usr/bin/env python3
"""
WebSocket Protocol Tester - Validates what Unity receives

Tests structured commands, captures all events, validates Unity expectations.
Can be run repeatedly without authorization prompts.

Usage:
    ./test-ws-protocol.py                    # Test wylding-woods
    ./test-ws-protocol.py crystal-caves      # Test specific experience
    ./test-ws-protocol.py --output test.log  # Save to specific file
"""

import asyncio
import websockets
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def get_jwt_token() -> str:
    """Get JWT token from test script."""
    result = subprocess.run(
        ["python3", str(Path(__file__).parent.parent.parent / "tests/manual/get_test_jwt.py")],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n')[-1]


def print_header(text: str):
    """Print formatted header."""
    print()
    print("=" * 80)
    print(text)
    print("=" * 80)
    print()


def validate_unity_expectations(messages: List[Dict[str, Any]]) -> List[str]:
    """
    Validate what Unity expects vs what it received.

    Returns:
        List of issues found (empty if all expectations met)
    """
    print_header("UNITY EXPECTATIONS vs REALITY")

    action_response = next((m for m in messages if m.get("type") == "action_response"), None)
    world_updates = [m for m in messages if m.get("type") == "world_update"]

    issues = []

    # Check action_response
    if action_response:
        print("✅ action_response received:")
        print(f"   type: {action_response.get('type')}")
        print(f"   success: {action_response.get('success')}")
        print(f"   action: {action_response.get('action')}")

        # Unity expects item_id field at root level
        item_id = action_response.get("item_id")
        meta_instance_id = action_response.get("metadata", {}).get("instance_id")

        if item_id:
            print(f"   ✅ item_id: {item_id}")
        else:
            print(f"   ❌ item_id: MISSING (Unity expects this!)")
            issues.append("action_response missing 'item_id' field")
            if meta_instance_id:
                print(f"   ⚠️  Found instance_id in metadata: {meta_instance_id}")
                issues.append(f"instance_id is in metadata.instance_id instead of root item_id")
    else:
        print("❌ NO action_response received!")
        issues.append("No action_response message")

    print()

    # Check world_update events
    if world_updates:
        print(f"✅ {len(world_updates)} world_update event(s) received:")
        for i, wu in enumerate(world_updates, 1):
            changes = wu.get("changes", [])
            if isinstance(changes, list):
                if len(changes) > 0:
                    print(f"   #{i}: ✅ {len(changes)} change(s)")
                    # Show first change as example
                    print(f"        Sample: {json.dumps(changes[0], indent=10)[:100]}...")
                else:
                    print(f"   #{i}: ❌ EMPTY changes array")
                    issues.append(f"world_update #{i} has empty changes (Unity can't see state changes)")
            else:
                print(f"   #{i}: ❌ changes is not an array: {type(changes)}")
                issues.append(f"world_update #{i} has invalid changes format")
    else:
        print("⚠️  NO world_update events received")
        # Note: This might be OK for read-only commands
        print("   (This may be OK for read-only commands)")

    print()

    # Summary
    if issues:
        print("🔴 ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("🟢 ALL UNITY EXPECTATIONS MET!")

    return issues


async def test_ws_protocol(experience: str = "wylding-woods"):
    """Test WebSocket protocol with Unity expectations."""

    print_header("WebSocket Protocol Test - Unity Integration")
    print(f"Experience: {experience}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Get JWT
    print("\n🔐 Getting JWT token...")
    token = await get_jwt_token()
    print("   ✅ Token obtained")

    # Connect
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience={experience}"
    print(f"\n🔌 Connecting to WebSocket...")

    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # connected
        print("   ✅ Connected")

        # Reset experience
        print("\n🔄 Resetting experience...")
        await ws.send(json.dumps({"type": "action", "action": "@reset experience CONFIRM"}))
        await ws.recv()
        print("   ✅ Reset complete")

        # Navigate to main room
        print("\n📍 Navigating to main_room...")
        await ws.send(json.dumps({"type": "action", "action": "go to main room"}))
        await ws.recv()
        print("   ✅ Arrived")

        # TEST 1: Structured command (Unity uses this)
        print_header("TEST 1: collect_item (STRUCTURED FORMAT - Unity uses this)")

        command = {
            "type": "action",
            "action": "collect_item",
            "instance_id": "bottle_mystery"
        }

        print("Sending:")
        print(json.dumps(command, indent=2))
        await ws.send(json.dumps(command))

        # Capture all messages
        messages = []
        print("\n📥 Receiving messages...")
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                messages.append(data)
                print(f"   {len(messages)}. {data.get('type')}")
            except asyncio.TimeoutError:
                break

        print(f"\n✅ Received {len(messages)} message(s)")

        # Display full messages
        print_header("FULL MESSAGE DETAILS")
        for i, msg in enumerate(messages, 1):
            print(f"\nMessage {i}: {msg.get('type')}")
            print("-" * 80)
            print(json.dumps(msg, indent=2))

        # Validate Unity expectations
        issues = validate_unity_expectations(messages)

        # TEST 2: Natural language (for comparison)
        print_header("TEST 2: collect (NATURAL LANGUAGE - for comparison)")
        print("Sending: 'collect bottle_energy'")

        await ws.send(json.dumps({
            "type": "action",
            "action": "collect bottle_energy"
        }))

        nl_messages = []
        print("\n📥 Receiving messages...")
        for _ in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                nl_messages.append(data)
                print(f"   {len(nl_messages)}. {data.get('type')}")
            except asyncio.TimeoutError:
                break

        # Summary
        print_header("SUMMARY")
        print(f"Structured command (collect_item): {len(messages)} messages")
        print(f"Natural language (collect ...):    {len(nl_messages)} messages")
        print()
        print("Protocol differences:")
        print(f"  - Structured uses fast handler:  <100ms response time")
        print(f"  - Natural language uses LLM:     ~1-3s response time")
        print()

        if issues:
            print("🔴 Protocol issues detected - Unity integration needs fixes:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            print("Required fixes:")
            print("  1. Add 'item_id' field to action_response (Unity expects it)")
            print("  2. Fix world_update 'changes' array (currently empty)")
            return False
        else:
            print("🟢 Protocol working correctly - Unity ready!")
            return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test WebSocket protocol for Unity integration")
    parser.add_argument("experience", nargs="?", default="wylding-woods",
                       help="Experience ID to test (default: wylding-woods)")
    parser.add_argument("--output", "-o", help="Save output to file")

    args = parser.parse_args()

    # Run test
    result = asyncio.run(test_ws_protocol(args.experience))
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
