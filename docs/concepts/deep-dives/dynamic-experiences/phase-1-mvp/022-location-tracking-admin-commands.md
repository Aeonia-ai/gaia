# Location Tracking & Admin Commands Design

> **Status:** 🔵 DESIGN SPECIFICATION - Detailed design, implementation TBD
> **Version:** 1.0
> **Date:** October 27, 2025 (Created)
> **Last Updated:** December 4, 2025
> **Related:** [021-kb-command-processing-spec.md](./021-kb-command-processing-spec.md)

## ⚠️ Implementation Status

**This is a DESIGN SPECIFICATION, not implemented code.**

**Current Reality:**
- Basic admin commands exist: `@list-waypoints`, `@inspect-waypoint`, etc. (see [Admin Command System](docs/admin-command-system.md))
- Admin commands use @ prefix and operate on KB files
- Response time < 30ms (zero LLM latency)
- NO hierarchical location tracking (Waypoint → Location → Sublocation) implemented
- NO session-based navigation graph implemented
- NO MUD/MOO-style world building implemented

**This Document Describes:**
- Proposed hierarchical location model (3-tier structure)
- Graph-based navigation system (not implemented)
- Session state tracking (not implemented)
- Comprehensive admin command set (only subset exists)
- Player navigation commands (not implemented)

**Before Implementing:** Verify this design still matches requirements, assess alternatives, validate with actual gameplay needs.

## Overview (PROPOSED SYSTEM)

This document specifies a hierarchical location tracking system and admin command set for creating a Zork-like AR MMO experience. Players navigate through a nested location hierarchy (Waypoint → Location → Sublocation), while admins can dynamically create and edit world content using MUD/MOO-style @ commands.

**Note**: This is a detailed design proposal, not current implementation.

**Design Goals:**
- Natural language player commands for exploration and interaction
- MUD/MOO-inspired admin commands (@ prefix) for world building
- Hierarchical location context (room-location-sublocation pattern)
- No RBAC initially - focus on command functionality
- File-based content storage (JSON) for MVP phase

## Location Hierarchy Model

### Three-Tier Structure

```
Waypoint/Room (GPS-anchored AR location or scene-based container)
  └── Location (named area within waypoint - building/zone)
      └── Sublocation (interactable spot within location)
```

**Why this structure?**
- **Waypoint/Room**: GPS-based or scene-based container (e.g., GPS coordinate, VR scene)
- **Location**: Named area within waypoint (like a building, shop, clearing)
- **Sublocation**: Interactive spot within location (shelf, door, corner, object)

**Example 1: The Fairy Grove (Natural Environment)**
```
waypoint_28a (The Fairy Grove - GPS: 37.7749, -122.4194)
  └── clearing (central clearing)
      ├── shelf_1 (mushroom shelf)
      ├── fairy_door_1 (spiral fairy house door)
      └── ancient_tree (the ancient oak)
  └── pond_area (quiet pond)
      ├── water_edge (pond's edge)
      └── lily_pad (floating lily pad)
```

**Example 2: Woander Store (Indoor Location)**
```
waypoint_28a (Woander Store Area - GPS: 37.906233, -122.547721)
  └── woander_store (mystical shop interior)
      ├── entrance (store entrance)
      ├── shelf_area (display shelves)
      ├── fairy_doors (wall of fairy doors)
      └── fountain (magical fountain)
```

### Location Data Model

**File:** `experiences/wylding-woods/locations.json`

```json
{
  "waypoint_28a": {
    "waypoint_id": "waypoint_28a",
    "name": "The Fairy Grove",
    "gps": {
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "description": "A mystical grove where fairies are said to dwell.",
    "locations": {
      "clearing": {
        "location_id": "clearing",
        "name": "Central Clearing",
        "description": "A peaceful clearing surrounded by ancient trees.",
        "default_sublocation": "shelf_1",
        "sublocations": {
          "shelf_1": {
            "sublocation_id": "shelf_1",
            "name": "Mushroom Shelf",
            "description": "A natural shelf of glowing mushrooms.",
            "interactable": true,
            "contains": ["dream_bottle_1"]
          },
          "fairy_door_1": {
            "sublocation_id": "fairy_door_1",
            "name": "Spiral Fairy House Door",
            "description": "A tiny door marked with a spiral symbol.",
            "interactable": true,
            "accepts": ["dream_bottle"],
            "quest_checkpoint": true
          },
          "ancient_tree": {
            "sublocation_id": "ancient_tree",
            "name": "The Ancient Oak",
            "description": "A massive oak tree with deep roots.",
            "interactable": true,
            "npc": "elder_squirrel"
          }
        }
      },
      "pond_area": {
        "location_id": "pond_area",
        "name": "Quiet Pond",
        "description": "A serene pond with crystal-clear water.",
        "default_sublocation": "water_edge",
        "sublocations": {
          "water_edge": {
            "sublocation_id": "water_edge",
            "name": "Pond's Edge",
            "description": "Smooth stones line the water's edge.",
            "interactable": true
          },
          "lily_pad": {
            "sublocation_id": "lily_pad",
            "name": "Floating Lily Pad",
            "description": "A large lily pad floating peacefully.",
            "interactable": false
          }
        }
      }
    }
  },
  "waypoint_28a_store": {
    "waypoint_id": "waypoint_28a_store",
    "name": "Woander Store Area",
    "gps": {
      "latitude": 37.906233,
      "longitude": -122.547721,
      "radius": 50
    },
    "description": "The entrance to Woander's mystical shop.",
    "locations": {
      "woander_store": {
        "location_id": "woander_store",
        "name": "Woander Store",
        "description": "A mystical shop with glowing displays and enchanted items.",
        "default_sublocation": "entrance",
        "sublocations": {
          "entrance": {
            "sublocation_id": "entrance",
            "name": "Store Entrance",
            "description": "The entrance to the store with a magical doorway.",
            "interactable": true,
            "exits": ["shelf_area", "fairy_doors"],
            "cardinal_exits": {
              "north": "shelf_area",
              "east": "fairy_doors"
            }
          },
          "shelf_area": {
            "sublocation_id": "shelf_area",
            "name": "Display Shelves",
            "description": "Three wooden shelves line the walls, filled with mysterious items.",
            "interactable": true,
            "exits": ["entrance", "fountain"],
            "cardinal_exits": {
              "south": "entrance",
              "west": "fountain"
            },
            "contains": ["dream_bottle_2", "magic_coin_1"]
          },
          "fairy_doors": {
            "sublocation_id": "fairy_doors",
            "name": "Wall of Fairy Doors",
            "description": "Four small doors decorated with various symbols.",
            "interactable": true,
            "exits": ["entrance"],
            "cardinal_exits": {
              "west": "entrance"
            }
          },
          "fountain": {
            "sublocation_id": "fountain",
            "name": "Magical Fountain",
            "description": "A fountain that glows with ethereal light.",
            "interactable": true,
            "exits": ["shelf_area"],
            "cardinal_exits": {
              "east": "shelf_area"
            }
          }
        }
      }
    }
  }
}
```

