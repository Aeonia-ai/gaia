# Wylding Woods Knowledge Base Inventory

**Date:** 2025-11-07
**Source:** `/Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/wylding-woods/`
**Status:** Complete Documentation

---

## Overview

**Wylding Woods** is a MMOIRL AR experience featuring dream bottle collection, NPC relationships, and GPS-based waypoint exploration.

**State Model:** Shared multiplayer with file locking
**Current Version:** 6 (last modified 2025-11-01)
**Player Starting Location:** `woander_store`

---

## 1. Player Commands (7 total)

All player commands are defined as markdown files in `game-logic/` and interpreted by LLM at runtime.

### 1.1 Movement Command

**File:** `go.md` (347 lines)
- **Aliases:** `go`, `move`, `walk`, `travel`
- **Purpose:** Navigate between locations and sublocations
- **Examples:**
  - `"go to entrance"`
  - `"move to the clearing"`
  - `"walk to shelf b"`
- **State Updates:**
  - Updates `player.current_location`
  - Updates `player.current_sublocation` (if entering sublocation)
  - Clears sublocation if moving to main location

### 1.2 Observation Commands

**File:** `look.md` (412 lines)
- **Aliases:** `look`, `examine`, `inspect`, `observe`
- **Purpose:** Examine locations, objects, NPCs
- **Context-Aware:**
  - No target → Describes current location/sublocation
  - With target → Examines specific item or NPC
- **Examples:**
  - `"look around"`
  - `"examine the shelf"`
  - `"inspect the glowing bottle"`

### 1.3 Item Collection

**File:** `collect.md` (518 lines)
- **Aliases:** `collect`, `take`, `grab`, `pick up`, `get`
- **Purpose:** Pick up items from world into inventory
- **Critical Logic:**
  - **Sublocation-Aware Path Construction:**
    ```
    If player.current_sublocation exists:
      → path = locations.{location}.sublocations.{sublocation}.items
    If player.current_sublocation is null:
      → path = locations.{location}.items
    ```
  - **NEVER assumes flat structure** - always checks sublocation first
- **State Updates:**
  - Removes item from world state (JSON path deletion)
  - Appends item to `player.inventory` with metadata
  - Updates `player.last_action`
- **Examples:**
  - `"collect bottle of joy"`
  - `"take the glowing bottle"`

### 1.4 NPC Interaction

**File:** `talk.md` (427 lines)
- **Aliases:** `talk`, `speak`, `chat`, `ask`
- **Purpose:** Converse with NPCs using trust-based relationship system
- **Trust System:**
  - Range: 0-100 (stored per NPC in player state)
  - Affects dialogue depth and quest availability
  - Trust increases through positive interactions
- **LLM Integration:**
  - Generates authentic, in-character responses
  - Uses NPC personality, conversation history, world context
- **State Updates:**
  - Appends to `player.conversation_history.{npc_id}` (last 20 turns)
  - Updates `player.npc_relationships.{npc_id}.trust_level`
  - Tracks `facts_learned`, `promises_made`
- **Examples:**
  - `"talk to Woander"`
  - `"ask Louisa about the dream bottles"`

### 1.5 Inventory Management

**File:** `inventory.md` (198 lines)
- **Aliases:** `inventory`, `inv`, `items`, `bag`, `check inventory`
- **Purpose:** Display player's collected items
- **Display Format:**
  - Categorized by item type
  - Shows item properties (rarity, description)
  - Indicates quest items
- **Examples:**
  - `"check inventory"`
  - `"show items"`

### 1.6 Quest System

**File:** `quests.md` (231 lines)
- **Aliases:** `quests`, `missions`, `tasks`, `objectives`
- **Purpose:** Display active and completed quests
- **Quest Tracking:**
  - Quest status (not_started, in_progress, completed)
  - Progress counters (e.g., bottles collected)
  - Objectives and rewards
- **Examples:**
  - `"show quests"`
  - `"check objectives"`

### 1.7 Help System

**File:** `help.md` (305 lines)
- **Aliases:** `help`, `commands`, `what can i do`
- **Purpose:** Context-aware command listing
- **Categories:**
  - Movement (go, move, walk)
  - Items (collect, take, inventory)
  - NPCs (talk, speak, ask)
  - Quests (quests, objectives)
  - System (help, look)
