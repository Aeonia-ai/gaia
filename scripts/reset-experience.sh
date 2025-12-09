#!/bin/bash
# Reset Experience Script
# Quick CLI tool for resetting game experiences during development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KB_CONTAINER="gaia-kb-service-1"
KB_PATH="/kb"

# Help text
show_help() {
    cat << EOF
${BLUE}Reset Experience Script${NC}

Usage:
  ./scripts/reset-experience.sh [OPTIONS] <experience>

Arguments:
  experience          Experience to reset (e.g., wylding-woods, west-of-house)

Options:
  --world-only        Reset world state only (keep player data)
  --player <user_id>  Reset specific player only
  --no-backup         Skip backup creation (dangerous!)
  --force             Skip confirmation prompt
  -h, --help          Show this help message

Examples:
  # Full reset with confirmation
  ./scripts/reset-experience.sh wylding-woods

  # Reset world only (keep players)
  ./scripts/reset-experience.sh --world-only wylding-woods

  # Reset single player
  ./scripts/reset-experience.sh --player jason@aeonia.ai wylding-woods

  # Force reset without confirmation
  ./scripts/reset-experience.sh --force wylding-woods

State Models:
  - Shared (wylding-woods): Resets /kb/experiences/{exp}/state/world.json
  - Isolated (west-of-house): Resets /kb/players/{user}/{exp}/view.json

EOF
}

# Parse arguments
WORLD_ONLY=false
PLAYER_ID=""
NO_BACKUP=false
FORCE=false
EXPERIENCE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --world-only)
            WORLD_ONLY=true
            shift
            ;;
        --player)
            PLAYER_ID="$2"
            shift 2
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
        *)
            EXPERIENCE="$1"
            shift
            ;;
    esac
done

# Validate experience argument
if [ -z "$EXPERIENCE" ]; then
    echo -e "${RED}Error: Experience name required${NC}"
    show_help
    exit 1
fi

# Detect state model
detect_state_model() {
    local config_file="$KB_PATH/experiences/$EXPERIENCE/config.json"

    if docker exec "$KB_CONTAINER" test -f "$config_file"; then
        STATE_MODEL=$(docker exec "$KB_CONTAINER" cat "$config_file" | jq -r '.state_model // "shared"')
    else
        echo -e "${YELLOW}Warning: config.json not found, assuming shared model${NC}"
        STATE_MODEL="shared"
    fi
}

# Check if experience exists
check_experience_exists() {
    if ! docker exec "$KB_CONTAINER" test -d "$KB_PATH/experiences/$EXPERIENCE"; then
        echo -e "${RED}Error: Experience '$EXPERIENCE' not found${NC}"
        echo -e "Available experiences:"
        docker exec "$KB_CONTAINER" ls "$KB_PATH/experiences/" | grep -v "^\\." || true
        exit 1
    fi
}

# Count what will be reset
count_resets() {
    echo -e "${BLUE}Analyzing current state...${NC}"

    # Count players
    PLAYER_COUNT=0
    if docker exec "$KB_CONTAINER" test -d "$KB_PATH/players"; then
        PLAYER_COUNT=$(docker exec "$KB_CONTAINER" find "$KB_PATH/players" -type d -name "$EXPERIENCE" 2>/dev/null | wc -l | tr -d ' ')
    fi

    # Count NPCs (estimate from player NPC dirs)
    NPC_COUNT=0
    if docker exec "$KB_CONTAINER" test -d "$KB_PATH/players"; then
        NPC_COUNT=$(docker exec "$KB_CONTAINER" find "$KB_PATH/players" -path "*/$EXPERIENCE/npcs/*.json" 2>/dev/null | wc -l | tr -d ' ')
    fi

    # Check world state exists
    WORLD_EXISTS=false
    if docker exec "$KB_CONTAINER" test -f "$KB_PATH/experiences/$EXPERIENCE/state/world.json"; then
        WORLD_EXISTS=true
    fi

    # Check template exists
    TEMPLATE_EXISTS=false
    if docker exec "$KB_CONTAINER" test -f "$KB_PATH/experiences/$EXPERIENCE/state/world.template.json"; then
        TEMPLATE_EXISTS=true
    fi
}