**Graph Representation Options:**

### Option 1: Embedded Adjacency Lists (Recommended for MVP)

Each sublocation contains its own `exits` array - this forms an **adjacency list representation** of the graph.

```json
"entrance": {
  "exits": ["shelf_area", "fairy_doors"]  // ← Adjacency list: neighbors of "entrance"
}
```

**Graph Structure:**
```
entrance ←→ shelf_area
    ↓           ↓
fairy_doors  fountain
```

**Pros:**
- Simple, co-located with location data
- Easy to read and edit
- No separate graph file needed
- Fast lookup: O(1) to get neighbors

**Cons:**
- Bidirectional connections require duplication (entrance → shelf_area AND shelf_area → entrance)
- No validation that connections are symmetric
- Harder to add edge metadata (weights, conditions)

**Implementation:**
```python
def get_exits(location, sublocation):
    """Get all reachable sublocations from current position."""
    subloc_data = locations[waypoint][location]["sublocations"][sublocation]
    return subloc_data.get("exits", [])

def can_move_to(current, target):
    """Check if movement is allowed."""
    return target in get_exits(current["location"], current["sublocation"])
```

### Option 2: Centralized Edge List (For Complex Systems)

Store navigation graph separately from location metadata.

**File:** `world/navigation.json`

```json
{
  "waypoint_28a_store": {
    "woander_store": {
      "edges": [
        {
          "from": "entrance",
          "to": "shelf_area",
          "bidirectional": true,
          "cost": 1,
          "cardinal": "north"
        },
        {
          "from": "entrance",
          "to": "fairy_doors",
          "bidirectional": true,
          "cost": 1,
          "cardinal": "east"
        },
        {
          "from": "shelf_area",
          "to": "fountain",
          "bidirectional": true,
          "cost": 2,
          "cardinal": "west"
        }
      ]
    }
  }
}
```

**Pros:**
- Single source of truth for navigation
- Easy to add edge metadata (cost, conditions, one-way vs bidirectional)
- Simple validation (check bidirectional consistency)
- Better for pathfinding algorithms (A*, Dijkstra)

**Cons:**
- Separate file to maintain
- Extra lookup when checking exits
- Overkill for simple navigation

**Implementation:**
```python
def build_adjacency_list(edges):
    """Convert edge list to adjacency list for fast lookups."""
    graph = defaultdict(list)
    for edge in edges:
        graph[edge["from"]].append(edge["to"])
        if edge.get("bidirectional", True):
            graph[edge["to"]].append(edge["from"])
    return graph

def get_exits(location, sublocation):
    """Get exits using centralized graph."""
    return navigation_graph[waypoint][location][sublocation]
```

### Option 3: Hybrid (Recommended Approach)

**For MVP Phase 1-2:** Use **embedded adjacency lists** (`exits` arrays in locations.json)
- Simple, fast, co-located with location data
- Sufficient for 5-20 sublocations per location

**For Phase 3-4 or complex systems:** Migrate to **centralized edge list** (navigation.json)
- Add when you need: pathfinding, conditional exits, one-way doors, edge metadata
- Can auto-generate from embedded exits as migration path

**Migration command:**
```
Admin: "@export navigation woander_store"
Game: ✓ Exported navigation graph to world/navigation_woander_store.json
      (50 edges extracted from 25 sublocations)
```

### Ensuring Graph Consistency

**Problem:** With embedded adjacency lists, bidirectional connections can become inconsistent.

**Example of inconsistency:**
```json
"entrance": {"exits": ["shelf_area"]},
"shelf_area": {"exits": ["fountain"]}  // ← Missing "entrance"!
```

**Solution: Validation on @connect**

```python
async def _admin_connect_sublocations(self, from_id, to_id, bidirectional=True):
    """Add navigation link between sublocations."""

    # Add forward connection
    from_subloc["exits"].append(to_id)

    if bidirectional:
        # Add reverse connection automatically
        to_subloc["exits"].append(from_id)

    return {
        "success": True,
        "narrative": f"✓ Connected {from_id} ↔ {to_id} (bidirectional)"
    }

async def _validate_graph_consistency(self, location_data):
    """Check that all bidirectional connections are symmetric."""
    issues = []

    for subloc_id, subloc_data in location_data["sublocations"].items():
        for exit_id in subloc_data.get("exits", []):
            # Check reverse connection exists
            exit_subloc = location_data["sublocations"][exit_id]
            if subloc_id not in exit_subloc.get("exits", []):
                issues.append(f"{subloc_id} → {exit_id} but not {exit_id} → {subloc_id}")

    return issues
```

### Graph Representation Summary

| Aspect | Embedded (MVP) | Centralized (Advanced) |
|--------|----------------|------------------------|
| **File** | `locations.json` with `exits` arrays | Separate `navigation.json` |
| **Structure** | Adjacency list (embedded) | Edge list (centralized) |
| **Lookup Speed** | O(1) - direct array access | O(1) - prebuilt adjacency list |
| **Validation** | Manual or @connect command | Automatic consistency checks |
| **Pathfinding** | BFS on adjacency list | A*/Dijkstra with edge weights |
| **Use Case** | Simple navigation, MVP | Complex systems, conditional exits |

**Recommendation:** Start with **embedded adjacency lists** (Option 1), add validation to `@connect` command, migrate to **centralized edge list** (Option 2) when you need:
- Pathfinding with costs
- Conditional navigation (locked doors, quest gates)
- One-way passages
- 50+ sublocations in a single location

---

## Player Commands

### Navigation Commands

| Command | Example | Description |
|---------|---------|-------------|
| `go <location>` | "go woander_store" | Move to a different location within current waypoint |
| `go to <sublocation>` | "go to shelf_area" | Move to specific sublocation (graph-based connection) |
| `move to <sublocation>` | "move to shelf_1" | Alias for `go to` |
| `enter <location>` | "enter woander_store" | Enter a location from waypoint |
| `exit` / `leave` | "exit" | Leave current location (go back to previous) |
| `back` | "go back" | Return to previous location in history |
| `north` / `south` / `east` / `west` | "go north" | **Optional** cardinal movement (only if explicitly mapped) |

