---
title: "Game Command System Developer Guide"
tags: ["game", "simulation", "game commands", "llm", "kb", "runtime", "developer guide", "architecture", "tool calling", "game logic", "yaml as llm training", "two-stage llm", "structured json response", "markdown as dsl"]
feature: "Game Commands"
status: "⚠️ PARTIALLY IMPLEMENTED - Infrastructure complete, core processor is stub"
version: "0.1"
created: "2025-10-22"
last_updated: "2025-12-04"
summary: "Practical guide to understanding and working with the KB-driven game command system, explaining how LLMs interpret natural language commands from Markdown to generate structured game responses."
related_docs:
  - title: "KB-Driven Command Processing Spec"
    path: "./kb-driven-command-processing-spec.md"
  - title: "KB Agent API"
    path: "./kb-agent-api.md"
---
# Game Command System Developer Guide

> **Status**: ⚠️ PARTIALLY IMPLEMENTED - Infrastructure complete, core processor pending
> **Version**: 0.1 (Specification + Stub Implementation)
> **Purpose**: Practical guide to understanding and working with KB-driven game commands
> **Created**: 2025-10-22
> **Last Updated**: 2025-12-04
> **Related**:
> - [KB-Driven Command Processing Spec](./kb-driven-command-processing-spec.md) - Complete technical specification
> - [KB Agent API](./kb-agent-api.md) - Agent endpoint documentation

## ⚠️ Implementation Status Alert

**What Works:**
- ✅ Chat service integration (`app/services/chat/kb_tools.py`)
- ✅ Tool calling infrastructure (LLM can detect game commands)
- ✅ KB service API endpoint (`/game/command`)
- ✅ Request/response models defined

**What's Missing:**
- ❌ Core game processor (`app/shared/tools/game_commands.py:execute_game_command()` returns "not_implemented" stub)
- ❌ KB content loading logic
- ❌ LLM interpretation of markdown rules
- ❌ Structured response generation

**Reality Check**: While this document describes the intended architecture, the actual implementation is incomplete. The code exists as infrastructure only - no actual game logic executes yet.

## Quick Overview

The game command system (when implemented) will process natural language game commands by reading markdown files from the Knowledge Base and using an LLM to interpret them into structured responses. There are **two planned ways** to run games in GAIA:

### Two Approaches to Game Commands

| Feature | KB Agent (`/agent/interpret`) | Game Command Tool (`/game/command`) |
|---------|-------------------------------|-------------------------------------|
| **Purpose** | Natural language interpretation | Structured programmatic responses |
| **Response Format** | Plain text narrative | JSON with actions + state changes |
| **Best For** | CLI chat gameplay | Unity/AR clients, web UI |
| **Status** | ✅ Working (Sept 2025 POC) | ⚠️ Infrastructure only (stub) |
| **Integration** | Direct HTTP endpoint | LLM tool calling in chat |
| **Example Use** | "Tell me what happens if I go north" | Unity needs `{type: "move", direction: "north"}` |

**Key Insight:** Both approaches read the same KB markdown files. The difference is in **how they return results**:
- KB Agent returns essays
- Game Command Tool returns structured JSON for programmatic consumption

## Current Implementation Status (October 2025)

### What's Complete ✅

**Infrastructure (Built Today):**
1. **Chat Service Integration** (`app/services/chat/kb_tools.py`)
   - `execute_game_command` added to KB_TOOLS list
   - LLM can detect and call game commands via tool calling
   - KBToolExecutor routes to KB service

2. **KB Service API** (`app/services/kb/game_commands_api.py`)
   - `/game/command` endpoint created
   - Request/response models defined
   - Integrated into KB service routing

3. **Unified Chat Detection**
   - KB_TOOLS automatically available to LLM
   - Zero string parsing - pure tool calling

### What's Missing ❌

**Core Game Processor** (`app/shared/tools/game_commands.py`):
```python
# Current state (line 29):
return {"success": False, "error": {"code": "not_implemented", ...}}

# Needs implementation:
# 1. Load game content from KB
# 2. Apply RBAC filtering
# 3. Call LLM to interpret command
# 4. Return structured GameCommandResponse
```

**Visual Status:**
```
User → Chat Service (✅ working)
         ↓
    LLM detects game command (✅ working)
         ↓
    Calls execute_game_command tool (✅ working)
         ↓
    KB Service /game/command endpoint (✅ working)
         ↓
    execute_game_command() function (❌ stub - returns "not_implemented")
```

## How YAML Blocks Teach the LLM

**Critical Concept:** The YAML blocks in game markdown files are NOT code to execute. They're **training examples** that show the LLM what to return.

### Example: Text Adventure

**KB File:** `/kb/experiences/west-of-house/world/rooms/west-of-house.md`

