# Chat Integration Complete

## Overview

The markdown command system is now fully integrated with the chat service, enabling complete game experiences through conversational AI.

## What Works

### ✅ Experience Selection
- Users can select experiences via natural language: "I want to play west-of-house"
- Mid-conversation switching supported: Switch from one experience to another anytime
- Proper welcome messages with experience descriptions

### ✅ Command Execution
- All markdown commands work via chat: look, go, collect, inventory, talk
- Both directional movement (north/south/east/west) and sublocation navigation (go to counter)
- NPC conversations via natural language (talk to Louisa)
- Admin commands via @ prefix (@list waypoints, @inspect item 1)
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
# Complete test including sublocation navigation and NPC interaction
1. Select experience: "I want to play wylding-woods" ✅
2. Go to counter: Sublocation movement works ✅
3. Take dream bottle: Item collection works ✅
4. Go to back room: Multiple sublocation navigation ✅
5. Take fairy dust: Multiple items in inventory ✅
6. Check inventory: State persistence confirmed ✅
7. Talk to Louisa: NPC conversation with trust system ✅
8. Ask Louisa about dreams: Quest offered ✅
```

### Admin Commands Workflow
```bash
# Admin commands work through chat with @ prefix
1. List waypoints: "@list waypoints" ✅
2. Inspect waypoint: "@inspect waypoint 4" ✅
3. List items: "@list items" ✅
4. Instant response: <30ms (no LLM) ✅
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

Commands are automatically discovered from markdown files in **two directories**:

```python
async def _discover_available_commands(experience: str) -> tuple[dict, dict]:
    """Scan both game-logic/ and admin-logic/ directories and parse frontmatter"""
    # Discovers player commands: look, collect, inventory, go, talk, etc.
    # Discovers admin commands: @list-waypoints, @inspect-item, etc.
    # Returns: (command_mappings, admin_required_dict)
```

**Benefits**:
- Add new commands by creating `.md` files (no code changes)
- Different experiences can have different command sets
- Single source of truth in markdown files
- Admin commands automatically separated via @ prefix

**Directory Structure**:
```
/kb/experiences/{exp}/
├── game-logic/      # Player commands (look, go, collect, talk)
└── admin-logic/     # Admin commands (@list, @inspect, @edit)
```

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

## Available Command Types

### Player Commands (game-logic/)
1. **look** - Observe surroundings and items
2. **go** - Navigate between locations/sublocations
3. **collect** - Pick up items from location
4. **inventory** - View items in player inventory
5. **talk** - Engage in natural conversation with NPCs (with trust system)

### Admin Commands (admin-logic/)
1. **@list-waypoints** - List all GPS waypoints (instant, no LLM)
2. **@inspect-waypoint** - View detailed waypoint info
3. **@edit-waypoint** - Modify waypoint properties
4. **@create-waypoint** - Create new waypoint
5. **@delete-waypoint** - Delete waypoint (requires CONFIRM)
6. **@list-items** - List all item instances
7. **@inspect-item** - View detailed item info

**See Documentation:**
- [Markdown Command System](./markdown-command-system.md) - Complete command architecture
- [Admin Command System](./admin-command-system.md) - Admin command reference
- [NPC Interaction System](./npc-interaction-system.md) - Talk command and NPC conversations

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

3. **Waypoint CRUD admin commands** (`e822600`)
   - Implemented @list, @inspect, @edit, @create, @delete for waypoints
   - Zero LLM latency (<30ms responses)
   - CONFIRM safety for destructive operations

4. **Item admin commands** (`205cebd`)
   - Implemented @list-items and @inspect-item
   - Admin command auto-discovery from admin-logic/

5. **NPC talk command** (`b8e05b6`)
   - Implemented natural language NPC conversations
   - Per-player state tracking (trust, history)
   - LLM-powered authentic dialogue
   - Quest integration foundation

## Next Steps (Future Enhancements)

### Additional Player Commands
- `drop.md` - Drop items from inventory
- `examine.md` - Detailed item inspection
- `use.md` - Use items in inventory
- `give.md` - Give items to NPCs

### Additional Admin Commands
- `@spawn` - Spawn instance from template
- `@reset` - Reset player progress or experience
- Batch operations (edit/delete multiple items)
- Import/export commands

### Performance
- Cache command discovery results per experience
- Invalidate cache on experience content updates

### Features
- Quest system integration (foundation complete with talk command)
- Multiplayer interactions in shared experiences
- Real-time AR waypoint integration
- GPS-based experience selection
- NPC-to-NPC conversations
- Dynamic NPC movement

## Testing Scripts

All test scripts in `/tmp/`:
- `test_game_master_chat.sh` - Basic chat with Game Master
- `test_complete_chat_workflow.sh` - Experience switching test
- `test_wylding_chat.sh` - Complete wylding-woods workflow