- **Situational Suggestions:**
  - Can provide hints based on player location and quest state
- **Examples:**
  - `"help"`
  - `"what can I do?"`

---

## 2. Admin Commands (8 total)

All admin commands use `@` prefix and are defined in `admin-logic/` directory. These bypass LLM for <30ms response time.

### 2.1 Waypoint Management

**@list-waypoints**
- Lists all GPS waypoints in the experience
- Shows coordinates, radius, enabled status

**@inspect-waypoint {id}**
- Shows detailed waypoint properties
- GPS coords, mission association, spawn points

**@edit-waypoint {id}**
- Modify waypoint properties
- Requires CONFIRM for safety

**@create-waypoint**
- Add new GPS waypoint
- Auto-generates ID, sets metadata

**@delete-waypoint {id}**
- Remove waypoint (CONFIRM required)
- Updates metadata timestamps

### 2.2 Item Management

**@list-items**
- Shows all items in world state
- Grouped by location and sublocation

**@inspect-item {id}**
- Detailed item properties
- Location, rarity, description, spawn info

**@create-item**
- Add new item to world
- Auto-assigns ID and metadata

---

## 3. World State Structure

**File:** `state/world.json`
**Version:** 6
**Last Modified:** 2025-11-01T18:23:45Z

### 3.1 Global State
```json
{
  "quest_started": false,
  "dream_bottles_found": 0,
  "dream_bottles_required": 4,
  "shop_open": true
}
```

### 3.2 Locations (3 main locations)

#### Location 1: `woander_store`
**Type:** Shop/Hub
**Description:** A cozy magical shop with shelves of dream bottles
**GPS:** 37.7749° N, -122.4194° W (San Francisco)
**Sublocations (3):**
- `entrance` - Front door area
- `shelf_a` - Left shelf with premium bottles
- `shelf_b` - Right shelf with common bottles

**Items at woander_store:**
- Dream bottles scattered across shelves (see Items section)

#### Location 2: `mystical_clearing`
**Type:** Outdoor gathering space
**Description:** A moonlit clearing where dreams take form
**GPS:** 37.7751° N, -122.4183° W
**Sublocations (8):**
- `center_altar` - Ancient stone altar
- `north_grove` - Dense tree cluster
- `east_spring` - Bubbling water source
- `south_circle` - Stone circle formation
- `west_path` - Trail to forest
- `dream_fountain` - Shimmering pool
- `meditation_stones` - Circle of flat rocks
- `ancient_tree` - Massive elder tree

**Items:** Dream fragments, mystical herbs

#### Location 3: `forest_edge`
**Type:** Wilderness boundary
**Description:** The transition between waking world and dream realm
**GPS:** 37.7753° N, -122.4201° W
**Sublocations (7):**
- `trailhead` - Marked path entrance
- `oak_grove` - Cluster of ancient oaks
- `wildflower_meadow` - Colorful field
- `moss_covered_rocks` - Boulder formation
- `stream_crossing` - Shallow ford
- `bird_watching_spot` - Elevated viewpoint
- `fairy_ring` - Mushroom circle

**Items:** Forest treasures, natural curiosities

### 3.3 Total Sublocation Count
**18 sublocations** across 3 main locations

---

## 4. NPCs (2 total)

### 4.1 Woander (Shopkeeper)

**ID:** `woander`
**Role:** Dream bottle merchant and quest giver
**Location:** `woander_store`
**Personality:** Warm, wise, mysterious, slightly whimsical
**Trust Level:** 0-100 (player-specific)

**Dialogue Themes:**
- Dream bottle properties and lore
- Quest initiation (bottle recovery)
- Shop inventory and trades
- Mystical knowledge about dreams

**Trust Gating:**
- 0-25: Basic shop talk
- 26-50: Personal stories, quest hints
- 51-75: Deep lore, special items
- 76-100: Secret knowledge, rare quests

**Quest:** "Dream Bottle Recovery" - Find 4 lost dream bottles

### 4.2 Louisa (Dream Weaver)

