#!/bin/bash
# Persona Iteration Workflow Helper Script
# Usage: ./scripts/iterate_louisa.sh [command] [args...]

set -e

# Configuration
API_KEY="${GAIA_API_KEY:-$(grep '^API_KEY=' .env | cut -d'=' -f2)}"
BASE_URL="${GAIA_LOCAL_URL:-http://localhost:8666}"
CHAT_SERVICE_URL="${GAIA_CHAT_SERVICE_URL:-http://localhost:8002}"  # Direct chat service for persona operations
LOUISA_ID="7b197909-8837-4ed5-a67a-a05c90e817f0"
CONV_FILE=".louisa_conversation_id"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_usage() {
    echo -e "${BLUE}Persona Iteration Workflow Helper${NC}"
    echo ""
    echo "Commands:"
    echo "  ${GREEN}update${NC} <prompt_file>    Update Louisa's system prompt from file"
    echo "  ${GREEN}chat${NC} <message>          Chat with Louisa (preserves conversation)"
    echo "  ${GREEN}new${NC}                     Start new conversation (clears history)"
    echo "  ${GREEN}clear${NC}                   Clear current conversation"
    echo "  ${GREEN}show${NC}                    Show current Louisa persona"
    echo "  ${GREEN}id${NC}                      Show current conversation ID"
    echo "  ${GREEN}test${NC}                    Test persona update functionality"
    echo ""
    echo "Example workflow:"
    echo "  1. ./scripts/iterate_louisa.sh show"
    echo "  2. ./scripts/iterate_louisa.sh new"
    echo "  3. ./scripts/iterate_louisa.sh chat \"Hello Louisa!\""
    echo "  4. Edit persona prompt, save to louisa_v2.txt"
    echo "  5. ./scripts/iterate_louisa.sh update louisa_v2.txt"
    echo "  6. ./scripts/iterate_louisa.sh chat \"How are you feeling now?\""
    echo ""
    echo "Testing:"
    echo "  ./scripts/iterate_louisa.sh test   # Verify prompt updates work"
}

function get_conversation_id() {
    if [[ -f "$CONV_FILE" ]]; then
        cat "$CONV_FILE"
    else
        echo ""
    fi
}

function save_conversation_id() {
    echo "$1" > "$CONV_FILE"
    echo -e "${GREEN}✓${NC} Saved conversation ID: $1"
}

function clear_conversation_id() {
    rm -f "$CONV_FILE"
    echo -e "${GREEN}✓${NC} Cleared conversation ID"
}

function cmd_show() {
    echo -e "${BLUE}Current Louisa Persona:${NC}"
    curl -s -H "X-API-Key: $API_KEY" \
        "$CHAT_SERVICE_URL/personas/$LOUISA_ID" \
        | jq -r '.persona | "Name: \(.name)\nActive: \(.is_active)\nCreated: \(.created_at)\n\nSystem Prompt:\n\(.system_prompt)\n\nPersonality Traits:\n\(.personality_traits | tojson)\n\nCapabilities:\n\(.capabilities | tojson)"'
}

function cmd_update() {
    local prompt_file="$1"

    if [[ ! -f "$prompt_file" ]]; then
        echo -e "${RED}✗${NC} File not found: $prompt_file"
        exit 1
    fi

    echo -e "${BLUE}Updating Louisa persona from: ${prompt_file}${NC}"

    # Read prompt from file and escape for JSON
    local prompt_content
    prompt_content=$(jq -Rs . < "$prompt_file")

    # Update persona
    local response
    response=$(curl -s -X PUT \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"system_prompt\": $prompt_content}" \
        "$CHAT_SERVICE_URL/personas/$LOUISA_ID")

    if echo "$response" | jq -e '.persona' > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Persona updated successfully"
        echo -e "${YELLOW}Note:${NC} Cache automatically cleared by service"
        echo ""
        echo -e "${BLUE}New prompt preview:${NC}"
        echo "$response" | jq -r '.persona.system_prompt' | head -5
        echo "..."

        # Reload prompts in active chat histories
        echo ""
        echo -e "${BLUE}Reloading prompts in active conversations...${NC}"
        local reload_response
        reload_response=$(curl -s -X POST \
            -H "X-API-Key: $API_KEY" \
            "$CHAT_SERVICE_URL/chat/reload-prompt")

        if echo "$reload_response" | jq -e '.status' > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Active conversation prompts reloaded"
        else
            echo -e "${YELLOW}⚠${NC} Could not reload prompts (continuing anyway)"
        fi

        # If we have an active conversation, offer to restart it
        local conv_id
        conv_id=$(get_conversation_id)
        if [[ -n "$conv_id" ]]; then
            echo ""
            echo -e "${YELLOW}Note:${NC} You have an active conversation"
            echo "  1. ./scripts/persona/iterate_louisa.sh show"
echo "  2. ./scripts/persona/iterate_louisa.sh new"
echo "  3. ./scripts/persona/iterate_louisa.sh chat \"Hello Louisa!\""
echo "  5. ./scripts/persona/iterate_louisa.sh update louisa_v2.txt"
echo "  6. ./scripts/persona/iterate_louisa.sh chat \"How are you feeling now?\""
echo "  ./scripts/persona/iterate_louisa.sh test   # Verify prompt updates work"
echo -e "Run ${GREEN}./scripts/persona/iterate_louisa.sh new${NC} to start fresh with the updated prompt"
        fi
    else
        echo -e "${RED}✗${NC} Update failed:"
        echo "$response" | jq '.'
        exit 1
    fi
}

