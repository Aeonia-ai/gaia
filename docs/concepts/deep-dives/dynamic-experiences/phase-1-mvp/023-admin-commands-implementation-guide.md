# Admin Commands Implementation Guide

## Overview

Admin commands provide structured, fast, non-LLM control over the game world. They use explicit syntax (`@command args`) for predictable behavior, unlike natural language commands that require LLM interpretation.

**Status**: ✅ **Implemented** - Core @list and @stats commands operational

## Architecture

### Command Flow

```
User sends "@list waypoints"
    ↓
execute_game_command() detects @ prefix
    ↓
Role check: user_context["role"] == "admin"?
    ↓
_execute_admin_command() parses and routes
    ↓
Handler method (_admin_list_waypoints)
    ↓
Read locations.json / instances / templates
    ↓
Return structured response
```

### File: `kb_agent.py`

- `execute_game_command()` - Entry point, detects @ prefix
- `_execute_admin_command()` - Command parser and router
- `_admin_list()` - @list command dispatcher
- `_admin_list_waypoints()` - List all waypoints
- `_admin_list_locations()` - List locations in waypoint
- `_admin_list_sublocations()` - List sublocations with exits
- `_admin_list_items()` - List items (all or filtered by location)
- `_admin_list_templates()` - List templates (all or by type)
- `_admin_stats()` - World statistics

## Implemented Commands

### @stats

Shows world statistics.

**Syntax:**
```bash
@stats
```

**Example Response:**
```
World Statistics for 'wylding-woods':
  - Waypoints: 1
  - Locations: 2
  - Sublocations: 10
  - Item Instances: 5
  - NPC Instances: 0
  - Active Players: 1
```

**Returns:**
```json
{
  "success": true,
  "narrative": "World Statistics...",
  "data": {
    "waypoints": 1,
    "locations": 2,
    "sublocations": 10,
    "item_instances": 5,
    "npc_instances": 0,
    "active_players": 1
  },
  "actions": []
}
```

---

### @list waypoints

List all waypoints in the experience.

**Syntax:**
```bash
@list waypoints
```

**Example Response:**
```
Waypoints:
  1. waypoint_28a - Woander Store Area (2 locations)
```

**Returns:**
```json
{
  "success": true,
  "narrative": "Waypoints:\n  1. waypoint_28a...",
  "data": {
    "waypoints": [
      {
        "id": "waypoint_28a",
        "name": "Woander Store Area",
        "location_count": 2
      }
    ]
  },
  "actions": []
}
```

---

### @list locations \<waypoint\>

List all locations within a waypoint.

**Syntax:**
```bash
@list locations waypoint_28a
```

**Example Response:**
```
Locations in waypoint_28a:
  1. clearing - Forest Clearing (6 sublocations)
  2. woander_store - Woander Store Interior (4 sublocations)
```

**Returns:**
```json
{
  "success": true,
  "narrative": "Locations in waypoint_28a...",
  "data": {
    "waypoint": "waypoint_28a",
    "locations": [
      {
        "id": "clearing",
        "name": "Forest Clearing",
        "sublocation_count": 6
      },
      {
        "id": "woander_store",
        "name": "Woander Store Interior",
        "sublocation_count": 4
      }
    ]
  },
  "actions": []
}
```

---

### @list sublocations \<waypoint\> \<location\>

List all sublocations in a location, showing the **navigation graph** (exits arrays).

**Syntax:**
```bash
@list sublocations waypoint_28a clearing
```

**Example Response:**
```
Sublocations in waypoint_28a → clearing:
  1. center - Center of Clearing (exits: shelf_1, shelf_2, shelf_3, fairy_door_1, magic_mirror)
  2. shelf_1 - Shelf 1 (exits: center, shelf_2)
  3. shelf_2 - Shelf 2 (exits: shelf_1, center, shelf_3)
  4. shelf_3 - Shelf 3 (exits: shelf_2, center, magic_mirror)
  5. fairy_door_1 - Fairy Door (exits: center, magic_mirror)
  6. magic_mirror - Magic Mirror (exits: center, fairy_door_1, shelf_3)
```

**Key Feature**: Shows the **graph-based navigation structure** - each sublocation's `exits` array defines adjacency relationships.

**Graph Visualization:**
```
       center (hub)
         / | \
shelf_1  |  fairy_door_1
    |    |       |
shelf_2  |   magic_mirror
    |    |       |
shelf_3 ─┴───────┘
```

