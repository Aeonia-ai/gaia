#!/bin/bash
# Reset wylding-woods experience to initial state
# Uses @reset experience CONFIRM admin command via WebSocket

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

USER_ID="${1:-da6dbf22-3209-457f-906a-7f5c63986d3e}"  # Default to admin user

echo "🔄 Resetting wylding-woods experience..."
echo "   User: $USER_ID"
echo ""

# Get JWT token
JWT_TOKEN=$(python3 "$ROOT_DIR/tests/manual/get_test_jwt.py" 2>/dev/null | tail -1)
if [ -z "$JWT_TOKEN" ]; then
    echo "❌ Failed to get JWT token"
    exit 1
fi

# Execute reset via WebSocket
python3 - <<EOF
import asyncio
import websockets
import json

async def reset_experience():
    uri = f"ws://localhost:8001/ws/experience?token=${JWT_TOKEN}&experience=wylding-woods"

    async with websockets.connect(uri) as ws:
        # Wait for initial_state
        await ws.recv()

        # Send reset command with CONFIRM
        await ws.send(json.dumps({
            "type": "action",
            "action": "@reset experience CONFIRM"
        }))

        # Get response
        response = json.loads(await ws.recv())

        if response.get("success"):
            print("✅ Experience reset complete")
            print(f"   {response.get('message', 'Reset successful')}")
        else:
            print(f"❌ Reset failed: {response.get('message', 'Unknown error')}")
            exit(1)

asyncio.run(reset_experience())
EOF

echo ""
echo "🎮 Experience ready for testing"