**Note on Navigation:** Movement is primarily **graph-based** using named sublocation connections (e.g., "go to shelf_area", "move to fountain"). Cardinal directions (north/south/east/west) are optional shortcuts that can be defined for specific connections, but are NOT required. This allows natural indoor navigation where "go to the shelves" is more intuitive than "go north".

### Observation Commands

| Command | Example | Description |
|---------|---------|-------------|
| `look` | "look around" | Describe current location and visible sublocations |
| `look at <target>` | "look at the mushroom shelf" | Examine specific sublocation or item |
| `examine <target>` | "examine the bottle" | Detailed inspection of item or feature |
| `inspect <item>` | "inspect dream_bottle" | Detailed item examination (player view) |
| `where` / `where am I` | "where" | Show current location hierarchy |
| `exits` | "exits" | Show available exits/connections from current location |
| `map` | "map" | Show location map (if available) |

### Interaction Commands

| Command | Example | Description |
|---------|---------|-------------|
| `take <item>` | "take dream_bottle" | Pick up item from current sublocation |
| `get <item>` | "get bottle" | Alias for `take` |
| `drop <item>` | "drop the bottle" | Place item at current sublocation |
| `give <item> to <target>` | "give bottle to fairy" | Transfer item to NPC or location |
| `use <item>` / `use <item> on <target>` | "use key on door" | Use/activate item (optionally with target) |
| `inventory` / `inv` / `i` | "inv" | List all items player is carrying |

### Social Commands

| Command | Example | Description |
|---------|---------|-------------|
| `talk to <npc>` | "talk to elder squirrel" | Initiate conversation with NPC |
| `ask <npc> about <topic>` | "ask squirrel about acorns" | Query NPC about specific topic |
| `greet <npc>` | "greet the fairy" | Say hello to NPC |

### Meta Commands

| Command | Example | Description |
|---------|---------|-------------|
| `help` | "help" | Show available player commands |
| `help <command>` | "help take" | Show detailed help for specific command |

## Admin Commands

Admin commands use the `@` prefix, inspired by MUD/MOO conventions.

### Waypoint Management

| Command | Example | Description |
|---------|---------|-------------|
| `@create waypoint <id>` | "@create waypoint waypoint_29" | Create new waypoint |
| `@edit waypoint <id>` | "@edit waypoint waypoint_28a" | Edit waypoint properties |
| `@delete waypoint <id>` | "@delete waypoint waypoint_old" | Remove waypoint (cascade delete) |
| `@move waypoint <id>` | "@move waypoint waypoint_28a 37.7750 -122.4195" | Change GPS coordinates |
| `@describe waypoint <id>` | "@describe waypoint waypoint_28a A mystical grove..." | Update description |

### Location Management

| Command | Example | Description |
|---------|---------|-------------|
| `@create location <waypoint> <id>` | "@create location waypoint_28a forest_path" | Add location to waypoint |
| `@edit location <waypoint> <id>` | "@edit location waypoint_28a clearing" | Edit location properties |
| `@delete location <waypoint> <id>` | "@delete location waypoint_28a old_area" | Remove location |
| `@describe location <waypoint> <id>` | "@describe location waypoint_28a clearing A peaceful..." | Update description |

### Sublocation Management

| Command | Example | Description |
|---------|---------|-------------|
| `@create sublocation <waypoint> <location> <id>` | "@create sublocation waypoint_28a clearing rock_1" | Add sublocation |
| `@edit sublocation <waypoint> <location> <id>` | "@edit sublocation waypoint_28a clearing shelf_1" | Edit sublocation |
| `@delete sublocation <waypoint> <location> <id>` | "@delete sublocation waypoint_28a clearing old_spot" | Remove sublocation |
| `@describe sublocation <waypoint> <location> <id>` | "@describe sublocation waypoint_28a clearing shelf_1 A shelf..." | Update description |
| `@flag sublocation <waypoint> <location> <id>` | "@flag sublocation waypoint_28a clearing shelf_1 interactable true" | Set property flag |

### Item Management

| Command | Example | Description |
|---------|---------|-------------|
| `@spawn item <template> at <location>` | "@spawn item dream_bottle at waypoint_28a clearing shelf_1" | Create item instance at location |
| `@move item <instance_id> to <location>` | "@move item dream_bottle_1 to waypoint_28a clearing rock_1" | Relocate item instance |
| `@edit item <instance_id>` | "@edit item dream_bottle_1" | Modify item instance state |
| `@delete item <instance_id>` | "@delete item dream_bottle_old" | Remove item instance |
| `@inspect item <instance_id>` | "@inspect item dream_bottle_1" | Show full item state (including metadata) |

### NPC Management

| Command | Example | Description |
|---------|---------|-------------|
| `@spawn npc <template> at <location>` | "@spawn npc elder_squirrel at waypoint_28a clearing ancient_tree" | Create NPC instance |
| `@move npc <instance_id> to <location>` | "@move npc elder_squirrel_1 to waypoint_28a pond_area" | Relocate NPC |
| `@edit npc <instance_id>` | "@edit npc elder_squirrel_1" | Modify NPC state |
| `@delete npc <instance_id>` | "@delete npc old_npc_1" | Remove NPC instance |
| `@inspect npc <instance_id>` | "@inspect npc elder_squirrel_1" | Show full NPC state |

### Navigation Management

| Command | Example | Description |
|---------|---------|-------------|
| `@connect <from> to <to>` | "@connect entrance to shelf_area" | Add graph link between sublocations (bidirectional) |
| `@connect <from> to <to> as <direction>` | "@connect entrance to shelf_area as north" | Add connection with optional cardinal direction shortcut |
| `@disconnect <from> from <to>` | "@disconnect entrance from shelf_area" | Remove connection |
| `@exit <location> to <destination>` | "@exit woander_store to waypoint_28a" | Define location exit destination |

**Navigation Philosophy:**
- Primary method: Graph-based connections (sublocation to sublocation)
- Optional enhancement: Cardinal direction shortcuts (north/south/east/west)
- Player commands: "go to shelf_area" (graph) OR "go north" (cardinal, if defined)

### Bulk Operations