**Returns:**
```json
{
  "success": true,
  "narrative": "Sublocations in waypoint_28a → clearing...",
  "data": {
    "waypoint": "waypoint_28a",
    "location": "clearing",
    "sublocations": [
      {
        "id": "center",
        "name": "Center of Clearing",
        "exits": ["shelf_1", "shelf_2", "shelf_3", "fairy_door_1", "magic_mirror"],
        "interactable": true
      }
    ]
  },
  "actions": []
}
```

---

### @list items

List all item instances across the entire experience.

**Syntax:**
```bash
@list items
```

**Example Response:**
```
All items in wylding-woods:
  1. louisa at waypoint_28a/fairy_door_1 (instance #1)
  2. dream_bottle at waypoint_28a/shelf_1 (instance #2)
  3. dream_bottle at waypoint_28a/shelf_2 (instance #3)
  4. dream_bottle at waypoint_28a/shelf_3 (instance #4)
  5. dream_bottle at waypoint_28a/magic_mirror (instance #5)
```

**Returns:**
```json
{
  "success": true,
  "narrative": "All items in wylding-woods...",
  "data": {
    "items": [
      {
        "id": 2,
        "template": "dream_bottle",
        "semantic_name": "dream_bottle",
        "instance_file": "items/dream_bottle_1.json",
        "location": "waypoint_28a",
        "sublocation": "shelf_1",
        "description": "Dream bottle with spiral symbol (turquoise glow)",
        "created_at": "2025-10-26T18:00:00Z"
      }
    ]
  },
  "actions": []
}
```

---

### @list items at \<waypoint\> \<location\> \<sublocation\>

List items at a specific sublocation.

**Syntax:**
```bash
@list items at waypoint_28a clearing shelf_1
```

**Example Response:**
```
Items at waypoint_28a → clearing → shelf_1:
  1. dream_bottle (instance #2, template: dream_bottle)
```

**Returns:**
```json
{
  "success": true,
  "narrative": "Items at waypoint_28a → clearing → shelf_1...",
  "data": {
    "items": [
      {
        "id": 2,
        "template": "dream_bottle",
        "semantic_name": "dream_bottle",
        "instance_file": "items/dream_bottle_1.json",
        "location": "waypoint_28a",
        "sublocation": "shelf_1"
      }
    ]
  },
  "actions": []
}
```

---

### @list templates

List all content templates (items, NPCs, quests).

**Syntax:**
```bash
@list templates
```

**Example Response:**
```
Templates:
  1. louisa (npcs)
  2. dream_bottle (items)
```

**Returns:**
```json
{
  "success": true,
  "narrative": "Templates:\n  1. louisa (npcs)...",
  "data": {
    "templates": [
      {
        "name": "louisa",
        "type": "npcs",
        "path": "npcs/louisa.md"
      },
      {
        "name": "dream_bottle",
        "type": "items",
        "path": "items/dream_bottle.md"
      }
    ]
  },
  "actions": []
}
```

---

### @list templates \<type\>

List templates filtered by type (items, npcs, quests).

**Syntax:**
```bash
@list templates items
```

**Example Response:**
```
Templates (items):
  1. dream_bottle (items)
```

## Testing with GAIA CLI

### Direct API Testing (Python)

Use the test scripts for fast testing:

```bash
# Run all admin command tests
python test_admin_commands.py

# Test with conversation tracking
python test_admin_with_conversation.py

# Compare natural language vs admin commands
python test_natural_vs_admin.py
```

### GAIA CLI (Interactive)

The GAIA CLI routes through the conversational chat endpoint, which interprets commands via LLM. For testing **game commands** (not admin commands), use the `/game/command` endpoint directly.

**Example:**
```bash
# Using requests library (recommended for admin commands)
import requests

response = requests.post(
    "http://localhost:8001/game/command",
    headers={"X-API-Key": "YOUR_KEY", "Content-Type": "application/json"},
    json={
        "command": "@list waypoints",
        "experience": "wylding-woods",
        "user_context": {"role": "admin", "user_id": "admin@gaia.dev"}
    }
)
print(response.json())
```

## Role-Based Access Control

Admin commands require `role: "admin"` in `user_context`.

**Admin Role:**
```json
{
  "command": "@list waypoints",
  "user_context": {"role": "admin", "user_id": "admin@gaia.dev"}
}
```
✅ **Allowed** - Returns waypoint list

**Player Role:**
```json
{
  "command": "@list waypoints",
  "user_context": {"role": "player", "user_id": "player@test.com"}
}
```
❌ **Denied** - Returns:
```json
{
  "success": false,
  "error": {
    "code": "unauthorized",
    "message": "Admin commands require admin role"
  },
  "narrative": "🚫 You don't have permission to use admin commands."
}
```

## Error Handling

### Unknown Command