**ID:** `louisa`
**Role:** Dream weaver fairy, guide to dream realm
**Location:** `mystical_clearing` (primary), roams to other locations
**Personality:** Ethereal, playful, protective, enigmatic
**Trust Level:** 0-100 (player-specific)

**Dialogue Themes:**
- Dream interpretation
- Forest magic and nature lore
- Fairy realm connections
- Spiritual guidance

**Trust Gating:**
- 0-25: Cautious, basic guidance
- 26-50: Friendly advice, simple magic
- 51-75: Dream realm secrets, fairy gifts
- 76-100: Ancient wisdom, transformation quests

**Abilities:** Can teach dream magic at high trust levels

---

## 5. Items

### 5.1 Dream Bottles (4 total)

All bottles are `type: "collectible"` and contribute to the dream bottle quest.

#### Bottle 1: Bottle of Joy
**ID:** `bottle_of_joy_1`
**Location:** `woander_store.shelf_a.slot_1`
**Rarity:** Common
**Properties:**
```json
{
  "color": "golden",
  "glow": "warm",
  "dream_type": "happiness",
  "weight": "light",
  "value": 10
}
```
**Description:** "A golden bottle that radiates warmth and contentment"

#### Bottle 2: Bottle of Courage
**ID:** `bottle_of_courage`
**Location:** `mystical_clearing.center_altar`
**Rarity:** Uncommon
**Properties:**
```json
{
  "color": "crimson",
  "glow": "fierce",
  "dream_type": "bravery",
  "weight": "medium",
  "value": 25
}
```
**Description:** "A crimson bottle pulsing with bold determination"

#### Bottle 3: Bottle of Serenity
**ID:** `bottle_of_serenity`
**Location:** `mystical_clearing.dream_fountain`
**Rarity:** Rare
**Properties:**
```json
{
  "color": "azure",
  "glow": "gentle",
  "dream_type": "peace",
  "weight": "light",
  "value": 50
}
```
**Description:** "An azure bottle that whispers of tranquil waters"

#### Bottle 4: Bottle of Wonder
**ID:** `bottle_of_wonder`
**Location:** `forest_edge.fairy_ring`
**Rarity:** Epic
**Properties:**
```json
{
  "color": "prismatic",
  "glow": "shimmering",
  "dream_type": "curiosity",
  "weight": "light",
  "value": 100
}
```
**Description:** "A prismatic bottle containing the essence of discovery"

### 5.2 Spawn Point Summary

- **woander_store:** 1 bottle (Bottle of Joy)
- **mystical_clearing:** 2 bottles (Courage, Serenity)
- **forest_edge:** 1 bottle (Wonder)

---

## 6. Quest System

### Main Quest: Dream Bottle Recovery

**ID:** `dream_bottle_quest`
**Given By:** Woander
**Status:** Tracked in world.json global state

**Objective:** Collect 4 dream bottles scattered across the world

**Progress Tracking:**
```json
{
  "dream_bottles_found": 0,
  "dream_bottles_required": 4,
  "quest_started": false
}
```

**Completion Trigger:**
- When `dream_bottles_found >= dream_bottles_required`
- Return to Woander for reward

**Reward:** (Determined by quest logic, likely special item or ability unlock)

---

## 7. Configuration

**File:** `config.json`

### 7.1 State Model
```json
{
  "state_model": "shared",
  "multiplayer": {
    "enabled": true,
    "entity_ownership": "first_interaction",
    "state_conflict_resolution": "optimistic_locking"
  }
}
```

**Shared State Characteristics:**
- File locking for concurrent access
- Optimistic versioning (version field in world.json)
- Auto-save on state changes
- First player to interact owns entity

### 7.2 Bootstrap Configuration
```json
{
  "bootstrap": {
    "player_starting_location": "woander_store",
    "auto_initialize": true,
    "default_inventory": []
  }
}
```

**Player Initialization:**
- All players start at Woander's store
- Empty inventory by default
- Player view auto-created on first connection

### 7.3 Capabilities
```json
{
  "capabilities": {
    "gps_based": true,
    "ar_enabled": true,
    "inventory_system": true,
    "quest_system": true,
    "npc_interactions": true,
    "real_time_updates": true
  }
}
```

