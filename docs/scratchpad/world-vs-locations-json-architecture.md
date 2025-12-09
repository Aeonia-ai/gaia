# world.json vs locations.json: Architectural Analysis

**Date:** 2025-11-07
**Purpose:** Clarify the role of world.json and locations.json in GAIA's knowledge base system
**Status:** Architectural Documentation

---

## TL;DR: Critical Findings

**world.json** = Runtime game state (actively used by all commands)
**locations.json** = Static waypoint templates (LEGACY, mostly unused)
**Current waypoint system** = Individual markdown files in `/waypoints/*.md`

**Key Discovery**: locations.json is **NOT** used by player commands or the UnifiedStateManager. It's only referenced by legacy admin waypoint CRUD commands.

---

## 1. world.json - Runtime Game State

### Purpose
**Mutable runtime state** containing the current game world, player positions, item locations, NPC states, and quest progress.

### File Location
```
/experiences/{experience}/state/world.json
```

### Managed By
**UnifiedStateManager** (`app/services/kb/unified_state_manager.py`)

**Key methods:**
- `get_world_state(experience, user_id)` - Load current world state
- `update_world_state(experience, updates, user_id)` - Modify world state
- `_get_world_state_path()` - Returns path to world.json

**Code location**: `unified_state_manager.py:850-853`
```python
def _get_world_state_path(self, experience: str, config: Dict[str, Any]) -> Path:
    """Get path to world state file."""
    state_path = config["content"]["state_path"]
    return self.experiences_path / experience / state_path / "world.json"
```

### Used By

**All Player Commands** (via UnifiedStateManager):
- `collect` - Reads item locations, updates inventory
- `move` - Reads/writes player position
- `look` - Reads location descriptions and visible items
- `talk` - Reads NPC state, updates conversation history
- `help` - Reads available commands from world context

**Admin Commands** (referenced in markdown):
- `@reset-experience` - Restores world.json from template
- `@inspect-item` - Reads item state from world.json
- `@list-items` - Scans all items in world.json

**Markdown Scripts**:
- Player command markdown files (e.g., `collect.md`) include instructions like:
  ```markdown
  Required from world state:
  - `locations[current_location].items` - Items at top-level location
  - `locations[current_location].sublocations[current_sublocation].items`
  ```

**Python Command Handlers**:
- All handlers in `app/services/kb/handlers/` access world state via:
  ```python
  world_state = await state_manager.get_world_state(experience, user_id)
  ```

### Content Structure (wylding-woods example)

**From world.json:**
```json
{
  "locations": {
    "woander_store": {
      "name": "Woander's Dream Bottle Shop",
      "description": "...",
      "sublocations": {
        "entrance": {...},
        "counter": {...},
        "fairy_door_main": {...},
        "spawn_zone_1": {...},
        "spawn_zone_2": {...},
        "spawn_zone_3": {...},
        "spawn_zone_4": {...},
        "fairy_house_spiral": {...},
        "fairy_house_star": {...},
        "fairy_house_moon": {...},
        "fairy_house_sun": {...},
        "back_room": {...},
        "shop_floor_general": {...},
        "ceiling_hooks": {...}
      },
      "items": []
    }
  },
  "npcs": {
    "woander": {...},
    "louisa": {...}
  },
  "quests": {...},
  "session": {...},
  "metadata": {
    "_version": 6,
    "last_modified": "2025-11-05T19:42:13.123456Z"
  }
}
```

**Total sublocations in woander_store**: **14**

### Mutability
**✅ Constantly updated** - Every player action modifies world.json:
- Item collection → removes item from location, adds to inventory
- Movement → updates player.current_location and player.current_sublocation
- NPC conversation → increments turn count, updates trust level
- Quest completion → modifies quest state

### File Locking
**Shared state model**: Uses `fcntl.flock()` for concurrent access control
**Isolated state model**: Each player has their own copy (no locking needed)

### Version Tracking
```json
{
  "metadata": {
    "_version": 6,
    "last_modified": "2025-11-05T19:42:13.123456Z"
  }
}
```
Version increments with every state update for optimistic locking.

---