| Command | Example | Description |
|---------|---------|-------------|
| `@list waypoints` | "@list waypoints" | Show all waypoints |
| `@list locations <waypoint>` | "@list locations waypoint_28a" | Show locations in waypoint |
| `@list sublocations <waypoint> <location>` | "@list sublocations waypoint_28a clearing" | Show sublocations in location |
| `@list items at <location>` | "@list items at waypoint_28a clearing shelf_1" | Show items at specific location |
| `@list templates [type]` | "@list templates item" | Show all templates (optionally filtered by type) |
| `@export waypoint <id>` | "@export waypoint waypoint_28a" | Export waypoint to JSON |
| `@import waypoint <file>` | "@import waypoint waypoint_30.json" | Import waypoint from JSON |

### Inspection & Debugging

| Command | Example | Description |
|---------|---------|-------------|
| `@where <target>` | "@where louisa" | Show current location of NPC or item instance |
| `@find <name>` | "@find dream_bottle" | Search all instances by name or template |
| `@dump <location>` | "@dump woander_store" | Export location as JSON to file |
| `@stats` | "@stats" | Show world statistics (waypoint/item/NPC counts) |
| `@help` / `@help <command>` | "@help create" | Show admin command help |

### Mode Switching

| Command | Example | Description |
|---------|---------|-------------|
| `@admin` | "@admin" | Enter admin mode (all commands treated as admin) |
| `@play` | "@play" | Return to player mode |
| `@sudo <command>` | "@sudo edit item 5 state.glow_color purple" | Execute single admin command while in play mode |

## Session Context Tracking

### Player Position in Graph

**How We Track Position:**

The player's current position in the navigation graph is stored in a **session state file** unique to each player. This file persists between commands and enables stateful navigation.

**File:** `experiences/wylding-woods/sessions/{user_id}/state.json`

```json
{
  "user_id": "jason@aeonia.ai",
  "experience": "wylding-woods",

  "current_position": {
    "waypoint": "waypoint_28a_store",
    "location": "woander_store",
    "sublocation": "entrance"
  },

  "location_history": [
    {
      "waypoint": "waypoint_28a_store",
      "location": "woander_store",
      "sublocation": "shelf_area",
      "timestamp": "2025-10-27T08:05:00Z",
      "action": "go to entrance"
    },
    {
      "waypoint": "waypoint_28a_store",
      "location": "woander_store",
      "sublocation": "fairy_doors",
      "timestamp": "2025-10-27T08:03:00Z",
      "action": "go to shelf_area"
    }
  ],

  "inventory": [
    {
      "instance_id": "dream_bottle_1",
      "template": "dream_bottle",
      "acquired_at": "2025-10-27T08:05:00Z"
    }
  ],

  "metadata": {
    "session_start": "2025-10-27T07:00:00Z",
    "last_command": "2025-10-27T08:10:00Z",
    "total_moves": 15
  }
}
```

**Quest progress stored separately:**

**File:** `experiences/wylding-woods/sessions/{user_id}/progress.json`

```json
{
  "user_id": "jason@aeonia.ai",
  "quests": {
    "bottle_quest": {
      "status": "in_progress",
      "checkpoints": ["collected_bottle"],
      "started_at": "2025-10-27T07:30:00Z"
    }
  },
  "achievements": [],
  "statistics": {
    "items_collected": 5,
    "locations_visited": 12
  }
}
```

### Position Update Flow

**1. Player Issues Movement Command:**
```
You: "go to shelf_area"
```

**2. KB Agent Processes Command:**
```python
async def execute_game_command_v2(command, experience, user_context):
    # Load current session state
    session = await self._load_session(experience, user_context["user_id"])

    # Current position from session
    current_pos = session["current_position"]
    # → {"waypoint": "waypoint_28a_store", "location": "woander_store", "sublocation": "entrance"}

    # Parse command
    parsed = await self._parse_player_command(command, session)
    # → {"action": "go", "target": "shelf_area"}

    # Validate movement using graph
    if await self._can_move_to(current_pos, parsed["target"]):
        # Update position
        session["current_position"]["sublocation"] = parsed["target"]

        # Add to history
        session["location_history"].insert(0, {
            "waypoint": current_pos["waypoint"],
            "location": current_pos["location"],
            "sublocation": current_pos["sublocation"],
            "timestamp": datetime.utcnow().isoformat(),
            "action": command
        })

        # Save updated session
        await self._save_session(experience, user_context["user_id"], session)

        return {
            "success": True,
            "narrative": "You move to the shelf area...",
            "new_position": session["current_position"]
        }
```

**3. Validation Against Graph:**
```python
async def _can_move_to(self, current_pos, target_sublocation):
    """Check if movement is valid using navigation graph."""

    # Load location data
    location_data = await self._load_location(
        current_pos["waypoint"],
        current_pos["location"]
    )

    # Get current sublocation's exits
    current_subloc = location_data["sublocations"][current_pos["sublocation"]]
    exits = current_subloc.get("exits", [])

    # Check if target is in exits array (adjacency list)
    if target_sublocation in exits:
        return True

    # Also check cardinal directions
    cardinal_exits = current_subloc.get("cardinal_exits", {})
    if target_sublocation in cardinal_exits.values():
        return True

    return False
```

### Session Lifecycle

**Session Creation (First Command):**
```python
async def _load_session(self, experience, user_id):
    """Load or create player session."""
    session_path = f"{KB_BASE}/experiences/{experience}/sessions/{user_id}/state.json"

    if not os.path.exists(session_path):
        # Create new session at experience's starting location
        default_waypoint = await self._get_default_waypoint(experience)
        default_location = default_waypoint["locations"][0]  # First location
        default_sublocation = default_location["default_sublocation"]

        session = {
            "user_id": user_id,
            "experience": experience,
            "current_position": {
                "waypoint": default_waypoint["waypoint_id"],
                "location": default_location["location_id"],
                "sublocation": default_sublocation
            },
            "location_history": [],
            "inventory": [],
            "metadata": {
                "session_start": datetime.utcnow().isoformat(),
                "last_command": datetime.utcnow().isoformat(),
                "total_moves": 0
            }
        }

        await self._save_session(experience, user_id, session)
    else:
        # Load existing session
        with open(session_path, 'r') as f:
            session = json.load(f)

    return session
```