function cmd_chat() {
    local message="$1"
    local conv_id
    conv_id=$(get_conversation_id)

    if [[ -z "$conv_id" ]]; then
        echo -e "${YELLOW}Note:${NC} No existing conversation. Starting new one..."
        cmd_new
        conv_id=$(get_conversation_id)
    fi

    echo -e "${BLUE}Chatting with Louisa (conversation: ${conv_id})${NC}"
    echo ""

    # Use CLI client with conversation persistence
    python3.11 scripts/gaia_client.py \
        --env local \
        --conversation "$conv_id" \
        --batch "$message"
}

function cmd_new() {
    # Clear old conversation if exists
    local old_conv_id
    old_conv_id=$(get_conversation_id)
    if [[ -n "$old_conv_id" ]]; then
        echo -e "${YELLOW}Clearing old conversation: ${old_conv_id}${NC}"
        cmd_clear
    fi

    # Create new conversation
    echo -e "${BLUE}Creating new conversation...${NC}"
    local response
    response=$(curl -s -X POST \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        "$BASE_URL/conversations")

    local conv_id
    conv_id=$(echo "$response" | jq -r '.conversation.id')

    if [[ -n "$conv_id" && "$conv_id" != "null" ]]; then
        save_conversation_id "$conv_id"
        echo -e "${GREEN}✓${NC} New conversation created: $conv_id"
    else
        echo -e "${RED}✗${NC} Failed to create conversation:"
        echo "$response" | jq '.'
        exit 1
    fi
}

function cmd_clear() {
    local conv_id
    conv_id=$(get_conversation_id)

    if [[ -z "$conv_id" ]]; then
        echo -e "${YELLOW}No conversation to clear${NC}"
        return
    fi

    echo -e "${BLUE}Clearing conversation: ${conv_id}${NC}"
    curl -s -X DELETE \
        -H "X-API-Key: $API_KEY" \
        "$BASE_URL/conversations/$conv_id" > /dev/null

    clear_conversation_id
    echo -e "${GREEN}✓${NC} Conversation cleared"
}

function cmd_id() {
    local conv_id
    conv_id=$(get_conversation_id)

    if [[ -z "$conv_id" ]]; then
        echo -e "${YELLOW}No active conversation${NC}"
    else
        echo -e "${GREEN}Current conversation ID:${NC} $conv_id"
    fi
}

function cmd_test() {
    echo -e "${BLUE}Running persona update test...${NC}"
    echo ""

    # Check if test script exists
    if [[ ! -f "scripts/persona/test_persona_update.sh" ]]; then
        echo -e "${RED}✗${NC} Test script not found: scripts/persona/test_persona_update.sh"
        exit 1
    fi

    # Run the test
    bash scripts/persona/test_persona_update.sh
}

# Main command dispatch
case "${1:-}" in
    show)
        cmd_show
        ;;
    update)
        if [[ -z "$2" ]]; then
            echo -e "${RED}✗${NC} Missing prompt file argument"
            echo "Usage: $0 update <prompt_file>"
            exit 1
        fi
        cmd_update "$2"
        ;;
    chat)
        if [[ -z "$2" ]]; then
            echo -e "${RED}✗${NC} Missing message argument"
            echo "Usage: $0 chat \"<message>\""
            exit 1
        fi
        cmd_chat "$2"
        ;;
    new)
        cmd_new
        ;;
    clear)
        cmd_clear
        ;;
    id)
        cmd_id
        ;;
    test)
        cmd_test
        ;;
    help|--help|-h|"")
        print_usage
        ;;
    *)
        echo -e "${RED}✗${NC} Unknown command: $1"
        print_usage
        exit 1
        ;;
esac
