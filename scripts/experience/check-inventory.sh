#!/bin/bash
# Quick inventory checker for wylding-woods experience

USER_ID="${1:-da6dbf22-3209-457f-906a-7f5c63986d3e}"  # Default to admin user

echo "🎒 Checking inventory for user: $USER_ID"
echo ""

# Try to read from container first
PLAYER_FILE="/kb/experiences/wylding-woods/state/players/${USER_ID}.json"

docker exec gaia-kb-service-1 test -f "$PLAYER_FILE" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "📦 Current inventory:"
    docker exec gaia-kb-service-1 cat "$PLAYER_FILE" | jq -r '.player.inventory[] | "  - \(.semantic_name // .template_id // .instance_id)"'

    echo ""
    echo "📊 Inventory count:"
    docker exec gaia-kb-service-1 cat "$PLAYER_FILE" | jq '.player.inventory | length'
else
    echo "❌ No player state file found (player may not have connected yet)"
    echo "   Expected: $PLAYER_FILE"
fi