**Session Persistence:**
```python
async def _save_session(self, experience, user_id, session):
    """Save session state to disk."""
    session_path = f"{KB_BASE}/experiences/{experience}/sessions/{user_id}/state.json"

    # Update metadata
    session["metadata"]["last_command"] = datetime.utcnow().isoformat()

    # Ensure directory exists
    os.makedirs(os.path.dirname(session_path), exist_ok=True)

    # Write atomically (temp file + rename)
    temp_path = f"{session_path}.tmp"
    with open(temp_path, 'w') as f:
        json.dump(session, f, indent=2)
    os.rename(temp_path, session_path)
```

**Session Timeout:**
```python
async def _is_session_expired(self, session, timeout_hours=24):
    """Check if session should be reset."""
    last_command = datetime.fromisoformat(session["metadata"]["last_command"])
    elapsed = datetime.utcnow() - last_command
    return elapsed.total_seconds() > (timeout_hours * 3600)
```

### Position Tracking in Practice

**Example: Complete Movement Cycle**

```
Initial state (sessions/jason@aeonia.ai/state.json):
{
  "current_position": {"waypoint": "waypoint_28a_store", "location": "woander_store", "sublocation": "entrance"}
}

Command: "go to shelf_area"

Validation:
1. Load locations.json → woander_store → entrance → exits = ["shelf_area", "fairy_doors"]
2. Check if "shelf_area" in exits → YES ✓
3. Movement allowed

Update state:
{
  "current_position": {"waypoint": "waypoint_28a_store", "location": "woander_store", "sublocation": "shelf_area"},
  "location_history": [
    {"sublocation": "entrance", "timestamp": "2025-10-27T08:10:00Z", "action": "go to shelf_area"}
  ]
}

Response:
{
  "success": true,
  "narrative": "You move to the shelf area. Three wooden shelves line the walls...",
  "new_position": {"waypoint": "waypoint_28a_store", "location": "woander_store", "sublocation": "shelf_area"}
}
```

**Why Session Files Matter:**

1. **Stateful Navigation:** Player doesn't repeat location in every command
   - ✓ "look" → uses current_position automatically
   - ✓ "go to shelf_area" → validates against current_position.exits

2. **History Tracking:** Enable "back" command
   - Player: "back" → retrieves location_history[0] → moves there

3. **Inventory Persistence:** Items survive between sessions
   - Player collects bottle → saved to session → still in inventory tomorrow

4. **Quest Progress:** Long-term quest tracking
   - Separate progress.json for checkpoint tracking
   - Doesn't clutter position state

### Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Player Command: "go to shelf_area"                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. Load Session State                                           │
│    sessions/jason@aeonia.ai/state.json                          │
│    → current_position: {waypoint, location, sublocation}        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Load Location Graph                                          │
│    world/locations.json → waypoint → location → sublocations    │
│    → entrance.exits = ["shelf_area", "fairy_doors"]             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Validate Movement                                            │
│    Is "shelf_area" in entrance.exits? → YES ✓                   │
│    (Graph adjacency check)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Update Session State                                         │
│    current_position.sublocation = "shelf_area"                  │
│    location_history.insert(previous position)                   │
│    metadata.last_command = now()                                │
│    Save to sessions/jason@aeonia.ai/state.json                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Generate Narrative Response                                  │
│    "You move to the shelf area. Three wooden shelves..."        │
│    + new_position data                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Files Involved:**

| File | Purpose | Updated On |
|------|---------|------------|
| `sessions/{user_id}/state.json` | Current position + inventory | Every command |
| `sessions/{user_id}/progress.json` | Quest checkpoints | Quest events only |
| `world/locations.json` | Graph structure (exits arrays) | Admin commands only |
| `instances/items/*.json` | Item instances in world | Item spawn/move/collect |

**Position Tracking Summary:**

- **Where:** Session state file per player
- **What:** `current_position: {waypoint, location, sublocation}`
- **How:** Load → validate against graph → update → save
- **Why:** Enables stateful navigation without repeating location

## Implementation Architecture

### KB Agent Command Router

**File:** `app/services/kb/kb_agent.py`

**New Method:** `execute_game_command_v2()`

```python
async def execute_game_command_v2(
    self,
    command: str,
    experience: str,
    user_context: Dict[str, Any],
    session_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute game command with location hierarchy and admin support.

    Flow:
    1. Load player session context (waypoint/location/sublocation)
    2. Parse command (detect @ prefix for admin vs player)
    3. Extract targets and parameters
    4. Route to appropriate handler (player vs admin)
    5. Update session state
    6. Return narrative + state changes
    """

    user_id = user_context.get("user_id", "unknown")
    role = user_context.get("role", "player")

    # Load current session
    session = await self._load_session(experience, user_id)

    # Parse command type
    is_admin = command.strip().startswith("@")

    if is_admin and role != "admin":
        return {
            "success": False,
            "error": {"code": "unauthorized", "message": "Admin commands require admin role"},
            "narrative": "🚫 You don't have permission to use admin commands."
        }

    if is_admin:
        result = await self._execute_admin_command(command, experience, session)
    else:
        result = await self._execute_player_command(command, experience, session)

    # Update session state
    if result.get("success"):
        await self._save_session(experience, user_id, session)

    return result
```

### Player Command Handler

```python
async def _execute_player_command(
    self,
    command: str,
    experience: str,
    session: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Route player commands to appropriate handlers.

    Navigation: go, move, enter, leave, back
    Observation: look, examine, where
    Interaction: take, drop, give, use, inventory
    Social: talk, ask, greet
    """

    # Parse command with LLM
    parsed = await self._parse_player_command(command, session)

    action = parsed.get("action")

    if action in ["go", "move", "enter"]:
        return await self._handle_navigation(parsed, session)
    elif action in ["look", "examine", "where"]:
        return await self._handle_observation(parsed, session)
    elif action in ["take", "drop", "give", "use", "inventory"]:
        return await self._handle_interaction(parsed, session)
    elif action in ["talk", "ask", "greet"]:
        return await self._handle_social(parsed, session)
    else:
        return {"success": False, "error": {"code": "unknown_command"}}
```

### Admin Command Handler

