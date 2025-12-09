# Migration Plan: Hardcoded Commands → Markdown Files

> **Status:** 🔵 FUTURE PLAN - Migration NOT executed, hardcoded commands still in use
> **Created:** ~2025-10
> **Last Updated:** 2025-12-04
> **Estimated Effort:** 24-27 days (~5-6 weeks)
> **Priority:** Low (alternative approaches may be better)

## ⚠️ Implementation Status

**This migration has NOT been executed.**

**Current Reality:**
- Game commands are hardcoded in Python (see `app/services/kb/game_commands_legacy_hardcoded.py`)
- No markdown-based command logic exists
- Templates exist but aren't loaded at runtime for command processing
- Command processing uses `execute_game_command()` stub (returns "not_implemented")

**This Document Describes:**
- Proposed migration from hardcoded Python to markdown-driven commands
- 5-6 week effort estimate
- Detailed implementation plan
- Benefits and risks

**Before Executing:** Evaluate if this approach is still desired. Consider:
1. Is KB-driven command processing still the goal?
2. Are there simpler alternatives (hybrid approach)?
3. What's changed since this was written?

## Goal (PROPOSED MIGRATION)

Enable content-driven game command execution for wylding-woods and west-of-house by:
1. Moving interaction logic from Python to markdown
2. Keeping JSON for state management
3. Loading markdown at runtime (like `/agent/interpret`)

**Note**: This is a proposed migration plan, not executed work.

---

## Current Architecture vs Target Architecture

### Current (Code-Driven)
```
User: "look around"
  ↓
Haiku parses → action_type: "look"
  ↓
Python method: _find_instances_at_location()
  ↓
Hardcoded string: "You carefully lift the {item}..."
  ↓
JSON state update
```

### Target (Content-Driven)
```
User: "look around"
  ↓
Load markdown: game-logic/look.md
  ↓
LLM interprets markdown rules + current state
  ↓
Generate narrative from markdown templates
  ↓
JSON state update
```

---

## Step 1: Create Markdown Command Definitions

### Directory Structure

```
experiences/wylding-woods/
  game-logic/
    +commands.md          # Index of all commands
    look.md               # Look/examine logic
    collect.md            # Item collection logic
    return.md             # Item return logic
    inventory.md          # Inventory display logic
    talk.md               # NPC conversation logic

experiences/west-of-house/
  game-logic/
    +commands.md          # Index of all commands
    look.md               # Observation rules
    take.md               # Item pickup rules
    use.md                # Item usage rules
    go.md                 # Movement rules
    inventory.md          # Inventory rules
```

### Example: look.md

```markdown
# Look Command

## Purpose
Allow players to observe their surroundings, examine items, and discover interactive elements.

## Triggers
- "look around"
- "examine [object]"
- "inspect [location]"
- "what's here?"
- "describe the area"

## Behavior Rules

### When Player Looks Around
1. Describe the current sublocation based on its `description` property
2. List all visible items at the location:
   - Read `manifest.json` for items at current waypoint/sublocation
   - For each item not yet collected:
     - Show item's `name` from template
     - Show brief `description` (first sentence)
3. List all NPCs at the location:
   - Show NPC `name` and current `state`
   - Indicate if NPC is available for conversation
4. Show available exits/directions

### When Player Examines Specific Object
1. Find object in manifest at current location
2. If object is an item:
   - Show full description from template
   - Show interaction hints from template's "On Discovery" section
   - Indicate if collectible
3. If object is an NPC:
   - Show character description
   - Show current mood/state
   - Suggest conversation topics

## Narrative Templates

### Sublocation Description
```
You find yourself in {sublocation.name}. {sublocation.description}
```

### Items Present
```
You notice:
{for each item}
- A {item.name}: {item.brief_description}
{end for}
```

### NPCs Present
```
{npc.name} is here, {npc.current_state}.
```

### Nothing Found
```
You look around carefully but don't notice anything of particular interest right now.
```

## State Changes
- None (pure observation)
- May trigger discovery flags for first-time observations

## Examples

**Input**: "look around"
**Location**: waypoint_28a/clearing/center
**Output**:
```
You find yourself at the center of a sunlit clearing. Ancient trees form a natural
cathedral around you, their branches filtering golden afternoon light.

You notice:
- A dream bottle: A small glass bottle filled with swirling, luminescent mist

Louisa is here, tending to the garden with gentle movements.

From here, you can go north to the forest path or east toward the shelf.
```

**Input**: "examine dream bottle"
**Output**:
```
A small glass bottle, no larger than your palm. Inside, luminescent mist swirls with
colors that don't quite exist in the waking world - shades between purple and silver,
hints of forgotten memories.

The bottle seems to pulse gently, as if breathing. You could collect it.
```
```

### Example: collect.md