### 7.4 GPS Waypoints
**Total Waypoints:** 36
**Distribution:**
- woander_store area: 12 waypoints
- mystical_clearing area: 12 waypoints
- forest_edge area: 12 waypoints

**Waypoint Properties:**
- GPS coordinates (latitude, longitude)
- Activation radius (meters)
- Associated missions/quests
- Item spawn points
- Enabled/disabled status

---

## 8. Markdown Logic Examples

### 8.1 Critical Pattern: Sublocation Handling (from collect.md)

**The Fundamental Rule:**
```markdown
**CRITICAL PATH CONSTRUCTION RULE**:
- If `player.current_sublocation` exists → path MUST be `locations.{location}.sublocations.{sublocation}.items`
- If `player.current_sublocation` is null → path MUST be `locations.{location}.items`
- **NEVER** assume flat structure - ALWAYS check sublocation first!
```

**Why This Matters:**
- Prevents "Item not found" errors
- Ensures correct JSON path construction
- Handles hierarchical location system properly

**Code Pattern:**
```python
# Pseudocode from markdown logic
if player.current_sublocation:
    item_path = f"locations.{location}.sublocations.{sublocation}.items"
else:
    item_path = f"locations.{location}.items"
```

### 8.2 Trust System Pattern (from talk.md)

**Trust Level Progression:**
```markdown
- Trust 0-25: "Cautious" - Basic information only
- Trust 26-50: "Friendly" - Personal stories, quest hints
- Trust 51-75: "Trusted" - Deep lore, special offers
- Trust 76-100: "Intimate" - Secrets, rare opportunities
```

**Trust Increase Logic:**
```json
{
  "player.npc_relationships.{npc_id}.trust_level": {
    "$increment": 5
  }
}
```

**Conversation History:**
```json
{
  "player.conversation_history.woander": {
    "$append": {
      "timestamp": "2025-11-07T10:30:00Z",
      "player_message": "Tell me about the dream bottles",
      "npc_response": "Ah, those are special...",
      "trust_change": 5
    },
    "$limit": 20
  }
}
```

### 8.3 State Update Pattern (from collect.md)

**Item Collection State Changes:**
```json
{
  "state_updates": {
    "world": {
      "locations.woander_store.sublocations.shelf_a.items": {
        "$remove": {"id": "bottle_of_joy_1"}
      }
    },
    "player": {
      "inventory": {
        "$append": {
          "id": "bottle_of_joy_1",
          "type": "collectible",
          "collected_at": "2025-11-07T10:30:00Z",
          "collected_from": "woander_store.shelf_a"
        }
      },
      "last_action": {
        "$set": {
          "action": "collect",
          "target": "bottle_of_joy_1",
          "timestamp": "2025-11-07T10:30:00Z"
        }
      }
    }
  }
}
```

**Key Operators:**
- `$remove` - Delete item from array
- `$append` - Add item to array
- `$set` - Replace value
- `$increment` - Increase number
- `$limit` - Cap array length

---

## 9. Critical Patterns & Insights

### 9.1 Command Routing Performance

**Fast Path (Python Handlers):**
- Registered actions: `collect_item`
- Response time: <50ms
- Use for: High-frequency, deterministic actions

**Flexible Path (LLM-Interpreted):**
- All markdown-defined commands
- Response time: 1-3 seconds
- Use for: Context-aware, narrative-driven actions

**Known Mismatch:**
- Test uses `collect_bottle` action
- Only `collect_item` is registered as fast-path
- Result: Bottles go through slow LLM path unnecessarily

**Recommendation:** Register `collect_bottle` as alias to `collect_item` handler

### 9.2 State Consistency Patterns

**Optimistic Locking:**
```json
{
  "version": 6,
  "last_modified": "2025-11-01T18:23:45Z",
  "last_modified_by": "player_123"
}
```

**Conflict Resolution:**
1. Read current version
2. Apply changes
3. Increment version
4. Save with version check
5. Retry if version mismatch

### 9.3 Multiplayer Entity Ownership

**First Interaction Rule:**
- First player to interact "owns" entity
- Subsequent interactions check ownership
- Prevents simultaneous collection conflicts

