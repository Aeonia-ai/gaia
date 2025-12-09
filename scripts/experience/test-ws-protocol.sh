#!/bin/bash
# WebSocket Protocol Tester - Validates what Unity receives
# Tests structured commands, captures events, validates Unity expectations

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default parameters
EXPERIENCE="${1:-wylding-woods}"
OUTPUT_FILE="${2:-/tmp/ws-protocol-test-$(date +%Y%m%d-%H%M%S).log}"

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   WebSocket Protocol Test - Unity Integration     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Experience: $EXPERIENCE"
echo "Output: $OUTPUT_FILE"
echo ""

# Create Python test script
python3 << 'EOF' > "$OUTPUT_FILE" 2>&1
import asyncio
import websockets
import json
import subprocess
import sys
from datetime import datetime

async def get_jwt_token():
    """Get JWT token from test script."""
    result = subprocess.run(
        ["python3", "tests/manual/get_test_jwt.py"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n')[-1]

def print_header(text):
    """Print formatted header."""
    print()
    print("=" * 80)
    print(text)
    print("=" * 80)
    print()

def validate_unity_expectations(messages):
    """Validate what Unity expects vs what it received."""
    print_header("UNITY EXPECTATIONS vs REALITY")

    action_response = next((m for m in messages if m.get("type") == "action_response"), None)
    world_updates = [m for m in messages if m.get("type") == "world_update"]

    issues = []

    if action_response:
        print("✅ action_response received:")
        print(f"   type: {action_response.get('type')}")
        print(f"   success: {action_response.get('success')}")
        print(f"   action: {action_response.get('action')}")

        # Check for item_id field (Unity expects this)
        item_id = action_response.get("item_id")
        meta_instance_id = action_response.get("metadata", {}).get("instance_id")

        if item_id:
            print(f"   ✅ item_id: {item_id}")
        else:
            print(f"   ❌ item_id: MISSING (Unity expects this!)")
            issues.append("action_response missing 'item_id' field")
            if meta_instance_id:
                print(f"   ⚠️  Found instance_id in metadata: {meta_instance_id}")
                issues.append(f"instance_id is in metadata instead of root level")
    else:
        print("❌ NO action_response received!")
        issues.append("No action_response message")

    print()

    if world_updates:
        print(f"✅ {len(world_updates)} world_update event(s) received:")
        for i, wu in enumerate(world_updates, 1):
            changes = wu.get("changes", [])
            if isinstance(changes, list):
                if len(changes) > 0:
                    print(f"   #{i}: ✅ {len(changes)} change(s)")
                else:
                    print(f"   #{i}: ❌ EMPTY changes array")
                    issues.append(f"world_update #{i} has empty changes")
            else:
                print(f"   #{i}: ❌ changes is not an array")
                issues.append(f"world_update #{i} has invalid changes format")
    else:
        print("⚠️  NO world_update events received")
        issues.append("No world_update events")

    print()

    if issues:
        print("🔴 ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("🟢 ALL UNITY EXPECTATIONS MET!")

    return issues

async def test_structured_command():
    """Test collect_item with structured command format."""
    print_header("WebSocket Protocol Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Testing: collect_item (structured format)")

    # Get JWT
    print("\n🔐 Getting JWT token...")
    token = await get_jwt_token()
    print("   ✅ Token obtained")

    # Connect
    ws_url = f"ws://localhost:8001/ws/experience?token={token}&experience=wylding-woods"
    print(f"\n🔌 Connecting to {ws_url}...")

    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # connected
        print("   ✅ Connected")

        # Reset experience
        print("\n🔄 Resetting experience...")
        await ws.send(json.dumps({"type": "action", "action": "@reset experience CONFIRM"}))
        await ws.recv()
        print("   ✅ Reset complete")

        # Navigate
        print("\n📍 Navigating to main_room...")
        await ws.send(json.dumps({"type": "action", "action": "go to main room"}))
        await ws.recv()
        print("   ✅ Arrived")

        # Collect with STRUCTURED format
        print_header("TEST 1: collect_item (structured format)")
        print("Sending:")
        command = {
            "type": "action",
            "action": "collect_item",
            "instance_id": "bottle_mystery"
        }
        print(json.dumps(command, indent=2))

        await ws.send(json.dumps(command))

        # Capture all messages
        messages = []
        print("\n📥 Receiving messages...")
        for _ in range(10):  # Increased to capture more messages
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

        # Test natural language for comparison
        print_header("TEST 2: collect (natural language) - FOR COMPARISON")
        print("Sending: 'collect bottle_energy'")

        await ws.send(json.dumps({
            "type": "action",
            "action": "collect bottle_energy"
        }))

        nl_messages = []
        for _ in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                nl_messages.append(data)
            except asyncio.TimeoutError:
                break

        print(f"\n📥 Received {len(nl_messages)} message(s)")
        for i, msg in enumerate(nl_messages, 1):
            print(f"   {i}. {msg.get('type')}")

        # Summary
        print_header("SUMMARY")
        print(f"Structured command (collect_item): {len(messages)} messages")
        print(f"Natural language (collect ...): {len(nl_messages)} messages")
        print()

        if issues:
            print("🔴 Protocol issues detected - Unity integration incomplete")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("🟢 Protocol working correctly - Unity ready!")
            return True

if __name__ == "__main__":
    result = asyncio.run(test_structured_command())
    sys.exit(0 if result else 1)
EOF

# Run the test
python3 << 'RUNNER'
import subprocess
import sys

# Read and execute the test
with open(sys.argv[1], 'r') as f:
    exec(f.read())
RUNNER "$OUTPUT_FILE" | tee "$OUTPUT_FILE"

# Check result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Test completed successfully${NC}"
else
    echo -e "\n${RED}❌ Test found protocol issues${NC}"
fi

echo ""
echo "Full output saved to: $OUTPUT_FILE"