# Show reset preview
show_preview() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Reset Preview: $EXPERIENCE${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "State Model: ${BLUE}$STATE_MODEL${NC}"
    echo ""

    if [ "$PLAYER_ID" != "" ]; then
        echo -e "${RED}❗ Single player reset:${NC}"
        echo "   - Player: $PLAYER_ID"
        echo "   - Clear player view"
        echo "   - Delete NPC conversations"
        echo "   - Clear inventory"
    elif [ "$WORLD_ONLY" = true ]; then
        echo -e "${RED}❗ World-only reset:${NC}"
        echo "   - Restore world state from template"
        echo "   - Keep $PLAYER_COUNT player views"
        echo "   - Keep $NPC_COUNT NPC conversations"
    else
        echo -e "${RED}❗ Full reset:${NC}"
        echo "   - Restore world state from template"
        echo "   - Delete $PLAYER_COUNT player views"
        echo "   - Clear $NPC_COUNT NPC conversations"
        echo "   - Reset all inventories"
    fi

    echo ""

    if [ "$WORLD_EXISTS" = true ] && [ "$NO_BACKUP" = false ]; then
        echo -e "${GREEN}📦 Backup will be created${NC}"
    fi

    if [ "$TEMPLATE_EXISTS" = false ]; then
        echo -e "${RED}⚠️  Warning: No template file found${NC}"
        echo "   Current state will be used as template"
    fi

    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════${NC}"
    echo ""
}

# Confirm reset
confirm_reset() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    read -p "$(echo -e ${YELLOW}Proceed with reset? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Reset cancelled${NC}"
        exit 0
    fi
}

# Create backup
create_backup() {
    if [ "$NO_BACKUP" = true ]; then
        echo -e "${YELLOW}Skipping backup (--no-backup flag set)${NC}"
        return 0
    fi

    if [ "$WORLD_ONLY" = false ] && [ "$PLAYER_ID" != "" ]; then
        # Player-specific reset, no world backup needed
        return 0
    fi

    local world_file="$KB_PATH/experiences/$EXPERIENCE/state/world.json"

    if ! docker exec "$KB_CONTAINER" test -f "$world_file"; then
        echo -e "${YELLOW}No world state to backup${NC}"
        return 0
    fi

    echo -e "${BLUE}Creating backup...${NC}"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$KB_PATH/experiences/$EXPERIENCE/state/backups"
    local backup_file="$backup_dir/world.$timestamp.json"

    # Create backup directory
    docker exec "$KB_CONTAINER" mkdir -p "$backup_dir"

    # Copy to backup
    docker exec "$KB_CONTAINER" cp "$world_file" "$backup_file"

    echo -e "${GREEN}✓ Backup created: backups/world.$timestamp.json${NC}"

    # Rotate old backups (keep last 5)
    echo -e "${BLUE}Rotating old backups...${NC}"
    docker exec "$KB_CONTAINER" sh -c "cd '$backup_dir' && ls -t world.*.json | tail -n +6 | xargs -r rm"

    BACKUP_FILE="$backup_file"
}

# Ensure template exists
ensure_template() {
    local template_file="$KB_PATH/experiences/$EXPERIENCE/state/world.template.json"
    local world_file="$KB_PATH/experiences/$EXPERIENCE/state/world.json"

    if docker exec "$KB_CONTAINER" test -f "$template_file"; then
        return 0
    fi

    echo -e "${YELLOW}No template found, creating from current state...${NC}"

    if docker exec "$KB_CONTAINER" test -f "$world_file"; then
        docker exec "$KB_CONTAINER" cp "$world_file" "$template_file"
        echo -e "${GREEN}✓ Template created from current state${NC}"
    else
        echo -e "${RED}Error: No template and no current state to copy from${NC}"
        exit 1
    fi
}

