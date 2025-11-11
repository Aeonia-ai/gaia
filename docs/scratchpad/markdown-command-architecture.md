# Markdown-Driven Command Architecture

**Date**: 2025-11-10
**Discovery Context**: WebSocket v0.4 testing revealed the LLM command processing system

---

## Executive Summary

Commands in GAIA are defined as **markdown specifications** that the LLM reads and executes. This isn't traditional code - it's **executable documentation** where markdown files act as both specification and implementation.

**Key Insight**: When you write "go to spawn_zone_1", the LLM:
1. Reads `game-logic/go.md`
2. Matches your input against natural language patterns
3. Executes the logic described in markdown
4. Constructs state updates following markdown examples
5. Generates narrative responses

**Processing Time**: 25-30 seconds (2-pass system: logic + narrative)

---

## Command Directory Structure

```bash
/Vaults/gaia-knowledge-base/experiences/wylding-woods/
├── game-logic/          # Player commands (LLM-processed)
│   ├── collect.md       # Take items from world
│   ├── go.md            # Move between locations/sublocations
│   ├── look.md          # Observe surroundings
│   ├── inventory.md     # Check player's items
│   ├── talk.md          # Converse with NPCs
│   ├── help.md          # Show available commands
│   └── quests.md        # Quest management
├── admin-logic/         # Admin commands (instant, no LLM)
│   ├── @list-waypoints.md
│   ├── @inspect-waypoint.md
│   └── ...
└── commands/            # (Legacy? Less clear usage)
```

**Command Types**:
- **Player commands** (game-logic): Natural language, LLM-processed, 25-30s response time
- **Admin commands** (admin-logic): @ prefix, instant (<30ms), no LLM processing

---

## Markdown Command Structure

### 1. YAML Frontmatter (Metadata)

Every command starts with YAML metadata:

```yaml
---
command: go
aliases: [move, walk, travel, head, enter]
description: Move to a different location or sublocation
requires_location: true
requires_target: true
state_model_support: [shared, isolated]
---
```

**Fields**:
- `command`: Primary command name
- `aliases`: Synonyms the LLM will recognize
- `description`: What the command does
- `requires_location`: Whether player must be at a location
- `requires_target`: Whether a target/destination is required
- `state_model_support`: Shared (multiplayer) vs isolated (single-player)

### 2. Intent Detection Section

Defines natural language patterns the LLM should recognize:

```markdown
## Intent Detection

This command handles:
- Directional movement: "go north", "head east", "walk south"
- Sublocation movement: "go to counter", "enter back room"
- Natural language: "go to the shop counter", "walk to the back"

Natural language patterns:
- go [direction]
- go to [sublocation]
- move [to] [direction/sublocation]
- [direction] (standalone)
```

**Why This Matters**: When testing, we found "go to spawn_zone_1" worked but "go spawn_zone_1" didn't. This is because the markdown explicitly defines `"go to [sublocation]"` as a valid pattern (line 22 of go.md).

### 3. Input Parameters Section

Tells the LLM what to extract from user input:

```markdown
## Input Parameters

Extract from user message:
- `destination`: Direction (north/south/east/west) OR sublocation name
- `destination_type`: Automatically determine if "direction" or "sublocation"
```

### 4. State Access Section

Defines what data the LLM needs to query:

```markdown
## State Access

Required from player view:
- `player.current_location` - Player's current room/location ID
- `player.current_sublocation` (optional) - Player's sublocation

Required from world state:
- `locations[current_location].connections` - Valid directional exits
- `locations[current_location].sublocations` - Available sublocations
```

### 5. Execution Logic Section

Step-by-step instructions for the LLM:

```markdown
## Execution Logic

1. **Parse destination**:
   - Extract direction or sublocation name from user message
   - Normalize: "back room" → "back_room"

2. **Get current position**:
   - Get `player.current_location` from player_view

3. **Validate movement**:
   - If direction: Check if `connections[direction]` exists
   - If sublocation: Check if sublocation exists in `sublocations`

4. **Execute movement**:
   - Update `player.current_location` OR `player.current_sublocation`

5. **Generate narrative**:
   - Describe the movement
   - Include description of new location
```

### 6. State Updates Section

JSON examples showing how to construct state change payloads:

```json
{
  "player": {
    "path": "player.current_location",
    "operation": "update",
    "data": "new_location_id"
  }
}
```

### 7. Response Format Section

Complete JSON examples of success and error responses:

```json
{
  "success": true,
  "narrative": "You head north...",
  "available_actions": ["go south", "look around"],
  "state_updates": {...},
  "metadata": {...}
}
```

### 8. Examples Section

Full worked examples showing state before/after and processing steps.

---

## Critical Pattern: Hierarchical State Paths

**Critical Discovery**: The requirement for players to navigate to correct sublocations before collecting items (e.g., `locations.{location}.sublocations.{sublocation}.items`) is not a bug, but an **intentional design enforced by the markdown specifications**. This hierarchical state path structure is a core architectural decision for managing game world entities.

### The Problem (from collect.md lines 205-208)

```markdown
**CRITICAL PATH CONSTRUCTION RULE**:
- If `player.current_sublocation` exists → path MUST be `locations.{location}.sublocations.{sublocation}.items`
- If `player.current_sublocation` is null → path MUST be `locations.{location}.items`
- **NEVER** assume flat structure - ALWAYS check sublocation first!
```

### Why This Caused Our Test Failures

**Initial Test (Failed)**:
```bash
# Player at: woander_store (no sublocation)
collect dream bottle
# Result: "item_not_found"
# Reason: Item is at woander_store.sublocations.spawn_zone_1.items
#         Player is at woander_store (top-level)
```

**Working Test**:
```bash
# Step 1: Navigate to sublocation
go to spawn_zone_1
# Player now at: woander_store.spawn_zone_1

# Step 2: Collect item
collect dream bottle
# Result: SUCCESS!
# Reason: Player location matches item location
```

### Example from collect.md (Lines 346-447)

```json
{
  "player": {
    "current_location": "woander_store",
    "current_sublocation": "spawn_zone_3"  // CRITICAL: Must match item location
  }
}
```

```json
{
  "locations": {
    "woander_store": {
      "sublocations": {
        "spawn_zone_3": {
          "items": [
            {
              "id": "dream_bottle_3",
              "semantic_name": "joyful dream bottle",
              "collectible": true
            }
          ]
        }
      }
    }
  }
}
```

**State Update Path**:
```json
{
  "world": {
    "path": "locations.woander_store.sublocations.spawn_zone_3.items",
    "operation": "remove",
    "item_id": "dream_bottle_3"
  }
}
```

**Warning from collect.md line 446**:
> ⚠️ WRONG PATH BUG: If you generate `path: "locations.woander_store.items"` (missing `.sublocations.spawn_zone_3`), the item will NOT be removed from world state, causing **item duplication**!

---

## Two-Pass LLM Processing

Based on observed 25-30 second processing times and documentation patterns:

### Pass 1: Logic Processing (15-20 seconds)
1. Parse user input against natural language patterns
2. Query player_view and world_state
3. Validate command requirements
4. Execute state changes
5. Construct state_updates JSON

### Pass 2: Narrative Generation (5-10 seconds)
1. Generate natural language response
2. Describe what happened
3. Suggest next actions
4. Format final response

**Total**: 25-30 seconds for complex commands

**Why So Slow?**
- Reading and interpreting markdown specifications
- Natural language parsing (not regex)
- Complex state queries (hierarchical paths)
- LLM generates both logic AND narrative
- Two separate LLM calls (logic + narrative)

---

## Command Format Requirements

### Why Exact Formats Matter

**Example: go command**

✅ **Working Formats** (from go.md lines 20-26):
```
go to spawn_zone_1        # Matches: "go to [sublocation]"
go north                  # Matches: "go [direction]"
move to counter           # Matches: "move [to] [sublocation]"
enter back room           # Matches: "enter [sublocation]"
north                     # Matches: "[direction] (standalone)"
```

❌ **Non-Working Formats**:
```
go spawn_zone_1           # No pattern for "go [sublocation]" (missing "to")
goto spawn_zone_1         # No pattern for "goto"
move spawn_zone_1         # No pattern for "move [sublocation]" (missing "to")
```

### Why "go to spawn_zone_1" Works

From go.md line 22:
```markdown
Natural language patterns:
- go to [sublocation]    # ← This pattern matches!
```

The LLM:
1. Reads "go to spawn_zone_1"
2. Matches against pattern "go to [sublocation]"
3. Extracts: `destination = "spawn_zone_1"`, `type = "sublocation"`
4. Executes sublocation movement logic

### Why "collect dream bottle" Works

From collect.md lines 20-24:
```markdown
Natural language patterns:
- collect [item]         # ← This pattern matches!
- take [item]            # Also valid
- pick up [item]         # Also valid
```