```markdown
# Collect Command

## Purpose
Allow players to pick up items and add them to inventory.

## Triggers
- "take [item]"
- "collect [item]"
- "pick up [item]"
- "grab [item]"
- "get [item]"

## Behavior Rules

### Preconditions
1. Item must exist at player's current location (check manifest)
2. Item must not already be collected by someone else
3. Item must have `collectible: true` in template (if specified)
4. Player inventory must not exceed max capacity (if defined)

### Collection Process
1. Find item in manifest at current waypoint/sublocation
2. Load item template to get collection narrative
3. Update item instance JSON:
   ```json
   {
     "collected_by": "player@example.com",
     "collected_at": "2025-10-27T14:30:00Z",
     "status": "collected"
   }
   ```
4. Update player inventory JSON:
   ```json
   {
     "items": ["dream_bottle_1", "..."],
     "updated_at": "2025-10-27T14:30:00Z"
   }
   ```

## Narrative Templates

### Success - Use Template's "On Collection" Section
```
{item.template.on_collection}

The {item.name} is now in your inventory.
```

### Fallback if Template Missing On Collection
```
You carefully lift the {item.name}. {item.description}

It feels {item.properties.weight} in your hands. You tuck it away safely.
```

### Item Not Found
```
You don't see "{item_name}" here. Try looking around first to see what's available.
```

### Already Collected
```
The {item.name} has already been collected.
```

### Not Collectible
```
The {item.name} isn't something you can take with you.
```

## State Changes
```json
{
  "actions": [
    {
      "type": "collect_item",
      "item_id": "dream_bottle_1",
      "item_name": "Dream Bottle",
      "location": "waypoint_28a/clearing/center"
    }
  ],
  "state_changes": {
    "inventory": ["dream_bottle_1"],
    "location_items": []  // Removed from location
  }
}
```

## Examples

**Input**: "take dream bottle"
**Context**: Player at waypoint_28a/clearing/center, dream_bottle_1 present
**Output**:
```
You reach out slowly, and the bottle seems to lean into your hand, as if it
has been waiting for you. The moment your fingers close around the cool glass,
you feel a gentle vibration - not physical, but something deeper, like a
harmonious note resonating through your chest.

The dream bottle is now in your inventory.
```

**Input**: "collect ancient tree"
**Output**:
```
The ancient tree isn't something you can take with you.
```
```

---

## Step 2: Update Template Files to Include Interaction Narratives

### Current Template: dream_bottle.md (Partial)
```markdown
# Dream Bottle

## Item Properties
- **Type**: Collectible
- **Rarity**: Unique
...
```

### Enhanced Template: dream_bottle.md
```markdown
# Dream Bottle

## Item Properties
- **Type**: Collectible
- **Rarity**: Unique
...

## Interaction Narratives

### On Discovery (First Look)
You spot a small glass bottle half-hidden among the wildflowers.
Something about it draws your attention - perhaps the way the
light seems to move inside it, or maybe it's calling to you.

### On Collection
You reach out slowly, and the bottle seems to lean into your hand,
as if it has been waiting for you. The moment your fingers close
around the cool glass, you feel a gentle vibration - not physical,
but something deeper, like a harmonious note resonating through
your chest.

### On Return (When Brought Back to Louisa)
Louisa's eyes light up as you present the dream bottle. "Oh, you
found it!" she breathes, cradling it in her palms. "This one
contains the dream of the first sunrise the forest ever saw. It's
been missing for so long."

She holds it up to the light, and for a moment, you both see it -
that ancient dawn, painting the world in colors that no longer exist.

### On Examine (While in Inventory)
The dream bottle pulses gently in your pack. The mist inside swirls
with colors between purple and silver, like captured twilight. When
you concentrate, you can almost hear whispers of forgotten memories.
```

---

## Step 3: Modify execute_game_command() to Load Markdown

### Current Code Structure
```python
async def execute_game_command(...):
    # Parse command with Haiku
    action_type = await self._parse_command_haiku(command)

    # Hardcoded routing
    if action_type == "look":
        return await self._find_instances_at_location(...)
    elif action_type == "collect":
        return await self._collect_item(...)
```