```markdown
---
experience_id: "west-of-house"
content_type: "room"
---

# West of House

## Description
You are standing west of a white house. There is a small mailbox here.

## Valid Actions

### open mailbox
**Conditions**: mailbox_opened == false
**Response**: "You open the small mailbox. A leaflet is inside."
**Actions**:
```yaml
state_changes:
  mailbox_opened: true
actions:
  - type: "add_to_inventory"
    item: "leaflet"
  - type: "award_points"
    amount: 5
```

### go north
**Response**: "You walk to the north side of the house."
**Actions**:
```yaml
state_changes:
  current_room: "north_of_house"
actions:
  - type: "move"
    direction: "north"
```
```

### How the LLM Uses This

**Step 1: System loads the markdown**
```python
game_content = await kb_service.load_game_content(
    experience="west-of-house"
)
# Returns the markdown file above
```

**Step 2: Send to LLM with system prompt**
```
System: You are a game interpreter. Read the game rules from the markdown.
        Return JSON matching GameCommandResponse format.
        Use the YAML blocks to know what actions/state_changes to return.

Markdown: [entire file above]

Current State: {"mailbox_opened": false, "current_room": "west_of_house"}

User: "I want to open the mailbox"
```

**Step 3: LLM pattern-matches and generates**

The LLM:
1. Reads the markdown and finds the "### open mailbox" section
2. Checks condition: `mailbox_opened == false` ✓
3. Sees the YAML example showing what to return
4. Copies the structure and fills in values

**LLM Returns:**
```json
{
  "success": true,
  "narrative": "You open the small mailbox. A leaflet is inside.",
  "actions": [
    {"type": "add_to_inventory", "item": "leaflet"},
    {"type": "award_points", "amount": 5}
  ],
  "state_changes": {
    "mailbox_opened": true
  },
  "next_suggestions": ["examine leaflet", "read leaflet", "go north"],
  "metadata": {
    "processing_time_ms": 234,
    "kb_files_accessed": ["west-of-house.md"],
    "user_role": "player",
    "experience": "west-of-house"
  }
}
```

**Key Point:** The YAML isn't executed. It's a **recipe** the LLM reads and follows.

## Format Flexibility: One Structure, Any Game Type

The GameCommandResponse format is intentionally generic - games define their own action vocabulary in the YAML.

### Text Adventure Actions
```yaml
actions:
  - type: "add_to_inventory"
    item: "lamp"
  - type: "award_points"
    amount: 5
  - type: "move"
    direction: "north"
```

### AR Location Game Actions
```yaml
actions:
  - type: "play_sound"
    file: "magical_chime.wav"
  - type: "trigger_ar_effect"
    effect: "golden_sparkles"
  - type: "award_xp"
    amount: 10
  - type: "unlock_waypoint"
    waypoint_id: "woander_storefront"
```

### Turn-Based Game Actions
```yaml
actions:
  - type: "update_score"
    winner: "player"
  - type: "advance_round"
    round: 2
```

### Card Game Actions (Hypothetical)
```yaml
actions:
  - type: "draw_card"
    card_id: "fireball_spell"
  - type: "spend_mana"
    amount: 3
  - type: "deal_damage"
    target: "enemy_minion_1"
    damage: 6
```

**The format doesn't care** - it just delivers whatever the KB markdown defines.

### Client-Side Interpretation

The Unity/AR client interprets action types:

```csharp
// Unity client
foreach (var action in response.actions) {
    switch (action.type) {
        case "play_sound":
            audioManager.Play(action.file);
            break;
        case "trigger_ar_effect":
            arManager.SpawnEffect(action.effect);
            break;
        case "add_to_inventory":
            inventory.AddItem(action.item);
            break;
        case "custom_game_action":
            // Your custom handler
            HandleCustomAction(action.params);
            break;
    }
}
```

## Two-Stage LLM Architecture

The system uses **two separate LLM calls** to avoid string parsing:

### Stage 1: Chat Service LLM (Command Detection)

**Location:** `app/services/chat/unified_chat.py` (lines 271-276)

```python
# Chat LLM sees these tools:
all_tools = self.routing_tools + KB_TOOLS

# KB_TOOLS includes:
{
  "name": "execute_game_command",
  "description": "Process game commands when user input looks like:
                  'go north', 'take lamp', 'examine mailbox',
                  'play rock', 'scan marker'...",
  "parameters": {...}
}

# LLM decides: "This looks like a game command, I should call the tool"
# NOT: if message.startswith("go"): ...
```

**No string parsing!** The LLM uses tool calling to detect game-like inputs.

### Stage 2: KB Service LLM (Command Interpretation)

**Location:** `app/shared/tools/game_commands.py` (future implementation)

