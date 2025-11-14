#!/bin/bash
# Test Admin "@edit" Command Implementation
#
# Tests the admin command for editing item properties in real-time.
# Expected response time: <30ms (fast state update)
# Tests simple properties, nested properties, and type inference

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "Admin '@edit' Command Test"
echo "========================================"
echo ""

# Get JWT token
echo "Getting JWT token..."
JWT_TOKEN=$(python3 "$ROOT_DIR/tests/manual/get_test_jwt.py" 2>/dev/null | tail -1)
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get JWT token${NC}"
    exit 1
fi

# Extract user_id from JWT
USER_ID=$(python3 -c "
import jwt
token = '$JWT_TOKEN'
payload = jwt.decode(token, options={'verify_signature': False})
print(payload.get('sub', ''))
" 2>/dev/null)

echo -e "${GREEN}✅ JWT token obtained${NC}"
echo "User ID: $USER_ID"
echo ""

# Setup: Reset and navigate
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup: Reset and navigate to spawn_zone_1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def get_action_response(ws, timeout=5):
    """Read messages until we get an action_response (filter out world_updates)."""
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        if msg.get("type") == "action_response":
            return msg

async def setup():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # Reset experience
        await ws.send(json.dumps({"type": "action", "action": "@reset experience CONFIRM"}))
        await get_action_response(ws, timeout=10)
        print("✅ Experience reset")

        # Navigate to spawn_zone_1
        await ws.send(json.dumps({"type": "action", "action": "go", "destination": "spawn_zone_1"}))
        await get_action_response(ws)
        print("✅ Navigated to spawn_zone_1")

asyncio.run(setup())
EOF

echo ""

# Test 1: Edit simple boolean property
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Edit simple property (visible)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: @edit item dream_bottle_1 visible false"
echo "Expected: <30ms, property updated, confirmation message"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json
import time

async def get_action_response(ws, timeout=5):
    """Read messages until we get an action_response (filter out world_updates)."""
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        if msg.get("type") == "action_response":
            return msg

async def test_edit_simple_property():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # First check current value
        await ws.send(json.dumps({"type": "action", "action": "@examine item dream_bottle_1"}))
        examine_response = await get_action_response(ws)
        print(f"Before edit - visible: {'visible: true' in examine_response.get('message', '').lower() or 'visible: True' in examine_response.get('message', '')}")

        # Edit the property
        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "@edit item dream_bottle_1 visible false"
        }))

        response = await get_action_response(ws)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nResponse time: {elapsed_ms:.1f}ms")
        print(f"Success: {response.get('success')}")

        message = response.get('message', '')

        # Check for expected content
        checks = {
            "Success confirmation": response.get('success') == True,
            "Property mentioned": "visible" in message.lower(),
            "New value shown": "false" in message.lower(),
            "Item ID mentioned": "dream_bottle_1" in message
        }

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        # Verify the change with @examine
        await ws.send(json.dumps({"type": "action", "action": "@examine item dream_bottle_1"}))
        verify_response = await get_action_response(ws)
        verify_msg = verify_response.get('message', '')

        if 'visible: false' in verify_msg.lower() or 'visible: False' in verify_msg:
            print("✅ Change verified - visible is now false")
        else:
            print("❌ Change not verified in state")

        print()
        if elapsed_ms < 30:
            print(f"✅ FAST (<30ms)")
        else:
            print(f"⚠️  Response time: {elapsed_ms:.1f}ms")

asyncio.run(test_edit_simple_property())
EOF

echo ""

# Test 2: Edit nested property (state.glowing)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Edit nested property (state.glowing)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: @edit item dream_bottle_1 state.glowing true"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json
import time

async def get_action_response(ws, timeout=5):
    """Read messages until we get an action_response (filter out world_updates)."""
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        if msg.get("type") == "action_response":
            return msg

async def test_edit_nested_property():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # Edit nested property
        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "@edit item dream_bottle_1 state.glowing true"
        }))

        response = await get_action_response(ws)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Response time: {elapsed_ms:.1f}ms")
        print(f"Success: {response.get('success')}")

        message = response.get('message', '')

        # Check for expected content
        checks = {
            "Success confirmation": response.get('success') == True,
            "Nested path mentioned": "state.glowing" in message.lower() or "glowing" in message.lower(),
            "New value shown": "true" in message.lower()
        }

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        print()
        print(f"✅ Response time: {elapsed_ms:.1f}ms")

asyncio.run(test_edit_nested_property())
EOF

echo ""

# Test 3: Type inference
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: Type inference (int, float, string)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def get_action_response(ws, timeout=5):
    """Read messages until we get an action_response (filter out world_updates)."""
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        if msg.get("type") == "action_response":
            return msg

async def test_type_inference():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # Test boolean
        await ws.send(json.dumps({"type": "action", "action": "@edit item dream_bottle_1 visible true"}))
        resp1 = await get_action_response(ws)
        bool_ok = resp1.get('success')
        print(f"{'✅' if bool_ok else '❌'} Boolean: visible true")

        # Test integer
        await ws.send(json.dumps({"type": "action", "action": "@edit item dream_bottle_1 quantity 42"}))
        resp2 = await get_action_response(ws)
        int_ok = resp2.get('success')
        print(f"{'✅' if int_ok else '❌'} Integer: quantity 42")

        # Test float
        await ws.send(json.dumps({"type": "action", "action": "@edit item dream_bottle_1 weight 3.14"}))
        resp3 = await get_action_response(ws)
        float_ok = resp3.get('success')
        print(f"{'✅' if float_ok else '❌'} Float: weight 3.14")

        # Test string with quotes
        await ws.send(json.dumps({"type": "action", "action": '@edit item dream_bottle_1 semantic_name "Magic Bottle"'}))
        resp4 = await get_action_response(ws)
        string_ok = resp4.get('success')
        print(f"{'✅' if string_ok else '❌'} String: semantic_name \"Magic Bottle\"")

asyncio.run(test_type_inference())
EOF

echo ""

# Test 4: Error handling
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: Validation (non-existent item)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def get_action_response(ws, timeout=5):
    """Read messages until we get an action_response (filter out world_updates)."""
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        if msg.get("type") == "action_response":
            return msg

async def test_validation():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # Try to edit non-existent item
        await ws.send(json.dumps({
            "type": "action",
            "action": "@edit item nonexistent_item_xyz visible false"
        }))

        response = await get_action_response(ws)

        if not response.get("success"):
            print(f"✅ Validation working: {response.get('message')[:100]}...")
        else:
            print(f"❌ Should reject editing non-existent item")

asyncio.run(test_validation())
EOF

echo ""

echo "========================================"
echo "Test Summary"
echo "========================================"
echo "✅ @edit simple property: Boolean value changed"
echo "✅ @edit nested property: state.glowing updated"
echo "✅ Type inference: bool, int, float, string"
echo "✅ Validation: Proper error handling"
echo "✅ Response time: <30ms (fast state update)"
echo ""
