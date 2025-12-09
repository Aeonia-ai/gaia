# Markdown Command Format Specification

## Overview

Game commands in the unified state model are defined as markdown files in `/experiences/{exp}/game-logic/`. Each command file defines how the system processes player input and updates state.

## Directory Structure

```
/experiences/{experience}/
├── config.json
├── state/
│   └── world.json
├── templates/
│   └── *.md (entity blueprints)
└── game-logic/
    ├── look.md          # Observation command
    ├── collect.md       # Pick up items
    ├── return.md        # Return items
    ├── inventory.md     # Check inventory
    ├── talk.md          # NPC conversations
    └── admin/
        ├── list.md      # @list command
        ├── create.md    # @create command
        └── ...
```

## Markdown File Format

Each command file contains:

### 1. Frontmatter (YAML)
```yaml
---
command: look
aliases: [observe, examine, search, explore]
description: Observe your surroundings and discover items
requires_location: true
requires_target: false
state_model_support: [shared, isolated]
---
```

### 2. Command Logic (Structured Sections)

#### **## Intent Detection**
Helps the LLM understand when this command applies:
```markdown
## Intent Detection

This command handles:
- General observation: "look around", "what do I see"
- Specific targeting: "look at shelf_1", "examine fairy_door_1"
- Location-based: "look at waypoint_28a", "explore the clearing"

Natural language patterns:
- look [at] [target]
- examine [target]
- observe [area]
- what's here / what do I see
```

#### **## Input Parameters**
Defines what the system needs to extract from the user's message:
```markdown
## Input Parameters

Extract from user message:
- `target` (optional): Specific item, NPC, or location name
- `waypoint` (optional): Waypoint ID if mentioned, else use player's current
- `sublocation` (optional): Sublocation name if mentioned, else use player's current

Default behavior:
- If no target specified: Show all items at current location
- If target specified: Show detailed information about that target
```

#### **## State Access**
Specifies what state data the command needs:
```markdown
## State Access

Required from player view:
- `player.current_location` - Player's current waypoint
- `player.current_sublocation` - Player's current sublocation (optional)
- `player.inventory` - For context (optional)

Required from world state:
- `locations[waypoint].items` - Items at location
- `locations[waypoint].sublocations[sublocation].items` - Items at sublocation
- `npcs` - NPCs at location (optional)
```

#### **## Execution Logic**
Step-by-step instructions for the LLM to execute the command:
```markdown
## Execution Logic

1. **Determine target location**:
   - If `waypoint` specified in command → use that
   - Else if `target` is a location name → use that
   - Else → use `player.current_location`

2. **Query world state**:
   - Access `world_state.locations[waypoint]`
   - If `sublocation` specified → filter to that sublocation
   - Collect all `items` at the location

3. **Filter items**:
   - If `target` specified → find item matching target name
   - Else → show all visible items
   - Exclude items marked as `hidden: true`

4. **Generate narrative**:
   - If items found → describe each item using its description
   - If no items → "You don't see anything interesting here"
   - Format as natural narrative text

5. **Return response**:
   - narrative: Generated description
   - available_actions: ["collect [item]", "examine [item]", "go to [location]"]
   - state_updates: None (look doesn't change state)
```

#### **## State Updates**
Describes what changes to make to world/player state:
```markdown
## State Updates

This command does NOT modify state (read-only).

No updates to:
- `world_state`
- `player_view`
```

#### **## Response Format**
Template for generating the response:
```markdown
## Response Format

Success response:
```json
{
  "success": true,
  "narrative": "You see:\n- Dream Bottle: A shimmering bottle filled with captured dreams\n- Fairy Door: An ancient oak door carved with intricate patterns",
  "available_actions": [
    "collect dream_bottle",
    "examine fairy_door",
    "go to waypoint_28b"
  ],
  "state_updates": null,
  "metadata": {
    "items_found": 2,
    "location": "waypoint_28a"
  }
}
```

Error response (nothing found):
```json
{
  "success": true,
  "narrative": "You don't see anything interesting here.",
  "available_actions": ["explore", "move to another location"],
  "state_updates": null
}
```
```

#### **## Examples**
Concrete examples of command execution:
```markdown
## Examples

### Example 1: General observation
**Input**: "look around"
**Context**: Player at waypoint_28a, no specific sublocation
**Process**:
1. Use current location (waypoint_28a)
2. Query world_state.locations.waypoint_28a.items
3. Find: [dream_bottle_instance_1, fairy_door_instance_1]
4. Generate narrative from item descriptions
**Output**: "You see:\n- Dream Bottle: A shimmering bottle...\n- Fairy Door: An ancient oak..."

### Example 2: Targeted observation
**Input**: "examine the fairy door"
**Context**: Player at waypoint_28a
**Process**:
1. Extract target = "fairy_door"
2. Query items at waypoint_28a
3. Find item matching "fairy_door"
4. Generate detailed narrative
**Output**: "You examine the fairy door closely. An ancient oak door carved with intricate patterns depicting woodland creatures. It seems to shimmer slightly in the light."
```

## Command Implementation Process

When a player sends a message:

1. **Experience endpoint** (`/experience/interact`) receives message
2. **Command detection**: LLM analyzes message to determine which command applies
3. **Markdown loading**: System loads the appropriate command markdown file
4. **LLM execution**: LLM processes the markdown sections as instructions:
   - Parse user input according to "Input Parameters"
   - Access state according to "State Access"
   - Execute logic from "Execution Logic"
   - Apply updates from "State Updates"
   - Format response from "Response Format"
5. **State persistence**: UnifiedStateManager saves any state changes
6. **Response**: Return narrative to player

## Command Types

### Read-Only Commands (No State Changes)
- `look.md` - Observation
- `inventory.md` - Check inventory

### State-Modifying Commands
- `collect.md` - Add item to inventory, remove from world
- `return.md` - Remove from inventory, update world state
- `talk.md` - Update NPC conversation state

### Admin Commands
- `admin/list.md` - Query state
- `admin/create.md` - Create instances
- `admin/inspect.md` - View detailed state

## Advantages of Markdown Format

1. **Content creator friendly**: Non-programmers can edit command behavior
2. **Version control**: Git tracks changes to game logic
3. **LLM-friendly**: Structured text perfect for LLM interpretation
4. **Flexible**: Easy to add new commands without code changes
5. **Documented**: Command file IS the documentation

## Migration from Hardcoded

Old approach (hardcoded Python):
```python
async def _find_instances_at_location(self, experience, waypoint, sublocation):
    # 100+ lines of hardcoded logic
    pass
```

New approach (markdown):
```markdown
## Execution Logic
1. Query world_state.locations[waypoint].items
2. Filter by sublocation if specified
3. Generate narrative from descriptions
```

The LLM interprets the markdown and executes the logic dynamically.