### Target Code Structure
```python
async def execute_game_command(...):
    # 1. Parse command to get action type + target
    parsed = await self._parse_command_haiku(command)
    action_type = parsed["action"]
    target = parsed.get("target")

    # 2. Load markdown for this command
    command_md_path = f"experiences/{experience}/game-logic/{action_type}.md"
    command_rules = await self._load_context(command_md_path)

    # 3. Load current game state
    game_state = await self._load_game_state(experience, user_id)

    # 4. If target object specified, load its template
    target_template = None
    if target:
        target_template = await self._find_and_load_template(
            experience, target, game_state
        )

    # 5. Build prompt with markdown rules + state + templates
    prompt = self._build_game_command_prompt(
        command=command,
        action_type=action_type,
        command_rules=command_rules,
        game_state=game_state,
        target_template=target_template
    )

    # 6. LLM interprets and generates response
    response = await self.llm_service.chat_completion(
        messages=[
            {"role": "system", "content": "You are the game master..."},
            {"role": "user", "content": prompt}
        ],
        model="claude-3-haiku-20240307",
        temperature=0.7
    )

    # 7. Parse LLM response for state changes
    state_changes = self._extract_state_changes(response)

    # 8. Execute state changes (still use existing JSON logic)
    if state_changes:
        await self._apply_state_changes(
            experience, user_id, state_changes
        )

    # 9. Return narrative + structured response
    return {
        "narrative": response["response"],
        "actions": state_changes.get("actions", []),
        "state_changes": state_changes.get("state", {})
    }
```

### New Helper Methods Needed

```python
async def _find_and_load_template(
    self,
    experience: str,
    target_name: str,
    game_state: Dict
) -> Optional[Dict]:
    """
    Find target object (item/NPC) in game state and load its template.

    1. Search manifest for object matching target_name
    2. Get template_id from instance
    3. Load template markdown file
    4. Return template content + instance data
    """
    pass

async def _load_game_state(
    self,
    experience: str,
    user_id: str
) -> Dict:
    """
    Load complete game state for player.

    Includes:
    - Current location (waypoint/sublocation)
    - Inventory contents
    - Discovered locations
    - NPC states
    - Quest progress
    """
    pass

def _build_game_command_prompt(
    self,
    command: str,
    action_type: str,
    command_rules: Dict[str, str],  # Markdown files
    game_state: Dict,
    target_template: Optional[Dict]
) -> str:
    """
    Build comprehensive prompt for LLM.

    Format:
    ---
    # Game Command Interpretation

    ## Command Rules
    {command_rules markdown content}

    ## Current Game State
    - Location: {waypoint}/{sublocation}
    - Inventory: {items}
    - Available objects: {objects at location}

    ## Target Object Template (if applicable)
    {target template markdown}

    ## Player Command
    "{command}"

    ## Your Task
    Interpret this command according to the rules above. Generate:
    1. Narrative response using templates where available
    2. State changes needed (JSON format)
    3. Any triggered events or discoveries
    ---
    """
    pass

def _extract_state_changes(self, llm_response: Dict) -> Dict:
    """
    Parse LLM response for structured state changes.

    Look for JSON blocks or structured sections indicating:
    - Items collected/dropped
    - Location changes
    - NPC state updates
    - Quest progress
    """
    pass
```

---

## Step 4: Create Markdown Files for Each Experience

### wylding-woods Commands to Create

1. **look.md** - Observation and examination
2. **collect.md** - Item pickup
3. **return.md** - Return items to NPCs
4. **inventory.md** - Show what player carries
5. **talk.md** - NPC conversations

Estimated: **5 command files** × ~150 lines = 750 lines markdown

### west-of-house Commands to Create

1. **look.md** - Classic Zork-style observation
2. **take.md** - Pick up items
3. **drop.md** - Drop items
4. **use.md** - Use items (lamp, matches, sword)
5. **go.md** - Navigation between rooms
6. **inventory.md** - List inventory
7. **open.md** - Open containers (mailbox)
8. **read.md** - Read text (leaflet)
9. **attack.md** - Combat (grue)
10. **light.md** - Special command for lamp

Estimated: **10 command files** × ~100 lines = 1000 lines markdown

### Template Enhancements Needed

**wylding-woods** (2 templates):
- `dream_bottle.md` - Add interaction narratives ✅ (example above)
- `louisa.md` - Add conversation trees and state-dependent dialogue

**west-of-house** (~10 templates):
- Each item (mailbox, matches, sword, lamp, leaflet) needs:
  - On Discovery narrative
  - On Take narrative
  - On Use narrative
  - Item-specific interactions
- Each room needs:
  - Detailed descriptions
  - Lighting variants (lit vs dark)
  - Exit descriptions

---

## Step 5: Test Migration

### Phase 1: Single Command (look)
1. Create `look.md` for wylding-woods
2. Modify `execute_game_command()` to load markdown ONLY for "look"
3. Keep other commands hardcoded during testing
4. Verify narrative quality matches or exceeds hardcoded version

### Phase 2: All Commands (wylding-woods)
1. Create all 5 command markdown files
2. Enable markdown loading for all actions
3. Run full playthrough test
4. Compare response times (will be slower, but within acceptable range)

### Phase 3: West-of-House
1. Create all 10 command markdown files
2. Enhance room/item templates
3. Test complete Zork-style gameplay
4. Verify parser handles classic adventure syntax

---

## Effort Estimation