```python
# KB LLM will:
# 1. Receive filtered game rules from KB
# 2. Interpret user command against those rules
# 3. Generate structured GameCommandResponse

interpretation = await llm_service.interpret_game_command(
    command=command,
    game_rules=filtered_content,
    current_state=session_state,
    response_format="structured"
)
```

**Also no string parsing!** The LLM generates structured output based on KB examples.

### Why Two Stages?

**Benefits:**
1. **Separation of Concerns**
   - Chat LLM: "Is this a game command?" (fast, low tokens)
   - KB LLM: "What does this mean in THIS game?" (complex, game-specific)

2. **Mixed Conversations**
   ```
   User: "What's the weather today?"
   → Chat LLM: Regular response (no tool call)

   User: "go north"
   → Chat LLM: Calls execute_game_command tool
   → KB LLM: Interprets against west-of-house rules
   ```

3. **Context Efficiency**
   - Stage 1: Small context (just detect command)
   - Stage 2: Large context (full game rules loaded)

## Creating a New Game Experience

### Step 1: Create KB Markdown Structure

```
/kb/experiences/your-game/
├── GAME.md              # Overview and introduction
├── rules/
│   ├── core.md         # Core game mechanics
│   └── advanced.md     # Advanced rules
└── content/
    ├── locations.md    # For location-based games
    ├── items.md        # For inventory games
    └── mechanics.md    # For turn-based games
```

### Step 2: Define Actions in YAML

**Example:** `/kb/experiences/your-game/rules/core.md`

```markdown
---
experience_id: "your-game"
content_type: "rule"
access_level: "public"
---

# Core Mechanics

## Valid Actions

### cast [spell_name]
**Conditions**: has_mana >= spell_cost
**Response**: "You cast [spell_name]! Magical energy flows from your hands."
**Actions**:
```yaml
state_changes:
  mana: "current_mana - spell_cost"
  spell_cast_count: "spell_cast_count + 1"
actions:
  - type: "cast_spell"
    spell: "[spell_name]"
  - type: "consume_mana"
    amount: "spell_cost"
  - type: "trigger_visual_effect"
    effect: "spell_casting_glow"
```

### Step 3: Test with KB Agent First

Before implementing the full tool, test with the existing KB Agent:

```bash
curl -X POST http://localhost:8001/agent/interpret \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "cast fireball",
    "context_path": "/experiences/your-game",
    "mode": "decision"
  }'
```

This validates your markdown structure works.

### Step 4: Add to Game Command Tool

Once the core processor is implemented, your game will automatically work through `/game/command` - no code changes needed!

## Implementation Roadmap

### Phase 1: Core Processor (Next Priority)

Implement the stub in `app/shared/tools/game_commands.py`:

```python
async def execute_game_command(...):
    # 1. Load KB content
    game_content = await kb_storage.load_experience_content(experience)

    # 2. Filter by role (RBAC)
    filtered = GameRBAC.filter_content_for_role(game_content, user_role)

    # 3. Call LLM (similar to kb_agent.interpret_knowledge)
    response = await llm_service.chat_completion(
        messages=[
            {"role": "system", "content": GAME_INTERPRETER_PROMPT},
            {"role": "user", "content": f"Command: {command}\n\nRules:\n{filtered}"}
        ],
        response_format="json_schema"  # Force structured output
    )

    # 4. Parse and validate
    return parse_game_response(response)
```

### Phase 2: State Management

Add session state persistence:
- Store game state in conversation context
- Track inventory, location, progress
- Handle multi-turn narratives

### Phase 3: RBAC Implementation

Convert security stubs to full implementation:
- Code-enforced permission checks
- Content filtering by user role
- Admin vs player vs storyteller roles

### Phase 4: Performance Optimization

Add caching and optimization:
- Cache game content per experience
- Pre-filter content by role
- Optimize LLM token usage

## Testing Strategy

### Current Tests

Tests exist at `tests/unit/tools/test_game_command_execution.py` but currently fail (stub returns "not_implemented").

### TDD Workflow (From Spec)

**Phase 1: Basic Commands**
1. `test_basic_look_command()` - Get room description
2. `test_take_item_updates_inventory()` - Inventory management
3. `test_movement_between_rooms()` - Navigation
4. `test_rock_paper_scissors_game()` - Turn-based mechanics

**Phase 2: State Persistence**
1. `test_multi_turn_narrative_consistency()` - Story coherence
2. `test_inventory_capacity_limits()` - Game constraints

**Phase 3: Security**
1. `test_player_cannot_execute_admin_commands()` - RBAC enforcement
2. `test_cross_user_session_isolation()` - Multi-user safety

### Running Tests

```bash
# Once implemented
./scripts/pytest-for-claude.sh tests/unit/tools/test_game_command_execution.py -v