# Reset world state
reset_world() {
    echo -e "${BLUE}Resetting world state...${NC}"

    local template_file="$KB_PATH/experiences/$EXPERIENCE/state/world.template.json"
    local world_file="$KB_PATH/experiences/$EXPERIENCE/state/world.json"

    # Copy template to world
    docker exec "$KB_CONTAINER" cp "$template_file" "$world_file"

    echo -e "${GREEN}✓ World state restored from template${NC}"
}

# Reset players
reset_players() {
    echo -e "${BLUE}Resetting player data...${NC}"

    local cleared=0

    if [ "$PLAYER_ID" != "" ]; then
        # Reset specific player
        local player_dir="$KB_PATH/players/$PLAYER_ID/$EXPERIENCE"
        if docker exec "$KB_CONTAINER" test -d "$player_dir"; then
            docker exec "$KB_CONTAINER" rm -rf "$player_dir"
            cleared=1
        fi
    else
        # Reset all players
        if docker exec "$KB_CONTAINER" test -d "$KB_PATH/players"; then
            # Find and delete all player experience directories
            docker exec "$KB_CONTAINER" find "$KB_PATH/players" -type d -name "$EXPERIENCE" -exec rm -rf {} + 2>/dev/null || true
            cleared=$PLAYER_COUNT
        fi
    fi

    echo -e "${GREEN}✓ Cleared $cleared player view(s)${NC}"
}

# Show completion summary
show_summary() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}  Reset Complete: $EXPERIENCE${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""

    if [ "$BACKUP_FILE" != "" ]; then
        echo -e "📦 Backup: ${BACKUP_FILE#$KB_PATH/experiences/$EXPERIENCE/state/}"
    fi

    echo ""
    echo -e "♻️  Reset summary:"

    if [ "$PLAYER_ID" != "" ]; then
        echo "   - Player '$PLAYER_ID' cleared"
        echo "   - Will bootstrap fresh on next login"
    elif [ "$WORLD_ONLY" = true ]; then
        echo "   - World state restored"
        echo "   - Player data preserved"
    else
        echo "   - World state restored"
        echo "   - $PLAYER_COUNT player view(s) cleared"
        echo "   - $NPC_COUNT NPC conversation(s) cleared"
    fi

    echo ""
    echo -e "${BLUE}Experience is now in pristine initial state${NC}"
    echo ""

    if [ "$PLAYER_ID" = "" ]; then
        echo -e "Next steps:"
        echo "  - Test: curl POST /experience/interact -d '{\"message\":\"look around\"}'"
        echo "  - Stats: curl POST /experience/interact -d '{\"message\":\"@stats\"}'"
        echo "  - List: curl POST /experience/interact -d '{\"message\":\"@list waypoints\"}'"
    fi

    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}╔════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   GAIA Experience Reset Tool      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════╝${NC}"
    echo ""

    # Check Docker container is running
    if ! docker ps | grep -q "$KB_CONTAINER"; then
        echo -e "${RED}Error: KB service container not running${NC}"
        echo "Start with: docker compose up -d"
        exit 1
    fi

    # Validate experience exists
    check_experience_exists

    # Detect state model
    detect_state_model

    # Count what will be reset
    count_resets

    # Show preview
    show_preview

    # Confirm
    confirm_reset

    echo ""
    echo -e "${BLUE}Starting reset...${NC}"
    echo ""

    # Create backup
    create_backup

    # Ensure template exists
    if [ "$PLAYER_ID" = "" ]; then
        ensure_template
    fi

    # Reset based on scope
    if [ "$PLAYER_ID" != "" ]; then
        # Player-specific reset
        reset_players
    elif [ "$WORLD_ONLY" = true ]; then
        # World-only reset
        reset_world
    else
        # Full reset
        reset_world
        reset_players
    fi

    # Show summary
    show_summary
}

# Run main
main
