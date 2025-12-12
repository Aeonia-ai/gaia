# Admin Command Reference

> **Auto-generated** from code docstrings in `app/services/kb/kb_agent.py`
> Generated: 2025-12-11 19:14
>
> Run `python scripts/generate-admin-docs.py` to regenerate.

**12 commands** for world-building. All start with `@` and execute instantly (<30ms).

## Quick Reference

| Command | Description |
|---------|-------------|
| `@connect` | Create a bidirectional navigation link between two... |
| `@create` | Create a new entity in the game world. |
| `@delete` ⚠️ | Remove an entity from the game world. |
| `@disconnect` | Remove a navigation link between two sublocations. |
| `@edit` | Modify properties of an existing game entity. |
| `@find` | Find all instances spawned from a specific templat... |
| `@inspect` | View detailed information about a game entity. |
| `@list` | List entities in the game world. |
| `@reset` ⚠️ | Reset game state to initial conditions. |
| `@spawn` | Spawn a new instance from a template (NOT YET IMPL... |
| `@stats` | Display statistics about the game world. |
| `@where` | Find the location of an item or NPC by ID or name. |

---

## @connect

Create a bidirectional navigation link between two sublocations.

**Syntax:**
```bash
@connect <waypoint_id> <location_id> <from_subloc> <to_subloc>
@connect <waypoint_id> <location_id> <from_subloc> <to_subloc> <direction>
```

**Examples:**
```bash
@connect forest_01 clearing entrance pond
@connect forest_01 clearing entrance pond north
```

**Side Effects:**
- Adds to_subloc to from_subloc.exits
- Adds from_subloc to to_subloc.exits (bidirectional)
- If direction specified, adds cardinal_exits with automatic opposite

*Implementation: `_admin_connect()` in kb_agent.py*

## @create

Create a new entity in the game world.

**Syntax:**
```bash
@create waypoint <waypoint_id> "<name>"
@create location <waypoint_id> <location_id> "<name>"
@create sublocation <waypoint_id> <location_id> <subloc_id> "<name>"
```

**Examples:**
```bash
@create waypoint forest_01 "Dark Forest"
@create location forest_01 clearing "Forest Clearing"
@create sublocation forest_01 clearing pond "Small Pond"
```

**Side Effects:**
- Creates new entry in locations.json
- Sets metadata: created_at, created_by, last_modified, last_modified_by
- For locations: initializes empty sublocations list
- For sublocations: adds to parent location's sublocations list

*Implementation: `_admin_create()` in kb_agent.py*

## @delete

Remove an entity from the game world.

> ⚠️ **Destructive operation** - requires `CONFIRM` keyword.

**Syntax:**
```bash
@delete waypoint <waypoint_id> CONFIRM
@delete location <waypoint_id> <location_id> CONFIRM
@delete sublocation <waypoint_id> <location_id> <subloc_id> CONFIRM
```

**Examples:**
```bash
@delete waypoint abandoned_area CONFIRM
@delete location forest_01 old_clearing CONFIRM
@delete sublocation forest_01 clearing dried_pond CONFIRM
```

**Side Effects:**
- Removes entity from locations.json
- For waypoints: also removes all child locations and sublocations
- For locations: also removes all child sublocations
- Cleans up orphaned navigation edges

*Implementation: `_admin_delete()` in kb_agent.py*

## @disconnect

Remove a navigation link between two sublocations.

**Syntax:**
```bash
@disconnect <waypoint_id> <location_id> <from_subloc> <to_subloc>
```

**Examples:**
```bash
@disconnect forest_01 clearing entrance pond
```

**Side Effects:**
- Removes to_subloc from from_subloc.exits
- Removes from_subloc from to_subloc.exits (bidirectional)
- Removes any cardinal_exits pointing between them

*Implementation: `_admin_disconnect()` in kb_agent.py*

## @edit

Modify properties of an existing game entity.

**Syntax:**
```bash
@edit waypoint <waypoint_id> name "<new_name>"
@edit waypoint <waypoint_id> description "<new_description>"
@edit location <waypoint_id> <location_id> name "<new_name>"
@edit location <waypoint_id> <location_id> description "<text>"
@edit sublocation <waypoint_id> <location_id> <subloc_id> name "<name>"
@edit sublocation <waypoint_id> <location_id> <subloc_id> interactable <true|false>
```

**Examples:**
```bash
@edit waypoint forest_01 name "Enchanted Forest"
@edit location forest_01 clearing description "A sun-dappled clearing"
@edit sublocation forest_01 clearing pond interactable true
```

**Side Effects:**
- Updates entity in locations.json
- Sets last_modified and last_modified_by metadata

*Implementation: `_admin_edit()` in kb_agent.py*

## @find

Find all instances spawned from a specific template.

**Syntax:**
```bash
@find <template_name>
```

**Examples:**
```bash
@find dream_bottle
@find fairy_npc
@find magic_sword
```

*Implementation: `_admin_find()` in kb_agent.py*

## @inspect

View detailed information about a game entity.

**Syntax:**
```bash
@inspect waypoint <waypoint_id>
@inspect location <waypoint_id> <location_id>
@inspect sublocation <waypoint_id> <location_id> <subloc_id>
@inspect item <instance_id>
```

**Examples:**
```bash
@inspect waypoint forest_01
@inspect location forest_01 clearing
@inspect sublocation forest_01 clearing pond
@inspect item bottle_001
```

*Implementation: `_admin_inspect()` in kb_agent.py*

## @list

List entities in the game world.

**Syntax:**
```bash
@list waypoints
@list locations <waypoint_id>
@list sublocations <waypoint_id> <location_id>
@list items
@list items at <waypoint_id> <location_id> <subloc_id>
@list templates [item|npc]
```

**Examples:**
```bash
@list waypoints
@list locations forest_01
@list sublocations forest_01 clearing
@list items at forest_01 clearing pond
```

*Implementation: `_admin_list()` in kb_agent.py*

## @reset

Reset game state to initial conditions.

> ⚠️ **Destructive operation** - requires `CONFIRM` keyword.

**Syntax:**
```bash
@reset instance <instance_id> CONFIRM
@reset player <user_id> CONFIRM
@reset experience CONFIRM
```

**Examples:**
```bash
@reset instance 42 CONFIRM
@reset player user@example.com CONFIRM
@reset experience CONFIRM
```

**Side Effects:**
- instance: Resets single item/NPC to template defaults
- player: Clears player's inventory and progress
- experience: Resets entire world to pristine state (creates backup first)

*Implementation: `_admin_reset()` in kb_agent.py*

## @spawn

Spawn a new instance from a template (NOT YET IMPLEMENTED).

**Syntax:**
```bash
@spawn item <template_name> <waypoint_id> <location_id> <subloc_id>
@spawn npc <template_name> <waypoint_id> <location_id> <subloc_id>
```

**Examples:**
```bash
@spawn item dream_bottle forest_01 clearing pond
@spawn npc fairy_guide forest_01 clearing entrance
```

*Implementation: `_admin_spawn()` in kb_agent.py*

## @stats

Display statistics about the game world.

**Syntax:**
```bash
@stats
```

**Examples:**
```bash
@stats
```

*Implementation: `_admin_stats()` in kb_agent.py*

## @where

Find the location of an item or NPC by ID or name.

**Syntax:**
```bash
@where <instance_id>
@where item <instance_id>
@where npc <instance_id>
@where <semantic_name>
```

**Examples:**
```bash
@where 42
@where item 1
@where louisa
@where dream_bottle
```

*Implementation: `_admin_where()` in kb_agent.py*
