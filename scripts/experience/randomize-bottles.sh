#!/bin/bash
# Randomize bottle placement across woander_store spots

set -e

EXPERIENCE="wylding-woods"
WORLD_FILE="../../Vaults/gaia-knowledge-base/experiences/${EXPERIENCE}/state/world.json"

echo "🎲 Randomizing bottle placement in woander_store..."

# Available spots (8 total in woander_store)
ALL_SPOTS=("spot_1" "spot_2" "spot_3" "spot_4" "spot_5" "spot_6" "spot_7" "spot_8")

# Get all collectible bottles from current world state
BOTTLES=$(cat "$WORLD_FILE" | jq '[
  .locations.woander_store.areas.main_room.spots | to_entries[] |
  .value.items[]? | select(.type == "collectible")
]')

BOTTLE_COUNT=$(echo "$BOTTLES" | jq 'length')

if [ "$BOTTLE_COUNT" -eq 0 ]; then
  echo "❌ No bottles found in world. Run reset-experience.sh first."
  exit 1
fi

echo "📦 Found $BOTTLE_COUNT bottles"

# Shuffle spots and take first N bottles
SELECTED_SPOTS=($(printf '%s\n' "${ALL_SPOTS[@]}" | sort -R | head -$BOTTLE_COUNT))

echo "🎯 New random placement:"
for i in $(seq 0 $(($BOTTLE_COUNT - 1))); do
  BOTTLE_NAME=$(echo "$BOTTLES" | jq -r ".[$i].semantic_name")
  echo "   ${SELECTED_SPOTS[$i]}: $BOTTLE_NAME"
done

# Create new world state with bottles in random spots
echo ""
echo "🔧 Updating world.json..."

# Build jq script to clear all spots and reassign bottles
JQ_SCRIPT='
# Clear all spots first
.locations.woander_store.areas.main_room.spots.spot_1.items = [] |
.locations.woander_store.areas.main_room.spots.spot_2.items = [] |
.locations.woander_store.areas.main_room.spots.spot_3.items = [] |
.locations.woander_store.areas.main_room.spots.spot_4.items = [] |
.locations.woander_store.areas.main_room.spots.spot_5.items = [] |
.locations.woander_store.areas.main_room.spots.spot_6.items = [] |
.locations.woander_store.areas.main_room.spots.spot_7.items = [] |
.locations.woander_store.areas.main_room.spots.spot_8.items = [] |
'

# Add bottles to selected spots
for i in $(seq 0 $(($BOTTLE_COUNT - 1))); do
  SPOT="${SELECTED_SPOTS[$i]}"
  BOTTLE=$(echo "$BOTTLES" | jq -c ".[$i]")
  JQ_SCRIPT+="
.locations.woander_store.areas.main_room.spots.${SPOT}.items += [$BOTTLE] |
"
done

# Increment version and update timestamp
JQ_SCRIPT+='
.metadata._version += 1 |
.metadata.last_modified = (now | todate)
'

# Apply changes
TEMP_FILE=$(mktemp)
cat "$WORLD_FILE" | jq "$JQ_SCRIPT" > "$TEMP_FILE"
mv "$TEMP_FILE" "$WORLD_FILE"

echo "✅ World state updated"
echo "   New version: $(cat "$WORLD_FILE" | jq '.metadata._version')"
echo ""
echo "✨ Bottle randomization complete!"
echo ""
echo "🔍 Verify with: ./scripts/experience/inspect-world.sh"