### Content Creation
| Task | Effort | Lines | Who |
|------|--------|-------|-----|
| wylding-woods commands (5) | 2-3 days | ~750 lines | Game designer |
| wylding-woods templates (2) | 1 day | ~200 lines | Game designer |
| west-of-house commands (10) | 4-5 days | ~1000 lines | Game designer |
| west-of-house templates (10) | 2-3 days | ~800 lines | Game designer |
| **Total Content** | **9-12 days** | **~2750 lines** | |

### Code Changes
| Task | Effort | Who |
|------|--------|-----|
| Modify `execute_game_command()` | 1 day | Backend dev |
| Add `_find_and_load_template()` | 0.5 day | Backend dev |
| Add `_load_game_state()` | 0.5 day | Backend dev |
| Add `_build_game_command_prompt()` | 1 day | Backend dev |
| Add `_extract_state_changes()` | 1 day | Backend dev |
| Write unit tests | 2 days | Backend dev |
| **Total Code** | **6 days** | |

### Testing & Refinement
| Task | Effort | Who |
|------|--------|-----|
| Phase 1 testing (look only) | 1 day | QA + dev |
| Phase 2 testing (all wylding) | 2 days | QA + dev |
| Phase 3 testing (west-of-house) | 2 days | QA + dev |
| Narrative refinement | 3 days | Game designer |
| Performance optimization | 1 day | Backend dev |
| **Total Testing** | **9 days** | |

### **Grand Total: 24-27 days** (~5-6 weeks)

---

## Benefits of Migration

### 1. Content-Driven Development
- Game designers edit markdown, not Python
- Faster iteration on narrative and rules
- No code deployment needed for content changes

### 2. Consistency with Design Intent
- Matches rock-paper-scissors architecture
- Fulfills original KB-driven vision
- Templates actually used at runtime

### 3. Rich Narrative Possibilities
- LLM generates contextual responses
- Can reference player history and state
- Natural language feels less robotic

### 4. Easier Expansion
- New commands = new markdown files
- New items = new templates with narratives
- No Python code changes needed

### 5. Multi-Experience Support
- Each experience defines its own commands
- Shared framework, customized logic
- Easy to add new game genres

---

## Risks & Mitigations

### Risk 1: Slower Response Times
**Current**: 1-2s (hardcoded)
**With Markdown**: 2-4s (LLM generation)

**Mitigation**:
- Cache common command interpretations
- Use Haiku for generation (fast + cheap)
- Pre-load markdown files in memory
- Stream responses to user

### Risk 2: Non-Deterministic Narratives
**Issue**: LLM might generate different text each time

**Mitigation**:
- Use low temperature (0.3-0.5) for consistency
- Provide strong narrative templates
- Cache and reuse good generations
- Allow designers to pin specific narratives

### Risk 3: State Change Parsing Errors
**Issue**: LLM might not format state changes correctly

**Mitigation**:
- Structured output format in prompt
- JSON validation before applying changes
- Fallback to no-op if parse fails
- Log failures for analysis

### Risk 4: Content Quality Varies
**Issue**: Markdown quality depends on writing skill

**Mitigation**:
- Provide templates and examples
- Establish style guide
- Review process for new content
- Iterate based on player feedback

---

## Alternative: Hybrid Approach

Keep JSON operations fast, use markdown for narratives only:

```python
async def execute_game_command(...):
    # Fast: Parse and execute state changes (current system)
    result = await self._execute_hardcoded_action(...)

    # Contextual: Load markdown to enhance narrative
    command_md = await self._load_context(f"game-logic/{action}.md")
    template_md = await self._load_template_if_applicable(...)

    # Generate rich narrative using markdown + state result
    enhanced_narrative = await self._generate_narrative(
        command_md, template_md, result
    )

    # Return enhanced result
    return {
        **result,  # Structured state changes (fast)
        "narrative": enhanced_narrative  # Rich text (slower but better)
    }
```

**Benefits**:
- Keeps fast JSON state management
- Adds rich markdown narratives
- Lower risk migration path
- Easier to test incrementally

---

## Recommendation

### Suggested Path Forward

1. **Start with Hybrid Approach** (2-3 weeks)
   - Keep hardcoded state management
   - Add markdown narrative enhancement
   - Migrate look + collect commands first
   - Measure impact on response time and quality

2. **Evaluate Results** (1 week)
   - Gather player feedback
   - Analyze response time metrics
   - Assess content creation workflow

3. **Full Migration if Successful** (3-4 weeks)
   - Move state change logic to markdown
   - Migrate all remaining commands
   - Enhance all templates
   - Deploy to production

### Success Criteria
- ✅ Response time < 3s for 95% of commands
- ✅ Narrative quality rated 4+ / 5 by players
- ✅ Game designers can add commands without dev help
- ✅ Zero Python changes needed for content updates