# Check specific test
./scripts/pytest-for-claude.sh tests/unit/tools/test_game_command_execution.py::TestGameCommandExecution::test_basic_look_command -v
```

## Common Patterns

### Pattern 1: Conditional Actions

```yaml
### open door
**Conditions**: has_key == true
**Response**: "You unlock the door with your key and push it open."
**Actions**:
```yaml
state_changes:
  door_open: true
actions:
  - type: "open_door"
    door_id: "main_entrance"
```
**Else**: "The door is locked. You need a key."
```

### Pattern 2: Random Outcomes

```yaml
### attack enemy
**Response**: "You swing your sword at the enemy!"
**Actions**:
```yaml
actions:
  - type: "roll_attack"
    target: "enemy"
    damage_range: [5, 15]
  - type: "trigger_combat_animation"
    animation: "sword_swing"
state_changes:
  combat_turn: "enemy"
```
```

### Pattern 3: Multi-Step Sequences

```yaml
### use teleporter
**Response**: "The teleporter activates with a brilliant flash of light!"
**Actions**:
```yaml
actions:
  - type: "play_sound"
    file: "teleport_activate.wav"
  - type: "fade_screen"
    duration: 1.5
  - type: "change_location"
    destination: "teleporter_hub"
  - type: "fade_in"
    duration: 1.0
  - type: "play_arrival_sequence"
state_changes:
  current_location: "teleporter_hub"
  teleports_used: "teleports_used + 1"
```
```

## Troubleshooting

### Issue: LLM doesn't recognize command

**Cause:** Command pattern not in markdown

**Solution:** Add the command to your game's markdown:
```yaml
### your command here
**Response**: "..."
**Actions**: ...
```

### Issue: Wrong action types returned

**Cause:** YAML examples unclear or inconsistent

**Solution:** Make YAML examples explicit and consistent:
```yaml
# ❌ Vague
actions:
  - type: "do_thing"

# ✅ Clear
actions:
  - type: "add_to_inventory"
    item: "brass_key"
```

### Issue: State not persisting

**Cause:** Session state not being passed/updated

**Solution:** Ensure client sends current state:
```json
{
  "command": "go north",
  "experience": "west-of-house",
  "session_state": {
    "current_room": "west_of_house",
    "inventory": ["lamp"],
    "visited_rooms": ["west_of_house"]
  }
}
```

## Next Steps

### For Developers

1. **Review the spec:** Read `kb-driven-command-processing-spec.md` for complete technical details
2. **Explore KB content:** Check `/kb/experiences/` for existing game examples
3. **Try KB Agent:** Test games through `/agent/interpret` to validate markdown
4. **Implement processor:** Help complete `execute_game_command()` core logic

### For Game Designers

1. **Study examples:** Look at west-of-house, rock-paper-scissors, wylding-woods
2. **Write markdown:** Create game rules with YAML examples
3. **Test with agent:** Validate your game works through KB Agent
4. **Define action vocabulary:** Decide what action types your game needs

## Related Documentation

### Experience Platform
- **[Experience Platform Architecture](../+experiences.md)** - Overall platform architecture
- **[Player Progress Storage](../storage/player-progress-storage.md)** - How player progress is tracked
- **[Experience Tools API](../content-creation/experience-tools-api.md)** - LLM tools for content creation
- **[Experience Data Models](../storage/experience-data-models.md)** - Database schemas
- **[AI Character Integration](../ai-systems/ai-character-integration.md)** - Multi-agent NPC system

### Game Command System
- **[KB-Driven Command Processing Spec](./kb-driven-command-processing-spec.md)** - Complete technical specification (910 lines)
- **[Action Vocabulary Spec](../../../../../Vaults/KB/users/jason@aeonia.ai/mmoirl/experiences/wylding-woods/action-vocabulary.md)** - Wylding Woods action types (external KB)
- **[KB Agent API](../../api/kb-agent-api.md)** - Agent endpoint documentation (if exists)
- **[KB Architecture Guide](../../kb/developer/kb-architecture-guide.md)** - Knowledge Base infrastructure
- **[Testing Guide](../../testing/TESTING_GUIDE.md)** - Testing patterns and best practices

---

## Summary

The game command system enables natural language gameplay by:
1. Reading game rules from KB markdown files
2. Using LLM to interpret commands against those rules
3. Returning structured responses (narrative + actions + state changes)

**Current Status:** Infrastructure complete, core processor pending implementation.

**Two approaches:** KB Agent (working, text responses) vs Game Command Tool (structured, for Unity/AR).

**Key insight:** YAML blocks teach the LLM what to return - they're examples, not code.
