# Chat-Based Game Testing Guide

## Overview

This guide provides comprehensive testing procedures for the GAIA markdown command system integrated with the chat service. Use this when validating chat integration after code changes, new features, or debugging issues.

## Prerequisites

### Service Health Check

```bash
# Verify all services are running
curl -s http://localhost:8666/health | jq

# Expected output:
{
  "status": "healthy",
  "services": {
    "auth": "healthy",
    "chat": "healthy",
    "kb": "healthy",
    "asset": "healthy"
  }
}
```

### Test Environment Setup

```bash
# Set required environment variables
export API_KEY="hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
export GATEWAY_URL="http://localhost:8666"
export GAME_MASTER_ID="7b197909-8837-4ed5-a67a-a05c90e817f1"
```

**Important**: Always use the **Game Master** persona (not Mu or other personas) for game testing.

## Test Suite 1: Experience Selection

### Test 1.1: Initial Experience Selection

**Purpose**: Verify users can select an experience via natural language

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "I want to play west-of-house",
    "stream": false,
    "persona_id": "'$GAME_MASTER_ID'"
  }' | jq -r '.response, .conversation_id'
```

**✅ Pass Criteria**:
- Response includes "West of House" or experience name
- Returns valid conversation_id (UUID format)
- Welcome message with experience description
- No error messages about missing experience

**❌ Failure Indicators**:
- "I couldn't find a game called..."
- No conversation_id returned
- Tool calls visible in response (should be hidden)
- Response is conversational without game content

**Debug Steps if Failed**:
```bash
# Check if Game Master persona is correct
echo $GAME_MASTER_ID
# Should be: 7b197909-8837-4ed5-a67a-a05c90e817f1

# Check chat service logs
docker logs gaia-chat-service-1 2>&1 | grep "interact_with_experience" | tail -10

# Check KB service response
docker logs gaia-kb-service-1 2>&1 | grep "Detected experience selection" | tail -5
```

### Test 1.2: Mid-Conversation Experience Switch

**Purpose**: Verify users can switch between experiences without starting new conversation

```bash
# Save conversation_id from Test 1.1, then:
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "I want to play wylding-woods",
    "stream": false,
    "conversation_id": "<CONV_ID_FROM_TEST_1>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Response mentions "Wylding Woods" or "Woander"
- Welcome message for new experience
- No references to previous experience (white house)
- Same conversation_id maintained

**❌ Failure Indicators**:
- Still shows west-of-house content
- "I don't understand 'play wylding-woods'" (command detection issue)
- Error about "go" command failing
- Player still at white house location

**Debug Steps if Failed**:
```bash
# Check if experience selection is being detected
docker logs gaia-kb-service-1 2>&1 | grep "I want to play wylding-woods" -A 5

# Should NOT see:
# "Detected command type: go"

# Should see:
# "Detected experience selection: 'wylding-woods'"
```

**Known Issue**: If you see "Detected command type: go" instead of experience selection, the fix in commit `3f54de9` may not be applied. The system is treating "play X" as a movement command instead of experience selection.

## Test Suite 2: Command Execution

### Test 2.1: Look Command

**Purpose**: Verify observation command works

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "look around",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Describes current location
- Lists visible items with descriptions
- Shows NPCs if present
- Shows available exits or sublocations
- No "I don't understand" messages

**Example Expected Output** (wylding-woods at entrance):
```
You are at the entrance to Woander's mystical shop...

You see:
- A glowing sign that reads 'Welcome to Woander's...'

You can explore other areas: counter, back_room
```

### Test 2.2: Directional Movement (west-of-house)

**Purpose**: Verify north/south/east/west navigation

```bash
# Start at west-of-house
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "go north",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Movement narrative ("You head north...")
- New location description
- Verify with "look around" - shows "North of House"
- Available exits updated

**Test Variations**:
- "go north" / "head north" / "north" (all should work)
- Try all four directions: north, south, east, west
- Test invalid direction: "go up" should fail gracefully

### Test 2.3: Sublocation Movement (wylding-woods)

**Purpose**: Verify named sublocation navigation

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "go to counter",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Movement narrative
- Shows "Shop Counter" or "counter" in description
- Lists dream bottles (adventurous, joyful, peaceful)
- Shows Woander NPC
- Can explore other areas: entrance, back_room

**Test Variations**:
- "go to counter" / "move to counter" / "enter counter"
- Test all sublocations: entrance, counter, back_room
- "go to entrance" then "go to back room" (multi-hop)

### Test 2.4: Item Collection

**Purpose**: Verify item collection and state updates

```bash
# At counter with dream bottles visible
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "take joyful dream bottle",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Success message: "You take the joyful dream bottle"
- Item removed from location (verify with look)
- Item appears in inventory (verify with inventory command)
- Other items remain (adventurous, peaceful still at counter)

