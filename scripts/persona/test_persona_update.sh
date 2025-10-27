#!/bin/bash
# Test script to verify persona updates take effect immediately in active conversations
# Tests that /chat/reload-prompt correctly updates in-memory chat histories

set -e

# Configuration
API_KEY="${GAIA_API_KEY:-$(grep '^API_KEY=' .env | cut -d'=' -f2)}"
BASE_URL="${GAIA_LOCAL_URL:-http://localhost:8666}"
LOUISA_ID="7b197909-8837-4ed5-a67a-a05c90e817f0"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Test marker to identify when new prompt is active
TEST_MARKER="TESTING_MARKER_$(date +%s)"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Persona Update Test - Verifying Prompt Reload${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Save original persona
echo -e "${BLUE}Step 1: Backing up original Louisa persona...${NC}"
ORIGINAL_PERSONA=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/personas/$LOUISA_ID")
ORIGINAL_PROMPT=$(echo "$ORIGINAL_PERSONA" | jq -r '.persona.system_prompt')
echo -e "${GREEN}✓${NC} Original prompt backed up ($(echo "$ORIGINAL_PROMPT" | wc -c) bytes)"
echo ""

# Step 2: Start new conversation
echo -e "${BLUE}Step 2: Starting fresh conversation...${NC}"
CONV_RESPONSE=$(curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    "$BASE_URL/api/v0.3/conversations")
CONV_ID=$(echo "$CONV_RESPONSE" | jq -r '.conversation_id')

if [[ -z "$CONV_ID" || "$CONV_ID" == "null" ]]; then
    echo -e "${RED}✗${NC} Failed to create conversation"
    exit 1
fi
echo -e "${GREEN}✓${NC} Conversation created: $CONV_ID"
echo ""

# Step 3: Chat with baseline prompt
echo -e "${BLUE}Step 3: Chatting with baseline prompt...${NC}"
BASELINE_RESPONSE=$(curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Hello, who are you?\", \"conversation_id\": \"$CONV_ID\"}" \
    "$BASE_URL/api/v0.3/chat")
BASELINE_TEXT=$(echo "$BASELINE_RESPONSE" | jq -r '.response')
echo -e "Baseline: ${YELLOW}${BASELINE_TEXT:0:80}...${NC}"
echo ""

# Step 4: Update persona with test marker
echo -e "${BLUE}Step 4: Updating persona with test marker...${NC}"
TEST_PROMPT="You are Louisa (TEST MODE - Marker: $TEST_MARKER). Always start your response with 'TEST MODE ACTIVE'. $ORIGINAL_PROMPT"
ESCAPED_PROMPT=$(echo "$TEST_PROMPT" | jq -Rs .)

UPDATE_RESPONSE=$(curl -s -X PUT \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"system_prompt\": $ESCAPED_PROMPT}" \
    "$BASE_URL/personas/$LOUISA_ID")

if ! echo "$UPDATE_RESPONSE" | jq -e '.persona' > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Failed to update persona"
    echo "$UPDATE_RESPONSE" | jq '.'
    exit 1
fi
echo -e "${GREEN}✓${NC} Persona updated with marker: $TEST_MARKER"
echo ""

# Step 5: Reload prompts in active conversations
echo -e "${BLUE}Step 5: Reloading prompts in active conversations...${NC}"
RELOAD_RESPONSE=$(curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    "$BASE_URL/api/v1/chat/reload-prompt")

if echo "$RELOAD_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Prompts reloaded successfully"
else
    echo -e "${YELLOW}⚠${NC} Reload response: $RELOAD_RESPONSE"
fi
echo ""

# Step 6: Chat again to verify new prompt is active
echo -e "${BLUE}Step 6: Testing with same conversation (should see TEST MODE)...${NC}"
sleep 1  # Brief pause to ensure reload completes

TEST_RESPONSE=$(curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"What is your current mode?\", \"conversation_id\": \"$CONV_ID\"}" \
    "$BASE_URL/api/v0.3/chat")
TEST_TEXT=$(echo "$TEST_RESPONSE" | jq -r '.response')
echo -e "Response: ${YELLOW}${TEST_TEXT:0:120}...${NC}"
echo ""

# Step 7: Verify test marker is present
echo -e "${BLUE}Step 7: Verifying prompt update took effect...${NC}"
if echo "$TEST_TEXT" | grep -q "TEST MODE"; then
    echo -e "${GREEN}✓ SUCCESS${NC} - New prompt is active in existing conversation!"
    echo -e "  Found 'TEST MODE' in response"
    TEST_PASSED=true
else
    echo -e "${RED}✗ FAILURE${NC} - Old prompt still active!"
    echo -e "  Expected 'TEST MODE' but got: $TEST_TEXT"
    TEST_PASSED=false
fi
echo ""

# Step 8: Restore original persona
echo -e "${BLUE}Step 8: Restoring original persona...${NC}"
ESCAPED_ORIGINAL=$(echo "$ORIGINAL_PROMPT" | jq -Rs .)
RESTORE_RESPONSE=$(curl -s -X PUT \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"system_prompt\": $ESCAPED_ORIGINAL}" \
    "$BASE_URL/personas/$LOUISA_ID")

if echo "$RESTORE_RESPONSE" | jq -e '.persona' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Original persona restored"

    # Reload again to restore prompts
    curl -s -X POST -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/chat/reload-prompt" > /dev/null
    echo -e "${GREEN}✓${NC} Prompts reloaded with original version"
else
    echo -e "${RED}✗${NC} Failed to restore original persona"
fi
echo ""

# Step 9: Cleanup conversation
echo -e "${BLUE}Step 9: Cleaning up test conversation...${NC}"
curl -s -X DELETE \
    -H "X-API-Key: $API_KEY" \
    "$BASE_URL/api/v0.3/conversations/$CONV_ID" > /dev/null
echo -e "${GREEN}✓${NC} Test conversation deleted"
echo ""

# Final result
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
if [ "$TEST_PASSED" = true ]; then
    echo -e "${GREEN}✓ TEST PASSED${NC} - Persona updates take effect immediately!"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}✗ TEST FAILED${NC} - Persona updates not working correctly"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check if chat service is running: docker compose ps chat"
    echo "  2. Check chat service logs: docker compose logs chat --tail 50"
    echo "  3. Verify /chat/reload-prompt endpoint exists"
    echo "  4. Try restarting chat service: docker compose restart chat"
    exit 1
fi