```python
async def _execute_admin_command(
    self,
    command: str,
    experience: str,
    session: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Route admin commands to appropriate handlers.

    Waypoint: @create/edit/delete/move/describe waypoint
    Location: @create/edit/delete/describe location
    Sublocation: @create/edit/delete/describe/flag sublocation
    Item: @spawn/move/edit/delete/inspect item
    NPC: @spawn/move/edit/delete/inspect npc
    Bulk: @list/export/import
    """

    # Parse admin command (simpler than player commands)
    parsed = await self._parse_admin_command(command)

    command_type = parsed.get("command")  # e.g., "create", "edit", "delete"
    target_type = parsed.get("target")    # e.g., "waypoint", "location", "item"

    handler_map = {
        ("create", "waypoint"): self._admin_create_waypoint,
        ("edit", "waypoint"): self._admin_edit_waypoint,
        ("delete", "waypoint"): self._admin_delete_waypoint,
        ("create", "location"): self._admin_create_location,
        ("spawn", "item"): self._admin_spawn_item,
        ("list", "waypoints"): self._admin_list_waypoints,
        # ... more mappings
    }

    handler = handler_map.get((command_type, target_type))
    if handler:
        return await handler(parsed, experience)
    else:
        return {"success": False, "error": {"code": "unknown_admin_command"}}
```

## Example Gameplay Flows

### Player Flow 1: Exploration and Quest (Natural Environment)

```
You: "where am I?"
Game: You are at The Fairy Grove (waypoint_28a), standing in the Central Clearing,
      currently at the Mushroom Shelf (shelf_1).

You: "look around"
Game: You're in a peaceful clearing surrounded by ancient trees. You can see:
      - A mushroom shelf (shelf_1) with a glowing bottle
      - A tiny fairy house door (fairy_door_1) marked with a spiral
      - An ancient oak tree (ancient_tree) with deep roots

You: "examine the bottle"
Game: You see a dream bottle with a turquoise glow and a spiral symbol etched on its side.

You: "take the bottle"
Game: You carefully pick up the dream bottle. It feels warm to the touch.
      [Inventory updated: dream_bottle_1 added]

You: "go to the pond"
Game: You walk toward the quiet pond. The air grows cooler near the water.
      [Location updated: waypoint_28a → pond_area → water_edge]

You: "back"
Game: You return to the Central Clearing.
      [Location updated: waypoint_28a → clearing → shelf_1]

You: "give bottle to fairy door"
Game: You place the dream bottle near the spiral fairy house door. The door glows briefly!
      [Quest progress: bottle_quest → completed]
      [Inventory updated: dream_bottle_1 removed]
```

### Player Flow 2: Indoor Exploration (Woander Store - Graph Navigation)

```
You: "look"
Game: You're at the entrance of Woander Store. A mystical shop with glowing displays...

You: "exits"
Game: You can go to: shelf_area, fairy_doors

You: "go to shelf_area"
Game: You move to the shelf area. Three wooden shelves line the walls with mysterious items...

You: "look at shelf_area"
Game: You see:
      - dream_bottle (spiral symbol, turquoise glow)
      - magic_coin (glowing gold coin)

You: "take dream_bottle"
Game: You carefully lift the dream bottle. It pulses with soft light.

You: "inventory"
Game: You're carrying:
      - dream_bottle (spiral symbol)

You: "exits"
Game: You can go to: entrance, fountain

You: "go to entrance"
Game: You return to the entrance.

You: "go to fairy_doors"
Game: You move to the fairy doors area. Four small doors decorated with various symbols...

You: "examine fairy_door_1"
Game: A small door decorated with a spiral symbol. It seems to be waiting for something...

You: "use dream_bottle at fairy_door_1"
Game: The bottle dissolves into light and flows into the door! The spiral glows brightly.
      [Quest progress: bottle_quest → completed]

You: "go north"
Game: [If cardinal_exits defined] You move to the entrance.
      [If not defined] I don't understand that direction. Try "exits" to see where you can go.
```

**Note:** This flow demonstrates **graph-based navigation** where players use place names ("go to shelf_area") rather than cardinal directions. The final "go north" command shows optional cardinal shortcuts - they work if defined, but aren't required for navigation.

### Admin Flow 1: Building a New Location from Scratch

```
You: "@admin"
Game: Entering admin mode. Type @play to return to player mode.

Admin: "@create location waypoint_28a forest_path"
Game: ✓ Created location 'forest_path' in waypoint_28a with default properties.
      [Use @describe to add description]

Admin: "@describe location waypoint_28a forest_path A winding path through dense forest, sunlight filtering through the canopy."
Game: ✓ Updated description for forest_path.

Admin: "@create sublocation waypoint_28a forest_path hollow_log"
Game: ✓ Created sublocation 'hollow_log' in waypoint_28a → forest_path.

Admin: "@describe sublocation waypoint_28a forest_path hollow_log A fallen log with a hollow opening."
Game: ✓ Updated description for hollow_log.

Admin: "@flag sublocation waypoint_28a forest_path hollow_log interactable true"
Game: ✓ Set interactable = true for hollow_log.

Admin: "@connect entrance to hollow_log"
Game: ✓ Connected entrance ↔ hollow_log (bidirectional graph link).
      Players can now: "go to hollow_log" (from entrance) or "go to entrance" (from hollow_log)

Admin: "@connect entrance to hollow_log as west"
Game: ✓ Added cardinal shortcut: west → hollow_log
      Players can also: "go west" (from entrance)

Admin: "@spawn item mushroom_red at waypoint_28a forest_path hollow_log"
Game: ✓ Spawned mushroom_red instance (mushroom_red_1) at hollow_log.
      [Instance ID: mushroom_red_1]

Admin: "@list items at waypoint_28a forest_path hollow_log"
Game: Items at hollow_log:
      - Instance #mushroom_red_1: mushroom_red (edible: true)

Admin: "@inspect item mushroom_red_1"
Game: Item Instance: mushroom_red_1
      Template: mushroom_red
      Location: waypoint_28a → forest_path → hollow_log
      State: { "edible": true, "toxicity": "mild" }
      Metadata: { "created_at": "2025-10-27T09:00:00Z", "created_by": "admin@gaia.dev" }

Admin: "@play"
Game: Returning to player mode. You can now explore the world you've built!
```

### Admin Flow 2: Managing Existing Content