**Verification Sequence**:
```bash
# 1. Take item
# 2. Look around - item should be gone
# 3. Check inventory - item should be there
```

**Test Variations**:
- "take joyful dream bottle" / "pick up joyful dream bottle" / "get joyful dream bottle"
- Try taking item not at location: "take telescope" (should fail gracefully)
- Try taking item already in inventory (should say already have it)

### Test 2.5: Inventory Check

**Purpose**: Verify inventory display

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "inventory",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Lists all collected items with descriptions
- Shows item count: "Inventory: X items"
- Empty inventory: "You aren't carrying anything"
- No duplicate items

**Test Variations**:
- "inventory" / "inv" / "check inventory" / "what am I carrying"

## Test Suite 3: State Persistence

### Test 3.1: Cross-Request State

**Purpose**: Verify state persists across multiple commands

```bash
# Sequence test
1. "take joyful dream bottle"
2. "go to back room"
3. "look around"
4. "inventory"  # Should still have bottle

# Expected: Item stays in inventory across location changes
```

**✅ Pass Criteria**:
- Item remains in inventory after movement
- Location changes persist
- No state loss between requests
- Conversation context maintained

**Full Test Script**:
```bash
CONV_ID="<your_conv_id>"

# 1. Take item
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"take joyful dream bottle\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'

# 2. Move locations
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"go to back room\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'

# 3. Look around (verify location changed)
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"look around\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'

# 4. Check inventory (bottle should still be there)
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"inventory\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
```

### Test 3.2: Multiple Items

**Purpose**: Verify multiple items tracked correctly

```bash
# Sequence
1. "take peaceful dream bottle"
2. "go to back room"
3. "take fairy dust pouch"
4. "inventory"  # Should show both items
```

**✅ Pass Criteria**:
- All items appear in inventory
- Correct count shown (2 items)
- Items properly described
- No duplicate entries

## Test Suite 4: Error Handling

### Test 4.1: Invalid Command

**Purpose**: Verify graceful handling of unrecognized commands

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "fly to the moon",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- No server errors (500)
- User-friendly error message
- Suggests valid actions
- Conversation continues normally
- No crash or state corruption

**Example Expected Output**:
```
You can't fly to the moon from here. You're currently at...

You can explore other areas: entrance, counter, back_room
```

### Test 4.2: Invalid Item

**Purpose**: Verify item not found errors

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "take telescope",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Clear "item not found" message
- Suggests what items ARE available at location
- Doesn't break conversation flow

### Test 4.3: Invalid Direction

**Purpose**: Verify direction validation

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "go up",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Clear error about invalid direction
- Shows available directions/exits
- Doesn't crash service

## Test Suite 5: Natural Language Variations

### Test 5.1: Command Synonyms

**Purpose**: Verify natural language flexibility

**Test all variations**:

**Look variants**:
- "look around"
- "what do I see"
- "observe"
- "examine the area"

**Movement variants**:
- "go north"
- "head north"
- "walk north"
- "north"

**Collection variants**:
- "take lantern"
- "pick up lantern"
- "get lantern"
- "grab lantern"

**Inventory variants**:
- "inventory"
- "inv"
- "check inventory"
- "what am I carrying"
- "what do I have"

**✅ Pass Criteria**:
- All synonyms properly recognized
- Same behavior regardless of phrasing
- No "I don't understand" for valid synonyms

### Test 5.2: Multi-Word Items

**Purpose**: Verify handling of items with spaces in names

```bash
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "take peaceful dream bottle",
    "stream": false,
    "conversation_id": "<CONV_ID>"
  }' | jq -r '.response'
```

**✅ Pass Criteria**:
- Full name works: "peaceful dream bottle"
- Partial name works: "peaceful bottle"
- "the" is optional: "take the peaceful bottle" = "take peaceful bottle"
- Case insensitive: "Peaceful Dream Bottle" = "peaceful dream bottle"

## Test Suite 6: Experience-Specific Features

### Test 6.1: Isolated State Model (west-of-house)

**Purpose**: Verify each player has separate world state

**Requires**: Two different API keys or user accounts

```bash
# User A
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "X-API-Key: ${API_KEY_USER_A}" \
  -d '{"message":"take brass lantern", ...}'

# User B (different API key)
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "X-API-Key: ${API_KEY_USER_B}" \
  -d '{"message":"look around", ...}'
```

**✅ Pass Criteria**:
- User A's actions don't affect User B's world
- Brass lantern still visible to User B
- Items exist independently for each player
- Location changes independent

### Test 6.2: Shared State Model (wylding-woods)

**Purpose**: Verify all players see same world state