**Example:**
```json
{
  "items": [
    {
      "id": "bottle_of_joy_1",
      "owned_by": "player_123",
      "owned_at": "2025-11-07T10:30:00Z",
      "interaction_type": "collecting"
    }
  ]
}
```

### 9.4 LLM Integration Points

**Where LLM is Used:**
1. **Natural Language Interpretation:** Player command → Structured action
2. **Markdown Logic Execution:** Execute game rules from .md files
3. **Narrative Generation:** Create contextual responses
4. **NPC Dialogue:** Generate authentic character conversations

**Where LLM is NOT Used:**
1. State updates (deterministic JSON operations)
2. Admin commands (direct Python execution)
3. Fast-path handlers (registered Python functions)

---

## 10. File Structure Reference

```
gaia-knowledge-base/experiences/wylding-woods/
├── config.json                      # Experience configuration
├── state/
│   ├── world.json                   # Current world state (v6)
│   ├── world.template.json          # Initial state template
│   └── players/                     # Per-player state files
│       └── {user_id}.json
├── game-logic/                      # Player commands (LLM-interpreted)
│   ├── collect.md      (518 lines)  # Item collection
│   ├── talk.md         (427 lines)  # NPC conversations
│   ├── go.md           (347 lines)  # Movement
│   ├── look.md         (412 lines)  # Observation
│   ├── help.md         (305 lines)  # Help system
│   ├── inventory.md    (198 lines)  # Inventory display
│   └── quests.md       (231 lines)  # Quest tracking
├── admin-logic/                     # Admin commands (fast path)
│   ├── @list-waypoints.md
│   ├── @inspect-waypoint.md
│   ├── @edit-waypoint.md
│   ├── @create-waypoint.md
│   ├── @delete-waypoint.md
│   ├── @list-items.md
│   ├── @inspect-item.md
│   └── @create-item.md
└── waypoints/                       # GPS waypoints (36 total)
    ├── woander-store-*.md           # 12 waypoints
    ├── mystical-clearing-*.md       # 12 waypoints
    └── forest-edge-*.md             # 12 waypoints
```

---

## 11. Testing Coverage

### WebSocket E2E Test
**File:** `tests/manual/test_websocket_experience.py`
**Coverage:**
- Complete 7-bottle collection sequence
- Player initialization validation
- Quest progress tracking
- Real-time WebSocket message flow

**Bottle Collection Sequence:**
```
1. bottle_of_joy_1     @ woander_store.shelf_a.slot_1
2. bottle_of_joy_2     @ woander_store.shelf_b.slot_2
3. bottle_of_joy_3     @ woander_store.shelf_b.slot_3
4. bottle_of_joy_4     @ woander_store.shelf_b.slot_4
5. bottle_of_joy_5     @ woander_store.shelf_b.slot_5
6. bottle_of_joy_6     @ woander_store.shelf_b.slot_6
7. bottle_of_joy_7     @ woander_store.shelf_b.slot_7
```

### HTTP Endpoint Tests
**File:** `scripts/experience/test-commands.sh`
**Test Suites:** 7 (basic, movement, items, npc, quest, performance, errors, edge)
**Total Tests:** 21
**Current Pass Rate:** 14/21 (endpoint URL mismatch issues)

**Coverage:**
- Movement between locations
- Item collection and inventory
- NPC dialogue with Woander and Louisa
- Quest status tracking
- Error handling (invalid commands, missing items)
- Performance benchmarks
- Edge cases (empty inventory, unknown locations)

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Player Commands** | 7 |
| **Admin Commands** | 8 |
| **Locations** | 3 |
| **Sublocations** | 18 |
| **NPCs** | 2 |
| **Dream Bottles** | 4 |
| **GPS Waypoints** | 36 |
| **Markdown Logic Files** | 15 (7 player + 8 admin) |
| **State Model** | Shared (multiplayer) |
| **World Version** | 6 |

---

**Documentation Complete:** 2025-11-07
**Source Truth:** `/Users/jasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/experiences/wylding-woods/`
**Related Documentation:**
- [Command System Refactor Completion](command-system-refactor-completion.md)
- [Command System Refactor Proposal](command-system-refactor-proposal.md)