```bash
@unknown
```
```json
{
  "success": false,
  "error": {
    "code": "unknown_command",
    "message": "Unknown admin command: @unknown"
  },
  "narrative": "❌ Unknown command '@unknown'. Available: @list, @inspect, @create, @edit, @delete, @spawn, @where, @find, @stats"
}
```

### Missing Arguments

```bash
@list locations
```
```json
{
  "success": false,
  "error": {
    "code": "missing_arg",
    "message": "Missing waypoint ID"
  },
  "narrative": "❌ Usage: @list locations <waypoint>"
}
```

## Data Sources

Admin commands read from:

1. **`world/locations.json`** - Location hierarchy and navigation graphs
   - Waypoints → Locations → Sublocations
   - Graph structure (exits arrays)
   - Cardinal direction shortcuts (optional)

2. **`instances/manifest.json`** - Item and NPC instances
   - Instance IDs, templates, locations
   - Creation timestamps, states

3. **`templates/`** - Content templates
   - `items/*.md` - Item templates
   - `npcs/*.md` - NPC templates
   - `quests/*.md` - Quest templates

## Graph-Based Navigation

The key innovation is **graph-based sublocation navigation** using adjacency lists.

### Data Structure

Each sublocation has an `exits` array listing its neighbors:

```json
{
  "center": {
    "sublocation_id": "center",
    "exits": ["shelf_1", "shelf_2", "shelf_3", "fairy_door_1", "magic_mirror"]
  },
  "shelf_1": {
    "sublocation_id": "shelf_1",
    "exits": ["center", "shelf_2"]
  }
}
```

### Why Graph-Based?

1. **No forced spatial metaphors**: Indoor spaces don't need "north/south/east/west"
2. **Natural language**: "go to shelf_1" is clearer than "go north"
3. **Flexible topology**: Works for forests, stores, abstract spaces
4. **Optional cardinal shortcuts**: `cardinal_exits` provides "go north" if desired

### Navigation Example

Player at `center`:
- Can go to: `shelf_1`, `shelf_2`, `shelf_3`, `fairy_door_1`, `magic_mirror`

Player at `shelf_1`:
- Can go to: `center`, `shelf_2`

### Validating Connections

The `@connect` command (future) will validate bidirectional edges:

```bash
@connect waypoint_28a clearing center shelf_1
```

This ensures:
- `center.exits` includes `shelf_1`
- `shelf_1.exits` includes `center`

## Pending Commands

These commands are **not yet implemented** but have placeholder methods:

- `@inspect <waypoint|location|sublocation|item> <id>` - Detailed inspection
- `@create waypoint <id> <name>` - Create new waypoint
- `@create location <waypoint> <id> <name>` - Create new location
- `@create sublocation <waypoint> <location> <id> <name>` - Create new sublocation
- `@edit <type> <id> <field> <value>` - Edit properties
- `@delete <type> <id>` - Delete content (with confirmation)
- `@spawn <template> <location>` - Spawn instance from template
- `@connect <waypoint> <location> <from_subloc> <to_subloc>` - Add graph edge
- `@disconnect <waypoint> <location> <from_subloc> <to_subloc>` - Remove edge
- `@where <item_id>` - Find item location
- `@find <template>` - Find all instances of template

## Test Results

All 11 test cases passing:

1. ✅ @stats
2. ✅ @list waypoints
3. ✅ @list locations waypoint_28a
4. ✅ @list sublocations waypoint_28a clearing
5. ✅ @list items
6. ✅ @list items at waypoint_28a clearing shelf_1
7. ✅ @list templates
8. ✅ @list templates items
9. ✅ Unknown command error handling
10. ✅ Missing argument error handling
11. ✅ Role-based access control (player denied)

## Files Created

- `/kb/experiences/wylding-woods/world/locations.json` - Location data structure
- `test_admin_commands.py` - Comprehensive test suite
- `test_admin_with_conversation.py` - Conversation ID tracking tests
- `test_natural_vs_admin.py` - Natural language vs admin command comparison

## Next Steps

1. Implement CRUD commands (@create, @edit, @delete)
2. Implement navigation commands (@connect, @disconnect)
3. Implement inspection commands (@where, @find, @inspect)
4. Add transaction support for multi-step operations
5. Add undo/redo for admin actions
6. Add batch command execution
7. Add command history and replay

## References

- Design Document: [022-location-tracking-admin-commands.md](022-location-tracking-admin-commands.md)
- KB Agent Implementation: `/app/services/kb/kb_agent.py` (lines 143-1531)
- Test Scripts: `/test_admin_commands.py`, `/test_admin_with_conversation.py`
