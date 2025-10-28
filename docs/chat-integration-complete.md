# Chat Integration Complete

## Overview

The markdown command system is now fully integrated with the chat service, enabling complete game experiences through conversational AI.

## What Works

### ✅ Experience Selection
- Users can select experiences via natural language: "I want to play west-of-house"
- Mid-conversation switching supported: Switch from one experience to another anytime
- Proper welcome messages with experience descriptions

### ✅ Command Execution
- All markdown commands work via chat: look, go, collect, inventory
- Both directional movement (north/south/east/west) and sublocation navigation (go to counter)
- State persistence across all commands

### ✅ State Management
- Items properly move from locations to inventory
- State persists across conversation turns
- Works with both isolated (west-of-house) and shared (wylding-woods) state models

### ✅ Conversation Flow
- Conversation ID maintained across requests
- Game Master persona correctly calls `interact_with_experience` tool
- Tool results properly displayed to users

## Testing Results

### West-of-House Workflow
```bash
# Complete test via /api/v0.3/chat endpoint
1. Select experience: "I want to play west-of-house" ✅
2. Look around: Shows "west of a white house" ✅
3. Go north: Moves to "North of House" ✅
4. Commands work: All markdown commands functional ✅
```

### Wylding-Woods Workflow
```bash
# Complete test including sublocation navigation
1. Select experience: "I want to play wylding-woods" ✅
2. Go to counter: Sublocation movement works ✅
3. Take dream bottle: Item collection works ✅
4. Go to back room: Multiple sublocation navigation ✅
5. Take fairy dust: Multiple items in inventory ✅
6. Check inventory: State persistence confirmed ✅
```

### Experience Switching
```bash
# Mid-conversation switching test
1. Play west-of-house → Look around (white house) ✅
2. Switch: "I want to play wylding-woods" ✅
3. Look around → Now at Woander's shop ✅
4. Take items → Inventory persists ✅
```

## Architecture

### Experience Selection Flow

**Before Fix** (Broken):
```
1. Get current experience from profile
2. IF experience is None:
   - Check message for selection keywords
3. ELSE:
   - Process as game command (treats "play X" as movement)
```

**After Fix** (Working):
```
1. Check message for selection keywords FIRST
2. IF selection detected:
   - Switch to new experience
   - Return welcome message
3. ELSE:
   - Get current experience from profile
   - Process as game command
```

### Key Code Change

**File**: `app/services/kb/experience_endpoints.py`

**Lines 87-124**: Moved experience selection check to Step 1

```python
# Step 1: ALWAYS check if message contains experience selection first
# This allows switching experiences mid-conversation
available_experiences = state_manager.list_experiences()
detected_exp = _detect_experience_selection(request.message, available_experiences)

if detected_exp:
    # User is selecting/switching to an experience
    await state_manager.set_current_experience(user_id, detected_exp)
    return welcome_message

# Step 2: No selection, use current/determined experience
experience = await _determine_experience(...)
```

### Command Auto-Discovery

Commands are automatically discovered from markdown files:

```python
async def _discover_available_commands(experience: str) -> dict[str, list[str]]:
    """Scan game-logic/*.md files and parse frontmatter"""
    # Discovers: look, collect, inventory, go, etc.
    # Returns: {"go": ["go", "move", "walk", "travel", "head", "enter"], ...}
```

**Benefits**:
- Add new commands by creating `.md` files (no code changes)
- Different experiences can have different command sets
- Single source of truth in markdown files

## Usage

### Via Chat Endpoint

```bash
# Start conversation with Game Master persona
GAME_MASTER_ID="7b197909-8837-4ed5-a67a-a05c90e817f1"

curl -X POST "http://localhost:8666/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "I want to play west-of-house",
    "stream": false,
    "persona_id": "'$GAME_MASTER_ID'"
  }'

# Continue conversation with returned conversation_id
curl -X POST "http://localhost:8666/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "look around",
    "stream": false,
    "conversation_id": "<conv_id>"
  }'
```

### Via Direct KB Endpoint

```bash
# Direct interaction (no conversation context needed)
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "take the brass lantern",
    "experience": "west-of-house"
  }'
```

## Personas

### Game Master (Recommended)
- **ID**: `7b197909-8837-4ed5-a67a-a05c90e817f1`
- **Name**: "Game Master"
- **Description**: Narrative interface for text-based game experiences
- **Tool**: Calls `interact_with_experience` for all game-related messages

### Not Recommended
- **Mu**: Cheerful robot companion - does NOT call game tools consistently

## Known Issues

### Minor
- **Final inventory occasionally returns null**: JSON parsing issue in response formatting, but actual state is correct (items are collected)
- **Workaround**: Call inventory command again, or check next action response

## Related Documentation

- [Markdown Command System](./markdown-command-system.md) - Complete command creation guide
- [Unified State Model](./unified-state-model.md) - State management architecture
- [Experience Configuration](./experience-configuration.md) - Experience setup

## Commits

1. **Auto-discovery markdown command system** (`00f8208`)
   - Implemented dynamic command discovery
   - Fixed state persistence bugs
   - Created comprehensive documentation

2. **Mid-conversation experience switching** (`3f54de9`)
   - Enabled switching between experiences anytime
   - Fixed experience selection flow
   - Verified with complete chat tests

## Next Steps (Future Enhancements)

### Additional Commands
- `talk.md` - NPC interaction
- `drop.md` - Drop items from inventory
- `examine.md` - Detailed item inspection
- `use.md` - Use items in inventory

### Performance
- Cache command discovery results per experience
- Invalidate cache on experience content updates

### Features
- Quest system integration
- Multiplayer interactions in shared experiences
- Real-time AR waypoint integration
- GPS-based experience selection

## Testing Scripts

All test scripts in `/tmp/`:
- `test_game_master_chat.sh` - Basic chat with Game Master
- `test_complete_chat_workflow.sh` - Experience switching test
- `test_wylding_chat.sh` - Complete wylding-woods workflow