```bash
# User A
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "X-API-Key: ${API_KEY_USER_A}" \
  -d '{"message":"take peaceful dream bottle", ...}'

# User B (different API key)
curl -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "X-API-Key: ${API_KEY_USER_B}" \
  -d '{"message":"look around", ...}'
```

**✅ Pass Criteria**:
- User B does NOT see peaceful dream bottle at counter
- User A's action affected world for all users
- Items removed globally
- Shared locations visible to all

**Note**: Player-specific data (inventory, current location) is still separate - only world state is shared.

## Quick Regression Test Script

**Use after ANY changes to**:
- `experience_endpoints.py`
- `unified_state_manager.py`
- Command markdown files (*.md in game-logic/)
- Experience config files

```bash
#!/bin/bash
# Quick regression test for chat integration

API_KEY="hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
GATEWAY_URL="http://localhost:8666"
GAME_MASTER_ID="7b197909-8837-4ed5-a67a-a05c90e817f1"

echo "🧪 Chat Integration Regression Test"
echo ""

# Test 1: Experience selection
echo "Test 1: Experience Selection"
RESP=$(curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"I want to play wylding-woods\",\"stream\":false,\"persona_id\":\"$GAME_MASTER_ID\"}")

CONV_ID=$(echo "$RESP" | jq -r '.conversation_id')
echo "$RESP" | jq -r '.response' | grep -q "Wylding Woods" && echo "✅ PASS" || echo "❌ FAIL"
echo ""

# Test 2: Look command
echo "Test 2: Look Command"
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"look around\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | grep -q "Woander\|entrance" && echo "✅ PASS" || echo "❌ FAIL"
echo ""

# Test 3: Movement
echo "Test 3: Movement Command"
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"go to counter\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | grep -q "counter\|Counter" && echo "✅ PASS" || echo "❌ FAIL"
echo ""

# Test 4: Collection
echo "Test 4: Item Collection"
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"take adventurous dream bottle\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | grep -qi "take\|took\|picked" && echo "✅ PASS" || echo "❌ FAIL"
echo ""

# Test 5: State persistence
echo "Test 5: State Persistence"
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"inventory\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | grep -q "adventurous" && echo "✅ PASS" || echo "❌ FAIL"
echo ""

echo "✅ Regression test complete"
```

Save as `/tmp/test_chat_regression.sh` and run:
```bash
chmod +x /tmp/test_chat_regression.sh
./tmp/test_chat_regression.sh
```

## Complete Workflow Test Script

**Full end-to-end test** including experience switching:

```bash
#!/bin/bash
# Complete chat workflow test

API_KEY="hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
GATEWAY_URL="http://localhost:8666"
GAME_MASTER_ID="7b197909-8837-4ed5-a67a-a05c90e817f1"

echo "=== Complete Chat Workflow Test ==="
echo ""

# 1. Select west-of-house
echo "=== 1. Select West-of-House ==="
RESP=$(curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"I want to play west-of-house\",\"stream\":false,\"persona_id\":\"$GAME_MASTER_ID\"}")
echo "$RESP" | jq -r '.response'
CONV_ID=$(echo "$RESP" | jq -r '.conversation_id')
echo ""

# 2. Look around
echo "=== 2. Look Around (West-of-House) ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"look around\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 3. Go north
echo "=== 3. Go North ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"go north\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 4. Switch to wylding-woods
echo "=== 4. Switch to Wylding-Woods ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"I want to play wylding-woods\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 5. Look around in wylding-woods
echo "=== 5. Look Around (Wylding-Woods) ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"look around\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 6. Go to counter
echo "=== 6. Go to Counter ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"go to counter\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 7. Take dream bottle
echo "=== 7. Take Dream Bottle ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"take joyful dream bottle\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

# 8. Check inventory
echo "=== 8. Check Inventory ==="
curl -s -X POST "${GATEWAY_URL}/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"message\":\"inventory\",\"stream\":false,\"conversation_id\":\"$CONV_ID\"}" | jq -r '.response'
echo ""

echo "✅ Complete workflow test finished"
```

Save as `/tmp/test_complete_chat_workflow.sh`

## Common Issues and Debugging

### Issue 1: Experience Not Switching

**Symptom**: User says "I want to play X" but stays in current experience

**Check**:
```bash
# Look for experience selection detection in logs
docker logs gaia-kb-service-1 2>&1 | grep "Detected experience selection"

# Should see:
# INFO: Detected experience selection: 'west-of-house' from message 'I want to play west-of-house'
```

**If not seen**, check for command detection instead:
```bash
docker logs gaia-kb-service-1 2>&1 | grep "I want to play" -A 3

# BAD (bug):
# [DIAGNOSTIC] Starting command detection for: I want to play west-of-house
# [DIAGNOSTIC] Detected command type: go

# GOOD (working):
# INFO: Detected experience selection: 'west-of-house'
```