```
You: "@admin"
Game: Entering admin mode.

Admin: "@list locations waypoint_28a"
Game: Locations in waypoint_28a:
      1. clearing (Central Clearing) - 3 sublocations
      2. pond_area (Quiet Pond) - 2 sublocations
      3. forest_path (A winding path...) - 1 sublocation

Admin: "@where louisa"
Game: NPC 'louisa' (instance louisa_1) is located at:
      waypoint_28a → woander_store → fairy_doors

Admin: "@move npc louisa_1 to waypoint_28a clearing ancient_tree"
Game: ✓ Moved louisa_1 to waypoint_28a → clearing → ancient_tree

Admin: "@find dream_bottle"
Game: Found 3 instances of 'dream_bottle':
      - dream_bottle_1: waypoint_28a → clearing → shelf_1 (collected by jason@aeonia.ai)
      - dream_bottle_2: waypoint_28a_store → woander_store → shelf_area
      - dream_bottle_3: waypoint_28a → clearing → fairy_door_1 (quest completed)

Admin: "@dump woander_store"
Game: ✓ Exported location to: experiences/wylding-woods/exports/woander_store_20251027_093000.json

Admin: "@stats"
Game: World Statistics for 'wylding-woods':
      - Waypoints: 2
      - Locations: 5
      - Sublocations: 12
      - Item Instances: 15
      - NPC Instances: 3
      - Active Players: 8

Admin: "@export waypoint waypoint_28a"
Game: ✓ Exported waypoint_28a to experiences/wylding-woods/exports/waypoint_28a_20251027.json

Admin: "@play"
Game: Returning to player mode.
```

### Mixed Mode: Quick Admin Edit During Play

```
You: "look"
Game: You see a dream bottle here, but it looks wrong...

You: "@sudo edit item dream_bottle_1 state.glow_color purple"
Game: [Admin] ✓ Updated dream_bottle_1: state.glow_color = "purple"

You: "look"
Game: You see a dream bottle with a purple glow and a spiral symbol...
      Much better!

You: "take dream_bottle"
Game: You carefully pick up the dream bottle. It feels warm to the touch.
```

## Implementation Phases

### Phase 1: Location Hierarchy (Week 1)
**Goal:** Hierarchical location tracking with navigation

**Tasks:**
1. Create `locations.json` schema and example data
2. Implement session context loading/saving
3. Add navigation commands (go, move, enter, leave, back)
4. Add observation commands (look, examine, where)
5. Update LLM parsing prompt for location context
6. Test location transitions and history tracking

**Deliverables:**
- ✅ `locations.json` created with waypoint_28a example
- ✅ Session state management (load/save)
- ✅ Navigation command handlers
- ✅ Location context in narrative responses

### Phase 2: Enhanced Interaction (Week 2)
**Goal:** Items and inventory with location awareness

**Tasks:**
1. Integrate instance management with location hierarchy
2. Implement inventory commands (take, drop, give, use)
3. Update item spawn/collection to track current location
4. Add location-based item visibility filtering
5. Implement quest checkpoint triggers
6. Test multi-location item interactions

**Deliverables:**
- ✅ Items tied to specific sublocations
- ✅ Inventory system with location tracking
- ✅ Quest progress based on location checkpoints

### Phase 3: Admin Commands (Week 3)
**Goal:** World-building tools for content creators

**Tasks:**
1. Implement @ command detection and routing
2. Add waypoint CRUD operations
3. Add location/sublocation CRUD operations
4. Add item/NPC spawn and management commands
5. Implement bulk operations (list, export, import)
6. Add validation and error handling for admin commands
7. Test world creation workflow end-to-end

**Deliverables:**
- ✅ Full admin command set functional
- ✅ JSON export/import for waypoints
- ✅ Content validation and error feedback

### Phase 4: Polish & Documentation (Week 4)
**Goal:** Production-ready system with comprehensive docs

**Tasks:**
1. Add command aliases (inv, get, etc.)
2. Improve narrative generation for all actions
3. Add command help system (@help, help)
4. Create admin guide and player tutorial
5. Add audit logging for admin actions
6. Performance testing and optimization
7. Integration testing with Unity client

**Deliverables:**
- ✅ Command reference documentation
- ✅ Admin and player guides
- ✅ Audit log for world changes
- ✅ Performance benchmarks

## Testing Strategy

### Unit Tests

**Player Commands:**
```python
async def test_player_navigation():
    """Test go/move/enter commands update session context"""
    result = await kb_agent.execute_game_command_v2(
        command="go to the pond",
        experience="wylding-woods",
        user_context={"user_id": "test_user", "role": "player"}
    )
    assert result["success"] == True
    assert result["session"]["current_location"] == "pond_area"

async def test_player_inventory():
    """Test take/drop commands modify inventory"""
    # ... test inventory changes
```

**Admin Commands:**
```python
async def test_admin_create_location():
    """Test @create location command"""
    result = await kb_agent.execute_game_command_v2(
        command="@create location waypoint_28a test_area",
        experience="wylding-woods",
        user_context={"user_id": "admin", "role": "admin"}
    )
    assert result["success"] == True
    # Verify location exists in locations.json
```

### Integration Tests

**Full Player Flow:**
```python
async def test_full_exploration_flow():
    """Test complete exploration and quest completion"""
    # Start at waypoint
    # Look around
    # Take item
    # Navigate to different location
    # Return item to quest location
    # Verify quest completion
```

**Full Admin Flow:**
```python
async def test_full_world_building_flow():
    """Test creating waypoint → location → sublocation → item"""
    # Create waypoint
    # Add location
    # Add sublocation
    # Spawn item
    # Verify player can interact with created content
```

### Manual Testing Scenarios

**Player Testing:**
1. Navigation: Move through multiple locations, test back command
2. Observation: Look at different sublocations, examine items
3. Interaction: Take items, check inventory, drop items
4. Quest: Complete full quest chain with checkpoints

**Admin Testing:**
1. Creation: Build complete waypoint from scratch
2. Editing: Modify existing content, verify changes appear
3. Deletion: Remove content, verify cascade deletes
4. Import/Export: Export waypoint, modify JSON, reimport

## File Structure

Complete directory structure for the enhanced system:

```
/kb/experiences/wylding-woods/
├── world/
│   ├── locations.json          # All waypoints/locations/sublocations
│   └── navigation.json         # (Optional) Connection graph for complex navigation
├── templates/
│   ├── items/
│   │   ├── dream_bottle.md
│   │   ├── magic_coin.md
│   │   └── mushroom_red.md
│   └── npcs/
│       ├── louisa.md
│       └── elder_squirrel.md
├── instances/
│   ├── manifest.json           # Central registry of all instances
│   ├── items/
│   │   ├── dream_bottle_1.json
│   │   ├── dream_bottle_2.json
│   │   ├── magic_coin_1.json
│   │   └── mushroom_red_1.json
│   └── npcs/
│       ├── louisa_1.json
│       └── elder_squirrel_1.json
├── sessions/
│   └── {user_id}/
│       ├── state.json          # Current location + inventory
│       └── progress.json       # Quest state + history
└── exports/
    ├── waypoint_28a_20251027.json
    └── woander_store_20251027_093000.json
```