## 2. locations.json - Static Location Templates

### Purpose
**Static location definitions** with GPS coordinates, location hierarchies, and waypoint metadata.

**Original intent**: Provide templates for location structure and AR waypoint data.

### File Location
```
/experiences/{experience}/locations.json
```

**Note**: Also found at path `/experiences/{experience}/world/locations.json` in legacy admin commands.

### Managed By
**Legacy admin waypoint CRUD commands** ONLY

**Used in:**
- `app/services/kb/kb_agent.py` - Waypoint admin command handlers
- `app/services/kb/game_commands_legacy_hardcoded.py` - Legacy implementations

**Example usage** (`kb_agent.py:locations_file`):
```python
locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"
```

### NOT Used By
❌ **UnifiedStateManager** - Does NOT read locations.json
❌ **Player commands** - Do NOT reference locations.json
❌ **Current waypoint system** - Uses markdown files instead
❌ **Command processor** - Only uses world.json via state manager

### Content Structure (wylding-woods example)

**From locations.json:**
```json
{
  "waypoints": [
    {
      "id": "waypoint_28a",
      "name": "Store Entrance",
      "gps": {"lat": 37.7749, "lng": -122.4194},
      "radius_meters": 50,
      "locations": [
        {
          "id": "woander_store",
          "name": "Woander's Dream Bottle Shop",
          "sublocations": [
            {"id": "entrance", "name": "Entrance", "interactable": true},
            {"id": "counter", "name": "Counter", "interactable": true},
            {"id": "back_room", "name": "Back Room", "interactable": false}
          ]
        }
      ]
    }
  ]
}
```

**Total sublocations in woander_store**: **3**

**⚠️ DATA MISMATCH**: locations.json has only 3 sublocations, while world.json has 14!

### Mutability
**⚠️ Rarely updated** - Only modified by admin waypoint CRUD commands:
- `@create-waypoint` - Adds new waypoint
- `@edit-waypoint` - Modifies waypoint GPS/metadata
- `@delete-waypoint` - Removes waypoint
- `@create-location` - Adds location to waypoint
- `@create-sublocation` - Adds sublocation to location

These commands are defined in markdown but implemented in `kb_agent.py`.

### Why the Mismatch?

**locations.json**: Static **templates** defining the base structure
**world.json**: Runtime **instances** with additional dynamic sublocations

**Example**: `spawn_zone_1` through `spawn_zone_4` exist in world.json for gameplay, but are NOT in the static locations.json template.

---

## 3. Current Waypoint System (Markdown-Based)

### Purpose
**Active waypoint data source** for AR/GPS-based experiences.

### File Location
```
/experiences/{experience}/waypoints/*.md
```

**Example**: `/experiences/wylding-woods/waypoints/waypoint-28a.md`

### Managed By
**WaypointReader** (`app/services/locations/waypoint_reader.py`)
**Waypoints API** (`app/services/kb/waypoints_api.py`)

### How It Works

**1. API Endpoint**:
```
GET /waypoints/{experience}
```

**2. Implementation** (`waypoints_api.py:36-80`):
```python
waypoints_path = f"experiences/{experience}/waypoints"

# List waypoint files
result = await kb_server.list_kb_directory(
    path=waypoints_path,
    pattern="*.md"
)

# Read and parse each waypoint file
for file_info in result.get("files", []):
    content = await kb_server.read_kb_file(path=file_path)
    yaml_content = _extract_yaml_block(content)
    waypoint = yaml.safe_load(yaml_content)
    waypoints.append(waypoint)
```

**3. YAML Format** (embedded in markdown):
````markdown
# waypoint-28a.md

```yaml
id: waypoint_28a
name: Woander's Dream Bottle Shop
gps:
  lat: 37.7749
  lng: -122.4194
radius_meters: 50
description: "Entrance to Woander's magical shop"
```

## Details
This waypoint marks the entrance to Woander's shop...
````

**4. Gateway Service Consumption**:
```python
# app/services/locations/waypoint_reader.py:38-42
url = f"{self.kb_service_url}/waypoints/{experience}"
response = await self.http_client.get(url)
waypoints = response.json().get("waypoints", [])
```