**Fix**: Ensure commit `3f54de9` (mid-conversation experience switching) is applied.

### Issue 2: Commands Not Recognized

**Symptom**: "I had trouble understanding that command" for valid commands

**Check command files exist**:
```bash
# In Docker container
docker exec gaia-kb-service-1 ls -la /kb/experiences/wylding-woods/game-logic/

# Should show:
# collect.md
# go.md
# inventory.md
# look.md
```

**Check command discovery**:
```bash
docker logs gaia-kb-service-1 2>&1 | grep "Discovered command" | tail -10

# Should see logs like:
# INFO: Discovered command 'go' with aliases: ['move', 'walk', 'travel']
```

**Fix**: Verify command files have correct frontmatter and are in game-logic/ directory.

### Issue 3: State Not Persisting

**Symptom**: Collected items disappear, location resets between requests

**Check state updates**:
```bash
docker logs gaia-kb-service-1 2>&1 | grep "MERGE\|APPLY\|state_updates" | tail -20

# Should see:
# [MERGE] Processing $append for key='inventory'
# [APPLY] Player update - path='player.inventory', operation='append'
```

**Check player view file**:
```bash
# Replace USER_ID with actual user ID
docker exec gaia-kb-service-1 cat /kb/players/<USER_ID>/wylding-woods/view.json | jq

# Should show current inventory and location
```

**Fix**: Verify `_merge_updates()` and `_apply_state_updates()` are working (commits `00f8208` and earlier fixes).

### Issue 4: Wrong Persona Being Used

**Symptom**: Chat gives conversational responses without calling game tools

**Check persona ID**:
```bash
echo $GAME_MASTER_ID
# Must be: 7b197909-8837-4ed5-a67a-a05c90e817f1

# Verify in database
docker exec gaia-db-1 psql -U postgres -d llm_platform \
  -c "SELECT id, name FROM personas WHERE id = '7b197909-8837-4ed5-a67a-a05c90e817f1';"
```

**Check chat logs**:
```bash
docker logs gaia-chat-service-1 2>&1 | grep "persona_id\|Tool call" | tail -20

# Should see tool calls to interact_with_experience
```

**Fix**: Always pass `persona_id` in first message of conversation.

### Issue 5: Tool Calls Visible in Response

**Symptom**: Response shows XML-like tool call syntax instead of clean game narrative

**Example bad output**:
```
<function_calls>
<invoke name="interact_with_experience">
...
</invoke>
</function_calls>
```

**This indicates**: Chat service isn't properly processing tool results

**Check**:
```bash
docker logs gaia-chat-service-1 2>&1 | grep "Tool result" | tail -10
```

**Fix**: Restart chat service or check for errors in tool result processing.

## Success Criteria

### All Tests Pass
- ✅ Experience selection (Test 1.1)
- ✅ Mid-conversation switching (Test 1.2)
- ✅ All 4 command types (look, go, collect, inventory)
- ✅ State persistence across requests
- ✅ Error handling graceful
- ✅ No server errors (500)

### Performance Targets
- Response time: < 3 seconds per command
- State persistence: 100% reliable
- Command recognition: > 95% for valid synonyms

### Ready for Production
- All 6 test suites pass
- Tests pass consistently (3 consecutive runs)
- Error messages are user-friendly
- Documentation is up to date
- No known critical bugs

## Test Reporting Template

When reporting test results, use this format:

```markdown
## Test Results - [Date]

**Environment**: Local / Dev / Staging
**Branch**: feature/unified-experience-system
**Commit**: [commit hash]

### Results Summary
- ✅ Test Suite 1: Experience Selection (2/2 pass)
- ✅ Test Suite 2: Command Execution (5/5 pass)
- ✅ Test Suite 3: State Persistence (2/2 pass)
- ⚠️ Test Suite 4: Error Handling (2/3 pass)
- ✅ Test Suite 5: Natural Language (2/2 pass)
- ✅ Test Suite 6: Experience Features (2/2 pass)

### Failed Tests
- Test 4.1: Invalid command handling
  - Expected: User-friendly error
  - Actual: "I don't understand" message too vague
  - Severity: Low
  - Fix: Update command detection error messages

### Notes
[Any additional observations]

### Next Steps
[What needs to be done]
```

## Related Documentation

- [Chat Integration Complete](../chat-integration-complete.md) - Integration status
- [Markdown Command System](../markdown-command-system.md) - Command creation guide
- [Unified State Model](../unified-state-model.md) - State management
- [Testing Best Practices](./TESTING_BEST_PRACTICES.md) - General testing guidelines
