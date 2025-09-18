# Game State Management via JSON Blocks (Option 3)

## Overview

This document describes the revolutionary "JSON blocks" approach to game state management in the GAIA platform, where game state is embedded directly within conversation messages rather than stored in separate databases or cache systems.

**Key Innovation**: The conversation IS the game session - no separate state infrastructure needed.

## Table of Contents

1. [Core Concept](#core-concept)
2. [JSON Block Format](#json-block-format)
3. [Implementation Architecture](#implementation-architecture)
4. [State Flow Lifecycle](#state-flow-lifecycle)
5. [Benefits & Trade-offs](#benefits--trade-offs)
6. [Usage Examples](#usage-examples)
7. [Future Enhancements](#future-enhancements)

## Core Concept

Traditional game architectures separate narrative from state:
```
Narrative Layer → "You move north"
State Layer → UPDATE player SET room='forest' WHERE id=123
```

Our approach combines them:
```markdown
You move north into the forest.

```json:game_state
{"room": "forest", "inventory": ["lamp"], "score": 10}
```
```

The game state travels WITH the narrative in the same message, stored in PostgreSQL's conversation history.

## JSON Block Format

### Basic Structure

JSON blocks are embedded in assistant messages using markdown code blocks with a special tag:

````markdown
```json:game_state
{
  "game": "zork",
  "room": "west_of_house",
  "inventory": ["lamp", "sword"],
  "score": 10,
  "moves": 5,
  "last_updated": "2024-11-28T12:30:45Z"
}
```
````

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `game` | string | Yes | Game identifier (e.g., "zork", "rock_paper_scissors") |
| `room` | string | Yes* | Current location in game world |
| `inventory` | array | Yes* | Items player is carrying |
| `score` | number | Yes | Player's current points |
| `moves` | number | Yes | Total commands executed |
| `last_updated` | ISO 8601 | Yes | Timestamp of last state change |

*Required for adventure games, optional for others

### Game-Specific Variations

#### Text Adventure (Zork-style)
```json
{
  "game": "zork",
  "room": "cellar",
  "inventory": ["lamp", "sword"],
  "score": 25,
  "moves": 12,
  "flags": {
    "lamp_lit": true,
    "mailbox_opened": true,
    "grue_warning_given": false
  }
}
```

#### Simple Games (Rock Paper Scissors)
```json
{
  "game": "rock_paper_scissors",
  "player_score": 2,
  "ai_score": 1,
  "rounds_played": 3,
  "last_player_choice": "rock",
  "last_ai_choice": "scissors"
}
```

## Implementation Architecture

### Component Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Chat Service   │────▶│ Game State       │────▶│  KB Agent   │
│                 │     │ Handler          │     │             │
│ - Receives cmd  │     │ - Parse command  │     │ - Read game │
│ - Routes to KB  │     │ - Extract state  │     │   rules     │
│                 │     │ - Format query   │     │ - Execute   │
└─────────────────┘     └──────────────────┘     └─────────────┘
         ▲                       │                      │
         │                       ▼                      ▼
         │              ┌──────────────────┐    ┌─────────────┐
         │              │ PostgreSQL       │    │ KB Files    │
         └──────────────│ Conversations    │    │ (Markdown)  │
                        │                  │    └─────────────┘
                        │ - Messages with  │
                        │   embedded JSON  │
                        └──────────────────┘
```

### Key Components

1. **GameStateHandler** (`app/services/chat/game_state_handler.py`)
   - Parses game commands from natural language
   - Extracts state from conversation history
   - Embeds state in response messages
   - Formats queries for KB Agent

2. **Chat Service Integration** (`unified_chat.py`)
   - Detects game-related KB tool calls
   - Retrieves conversation history
   - Applies state transformations

3. **KB Agent** (existing)
   - Interprets game rules from markdown
   - Executes game logic
   - Returns narrative responses

## State Flow Lifecycle

### 1. Game Initialization

```python
# User: "play zork"
          ↓
# System creates initial state
{
  "game": "zork",
  "room": "west_of_house",
  "inventory": [],
  "score": 0,
  "moves": 0
}
          ↓
# Embedded in welcome message
"Welcome to Zork! You are west of a white house...
```json:game_state
{...}
```"
```

### 2. Command Processing

```python
# User: "go north"
          ↓
# Extract previous state from conversation
previous_state = {"room": "west_of_house", ...}
          ↓
# Format KB query with context
"In Zork, from room 'west_of_house', move north"
          ↓
# KB Agent processes
"You are now in the forest..."
          ↓
# Parse response for state changes
new_state = {"room": "forest", ...}
          ↓
# Embed in response
"You move north. [narrative]
```json:game_state
{new_state}
```"
```

### 3. State Persistence

Every message is automatically saved to PostgreSQL:
```sql
-- Conversation messages table
INSERT INTO messages (conversation_id, role, content)
VALUES ('conv-123', 'assistant', 'You move north...
```json:game_state
{"room": "forest", ...}
```');
```

### 4. State Recovery

When continuing a conversation:
```python
# Load conversation history
messages = conversation_store.get_messages(conversation_id)
          ↓
# Extract most recent game state
for message in reversed(messages):
    if "```json:game_state" in message.content:
        return extract_json_block(message.content)
```

## Benefits & Trade-offs

### Benefits ✅

1. **Zero Infrastructure**
   - No Redis needed
   - No state database required
   - No session management service

2. **Perfect Audit Trail**
   - Every state change is recorded
   - Complete game history preserved
   - Easy debugging and replay

3. **Human Readable**
   - State visible in conversation
   - Easy to understand and debug
   - Self-documenting sessions

4. **Backward Compatible**
   - Non-game conversations unaffected
   - Existing chat APIs work unchanged
   - Progressive enhancement

5. **Git-Friendly**
   - Conversations can be versioned
   - Game sessions can be shared
   - Collaborative debugging

### Trade-offs ⚠️

1. **Performance Considerations**
   - Parsing JSON from messages adds overhead
   - State extraction from history may be slow for long conversations
   - Not optimized for real-time multiplayer

2. **Storage Efficiency**
   - State duplicated in every message
   - Larger storage footprint than dedicated state store
   - May need conversation pruning for long games

3. **Query Limitations**
   - Can't easily query across game sessions
   - No indexed lookups by game state
   - Analytics require full conversation scans

## Usage Examples

### Starting a New Game

```python
# User message
{
  "message": "I want to play Zork",
  "conversation_id": null  # New conversation
}

# System response
{
  "response": "🎮 **Zork Adventure**\n\nWelcome, adventurer! You are standing in an open field west of a white house, with a boarded front door. There is a small mailbox here.\n\n---\n📍 Location: West Of House | 🏆 Score: 0 | 👣 Moves: 0\n\n```json:game_state\n{\"game\": \"zork\", \"room\": \"west_of_house\", \"inventory\": [], \"score\": 0, \"moves\": 0, \"last_updated\": \"2024-11-28T12:00:00Z\"}\n```",
  "conversation_id": "conv-abc123"
}
```

### Continuing a Game

```python
# User message
{
  "message": "open the mailbox",
  "conversation_id": "conv-abc123"  # Existing conversation
}

# System extracts previous state and processes command
# Returns updated state in response
{
  "response": "You open the small mailbox, revealing a leaflet.\n\n---\n📍 Location: West Of House | 🏆 Score: 5 | 👣 Moves: 1\n\n```json:game_state\n{\"game\": \"zork\", \"room\": \"west_of_house\", \"inventory\": [\"leaflet\"], \"score\": 5, \"moves\": 1, \"last_updated\": \"2024-11-28T12:01:00Z\"}\n```"
}
```

### Checking Game State

```python
# User message
{
  "message": "what's in my inventory?",
  "conversation_id": "conv-abc123"
}

# System reads state from conversation history
current_state = extract_game_state(conversation_messages)
inventory = current_state["inventory"]  # ["leaflet"]

# Response includes current state
{
  "response": "You are carrying:\n- A leaflet\n\nThat's all you have right now.\n\n```json:game_state\n{...current_state}\n```"
}
```

## Future Enhancements

### Phase 1: Optimization (Current POC)
- ✅ Basic state embedding
- ✅ Command parsing
- ✅ State extraction
- ✅ KB integration

### Phase 2: Performance
- [ ] Cache recent state in memory
- [ ] Index conversations by game type
- [ ] Compress older state blocks
- [ ] Batch state updates

### Phase 3: Advanced Features
- [ ] Multi-player state synchronization
- [ ] State branching for save/load
- [ ] State migration for game updates
- [ ] Cross-game state sharing

### Phase 4: Scale
- [ ] Move to dedicated state service
- [ ] Implement state sharding
- [ ] Add real-time state sync
- [ ] Support massive multiplayer

## Migration Path

When ready to optimize beyond POC:

1. **Add Redis Cache Layer**
   ```python
   # Check cache first
   state = redis.get(f"game:{conversation_id}")
   if not state:
       state = extract_from_messages()
       redis.set(f"game:{conversation_id}", state, ttl=3600)
   ```

2. **Introduce State Service**
   ```python
   # Gradual migration
   if settings.USE_STATE_SERVICE:
       state = state_service.get(conversation_id)
   else:
       state = extract_from_messages()
   ```

3. **Maintain Backward Compatibility**
   - Keep embedding JSON blocks
   - Use as fallback/backup
   - Provide audit trail

## Testing

### Unit Tests
```python
# See: scripts/test_game_poc.py
- Command parsing accuracy: 83%
- State round-trip integrity: 100%
- KB query formatting: 100%
- Response generation: 100%
```

### Integration Tests
```bash
# Test with live chat service
./scripts/test.sh --local chat "play zork"

# Verify state appears in response
curl -X POST http://localhost:8666/v0.3/unified/chat \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "go north", "conversation_id": "conv-123"}'
```

### Load Tests
```python
# Future: Test state extraction performance
for i in range(100):
    add_message_to_conversation()
    time_extraction = measure(extract_game_state)
    assert time_extraction < 100ms
```

## Conclusion

The JSON blocks approach proves that game state management doesn't require complex infrastructure. By embedding state in conversation messages, we achieve:

1. **Simplicity**: No new services or databases
2. **Transparency**: State is visible and debuggable
3. **Compatibility**: Works with existing chat infrastructure
4. **Scalability**: Can evolve to dedicated services when needed

This validates our hypothesis that **documentation can BE the game**, not just describe it. The conversation becomes the game session, the KB Agent becomes the game engine, and markdown files become executable game logic.

## References

- [KB Agent Documentation](kb-endpoints-integration-guide.md)
- [Game State Handler Source](../app/services/chat/game_state_handler.py)
- [POC Test Suite](../scripts/test_game_poc.py)
- [MMOIRL Platform Vision](../docs/README-FIRST.md)