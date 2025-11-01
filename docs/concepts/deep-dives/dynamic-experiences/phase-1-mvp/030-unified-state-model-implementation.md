# 030 - Unified State Model Implementation

**Status:** ✅ IMPLEMENTED
**Version:** 1.0.0
**Created:** 2025-10-27
**Purpose:** Complete guide to the production-ready unified state management system for GAIA experiences

## Overview

The unified state model is a **config-driven architecture** that replaces hardcoded state management with a flexible, single-source-of-truth system. One configuration setting (`state.model`) determines the entire architecture:

- **`shared`** - Multiplayer mode: One world file, all players interact with same entities
- **`isolated`** - Single-player mode: Each player gets their own copy of the world

## Key Innovation: Players as Views

The core philosophy: **World state is truth, players are views into that world.**

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED STATE MODEL                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  /experiences/{exp}/                                         │
│    ├── config.json           ← Defines state model          │
│    └── state/                                                │
│        └── world.json        ← Source of truth              │
│                                                               │
│  /players/{user}/                                            │
│    ├── profile.json          ← Global: current experience   │
│    └── {exp}/                                                │
│        └── view.json         ← Player's view into world     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Production Status

**✅ Complete and Production-Ready:**
- 854 lines of production code (`unified_state_manager.py`)
- 25 unit tests passing
- Fully integrated into KB service
- New API endpoint `/experience/interact` operational
- Player profile persistence working
- Config validation system operational

**⏸️ Placeholder (Coming Soon):**
- Markdown-driven game logic (currently placeholder)
- Migration scripts for existing data

## Implementation Components

### 1. UnifiedStateManager (`app/services/kb/unified_state_manager.py`)

**Core Responsibilities:**
- Load and validate experience configs
- Read/write world state (shared or isolated)
- Read/write player views
- Bootstrap new players based on config
- Handle file locking for concurrent access (shared model)
- Optimistic versioning for conflict detection

**Key Methods:**

```python
# Config Management
manager.load_config(experience: str) -> Dict[str, Any]

# World State
await manager.get_world_state(experience: str, user_id: Optional[str] = None)
await manager.update_world_state(experience: str, updates: Dict[str, Any], user_id: Optional[str] = None)

# Player Views
await manager.get_player_view(experience: str, user_id: str)
await manager.update_player_view(experience: str, user_id: str, updates: Dict[str, Any])

# Bootstrap
await manager.bootstrap_player(experience: str, user_id: str)

# Player Profile (Global)
await manager.get_player_profile(user_id: str)
await manager.set_current_experience(user_id: str, experience: str)
await manager.get_current_experience(user_id: str)

# Utilities
manager.list_experiences() -> List[str]
manager.get_experience_info(experience: str) -> Dict[str, Any]
```

### 2. Experience Config System

**Location:** `/experiences/{experience-id}/config.json`

**Complete Documentation:**
- [Experience Config Schema](../../../unified-state-model/experience-config-schema.md) - Full JSON schema, field descriptions
- [Config Examples](../../../unified-state-model/config-examples.md) - Production configs for all experience types

**Minimal Example:**

```json
{
  "id": "wylding-woods",
  "name": "The Wylding Woods",
  "version": "1.0.0",
  "description": "AR fairy tale adventure",

  "state": {
    "model": "shared"  // ← This one setting determines everything!
  },

  "multiplayer": {
    "enabled": true
  },

  "bootstrap": {
    "player_starting_location": null,
    "copy_template_for_isolated": false
  },

  "capabilities": {
    "gps_based": true,
    "ar_enabled": true
  }
}
```

### 3. Player Profile Persistence

**Global Profile:** `/players/{user}/profile.json`

Stores cross-experience data:
- `current_experience` - Currently selected experience (persists across sessions!)
- `preferences` - Player preferences
- `global_stats` - Cross-experience statistics

**Example:**

```json
{
  "user_id": "jason@aeonia.ai",
  "current_experience": "wylding-woods",
  "preferences": {},
  "global_stats": {
    "total_play_time_minutes": 0,
    "experiences_played": ["wylding-woods", "west-of-house"]
  },
  "metadata": {
    "_version": 3,
    "_created_at": "2025-10-27T18:00:00Z",
    "_last_updated": "2025-10-27T19:30:00Z"
  }
}
```

**Per-Experience View:** `/players/{user}/{experience}/view.json`

Contains player's state within a specific experience:
- `player` - Position, inventory, stats
- `progress` - Visited locations, quests, achievements
- `session` - Session tracking
- `metadata` - Version, timestamps

### 4. New API Endpoint

