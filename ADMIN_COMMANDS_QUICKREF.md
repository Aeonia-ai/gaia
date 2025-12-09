# Admin Commands Quick Reference

## 🚀 Fast Testing

```bash
# Run comprehensive test suite
python test_admin_commands.py

# Test with conversation tracking
python test_admin_with_conversation.py

# Compare natural vs admin commands
python test_natural_vs_admin.py
```

## 📋 Command Syntax

### Read Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| **@stats** | `@stats` | World statistics (waypoints, locations, sublocations, items) |
| **@list waypoints** | `@list waypoints` | List all waypoints with location counts |
| **@list locations** | `@list locations <waypoint>` | List locations in waypoint with sublocation counts |
| **@list sublocations** | `@list sublocations <waypoint> <location>` | **Show navigation graph with exits** |
| **@list items** | `@list items` | List all item instances |
| **@list items at** | `@list items at <waypoint> <location> <sublocation>` | List items at specific sublocation |
| **@list templates** | `@list templates` | List all templates (items, NPCs, quests) |
| **@list templates** | `@list templates <type>` | List templates of specific type |
| **@inspect waypoint** | `@inspect waypoint <id>` | Detailed waypoint inspection with metadata |
| **@inspect location** | `@inspect location <waypoint> <id>` | Detailed location inspection with metadata |
| **@inspect sublocation** | `@inspect sublocation <waypoint> <location> <id>` | Detailed sublocation with navigation graph |
| **@inspect item** | `@inspect item <instance_id>` | Detailed item instance inspection |
| **@where** | `@where <instance_id>` | Find item/NPC by ID or semantic name |
| **@where** | `@where item <instance_id>` | Find item by instance ID |
| **@find** | `@find <template_name>` | Find all instances of template (grouped by location) |

### Create Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| **@create waypoint** | `@create waypoint <id> <name>` | Create new waypoint with metadata |
| **@create location** | `@create location <waypoint> <id> <name>` | Create location in waypoint |
| **@create sublocation** | `@create sublocation <waypoint> <location> <id> <name>` | Create sublocation in location |
| **@connect** | `@connect <waypoint> <location> <from> <to> [direction]` | Create bidirectional navigation edge |
| **@disconnect** | `@disconnect <waypoint> <location> <from> <to>` | Remove bidirectional navigation edge |

### Update Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| **@edit waypoint** | `@edit waypoint <id> name <new_name>` | Edit waypoint name |
| **@edit waypoint** | `@edit waypoint <id> description <text>` | Edit waypoint description |
| **@edit location** | `@edit location <waypoint> <id> name <new_name>` | Edit location name |
| **@edit location** | `@edit location <waypoint> <id> description <text>` | Edit location description |
| **@edit location** | `@edit location <waypoint> <id> default_sublocation <id>` | Set default sublocation |
| **@edit sublocation** | `@edit sublocation <waypoint> <location> <id> name <new_name>` | Edit sublocation name |
| **@edit sublocation** | `@edit sublocation <waypoint> <location> <id> description <text>` | Edit sublocation description |
| **@edit sublocation** | `@edit sublocation <waypoint> <location> <id> interactable <true\|false>` | Toggle interactability |

### Delete Commands (⚠️ Requires CONFIRM)

| Command | Syntax | Description |
|---------|--------|-------------|
| **@delete waypoint** | `@delete waypoint <id> CONFIRM` | Delete waypoint and all children |
| **@delete location** | `@delete location <waypoint> <id> CONFIRM` | Delete location and all sublocations |
| **@delete sublocation** | `@delete sublocation <waypoint> <location> <id> CONFIRM` | Delete sublocation (orphan cleanup) |

## 🔑 Authentication

**Requires:** `role: "admin"` in `user_context`

```python
payload = {
    "command": "@list waypoints",
    "experience": "wylding-woods",
    "user_context": {
        "role": "admin",  # Required!
        "user_id": "admin@gaia.dev"
    }
}
```

## 🌐 Endpoint

```
POST http://localhost:8001/game/command
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "X-API-Key": "YOUR_API_KEY"
}
```

## 🗺️ Navigation Graph

The `@list sublocations` command shows the **graph-based navigation structure**:

```
@list sublocations waypoint_28a clearing
```

**Output shows exits arrays:**
```
1. center - Center of Clearing
   (exits: shelf_1, shelf_2, shelf_3, fairy_door_1, magic_mirror)
2. shelf_1 - Shelf 1
   (exits: center, shelf_2)
3. shelf_2 - Shelf 2
   (exits: shelf_1, center, shelf_3)
```

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

## 📊 Example Session

```python
import requests

BASE_URL = "http://localhost:8001"
API_KEY = "YOUR_API_KEY"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def admin_cmd(command):
    return requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "role": "admin",
                "user_id": "admin@gaia.dev"
            }
        }
    ).json()

# Get world overview
print(admin_cmd("@stats"))

# Explore hierarchy
print(admin_cmd("@list waypoints"))
print(admin_cmd("@list locations waypoint_28a"))
print(admin_cmd("@list sublocations waypoint_28a clearing"))

# Find content
print(admin_cmd("@list items"))
print(admin_cmd("@list items at waypoint_28a clearing shelf_1"))
print(admin_cmd("@list templates items"))
```

## ✅ Status

**Implemented (✅):**

### Read Operations
- ✅ @stats - World statistics
- ✅ @list waypoints/locations/sublocations/items/templates
- ✅ @list sublocations (with navigation graph!)
- ✅ @list items at (location filtering)
- ✅ @inspect waypoint/location/sublocation/item (detailed metadata)
- ✅ @where (find by ID or semantic name)
- ✅ @find (template instance discovery)

### Create Operations
- ✅ @create waypoint/location/sublocation
- ✅ @connect (bidirectional graph edges with cardinal directions)
- ✅ @disconnect (remove graph edges with orphan cleanup)

### Update Operations
- ✅ @edit waypoint/location/sublocation (name, description, properties)
- ✅ Automatic metadata tracking (last_modified timestamp and user)

### Delete Operations
- ✅ @delete waypoint/location/sublocation
- ✅ CONFIRM safety mechanism (prevents accidents)
- ✅ Cascade deletion counting
- ✅ Orphan cleanup (broken navigation references)

### Infrastructure
- ✅ Role-based access control
- ✅ Atomic file writes (prevent corruption)
- ✅ Comprehensive error handling
- ✅ Graph consistency maintenance

**Pending (⏳):**
- @spawn (spawn instance from template) - Coming soon!

## 🎯 Key Features

1. **Structured Commands**: Explicit syntax, no LLM parsing
2. **Fast Execution**: Direct file access, no AI latency
3. **Graph Navigation**: Adjacency lists show sublocation connections
4. **Role Protection**: Admin-only with proper error messages
5. **Rich Metadata**: Shows counts, exits, creation dates, instance IDs

## 📚 Full Documentation

See: `docs/features/dynamic-experiences/phase-1-mvp/023-admin-commands-implementation-guide.md`
