#!/bin/bash
# Move bottles from spots 1-4 to spots 5-8 in woander_store

set -e

EXPERIENCE="wylding-woods"
WORLD_FILE="../../Vaults/gaia-knowledge-base/experiences/${EXPERIENCE}/state/world.json"

echo "🔄 Moving bottles from spots 1-4 to spots 5-8..."

# Check if bottles exist in spots 1-4
BOTTLE_COUNT=$(cat "$WORLD_FILE" | jq '[
  .locations.woander_store.areas.main_room.spots |
  (.spot_1.items[], .spot_2.items[], .spot_3.items[], .spot_4.items[]) |
  select(.type == "collectible")
] | length')

if [ "$BOTTLE_COUNT" -eq 0 ]; then
  echo "❌ No bottles found in spots 1-4"
  exit 1
fi

echo "📦 Found $BOTTLE_COUNT bottles in spots 1-4"

# Move bottles using jq
TEMP_FILE=$(mktemp)

jq '
# Get bottles from spots 1-4
(.locations.woander_store.areas.main_room.spots.spot_1.items[0]) as $bottle1 |
(.locations.woander_store.areas.main_room.spots.spot_2.items[0]) as $bottle2 |
(.locations.woander_store.areas.main_room.spots.spot_3.items[0]) as $bottle3 |
(.locations.woander_store.areas.main_room.spots.spot_4.items[0]) as $bottle4 |

# Clear spots 1-4
.locations.woander_store.areas.main_room.spots.spot_1.items = [] |
.locations.woander_store.areas.main_room.spots.spot_2.items = [] |
.locations.woander_store.areas.main_room.spots.spot_3.items = [] |
.locations.woander_store.areas.main_room.spots.spot_4.items = [] |

# Move to spots 5-8
.locations.woander_store.areas.main_room.spots.spot_5.items = [$bottle1] |
.locations.woander_store.areas.main_room.spots.spot_6.items = [$bottle2] |
.locations.woander_store.areas.main_room.spots.spot_7.items = [$bottle3] |
.locations.woander_store.areas.main_room.spots.spot_8.items = [$bottle4] |

# Increment version
.metadata._version += 1 |
.metadata.last_modified = (now | todate)
' "$WORLD_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$WORLD_FILE"

NEW_VERSION=$(cat "$WORLD_FILE" | jq '.metadata._version')

echo "✅ Bottles moved successfully"
echo "   spot_1 → spot_5: $(cat "$WORLD_FILE" | jq -r '.locations.woander_store.areas.main_room.spots.spot_5.items[0].semantic_name')"
echo "   spot_2 → spot_6: $(cat "$WORLD_FILE" | jq -r '.locations.woander_store.areas.main_room.spots.spot_6.items[0].semantic_name')"
echo "   spot_3 → spot_7: $(cat "$WORLD_FILE" | jq -r '.locations.woander_store.areas.main_room.spots.spot_7.items[0].semantic_name')"
echo "   spot_4 → spot_8: $(cat "$WORLD_FILE" | jq -r '.locations.woander_store.areas.main_room.spots.spot_8.items[0].semantic_name')"
echo ""
echo "   New version: $NEW_VERSION"
echo ""
echo "🔍 Verify with: ./scripts/experience/inspect-world.sh"