---

## Testing Command Formats

### Strategy 1: Check Markdown Patterns

Before testing a command, read its markdown file:

```bash
# View command patterns
cat /Vaults/gaia-knowledge-base/experiences/wylding-woods/game-logic/collect.md
```

Look for the "Natural language patterns" section to see valid formats.

### Strategy 2: Use Error Messages

Server returns helpful error messages:

```json
{
  "error": {
    "code": "destination_not_specified",
    "message": "Where do you want to go?"
  },
  "available_actions": ["go to spawn_zone_1", "go north"]
}
```

The `available_actions` array shows correct command formats!

### Strategy 3: Test Incrementally

```bash
# Step 1: look around (see what's available)
{"type": "action", "action": "look"}

# Step 2: Use exact sublocation names from response
{"type": "action", "action": "go to spawn_zone_1"}

# Step 3: Collect items at your current location
{"type": "action", "action": "collect dream bottle"}
```

---

## Command Discovery

### How to Find Available Commands

**Option 1: Read game-logic directory**
```bash
ls /Vaults/gaia-knowledge-base/experiences/wylding-woods/game-logic/
# Output: collect.md, go.md, look.md, inventory.md, talk.md, help.md, quests.md
```

**Option 2: Use help command**
```json
{"type": "action", "action": "help"}
```

**Option 3: Check available_actions**

Every response includes:
```json
{
  "available_actions": [
    "go to spawn_zone_1",
    "take dream bottle",
    "look around"
  ]
}
```

These are contextual suggestions based on current game state.

---

## Creating New Commands

To add a new command (e.g., "use"):

### 1. Create Markdown File

`/experiences/wylding-woods/game-logic/use.md`:

```markdown
---
command: use
aliases: [activate, employ, utilize]
description: Use an item from your inventory
requires_location: false
requires_target: true
state_model_support: [shared, isolated]
---

# Use Command

## Intent Detection

This command handles:
- Using items: "use lantern", "activate key"
- Item actions: "turn on lamp", "light torch"

Natural language patterns:
- use [item]
- activate [item]
- [verb] [item] (context-dependent)

## Input Parameters

Extract from user message:
- `target` (REQUIRED): Item name to use

## State Access

Required from player view:
- `player.inventory` - Items player has

Required from world state:
- Item definition for `target` (to check usable actions)

## Execution Logic

1. **Find item in inventory**:
   - Query player.inventory for item matching target
   - If not found → return error "You don't have that"

2. **Check item capabilities**:
   - Does item have `actions` array?
   - Is item `usable: true`?

3. **Execute item action**:
   - Call item-specific logic
   - Update item state if needed

4. **Generate narrative**:
   - Describe what happened
   - Show effect of using item

## State Updates

Example:
```json
{
  "player": {
    "path": "player.inventory[0].state.active",
    "operation": "update",
    "data": true
  }
}
```

## Response Format

Success:
```json
{
  "success": true,
  "narrative": "You turn on the brass lantern. It casts a warm glow.",
  "available_actions": ["turn off lantern"],
  "state_updates": {...}
}
```

## Examples

[Add worked examples here]
```

### 2. Test New Command

```bash
# WebSocket test
{"type": "action", "action": "use lantern"}
```

### 3. LLM Auto-Discovery

The LLM will automatically:
- Find `use.md` in game-logic directory
- Read and interpret the specification
- Execute the command logic
- No code changes needed!

---

## Comparison: Player vs Admin Commands

### Player Commands (game-logic/)
- **Format**: Natural language (e.g., "go to spawn_zone_1")
- **Processing**: LLM-driven (reads markdown specs)
- **Response Time**: 25-30 seconds
- **Flexibility**: High (many synonyms, patterns)
- **Examples**: collect, go, look, talk, inventory

### Admin Commands (admin-logic/)
- **Format**: @ prefix (e.g., "@list-waypoints")
- **Processing**: Direct Python execution
- **Response Time**: <30ms
- **Flexibility**: Low (exact format required)
- **Examples**: @list-waypoints, @inspect-waypoint, @create-item

**Use Case Split**:
- **Player commands**: Immersive gameplay, natural interaction
- **Admin commands**: World building, debugging, instant results

---

## Debugging Commands

### Common Issues

**Issue 1: Command not recognized**
```
Error: "I don't understand that command"
```
**Solution**: Check markdown file exists and YAML frontmatter is correct