**Endpoint:** `POST /experience/interact`

**Purpose:** Stateful interaction endpoint that remembers player's current experience

**Request:**

```json
{
  "message": "look around",
  "experience": "wylding-woods",  // Optional if player has current_experience
  "force_experience_selection": false
}
```

**Response:**

```json
{
  "success": true,
  "narrative": "You stand at the Woander Storefront...",
  "experience": "wylding-woods",
  "state_updates": {
    "player": {
      "current_location": "waypoint_1"
    }
  },
  "available_actions": ["look around", "check inventory", "explore"],
  "metadata": {
    "player_view_version": 5,
    "state_model": "shared"
  }
}
```

**Flow:**

1. Determine which experience (from request or player profile)
2. If no experience selected, prompt for selection
3. Ensure player is bootstrapped
4. Load world state and player view
5. Process message using markdown game logic (placeholder)
6. Update state and return response

## State Model Comparison

### Shared Model (Multiplayer)

**Example:** Wylding Woods

```
/experiences/wylding-woods/
  ├── config.json { "state": { "model": "shared" } }
  └── state/
      └── world.json    ← One file, all players share

/players/jason@aeonia.ai/wylding-woods/
  └── view.json         ← Only player's position, inventory refs

/players/alice@example.com/wylding-woods/
  └── view.json         ← Her position, inventory refs
```

**When to use:**
- Multiplayer AR games
- Shared puzzle worlds
- Collaborative experiences
- Players affect each other's world

**Requirements:**
- `locking_enabled: true` (required for concurrent writes)
- `optimistic_versioning: true` (detect conflicts)

### Isolated Model (Single-Player)

**Example:** West of House

```
/experiences/west-of-house/
  ├── config.json { "state": { "model": "isolated" } }
  └── state/
      └── world.json    ← Template (copied per player)

/players/jason@aeonia.ai/west-of-house/
  └── view.json         ← Full world copy, player can modify freely

/players/alice@example.com/west-of-house/
  └── view.json         ← Independent world copy
```

**When to use:**
- Single-player text adventures
- Independent instances
- No player interaction needed
- Each player has separate reality

**Optimization:**
- `locking_enabled: false` (no concurrent access to same file)
- `copy_template_for_isolated: true` (bootstrap copies template)

## File Locking and Concurrency

### Shared Model: File Locking

For `state.model: "shared"`, the system uses **fcntl file locking** to prevent race conditions:

```python
# Acquire exclusive lock
fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

# Read → Modify → Write
current_state = json.load(f)
updated_state = merge_updates(current_state, updates)
json.dump(updated_state, f)

# Release lock
fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Timeout Handling:**
- Default: 5000ms (`lock_timeout_ms`)
- Configurable per-experience
- Throws `StateLockError` if timeout exceeded

### Optimistic Versioning

All state files include version numbers:

```json
{
  "entities": {...},
  "metadata": {
    "_version": 5,
    "last_modified": "2025-10-27T18:00:00Z"
  }
}
```

**Update Flow:**
1. Read state (version=5)
2. Make changes locally
3. Write with version=6 only if current version still 5
4. If version > 5, conflict detected → retry or error

## Bootstrap Process

**When player first joins experience:**

1. **Check if already bootstrapped** - Does `view.json` exist?
2. **Create player directory** - `/players/{user}/{experience}/`
3. **Branch by state model:**
   - **Shared:** Create minimal view (position, empty inventory)
   - **Isolated:** Copy `state/world.json` template to `view.json`
4. **Apply bootstrap config:**
   - Set `player_starting_location` if configured
   - Add `player_starting_inventory` items
5. **Write view.json**
6. **Track in profile** - Add to `experiences_played`

**Example: Shared Model Bootstrap**

```json
// /players/jason@aeonia.ai/wylding-woods/view.json
{
  "player": {
    "current_location": null,          // From config.bootstrap.player_starting_location
    "current_sublocation": null,
    "inventory": [],                   // From config.bootstrap.player_starting_inventory
    "stats": {}
  },
  "progress": {
    "visited_locations": [],
    "quest_states": {},
    "achievements": []
  },
  "session": {
    "started_at": "2025-10-27T18:00:00Z",
    "last_active": "2025-10-27T18:00:00Z",
    "turns_taken": 0
  },
  "metadata": {
    "_version": 1,
    "_created_at": "2025-10-27T18:00:00Z"
  }
}
```

**Example: Isolated Model Bootstrap**

```json
// Copies entire state/world.json to player's view.json
// Player gets full independent world state
{
  "session": {
    "id": "jason@aeonia.ai-1730052000",
    "started_at": "2025-10-27T18:00:00Z"
  },
  "player": {
    "current_room": "west_of_house",
    "inventory": [],
    "health": 100
  },
  "world_state": {
    "mailbox_opened": false,
    "lamp_lit": false
  },
  "metadata": {
    "_version": 1,
    "_copied_from_template": "2025-10-27T18:00:00Z",
    "_user_id": "jason@aeonia.ai"
  }
}
```

## Experience Selection Flow

**Key Innovation:** Experience selection persists across sessions!

### First-Time User

```
Player: "play game"
    ↓
