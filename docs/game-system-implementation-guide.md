# Game System Implementation Guide

## Quick Start: Running Games from Documentation

This guide explains how to implement and extend the game system where markdown documentation directly executes as game logic through the KB Agent.

**🚀 Want to test immediately?** See the [Game POC Practical Testing Guide](game-poc-testing-guide.md) for working command-line examples that demonstrate the revolutionary executable documentation pattern.

## Table of Contents

1. [System Components](#system-components)
2. [Creating a New Game](#creating-a-new-game)
3. [Game State Management](#game-state-management)
4. [KB Agent Integration](#kb-agent-integration)
5. [Testing Your Game](#testing-your-game)
6. [Debugging](#debugging)
7. [Performance Optimization](#performance-optimization)

## System Components

### Core Files

```
app/services/chat/
├── game_state_handler.py    # Manages game state in messages
├── unified_chat.py           # Enhanced with game detection
└── kb_tools.py              # KB Agent interface

app/services/kb/
├── kb_agent.py              # Interprets markdown as game logic
└── agent_endpoints.py       # HTTP endpoints for agent

/kb/experiences/              # Game documentation files
├── rock-paper-scissors/     # Simple game example
├── west-of-house/           # Zork-like adventure
└── your-game/              # Your new game here
```

### Data Flow

```
1. User Input: "go north"
        ↓
2. Chat Service: Detects game command
        ↓
3. Game Handler: Extracts previous state
        ↓
4. KB Agent: Reads markdown rules
        ↓
5. Game Logic: Executes from documentation
        ↓
6. Response: Narrative + embedded state
```

## Creating a New Game

### Step 1: Design Your Game Structure

Create a folder in `/kb/experiences/your-game-name/`:

```
/kb/experiences/space-adventure/
├── +game.md                 # Master index
├── GAME.md                  # Game overview
├── world/
│   ├── +world.md           # World index
│   ├── rooms/
│   │   ├── +rooms.md       # Room index
│   │   ├── bridge.md       # Starting location
│   │   ├── engine-room.md
│   │   └── cargo-bay.md
│   ├── items/
│   │   ├── +items.md
│   │   ├── keycard.md
│   │   └── spacesuit.md
│   └── characters/
│       ├── +characters.md
│       └── ai-companion.md
├── mechanics/
│   ├── +mechanics.md
│   ├── movement.md         # How movement works
│   ├── inventory.md        # Item management
│   └── oxygen.md          # Special mechanics
└── rules/
    ├── +rules.md
    └── win-conditions.md
```

### Step 2: Write Room Documentation

**`world/rooms/bridge.md`:**
```markdown
# Ship's Bridge

> **Room ID**: bridge
> **Atmosphere**: Pressurized
> **Exits**: south (corridor), east (captain_quarters)
> **Lighting**: Emergency power only

## Description
You are on the bridge of the spacecraft. Through the main viewscreen, you can see the infinite expanse of space. Most consoles are dark, running on emergency power. The captain's chair sits empty in the center.

## Items Present
- [[items/keycard]] - Captain's keycard on the chair
- navigation_console - Main ship controls (unpowered)

## Characters
- [[characters/ai-companion]] - Ship's AI (audio only)

## Valid Actions
- "take keycard" → Add keycard to inventory, +10 points
- "examine console" → "The console requires main power to operate"
- "go south" → Move to [[rooms/corridor]]
- "talk to ai" → Initiate dialogue with ship's AI

## State Changes
- If power_restored == true: Console becomes operational
- If has_keycard == true: Can access captain_quarters
```

### Step 3: Define Game Mechanics

**`mechanics/oxygen.md`:**
```markdown
# Oxygen System

## Resource Management
- Starting oxygen: 100 units
- Consumption rate: 1 unit per move
- Warning at: 20 units
- Fatal at: 0 units

## Replenishment
- Oxygen tanks restore 50 units
- Pressurized rooms: No consumption
- Spacewalk: 3 units per move

## Warning Messages
- 20 units: "Your oxygen is running low!"
- 10 units: "Critical oxygen level! Find air immediately!"
- 5 units: "Vision starting to blur..."
- 0 units: "You have suffocated." [GAME OVER]
```

### Step 4: Create Initial State Template

**`state/initial-state.json`:**
```json
{
  "game": "space_adventure",
  "room": "bridge",
  "inventory": [],
  "score": 0,
  "moves": 0,
  "oxygen": 100,
  "flags": {
    "power_restored": false,
    "has_spacesuit": false,
    "ai_trust_level": 0
  }
}
```

## Game State Management

### State Embedding Format

States are embedded in assistant messages using JSON blocks:

```markdown
You take the captain's keycard. It might grant access to restricted areas.

```json:game_state
{
  "game": "space_adventure",
  "room": "bridge",
  "inventory": ["keycard"],
  "score": 10,
  "moves": 1,
  "oxygen": 99,
  "flags": {
    "has_keycard": true
  }
}
```
```

### State Extraction

```python
from app.services.chat.game_state_handler import game_state_handler

# Extract from conversation history
messages = conversation_store.get_messages(conversation_id)
current_state = game_state_handler.extract_game_state(messages)

# Returns most recent state or None
if current_state:
    room = current_state["room"]
    inventory = current_state["inventory"]
```

### State Updates

```python
# Parse KB Agent response for state changes
kb_response = "You enter the engine room. The reactor hums with power."
new_state = game_state_handler.parse_kb_response_for_state(
    kb_response,
    current_state
)

# Detected room change: bridge → engine_room
# Increment moves counter
# Decrease oxygen if applicable
```

## KB Agent Integration

### Formatting Game Queries

The system automatically formats user commands for the KB Agent:

```python
# User says: "use keycard on door"
# Current state: {"room": "corridor", "inventory": ["keycard"]}

formatted_query = """
In Space Adventure game, the player is in 'corridor' with inventory: ['keycard'].
Execute command: use keycard on door
Check mechanics/inventory.md for item usage rules.
Apply any state changes based on success/failure.
"""
```

### KB Agent Execution

The KB Agent receives the formatted query and:

1. Loads relevant markdown files
2. Interprets the rules
3. Executes the logic
4. Returns narrative response

```python
# KB Agent response structure
{
  "interpretation": "Using keycard on locked door...",
  "narrative": "You slide the keycard through the reader. The door hisses open.",
  "state_changes": {
    "room": "captain_quarters",
    "flags.door_unlocked": true
  }
}
```

## Testing Your Game

### Unit Testing

Create `tests/test_space_adventure.py`:

```python
def test_initial_state():
    """Test game initialization."""
    state = create_initial_state("space_adventure")
    assert state["room"] == "bridge"
    assert state["oxygen"] == 100
    assert len(state["inventory"]) == 0

def test_oxygen_depletion():
    """Test oxygen mechanics."""
    state = {"oxygen": 100, "room": "bridge"}

    # Move to unpressurized area
    state["room"] = "spacewalk"
    state["oxygen"] -= 3  # Spacewalk consumption

    assert state["oxygen"] == 97

def test_keycard_pickup():
    """Test item interaction."""
    response = process_command("take keycard", current_state)
    assert "keycard" in response["new_state"]["inventory"]
    assert response["new_state"]["score"] == 10
```

### Integration Testing

Test with the live system using the **working CLI client commands**:

```bash
# Start a new game (server creates conversation ID automatically)
python3 scripts/gaia_client.py --env local --batch "Start space adventure game. Show starting location and embed game state as JSON block."

# Get the conversation ID from logs
CONV_ID=$(docker compose logs chat-service | grep "Created conversation" | tail -1 | grep -o '[a-f0-9-]\{36\}')
echo "Conversation ID: $CONV_ID"

# Continue with game commands using the conversation ID
python3 scripts/gaia_client.py --env local --conversation $CONV_ID --batch "take keycard"

# Test another action
python3 scripts/gaia_client.py --env local --conversation $CONV_ID --batch "examine keycard"
```

**Alternative: Direct API Testing** (if you need curl):
```bash
# Start a new game - correct endpoint path
curl -X POST http://localhost:8666/api/v0.3/chat \
  -H "X-API-Key: gaia-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "play space adventure",
    "stream": false
  }'

# Note: Extract conversation_id from response and use UUID format for subsequent calls
```

### Manual Testing Checklist

- [ ] Game initializes with correct starting state
- [ ] Movement between rooms works
- [ ] Items can be picked up and used
- [ ] Special mechanics (oxygen) function correctly
- [ ] Win/lose conditions trigger appropriately
- [ ] State persists across commands
- [ ] Invalid commands handled gracefully

## Debugging

### Enable Debug Logging

```python
# In game_state_handler.py
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Logs will show:
# - Command parsing results
# - State extraction attempts
# - KB query formatting
# - State change detection
```

### Common Issues and Solutions

#### State Not Persisting

**Problem**: Game resets on each command
**Solution**: Ensure conversation_id is provided
```python
# ✗ Wrong
{"message": "go north"}

# ✓ Correct
{"message": "go north", "conversation_id": "conv-123"}
```

#### Commands Not Recognized

**Problem**: "go north" treated as chat, not game command
**Solution**: Check command parsing patterns
```python
# Add to parse_game_command()
if "north" in input_lower:
    return ("move", {"direction": "north"})
```

#### KB Agent Not Finding Rules

**Problem**: KB Agent returns generic response
**Solution**: Verify markdown file paths
```bash
# Check if files exist
docker exec gaia-kb-service-1 ls -la /kb/experiences/your-game/
```

#### State Extraction Fails

**Problem**: Can't find previous state
**Solution**: Check JSON block format
```python
# Must match this pattern exactly
pattern = r'```json:game_state\s*\n(.*?)\n```'
```

### Debugging Tools

```python
# Debug script: scripts/debug_game_state.py

def debug_conversation(conversation_id):
    """Debug tool for game state issues."""

    # 1. Load conversation
    messages = conversation_store.get_messages(conversation_id)
    print(f"Total messages: {len(messages)}")

    # 2. Find game states
    states = []
    for msg in messages:
        if msg["role"] == "assistant":
            state = extract_game_state(msg["content"])
            if state:
                states.append(state)

    print(f"Found {len(states)} game states")

    # 3. Show state evolution
    for i, state in enumerate(states):
        print(f"\nState {i}:")
        print(f"  Room: {state.get('room')}")
        print(f"  Inventory: {state.get('inventory')}")
        print(f"  Score: {state.get('score')}")

    return states
```

## Performance Optimization

### Current Performance

- Command processing: ~2-3 seconds
- State extraction: ~100ms for 10 messages
- KB Agent query: ~1-2 seconds
- Response formatting: ~50ms

### Optimization Strategies

#### 1. Cache Recent State

```python
# Add to game_state_handler.py
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_state(conversation_id: str) -> dict:
    """Cache recent game states."""
    messages = conversation_store.get_messages(conversation_id)
    return extract_game_state(messages)
```

#### 2. Reduce KB Queries

```python
# Batch related files
context_paths = [
    "/experiences/game/rooms/current-room.md",
    "/experiences/game/mechanics/",
    "/experiences/game/rules/"
]
# Load all at once instead of multiple queries
```

#### 3. Progressive Response

```python
# Stream responses as they generate
async def stream_game_response():
    yield {"type": "thinking", "content": "Processing command..."}
    yield {"type": "narrative", "content": "You move north..."}
    yield {"type": "state", "content": new_state}
```

### Future Optimizations

#### Phase 1: Redis Caching (1 day)
```python
# Cache game states in Redis
redis_client.setex(
    f"game_state:{conversation_id}",
    ttl=3600,
    value=json.dumps(state)
)
```

#### Phase 2: Dedicated State Service (1 week)
```python
# Separate service for game state
class GameStateService:
    async def get_state(self, session_id: str) -> dict
    async def update_state(self, session_id: str, changes: dict)
    async def list_sessions(self, user_id: str) -> list
```

#### Phase 3: Real-time Multiplayer (2 weeks)
```python
# WebSocket for live updates
@websocket("/game/{session_id}")
async def game_session(websocket, session_id):
    async for command in websocket:
        state = await process_command(command)
        await broadcast_state(session_id, state)
```

## Best Practices

### 1. Markdown Organization

- Use `+index.md` files for navigation
- Keep files under 200 lines
- Use consistent formatting
- Cross-reference with `[[links]]`

### 2. State Design

- Keep state flat when possible
- Use flags for boolean conditions
- Version your state schema
- Include last_updated timestamp

### 3. Error Handling

```python
try:
    state = extract_game_state(messages)
except Exception as e:
    logger.error(f"State extraction failed: {e}")
    # Fall back to initial state
    state = create_initial_state(game_type)
```

### 4. Testing

- Test each command in isolation
- Verify state transitions
- Check edge cases (empty inventory, zero oxygen)
- Test invalid commands

### 5. Documentation

- Document special mechanics clearly
- Provide examples in markdown
- Include state change rules
- Note any dependencies

## Extending the System

### Adding New Mechanics

1. Create mechanics markdown file
2. Update state schema if needed
3. Add parsing logic to game_state_handler
4. Test with sample commands

### Supporting Multiple Games

```python
# Detect game type from conversation
def detect_game_type(message: str) -> str:
    if "zork" in message.lower():
        return "zork"
    elif "space" in message.lower():
        return "space_adventure"
    return "unknown"
```

### Custom State Formats

```python
# Override state format for specific games
class SpaceGameHandler(GameStateHandler):
    def format_state(self, state: dict) -> dict:
        # Add oxygen to status bar
        state["status_bar"] = f"O₂: {state['oxygen']}%"
        return state
```

## Conclusion

This game system proves that complex interactive experiences can run directly from documentation. By following this guide, you can:

1. Create new games using only markdown
2. Leverage existing chat infrastructure
3. Ship games in hours, not months
4. Enable non-programmers to design games

The future of game development is writing documentation that plays itself. Welcome to the revolution!