### Why Markdown Instead of locations.json?

**Advantages of markdown waypoints**:
- ✅ Individual files per waypoint (easier Git diff/merge)
- ✅ Embedded documentation in same file
- ✅ YAML frontmatter for structured data
- ✅ Supports hierarchical KB structure
- ✅ Can include narrative, images, and rich metadata

**locations.json limitations**:
- ❌ Single monolithic file (merge conflicts)
- ❌ No inline documentation
- ❌ Harder to version control
- ❌ Less flexible for narrative content

**Result**: Markdown waypoints became the **preferred system**, making locations.json largely obsolete.

---

## 4. How KB Markdown Scripts Handle Each File

### Player Command Markdown (game-logic/)

**Example**: `collect.md:40-44`
```markdown
Required from world state:
- `locations[current_location].items` - Items at top-level location
- `locations[current_location].sublocations[current_sublocation].items`
- **CRITICAL**: Must check BOTH `current_location` AND `current_sublocation`
```

**References**:
- ✅ **world.json** - Via state manager
- ❌ **locations.json** - NOT referenced

**Access pattern**:
```markdown
1. Read player view → get current_location and current_sublocation
2. Read world state → find items at that location
3. Modify world state → remove collected item, update inventory
4. Write player view → append item to player.inventory
```

### Admin Command Markdown (admin-logic/)

**Example**: `@reset-experience.md`
```markdown
Required actions:
1. Create backup of state/world.json
2. Copy state/world.template.json → state/world.json
3. Delete all player views in /players/{user}/{experience}/
```

**References**:
- ✅ **world.json** - Explicitly mentioned
- ❌ **locations.json** - NOT mentioned