**Issue 2: Command timeouts**
```
Error: No response after 5 seconds
```
**Solution**: LLM processing takes 25-30 seconds - increase timeout to 60s

**Issue 3: Item not found**
```
Error: "You don't see any bottle here"
```
**Solution**: Check player is at correct sublocation. Use "look around" then "go to [sublocation]"

**Issue 4: Invalid format**
```
Error: "Where do you want to go?"
```
**Solution**: Check markdown file for exact patterns. Use "go to [sublocation]" not "go [sublocation]"

### Debug Process

1. **Read the markdown file**
   ```bash
   cat /Vaults/gaia-knowledge-base/experiences/wylding-woods/game-logic/[command].md
   ```

2. **Check natural language patterns section**
   - Find valid input formats
   - Use exact patterns specified

3. **Verify game state requirements**
   - Are you at the right location?
   - Do you have the required items?
   - Is the target visible/available?

4. **Check available_actions in responses**
   - Server suggests valid commands
   - Use exact formats shown

---

## Performance Optimization

### Why Commands are Slow

1. **LLM reads entire markdown file** (200-500 lines)
2. **Natural language parsing** (not simple regex)
3. **State queries** (hierarchical JSON paths)
4. **Two LLM calls** (logic pass + narrative pass)

### Future Optimizations

**Option 1: Compiled Command Cache**
- Pre-process markdown into structured data
- Store as JSON schemas
- Faster lookups, same flexibility

**Option 2: Hybrid Processing**
- Simple commands (look, inventory) → direct Python
- Complex commands (collect with conditions) → LLM
- Reduces LLM calls by 50-70%

**Option 3: LLM Prompt Optimization**
- Smaller markdown files (remove verbose examples)
- Focused prompts (only relevant sections)
- Target: 10-15 second response times

---

## Architecture Benefits

### Why Markdown-Driven Commands?

**1. No Code Deployments**
- Change command behavior by editing markdown
- No Docker rebuilds
- No service restarts

**2. Natural Language Support**
- Players use conversational language
- Synonyms handled automatically
- Flexible input patterns

**3. Documentation = Implementation**
- Markdown files are both spec and code
- Always up to date (can't drift)
- Easy for non-programmers to understand

**4. Rapid Prototyping**
- Add new commands in minutes
- Test immediately
- Iterate quickly

**5. Multi-Experience Support**
- Each experience has its own game-logic/
- Commands can be experience-specific
- No cross-contamination

### Tradeoffs

**Pros**:
- ✅ Extreme flexibility
- ✅ No code changes needed
- ✅ Natural language support
- ✅ Self-documenting

**Cons**:
- ❌ Slower (25-30s vs <100ms for direct code)
- ❌ LLM cost (every command = LLM call)
- ❌ Less predictable (LLM interpretation varies)
- ❌ Harder to debug (LLM is black box)

---

## Related Documentation

**WebSocket Testing**:
- `docs/scratchpad/websocket-test-results-v04.md` - Test results showing 25-30s LLM processing
- `docs/scratchpad/UNITY-LOCAL-TESTING-GUIDE.md` - Unity integration guide with command examples

**Command System**:
- `docs/scratchpad/admin-command-system.md` - @ prefix admin commands (<30ms, no LLM)
- `docs/scratchpad/npc-interaction-system.md` - NPC talk command implementation

**Architecture**:
- `docs/scratchpad/WORLD-UPDATE-AOI-ALIGNMENT-ANALYSIS.md` - State structure and hierarchical paths
- `docs/scratchpad/TEMPLATE-INSTANCE-IMPLEMENTATION-COMPLETE.md` - Template/instance separation

---

## Conclusion

**Key Takeaway**: GAIA commands are executable markdown specifications. The LLM reads markdown files and executes them as code, enabling natural language interaction without hardcoded parsers.

**Testing Insight**: Command testing requires understanding both the markdown patterns AND the game state hierarchy. The timeout issues we encountered weren't bugs - they were the expected 25-30 second LLM processing time for the markdown-driven system.

**Unity Integration**: Unity clients should:
1. Use 60-second timeouts for action commands
2. Follow exact natural language patterns from markdown files
3. Navigate to correct sublocations before collecting items
4. Use available_actions arrays for context-aware suggestions

**Next Steps**:
1. ✅ v0.4 WorldUpdate validated via WebSocket
2. ⏸️ Unity local testing with 60s timeouts
3. ⏸️ Deploy to dev Monday after Unity validation
