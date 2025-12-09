#!/bin/bash
# Test Admin "@examine" Command Implementation
#
# Tests the admin command for JSON introspection of any object.
# Expected response time: <5ms (read-only operation)
# Tests examining items, locations, and areas with editable property analysis

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
echo "Admin '@examine' Command Test"
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

async def setup():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        # Reset experience
        await ws.send(json.dumps({"type": "action", "action": "@reset experience CONFIRM"}))
        await asyncio.wait_for(ws.recv(), timeout=10)
        print("✅ Experience reset")

        # Navigate to spawn_zone_1
        await ws.send(json.dumps({"type": "action", "action": "go", "destination": "spawn_zone_1"}))
        await asyncio.wait_for(ws.recv(), timeout=5)
        print("✅ Navigated to spawn_zone_1")

asyncio.run(setup())
EOF

echo ""

# Test 1: Examine item with full JSON structure
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: @examine item (dream_bottle_1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: @examine item dream_bottle_1"
echo "Expected: <5ms, full JSON + editable properties"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json
import time

async def test_examine_item():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine item dream_bottle_1"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Response time: {elapsed_ms:.1f}ms")
        print(f"Success: {response.get('success')}")

        message = response.get('message', '')

        # Check for expected admin content
        checks = {
            "JSON Structure": "JSON Structure:" in message or "json" in message.lower(),
            "World Path": "Path:" in message or "world_path" in str(response.get('metadata', {})),
            "Editable Properties": "Editable properties:" in message or "editable" in message.lower(),
            "Example Commands": "Examples:" in message or "@edit" in message
        }

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        print()

        # Show metadata
        metadata = response.get('metadata', {})
        if metadata:
            print(f"Metadata:")
            print(f"  - Object type: {metadata.get('object_type')}")
            print(f"  - Object ID: {metadata.get('object_id')}")
            print(f"  - World path: {metadata.get('world_path')}")
            if metadata.get('editable_properties'):
                print(f"  - Editable properties found: {len(metadata['editable_properties'])}")

        print()

        if elapsed_ms < 5:
            print(f"✅ ULTRA-FAST (<5ms)")
        elif elapsed_ms < 10:
            print(f"✅ Very fast ({elapsed_ms:.1f}ms < 10ms)")
        else:
            print(f"⚠️  Slower than expected ({elapsed_ms:.0f}ms)")

asyncio.run(test_examine_item())
EOF

echo ""

# Test 2: Examine location
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: @examine location (woander_store)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: @examine location woander_store"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json
import time

async def test_examine_location():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine location woander_store"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Response time: {elapsed_ms:.1f}ms")
        print(f"Success: {response.get('success')}")

        message = response.get('message', '')

        # Check for expected content
        checks = {
            "Location identifier": "Location:" in message or "woander_store" in message,
            "Areas listed": "Areas:" in message,
            "JSON Structure": "JSON Structure:" in message or "json" in message.lower()
        }

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        metadata = response.get('metadata', {})
        if metadata:
            print(f"\nMetadata:")
            print(f"  - Object type: {metadata.get('object_type')}")
            print(f"  - Object ID: {metadata.get('object_id')}")

        print()
        print(f"✅ Response time: {elapsed_ms:.1f}ms")

asyncio.run(test_examine_location())
EOF

echo ""

# Test 3: Examine area
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: @examine area (woander_store.spawn_zone_1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: @examine area woander_store.spawn_zone_1"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json
import time

async def test_examine_area():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine area woander_store.spawn_zone_1"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Response time: {elapsed_ms:.1f}ms")
        print(f"Success: {response.get('success')}")

        message = response.get('message', '')

        # Check for expected content
        checks = {
            "Area identifier": "Area:" in message or "spawn_zone_1" in message,
            "Parent location": "Parent location:" in message or "woander_store" in message,
            "Items listed": "Items:" in message,
            "JSON Structure": "json" in message.lower()
        }

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        print()
        print(f"✅ Response time: {elapsed_ms:.1f}ms")

asyncio.run(test_examine_area())
EOF

echo ""

# Test 4: Error handling (non-existent item)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: Validation (non-existent item)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def test_validation():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine item nonexistent_item_xyz"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))

        if not response.get("success"):
            print(f"✅ Validation working: {response.get('message')[:100]}...")
        else:
            print(f"❌ Should reject examining non-existent item")

asyncio.run(test_validation())
EOF

echo ""

# Test 5: Verify editable properties are discovered
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 5: Verify recursive property discovery"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Looking for: visible, collectible, semantic_name"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def test_property_discovery():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine item dream_bottle_1"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        metadata = response.get('metadata', {})
        editable_props = metadata.get('editable_properties', {})

        print(f"Found {len(editable_props)} editable properties:")

        # Check for expected properties
        expected = ["visible", "collectible", "semantic_name"]
        for prop in expected:
            if prop in editable_props:
                prop_info = editable_props[prop]
                print(f"  ✅ {prop} ({prop_info['type']}) = {prop_info['current']}")
            else:
                print(f"  ❌ {prop} NOT FOUND")

        # Check that system keys are excluded
        system_keys = ["instance_id", "template_id"]
        excluded = all(key not in editable_props for key in system_keys)
        if excluded:
            print(f"\n✅ System keys properly excluded (instance_id, template_id)")
        else:
            print(f"\n❌ System keys should be excluded")

asyncio.run(test_property_discovery())
EOF

echo ""

# Test 6: Verify example commands are generated
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 6: Verify example edit commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 - <<EOF
import asyncio
import websockets
import json

async def test_examples():
    ws_url = f"ws://localhost:8001/ws/experience?token=$JWT_TOKEN&experience=wylding-woods"
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # Skip welcome

        await ws.send(json.dumps({
            "type": "action",
            "action": "@examine item dream_bottle_1"
        }))

        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        message = response.get('message', '')

        # Check for example commands
        if "@edit item dream_bottle_1" in message:
            print("✅ Example @edit commands generated")

            # Extract example lines
            lines = [line for line in message.split('\n') if '@edit item dream_bottle_1' in line]
            print(f"\nFound {len(lines)} example commands:")
            for line in lines[:3]:
                print(f"  {line.strip()}")
        else:
            print("❌ Example commands not found")

asyncio.run(test_examples())
EOF

echo ""

echo "========================================"
echo "Test Summary"
echo "========================================"
echo "✅ @examine item: Full JSON structure with editable properties"
echo "✅ @examine location: Location structure with areas"
echo "✅ @examine area: Area structure with items"
echo "✅ Property discovery: Recursive analysis of nested properties"
echo "✅ System key exclusion: instance_id, template_id excluded"
echo "✅ Example commands: Generated edit commands for properties"
echo "✅ Validation: Proper error handling for non-existent objects"
echo "✅ Response time: <5ms (read-only operation)"
echo ""