**Example**: `@list-items.md:40-42`
```markdown
Required from world state:
- All item definitions in `/kb/experiences/{experience}/items/*.md`
- Current item locations from state/world.json
- Player inventories (to show collected status)
```

**References**:
- ✅ **world.json** - Explicitly mentioned
- ❌ **locations.json** - NOT mentioned

### Legacy Admin Waypoint Commands

**NOT in current codebase markdown**, but implemented in Python:

`kb_agent.py` contains handlers for:
- `@create-waypoint`
- `@edit-waypoint`
- `@delete-waypoint`
- `@list-waypoints`
- `@inspect-waypoint`
- `@create-location`
- `@create-sublocation`

These are the **ONLY** code paths that access `locations.json`:
```python
locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"
```

---

## 5. How KB Command System Code Handles Each File

### UnifiedStateManager (`unified_state_manager.py`)

**Accesses**:
- ✅ **world.json** - Primary state file
- ✅ **config.json** - Experience configuration
- ✅ **view.json** (player views) - Per-player state
- ❌ **locations.json** - NOT accessed

**Methods**:
```python
async def get_world_state(experience, user_id) -> Dict[str, Any]:
    # Loads /experiences/{exp}/state/world.json
    world_path = self._get_world_state_path(experience, config)
    with open(world_path, 'r') as f:
        return json.load(f)

async def update_world_state(experience, updates, user_id) -> Dict[str, Any]:
    # Modifies /experiences/{exp}/state/world.json
    # Uses file locking for shared state model
```

**No methods for locations.json!**

### Command Processor (`command_processor.py`)

**Accesses**:
- ✅ **world.json** - Via state_manager
- ✅ **player view** - Via state_manager
- ✅ **markdown commands** - Loaded as LLM context
- ❌ **locations.json** - NOT accessed

**Flow**:
```python
async def process_command(user_id, experience, command_data):
    # 1. Load player view (via state manager)
    player_view = await state_manager.get_player_view(experience, user_id)

    # 2. Load world state (via state manager)
    world_state = await state_manager.get_world_state(experience, user_id)

    # 3. Load command markdown
    command_md = await kb_storage.read_command(experience, action)

    # 4. Execute via LLM or Python handler
    result = await execute_command(player_view, world_state, command_md)

    # 5. Update state (via state manager)
    await state_manager.update_world_state(experience, result.state_changes, user_id)
```

**No interaction with locations.json at any step!**

### Legacy Admin Commands (`kb_agent.py`)

**Accesses**:
- ✅ **locations.json** - Direct file read/write
- ✅ **world.json** - Via state manager (for @reset-experience)

**Methods using locations.json**:
```python
async def handle_create_waypoint(...):
    locations_file = f"{kb_path}/experiences/{experience}/world/locations.json"
    with open(locations_file, 'r') as f:
        data = json.load(f)
    # ... modify data ...
    with open(locations_file, 'w') as f:
        json.dump(data, f, indent=2)
```

**Similar pattern in**:
- `handle_edit_waypoint()`
- `handle_delete_waypoint()`
- `handle_list_waypoints()`
- `handle_inspect_waypoint()`

---

## 6. Summary: Architectural Roles

| Feature | world.json | locations.json |
|---------|-----------|----------------|
| **Purpose** | Runtime game state | Static location templates |
| **Mutability** | Constantly updated | Rarely updated (admin only) |
| **Managed By** | UnifiedStateManager | Legacy admin commands |
| **Used By** | All player commands, admin commands | ONLY legacy waypoint CRUD |
| **File Locking** | Yes (shared model) | No |
| **Version Tracking** | Yes (_version field) | No |
| **Current Status** | ✅ **Active** | ⚠️ **Legacy/Unused** |
| **Sublocation Count** | 14 (woander_store) | 3 (woander_store) |

### Data Flow Diagram

```
Player Command
     ↓
Command Processor
     ↓
UnifiedStateManager
     ↓
world.json ← Reads/Writes
     ↓
Updated Game State
```

**locations.json is NOT in this flow!**

### Waypoint Data Flow

```
Unity Client
     ↓
GET /api/v0.3/locations/nearby
     ↓
Gateway Service
     ↓
GET /waypoints/wylding-woods (KB Service)
     ↓
Waypoints API
     ↓
Markdown Files ← Reads YAML blocks
     ↓
Waypoint JSON Response
```

**locations.json is NOT in this flow either!**

---

## 7. Why the Mismatch Exists

### Design Evolution

**Phase 1: Original Design** (locations.json)
- Single JSON file for all location data
- GPS waypoints + location hierarchy in one place
- Intended for simple experiences

**Phase 2: Runtime Complexity** (world.json)
- Game needed dynamic sublocations (spawn_zone_1, fairy_house_spiral)
- Items move between sublocations
- NPCs appear/disappear dynamically
- **Solution**: Separate runtime state (world.json) from templates

**Phase 3: Markdown Waypoints** (waypoints/*.md)
- Individual files per waypoint
- Embedded documentation
- Better Git workflow
- **Result**: locations.json became obsolete for waypoint system

### Current State

**locations.json**:
- Contains only **static base structure** (3 sublocations)
- Used for **admin waypoint editing** (GPS coordinates, metadata)
- Acts as **template** for location definitions

**world.json**:
- Contains **full runtime structure** (14 sublocations)
- Used for **all gameplay** (items, NPCs, player positions)
- Includes **dynamic game elements** not in templates

**waypoints/*.md**:
- Contains **active waypoint data** (GPS, descriptions)
- Used by **AR/location system** via API
- Replaces locations.json for waypoint purposes

---

## 8. Architectural Decision: Status Quo (Option C)

**Decision Date**: 2025-11-07
**Status**: ✅ **ACCEPTED**

After analysis, the team has chosen to **maintain the current architecture** (Status Quo) with explicit documentation of the separation.

### Rationale

1. **System works reliably** - world.json + waypoints/*.md handle all production use cases
2. **No breaking changes** - Admin waypoint commands continue to function
3. **Minimal maintenance burden** - locations.json is stable and rarely modified
4. **Clear separation of concerns** - Each file serves distinct purposes
5. **Defer complexity** - Can revisit if compelling use case emerges

### Architectural Reality

```
┌─────────────────────────────────────────────────────────┐
│ Primary Architecture (Production Game Logic)            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  world.json ────→ UnifiedStateManager ────→ Commands    │
│  waypoints/*.md ─→ Waypoints API ──────────→ Unity AR   │
│                                                          │
│  ✅ Actively maintained                                 │
│  ✅ Used by all player-facing features                  │
│  ✅ Source of truth for game state                      │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Secondary Architecture (Admin Tooling Only)              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  locations.json ───→ 5 Admin Waypoint Commands          │
│                                                          │
│  ⚠️ Separate from game logic                            │
│  ⚠️ Only modified via admin commands                    │
│  ⚠️ Not required for gameplay                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Known Architectural Debt

**This is documented debt, not a bug:**

- locations.json has only 3 sublocations while world.json has 14
- This mismatch is **intentional** - they serve different purposes
- No synchronization mechanism exists (by design)
- locations.json is for waypoint metadata, not game structure

### Developer Guidelines

**DO:**
- ✅ Use `world.json` for all game logic (items, NPCs, locations, state)
- ✅ Use `waypoints/*.md` for GPS coordinates and AR placement
- ✅ Use UnifiedStateManager to access world state
- ✅ Understand locations.json is separate from game logic

**DON'T:**
- ❌ Try to sync locations.json with world.json
- ❌ Read locations.json for game logic purposes
- ❌ Assume locations.json reflects current game structure
- ❌ Modify locations.json manually (use admin commands)

## 9. Recommendations

### For Developers

**1. Use world.json for gameplay**:
```python
# ✅ CORRECT - Primary game state source
world_state = await state_manager.get_world_state(experience, user_id)
current_items = world_state["locations"][location]["items"]
```

**2. Don't rely on locations.json**:
```python
# ❌ WRONG - This file is not part of game logic
with open("locations.json") as f:
    locations = json.load(f)
```

**3. Use waypoints API for GPS data**:
```python
# ✅ CORRECT - Uses markdown waypoints
waypoints = await waypoint_reader.get_waypoints_for_experience(experience)
```

**4. Accessing locations.json (Admin Only)**:
```python
# ⚠️ ONLY if implementing admin waypoint commands
# Most developers will never need this
locations_file = f"{kb_path}/experiences/{exp}/world/locations.json"
```

### For Content Designers

**1. Add new sublocations** → Edit `world.json` or `world.template.json`:
```json
{
  "locations": {
    "woander_store": {
      "sublocations": {
        "new_sublocation": {
          "id": "new_sublocation",
          "name": "New Area",
          "description": "..."
        }
      }
    }
  }
}
```

**2. Add new waypoints** → Create `waypoints/new-waypoint.md`:
````markdown
```yaml
id: new_waypoint
name: New Location
gps:
  lat: 37.7749
  lng: -122.4194
```
````

**3. Editing locations.json**:
- ✅ Use admin commands: `@create-waypoint`, `@edit-waypoint`, etc.
- ❌ Don't edit locations.json file directly
- ⚠️ Changes to locations.json do NOT affect gameplay

### For System Architects

**Current Architecture Decision**: **Status Quo (Option C)**

**If Future Refactoring Needed:**

**Option 1: Deprecate locations.json**
- Remove legacy admin waypoint commands
- Migrate any remaining data to waypoints/*.md
- Simplify architecture
- **When**: If waypoints/*.md becomes feature-complete for all admin needs

**Option 2: Repurpose locations.json**
- Use as source of truth for location structure templates
- Generate world.template.json FROM locations.json
- Maintain consistency between template and runtime
- **When**: If strong need emerges for canonical structure definitions

**Option 3: Status Quo** ✅ **CURRENT**
- Keep locations.json for admin waypoint tools
- Document as separate from game logic
- Acknowledge as architectural debt
- **Revisit**: When pain points emerge or major refactor needed

---

## 9. Related Documentation

- [Command System Refactor Completion](command-system-refactor-completion.md)
- [Wylding Woods Knowledge Base Inventory](wylding-woods-knowledge-base-inventory.md)
- [Command Formats Comparison](command-formats-comparison.md)
- [UnifiedStateManager Source](../../app/services/kb/unified_state_manager.py)
- [Waypoints API Source](../../app/services/kb/waypoints_api.py)

---

**Last Updated**: 2025-11-07
**Author**: GAIA Architecture Analysis