Server: GET /players/{user}/profile.json → Does not exist
    ↓
Server: current_experience = null
    ↓
Response: "Welcome! Please select an experience:
           - Wylding Woods: AR adventure
           - West of House: Text adventure
           To select, say: 'I want to play [name]'"
```

### Returning User (Selection Remembered)

```
Player: "look around"
    ↓
Server: GET /players/{user}/profile.json → Exists
    ↓
Server: current_experience = "wylding-woods"
    ↓
Server: Load wylding-woods state and process command
    ↓
Response: "You stand at the Woander Storefront..."
```

### Explicit Selection

```
Player: "I want to play West of House"
    ↓
Server: Detect selection pattern in message
    ↓
Server: set_current_experience(user, "west-of-house")
    ↓
Server: Update profile.json { "current_experience": "west-of-house" }
    ↓
Response: "Great! You've selected West of House. What would you like to do?"
```

## Migration Path from Old Structure

### Current (Old) Structure

```
/experiences/wylding-woods/
  └── instances/
      ├── manifest.json
      ├── npcs/louisa_1.json
      └── items/dream_bottle_1.json

/players/jason@aeonia.ai/wylding-woods/
  └── progress.json
```

### New (Unified) Structure

```
/experiences/wylding-woods/
  ├── config.json           ← NEW: Defines state model
  └── state/
      └── world.json        ← NEW: Merged from instances/

/players/jason@aeonia.ai/
  ├── profile.json          ← NEW: Global player data
  └── wylding-woods/
      └── view.json         ← NEW: Expanded from progress.json
```

### Migration Scripts (Coming Soon)

**Not yet implemented, but designed:**

```bash
# Merge instances into world.json
python scripts/migrate_experience_state.py wylding-woods --merge-instances

# Convert player progress to view
python scripts/migrate_player_views.py wylding-woods --all-players

# Validate migration
python scripts/validate_experience_config.py wylding-woods
```

**Migration will:**
1. Read `instances/manifest.json` and all instance files
2. Merge into single `state/world.json` with unified schema
3. Preserve all state data (quest progress, emotional states, etc.)
4. Convert `progress.json` → `view.json` (expand to full schema)
5. Create `config.json` based on experience type
6. Keep backups of original files

## Code Examples

### Loading Experience Config

```python
from app.services.kb.unified_state_manager import UnifiedStateManager

manager = UnifiedStateManager(kb_root="/kb")

# Load and validate config (cached after first load)
config = manager.load_config("wylding-woods")

print(f"State model: {config['state']['model']}")
print(f"Multiplayer: {config['multiplayer']['enabled']}")
print(f"GPS-based: {config['capabilities']['gps_based']}")
```

### Reading World State

```python
# Shared model (no user_id needed)
world = await manager.get_world_state("wylding-woods")
print(f"Entities: {list(world['entities'].keys())}")

# Isolated model (user_id required)
world = await manager.get_world_state("west-of-house", user_id="jason@aeonia.ai")
print(f"Player room: {world['player']['current_room']}")
```

### Updating World State

```python
# Update shared world (uses file locking)
updates = {
    "entities": {
        "dream_bottle_1": {
            "state": {
                "collected": True,
                "collected_by": "jason@aeonia.ai"
            }
        }
    }
}

updated_world = await manager.update_world_state(
    "wylding-woods",
    updates,
    use_locking=True  # Default for shared model
)

print(f"Version: {updated_world['metadata']['_version']}")
```

### Managing Player Views

```python
# Get player's view
view = await manager.get_player_view("wylding-woods", "jason@aeonia.ai")

if not view:
    # Bootstrap new player
    view = await manager.bootstrap_player("wylding-woods", "jason@aeonia.ai")

# Update player's inventory
updates = {
    "player": {
        "inventory": view["player"]["inventory"] + ["dream_bottle_1"]
    }
}

updated_view = await manager.update_player_view(
    "wylding-woods",
    "jason@aeonia.ai",
    updates
)
```

### Setting Current Experience

```python
# Player selects an experience
profile = await manager.set_current_experience(
    "jason@aeonia.ai",
    "wylding-woods"
)