**Key Files:**
- **world/locations.json**: Master location hierarchy (waypoints → locations → sublocations)
- **world/navigation.json**: Optional navigation graph for complex pathfinding
- **sessions/{user_id}/state.json**: Player's current position and inventory
- **exports/**: Admin-generated backups and world exports

## Dependencies

**Existing Systems:**
- Instance management (`kb_agent.py` lines 279-442)
- Game commands API (`game_commands_api.py`)
- LLM command parsing (Claude Haiku 4.5)
- Session state storage (file-based JSON)

**New Dependencies:**
- Location hierarchy data model (`world/locations.json`)
- Session context management (`sessions/{user_id}.json`)
- Admin command parser (simpler than player commands)
- Location validation and cascade delete logic
- Navigation graph support (optional `world/navigation.json`)

**No Changes Required:**
- Chat service integration (already routes to KB)
- Authentication system (role-based routing)
- Instance file structure (items/npcs JSON files)

## Integration with Existing System

### Backward Compatibility

**No Breaking Changes:**
- Existing `execute_game_command()` method remains functional
- New `execute_game_command_v2()` is additive, not replacement
- Current instance management methods unchanged
- File-based storage structure extended, not replaced

**Enhanced Parsing:**
```python
# Old: Location extraction from command text
parsed_action = {
    "action": "collect",
    "target": "dream_bottle",
    "waypoint": "waypoint_28a",  # From command or context
    "sublocation": "shelf_1"      # From command or context
}

# New: Plus session-based location tracking
session = {
    "current_waypoint": "waypoint_28a",
    "current_location": "woander_store",
    "current_sublocation": "entrance",
    "location_history": [...]
}
```

**Player State Always Tracked:**
- Every command updates `sessions/{user_id}/state.json`
- `look` command automatically uses current location context
- `go/move/enter` commands update location and return new description
- No need to repeat location in every command (unless changing location)

### Migration Path

**Phase 1: Parallel Systems**
- Both `execute_game_command()` and `execute_game_command_v2()` available
- Existing clients continue using v1
- New clients can opt into v2 with location tracking

**Phase 2: Gradual Migration**
- Add session state to existing players
- Enable location hierarchy for new waypoints
- Keep backward compatibility for simple commands

**Phase 3: Full Adoption**
- All commands route through v2
- v1 deprecated but still available
- Complete location hierarchy coverage

## Future Enhancements (Post-MVP)

**Not Included in Initial Implementation:**
1. **RBAC Content Filtering** - Filter locations/items by user permissions
2. **Real-time Multiplayer** - See other players in same location
3. **Location Events** - Time-based or trigger-based events at locations
4. **Dynamic Weather** - Location descriptions change with weather
5. **NPC Schedules** - NPCs move between locations on schedule
6. **Location Locking** - Require keys/quests to access locations
7. **Database Backend** - Replace file-based storage with PostgreSQL
8. **Web Admin UI** - Visual world editor instead of text commands

## Key Design Decisions

### 1. Hierarchical Location Tracking (Waypoint → Location → Sublocation)
**Why:** Provides the right level of granularity for both GPS-based AR (waypoints) and detailed indoor navigation (locations/sublocations). Mirrors real-world spatial hierarchy while enabling Zork-style interaction depth.

**Benefit:** Players always know where they are, context is preserved across commands, and developers can reason about spatial relationships easily.

### 2. Admin Commands Prefixed with @
**Why:** MUD/MOO tradition that's instantly recognizable and easy to parse. Clear visual distinction prevents accidental world edits during gameplay.

**Benefit:** Single character distinguishes builder mode from player mode. Familiar to anyone with MUD/MOO experience.

### 3. Location as Primary Context
**Why:** Natural conversation flow - "look" always uses current location, "take X" looks here first, movement updates context automatically.

**Benefit:** Players don't need to repeat location in every command. More natural language interaction.

### 4. File-Based Until Scale Demands DB
**Why:** MVP can move fast with JSON files. Clear migration path to PostgreSQL when needed (50k+ instances).

**Benefit:** Simple, version-controllable, fast to iterate. No database setup complexity for initial development.

### 5. Natural Language + Structured Commands (Player) vs Structured Only (Admin)
**Why:** Players should feel like they're having a conversation. Admins are building content and need precision.

**Examples:**
- Player: "pick up the bottle" OR "take dream_bottle" (both work)
- Admin: "@spawn item dream_bottle at waypoint_28a clearing shelf_1" (precise)

**Benefit:** Best of both worlds - natural player experience, precise admin tooling.

### 6. Mode Switching (@admin, @play, @sudo)
**Why:** Admins often need to quickly test player experience, then make edits, then test again.

**Benefit:** Seamless context switching without logging out/in. @sudo enables one-off edits during playtesting.

### 7. Session-Based Location Tracking
**Why:** Stateless parsing was forcing players to specify location every time. Stateful sessions enable natural conversation flow.

**Benefit:** "look" → "take bottle" → "go pond" works naturally without repeating location context.

### 8. Graph-Based Navigation with Optional Cardinal Directions
**Why:** Indoor spaces don't have clear north/south/east/west. "Go to the shelves" is more natural than "go north". Cardinal directions are shortcuts, not requirements.

**Implementation:**
- Primary: Graph links between sublocations (exits array)
- Optional: Cardinal shortcuts (cardinal_exits object)
- Player experience: "go to shelf_area" (always works) or "go north" (works if defined)

**Benefit:** Natural navigation for any environment (indoor stores, outdoor forests, abstract spaces) without forcing spatial metaphors that don't fit.

## Open Questions

1. **Session Timeout:** How long should session context persist? (Proposal: 24 hours)
2. **Location Limits:** Max sublocations per location? (Proposal: 10 for readability)
3. **Admin Permissions:** Should we track admin action attribution now? (Proposal: Yes, for audit)
4. **Export Format:** Should exports include instances or just templates? (Proposal: Separate exports)
5. **Cascade Deletes:** Confirm cascade behavior for waypoint deletion? (Proposal: Require explicit flag)
6. **Navigation Graph:** Use embedded exits in locations.json or separate navigation.json? (Proposal: Embedded for MVP, separate for complex systems)

---

**Next Steps:**
1. Review and approve design document
2. Create implementation tasks in project tracker
3. Begin Phase 1: Location hierarchy implementation
4. Set up test data for waypoint_28a with full location tree
5. Create example woander_store location for testing indoor navigation
