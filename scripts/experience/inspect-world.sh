#!/bin/bash
# World State Inspector - Wrapper for common jq queries
# Authorize once, use repeatedly for debugging world state

set -euo pipefail

# Default paths
EXPERIENCE="${1:-wylding-woods}"
WORLD_FILE="/Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/${EXPERIENCE}/state/world.json"
QUERY="${2:-bottles}"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [experience] [query]"
    echo ""
    echo "Experience: wylding-woods (default), crystal-caves, etc."
    echo ""
    echo "Queries:"
    echo "  bottles    - Show bottle locations in spots (default)"
    echo "  quest      - Show Louisa quest state"
    echo "  npcs       - Show all NPC locations and states"
    echo "  spots      - Show all spots with item counts"
    echo "  global     - Show global state"
    echo "  full       - Show complete world state (large output)"
    echo "  inventory USER_ID - Show player inventory"
    echo ""
    echo "Examples:"
    echo "  $0                           # Show bottles in wylding-woods"
    echo "  $0 wylding-woods quest       # Show quest state"
    echo "  $0 wylding-woods inventory test-user-123"
    exit 1
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
fi

if [[ ! -f "$WORLD_FILE" ]]; then
    echo "❌ World file not found: $WORLD_FILE"
    exit 1
fi

echo -e "${BLUE}🔍 Inspecting: $EXPERIENCE${NC}"
echo ""

case "$QUERY" in
    bottles)
        echo -e "${GREEN}📦 Bottle Locations:${NC}"
        jq '.locations.woander_store.areas.main_room.spots | to_entries | map({
            spot: .key,
            items: (.value.items | length),
            bottles: [.value.items[]? | select(.template_id | startswith("bottle_")) | .instance_id]
        }) | sort_by(.spot)' "$WORLD_FILE"
        ;;

    quest)
        echo -e "${GREEN}🎯 Quest State:${NC}"
        jq '{
            louisa_bottles_collected: .npcs.louisa.state.bottles_collected,
            quest_active: .npcs.louisa.state.quest_active,
            global_bottles_found: .global_state.dream_bottles_found,
            global_bottles_required: .global_state.dream_bottles_required,
            quest_started: .global_state.quest_started
        }' "$WORLD_FILE"
        ;;

    npcs)
        echo -e "${GREEN}👥 NPC Locations & States:${NC}"
        jq '.npcs | to_entries | map({
            id: .key,
            name: .value.name,
            type: .value.type,
            location: .value.location,
            state: .value.state
        })' "$WORLD_FILE"
        ;;

    spots)
        echo -e "${GREEN}📍 All Spots (main_room):${NC}"
        jq '.locations.woander_store.areas.main_room.spots | to_entries | map({
            id: .key,
            name: .value.name,
            items: (.value.items | length),
            item_ids: [.value.items[]?.instance_id],
            has_npc: (.value.npc // null)
        }) | sort_by(.id)' "$WORLD_FILE"
        ;;

    global)
        echo -e "${GREEN}🌍 Global State:${NC}"
        jq '.global_state' "$WORLD_FILE"
        ;;

    full)
        echo -e "${YELLOW}📋 Full World State (large output):${NC}"
        jq '.' "$WORLD_FILE"
        ;;

    inventory)
        if [[ -z "${3:-}" ]]; then
            echo "❌ User ID required for inventory query"
            echo "Usage: $0 $EXPERIENCE inventory USER_ID"
            exit 1
        fi
        USER_ID="$3"
        VIEW_FILE="/Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/${EXPERIENCE}/players/${USER_ID}/view.json"

        if [[ ! -f "$VIEW_FILE" ]]; then
            echo "❌ Player view not found: $VIEW_FILE"
            exit 1
        fi

        echo -e "${GREEN}🎒 Player Inventory: $USER_ID${NC}"
        jq '.collected_items | to_entries | map({
            id: .key,
            item: .value
        })' "$VIEW_FILE"
        ;;

    *)
        echo "❌ Unknown query: $QUERY"
        usage
        ;;
esac