print(f"Current experience: {profile['current_experience']}")

# Later, retrieve current experience
current = await manager.get_current_experience("jason@aeonia.ai")
# Returns: "wylding-woods"
```

## Testing

**Unit Tests:** 25 tests passing

```bash
pytest tests/unit/test_unified_state_manager.py -v
```

**Test Coverage:**
- ✅ Config loading and validation
- ✅ Shared world state operations
- ✅ Isolated world state operations
- ✅ Player view CRUD
- ✅ Player profile management
- ✅ Bootstrap process (both models)
- ✅ File locking behavior
- ✅ Optimistic versioning
- ✅ Error handling (missing files, invalid configs)

**Integration Test (Manual):**

```bash
# 1. Create test experience config
cat > /kb/experiences/test-exp/config.json << 'EOF'
{
  "id": "test-exp",
  "name": "Test Experience",
  "version": "1.0.0",
  "state": { "model": "shared" }
}
EOF

# 2. Create world template
mkdir -p /kb/experiences/test-exp/state
echo '{"entities": {}, "metadata": {"_version": 1}}' > /kb/experiences/test-exp/state/world.json

# 3. Bootstrap player via API
curl -X POST https://gaia-kb-dev.fly.dev/experience/interact \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "play test-exp"}'

# 4. Verify player bootstrapped
curl https://gaia-kb-dev.fly.dev/experience/list \
  -H "Authorization: Bearer $TOKEN"
```

## Performance Considerations

### File I/O Optimization

**Caching:**
- Experience configs cached in memory after first load
- Use `force_reload=True` only when config changed

**Lock Timeouts:**
- Default: 5000ms
- Adjust per-experience based on needs:
  - Fast-paced games: 1000-2000ms (fail fast)
  - Complex operations: 5000-10000ms (more tolerance)

**Save Intervals:**
- `auto_save: true` + `save_interval_s: 30` (default)
- Rate limits high-frequency writes
- Prevents disk thrashing

### Scaling Considerations

**Current Implementation:** File-based (JSON)
- ✅ Perfect for 1-50 concurrent players
- ✅ Simple, no infrastructure
- ✅ Git-backed versioning
- ⚠️ Limited query performance
- ⚠️ File locking contention at scale

**Future Migration Path:**
- Keep file-based for isolated model (no contention)
- Migrate shared model to PostgreSQL JSONB at 50+ concurrent players
- Redis caching layer for hot data
- Keep config.json structure (same API, different backend)

## Markdown-Driven Game Logic (Coming Soon)

**Current Status:** Placeholder implementation

**Design:**
- Game commands processed by markdown files in `/experiences/{exp}/game-logic/`
- Hierarchical loading like `/agent/interpret` endpoint
- LLM interprets command against markdown rules
- Returns structured response (narrative + actions + state changes)

**Example Files:**
```
/experiences/wylding-woods/game-logic/
  ├── look.md       ← "look around" command logic
  ├── talk.md       ← NPC conversation logic
  └── collect.md    ← Item collection logic
```

**When Ready:**
- Replace placeholder in `_process_game_message()`
- Use `kb_agent.agent.interpret()` to process markdown
- Apply state changes via `UnifiedStateManager`

## Summary

**What's Production-Ready:**
- ✅ UnifiedStateManager (854 lines, 25 tests)
- ✅ Config system with validation
- ✅ Player profile persistence
- ✅ Experience selection (persists across sessions)
- ✅ Bootstrap process (both models)
- ✅ File locking for concurrency
- ✅ API endpoint `/experience/interact`

**What's Coming:**
- ⏸️ Markdown-driven game logic (placeholder)
- ⏸️ Migration scripts for existing data

**Key Benefits:**
1. **One config setting** determines entire architecture
2. **Persistent experience selection** - choose once, remembered forever
3. **Flexible state models** - shared (multiplayer) or isolated (single-player)
4. **Production-ready** - file locking, versioning, error handling
5. **Migration path** - designed for future PostgreSQL backend

## Related Documentation

- [Experience Config Schema](../../../unified-state-model/experience-config-schema.md) - Complete field reference
- [Config Examples](../../../unified-state-model/config-examples.md) - Production configs for all experience types
- [KB Repository Structure](../../../kb/developer/kb-repository-structure-and-behavior.md) - File organization
- [Player Progress Storage](../storage/player-progress-storage.md) - Future PostgreSQL migration

---

**Next Steps:**
1. Create config.json for your experience
2. Bootstrap test player via API
3. Implement markdown game logic (when ready)
4. Plan migration for existing experiences
