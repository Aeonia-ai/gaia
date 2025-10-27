# KB Repository Structure and Agent Behavior

**Date**: October 2025
**Status**: Verified Against Production
**Repository**: [`Aeonia-ai/gaia-knowledge-base`](https://github.com/Aeonia-ai/gaia-knowledge-base)

## Overview

This document provides a verified walkthrough of the KB repository structure, agent behavior, and deployment architecture based on actual production inspection. It clarifies how the KB system sources its content from GitHub (not local filesystem) and how the intelligent agent interprets this content.

## Repository Source: Git-First Architecture

### ✅ Verified Configuration

**Source of Truth**: GitHub Repository
```bash
Repository: https://github.com/Aeonia-ai/gaia-knowledge-base
Size: 828KB
Files: 36 markdown files
Location: /kb inside container (ephemeral storage)
```

**Container Deployment**:
- ❌ **NOT** mounted from local filesystem
- ✅ **IS** cloned from GitHub on container startup
- ✅ **Ephemeral** container storage (no Docker volume for /kb)
- ✅ **Local-remote parity**: Dev environment matches production

**Recent Commits**:
```
1170648 - Add Zork-like text adventure game - West of House
9d391e4 - Implement KOS-style Rock Paper Scissors game
ad25859 - Implement MMOIRL KB structure - shared platform mechanics
c6a2bb2 - first commit
```

### Docker Configuration

**docker-compose.yml**:
```yaml
kb-service:
  volumes:
    - ./app:/app/app  # Code only, NO KB mount
  environment:
    - KB_PATH=/kb  # Container path, NOT host path
    - KB_GIT_REPO_URL=https://github.com/Aeonia-ai/gaia-knowledge-base
    - KB_GIT_AUTO_CLONE=true
    - KB_STORAGE_MODE=git
```

**Dockerfile.kb**:
```dockerfile
# Install tools for KB operations
RUN apt-get install -y \
    ripgrep \  # Fast search
    git        # Repository management
```

### Startup Sequence

```
Container Start
  ↓
Service Initialize (kb_startup.py)
  ↓
Check: /kb/.git exists?
  ├─ YES → Skip clone (files already present)
  └─ NO → Background git clone from GitHub
       ↓
       Service starts immediately (<2 seconds)
       ↓
       Clone completes in background (~5-10 seconds)
  ↓
KB Agent Ready (118 files loaded)
```

**Key Insight**: Service starts immediately, git clone happens in background. This ensures fast deployment and prevents timeout issues with large repositories.

## Repository Structure

### Directory Tree

```
/kb/ (828KB, 36 markdown files)
├── admin/
│   └── +admin_commands.md              # Admin command reference
│
├── experiences/                         # MMOIRL game experiences
│   ├── +experiences.md                 # Universal experience system
│   │
│   ├── rock-paper-scissors/            # Simple competitive game
│   │   ├── GAME.md                     # LLM execution instructions
│   │   ├── +game.md                    # Game index
│   │   ├── rules/
│   │   │   ├── +rules.md               # Rules index
│   │   │   ├── core/
│   │   │   │   ├── +core.md
│   │   │   │   ├── basic-play.md       # How to play
│   │   │   │   └── win-conditions.md   # Scoring rules
│   │   │   └── meta/
│   │   │       ├── +meta.md
│   │   │       └── ai-behavior.md      # AI opponent logic
│   │   └── state/                      # Game state (if used)
│   │
│   ├── west-of-house/                  # Zork-like text adventure
│   │   ├── +game.md                    # Game entry point
│   │   ├── mechanics/
│   │   │   └── +mechanics.md           # Game mechanics index
│   │   ├── state/                      # Session management
│   │   └── world/                      # Game world definition
│   │       ├── +world.md               # World index
│   │       ├── items/                  # Interactive objects
│   │       │   ├── +items.md
│   │       │   ├── lamp.md             # Brass lantern
│   │       │   ├── leaflet.md          # Welcome leaflet
│   │       │   ├── mailbox.md          # Small mailbox
│   │       │   ├── matches.md          # Box of matches
│   │       │   └── sword.md            # Elvish sword
│   │       ├── creatures/              # NPCs and enemies
│   │       │   ├── +creatures.md
│   │       │   └── grue.md             # The infamous Grue
│   │       └── rooms/                  # Locations
│   │           ├── +rooms.md
│   │           └── west-of-house.md    # Starting location
│   │
│   └── zork/                           # Classic text adventure
│       ├── +interpreter.md             # Game interpreter rules
│       ├── rules/
│       ├── state/
│       └── world/
│           └── locations.md
│
└── shared/                             # Platform-wide mechanics
    └── mmoirl-platform/
        └── core-mechanics/
            └── combat.md               # Universal combat system
```

## Instance Management Structure (Phase 2 - Implemented October 2025)

**Status**: ✅ Design Complete, Implementation In Progress

### Overview

Phase 2 introduces a file-based instance management system for tracking dynamic game objects and player progress in AR/location-based experiences like Wylding Woods. This extends the existing KB structure with runtime state management.

**See**: [100-instance-management-implementation.md](./100-instance-management-implementation.md) for complete design

### New Directory Structure

```
/kb/experiences/wylding-woods/
├── waypoints/                      # ✅ Existing (37 AR location markers)
│   ├── waypoint_01a.md
│   └── waypoint_28a.md
│
├── instances/                      # 🆕 NEW - Live game instances
│   ├── manifest.json               # Central instance registry
│   ├── npcs/
│   │   └── louisa_1.json           # NPC instance at specific location
│   └── items/
│       └── dream_bottle_1.json     # Item instance at specific location
│
├── templates/                      # 🆕 NEW - Design-time definitions
│   ├── npcs/
│   │   └── louisa.md               # Character template
│   └── items/
│       └── dream_bottle.md         # Item template
│
└── players/                        # 🆕 NEW - Per-player progress
    └── {user_id}/
        └── wylding-woods/
            └── progress.json       # Player's inventory, state
```

**Implementation Status**:
- ✅ `waypoints/` directory: 37 files exist (implemented)
- 📝 `instances/` directory: Empty, ready for manifest.json and instance files (to be created)
- 📝 `templates/` directory: Empty, ready for template markdown files (to be created)
- 📝 `players/` directory: Will be created on first player interaction

All directories follow the validated design in [100-instance-management-implementation.md](./100-instance-management-implementation.md).

### Key Design Decisions

**1. Incremental IDs (Not UUIDs)**
- File naming: `louisa_1.json`, `louisa_2.json`, `dream_bottle_1.json`
- Prevents LLM hallucination (validated via Perplexity research)
- Human-readable and debuggable
- IDs never reused (tracked in manifest.json)

**2. Template vs Instance Separation**
- **Templates** (markdown): Design-time definitions, shared across all instances
- **Instances** (JSON): Runtime state, specific to each spawned object
- Example: `louisa.md` template → `louisa_1.json` instance at waypoint_28a

**3. Three-Layer Architecture**
```
Layer 1: World Instances (instances/*.json)
  ↓ (shared state - NPC locations, world items)
Layer 2: Player Progress (players/{user_id}/*.json)
  ↓ (per-user state - inventory, quest status)
Layer 3: Player World View (runtime computed)
  ↓ (what player sees - Layer 1 minus collected items)
```

**4. GPS-to-Waypoint Resolution**
```
Unity sends GPS (37.9061, -122.5450)
  ↓
Server calculates closest waypoint via Haversine (50m radius)
  ↓ (finds waypoint_28a at Mill Valley Library)
Server filters instances by waypoint
  ↓ (returns [louisa_1, dream_bottle_1] at waypoint_28a)
Player sees available instances at current location
```

**5. Semantic Name Resolution**
- **LLM layer**: Works with semantic names ("dream_bottle", "louisa")
- **Code layer**: Resolves to instance IDs (dream_bottle_1.json)
- **Critical rule**: NEVER trust LLM to generate/select instance IDs
- Code enforces location-based filtering to prevent ambiguity

### File Formats

**instances/manifest.json** (Central Registry):
```json
{
  "experience": "wylding-woods",
  "next_id": 3,
  "instances": [
    {
      "id": 1,
      "semantic_name": "louisa",
      "type": "npc",
      "template": "/experiences/wylding-woods/templates/npcs/louisa.md",
      "location": "waypoint_28a",
      "state": {
        "active": true,
        "met_by_users": []
      },
      "_version": 1
    },
    {
      "id": 2,
      "semantic_name": "dream_bottle",
      "type": "item",
      "template": "/experiences/wylding-woods/templates/items/dream_bottle.md",
      "location": "waypoint_28a",
      "state": {
        "collected": false,
        "collected_by": null
      },
      "_version": 1
    }
  ]
}
```

**instances/items/dream_bottle_1.json** (Item Instance):
```json
{
  "id": 1,
  "semantic_name": "dream_bottle",
  "type": "item",
  "template": "/experiences/wylding-woods/templates/items/dream_bottle.md",
  "location": "waypoint_28a",
  "state": {
    "collected": false,
    "collected_by": null,
    "collected_at": null
  },
  "description": "A glass bottle filled with shimmering, ethereal liquid",
  "_version": 1,
  "_created": "2025-10-26T10:00:00Z",
  "_updated": "2025-10-26T10:00:00Z"
}
```

**players/{user_id}/wylding-woods/progress.json** (Player State):
```json
{
  "experience": "wylding-woods",
  "user_id": "user123",
  "state": {
    "inventory": [
      {
        "instance_id": 2,
        "semantic_name": "dream_bottle",
        "collected_at": "2025-10-26T10:30:00Z"
      }
    ],
    "met_npcs": [1],
    "current_waypoint": "waypoint_28a"
  },
  "_version": 1,
  "_created": "2025-10-26T09:00:00Z",
  "_updated": "2025-10-26T10:30:00Z"
}
```

### Integration with KB Agent

**Command Flow Example**: "Collect dream bottle"

```python
# 1. Unity sends GPS coordinates
gps = (37.9061, -122.5450)

# 2. Server resolves to waypoint
waypoint = find_closest_waypoint(gps)  # → waypoint_28a

# 3. Load manifest and filter by location
manifest = load_manifest("/kb/experiences/wylding-woods/instances/manifest.json")
candidates = [inst for inst in manifest['instances']
              if inst['semantic_name'] == "dream_bottle"
              and inst['location'] == waypoint]

# 4. LLM works with semantic name, code selects instance
instance = candidates[0]  # dream_bottle_1

# 5. Update instance state (atomic write)
instance['state']['collected'] = True
instance['state']['collected_by'] = user_id
save_instance_atomic(instance)

# 6. Update player progress
add_to_inventory(user_id, instance_id=1)
```

### Atomic File Operations

**Concurrency Safety**:
```python
# Pattern for atomic writes (prevents corruption)
temp_file = f"{instance_file}.tmp"
with open(temp_file, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(temp_file, instance_file)  # Atomic on POSIX
```

**Rationale**:
- "Last write wins" acceptable at 1-10 player MVP scale
- No complex locking needed (validated via Perplexity research)
- `_version` field included for future optimistic locking
- Migration to PostgreSQL planned at 20-50+ concurrent players

### Migration Path

**Current (MVP)**: File-based JSON storage
- Appropriate for 1-10 concurrent players (Perplexity validated)
- Dictionary-based implementation (not classes)
- Fast delivery (6-9 hours estimated)

**Future (Scale)**: PostgreSQL with class hierarchy
```sql
-- Migration at 20-50+ concurrent players
CREATE TABLE game_instances (
  id SERIAL PRIMARY KEY,
  semantic_name VARCHAR(255),
  location VARCHAR(255),
  state JSONB,
  _version INTEGER DEFAULT 1
);

-- Optimistic locking
UPDATE game_instances
SET state = $1, _version = _version + 1
WHERE id = $2 AND _version = $3;
```

### Design Validation

This design was validated by:
- **server-frantz** (this agent): GPS-to-waypoint resolution, file-based approach
- **server-frantz-gemini**: MMO best practices, template/instance separation
- **Perplexity research**: File-based storage for prototype scale, incremental IDs for LLMs

**See**: [101-design-decisions.md](./101-design-decisions.md) for complete decision rationale

### File Organization Patterns

**1. Index Files (`+name.md`)**
- Prefix `+` indicates navigation/index file
- Contains links to subcontent using wiki links `[[link]]`
- Acts as table of contents for directories
- Example: `+game.md`, `+rules.md`, `+items.md`

**2. GAME.md Files**
- Meta-instructions for the LLM
- Explains how to interpret the game's rules
- Defines execution flow patterns
- Present at experience root level

**3. Hierarchical Structure**
```
experiences/          # Top-level category
  └── game-name/      # Specific experience
      ├── GAME.md     # LLM meta-instructions
      ├── +game.md    # Navigation index
      ├── rules/      # Game mechanics
      ├── state/      # State management
      └── world/      # Content/data
```

**4. Wiki Links**
- Format: `[[relative/path]]` or `[[file-name]]`
- Enable semantic navigation between documents
- Used by agent for context discovery
- Example: `[[../items/lamp]]`, `[[rules/+rules]]`

**5. Frontmatter**
- YAML metadata at file start
- Provides structured data about content
- Example:
```yaml
---
item_id: lamp
type: light_source
danger_level: safe
---
```

## Content Examples

### Rock-Paper-Scissors (Natural Language Rules)

**GAME.md** - Meta-instructions for LLM:
```markdown
# LLM Game Execution Instructions

## Role
You are the game master for Rock Paper Scissors.
You interpret natural language rules and execute them
based on player commands.

## Navigation Pattern
1. Read +game.md for structure
2. Navigate to rules/+rules.md for rule categories
3. Load specific rules based on player action
4. Execute rules and return narrative results

## Rule Interpretation
Rules are written in natural language. When you see:
- "When X happens, Y occurs" - This is a trigger condition
- "The winner is determined by..." - This is a victory condition
- "Players simultaneously..." - This is a timing rule

Interpret these literally and apply them to the game situation.
```

**rules/core/basic-play.md** - Executable Rules:
```markdown
# Basic Play Rules

## Making a Choice
Players simultaneously form one of three shapes with their hand:
- **Rock**: A closed fist
- **Paper**: An open hand with fingers extended
- **Scissors**: A fist with index and middle fingers extended

When playing against an AI opponent, the human player
declares their choice, then the AI makes its choice
simultaneously (the AI does not know the human's choice).

## Valid Choices
Only rock, paper, or scissors are valid choices.
Any other input should prompt the player to choose again.
Variations in spelling or capitalization (ROCK, Rock, rock)
should all be accepted as valid.

## Round Completion
After both players reveal their choices:
1. The winner is determined according to win conditions
2. The result is announced
3. Scores are updated if playing multiple rounds
4. Players can choose to play again or end the game
```

### West of House (Zork-like Adventure)

**world/creatures/grue.md** - Enemy Behavior:
```markdown
# The Grue

> **Creature ID**: grue
> **Type**: Monster
> **Habitat**: Complete darkness
> **Danger Level**: Fatal
> **Weakness**: Any light source

## Description
The grue is a sinister, lurking presence in dark places.
No one has ever seen a grue and lived to tell the tale.

## Behavior Pattern
The grue follows a strict attack sequence in darkness:

### Turn Sequence
1. **Detection** (Turn 1)
   - Message: "It is pitch black. You are likely to be eaten by a grue."
   - Grue becomes aware of prey

2. **Stalking** (Turn 2)
   - Message: "You hear slavering and gnashing sounds in the darkness."
   - Grue moves closer

3. **Approach** (Turn 3)
   - Message: "You feel hot breath on your neck..."
   - Last chance to escape

4. **Attack** (Turn 4)
   - Message: "You have been eaten by a grue!"
   - Result: GAME OVER

## Prevention Methods
- **Primary**: Carry a lit light source (lamp, torch, candle)
- **Secondary**: Exit dark area before turn 4
- **Emergency**: Light a match (temporary, 1 turn protection)

## Grue Rules
- Only exists in complete darkness
- Immediately flees when light appears
- Cannot follow into lit areas
- Cannot be fought (instant death if attacked)
- Makes no sound until stalking phase
```

**world/rooms/west-of-house.md** - Location Definition:
```markdown
# West of House

> **Room ID**: west_of_house
> **Type**: Outdoor
> **Light**: Daylight
> **Exits**: north, east, south

## Description
You are standing in an open field west of a white house,
with a boarded front door. There is a small mailbox here.

## Items Present
- [[../items/mailbox]] - A small mailbox (closed)

## Exits
- **North**: [[north-of-house]] - Path around the house
- **East**: Cannot enter - The door is boarded shut
- **South**: [[forest]] - A forest path

## Valid Actions
### Mailbox Interactions
- "open mailbox" → Opens mailbox, reveals [[../items/leaflet]]
- "close mailbox" → Closes the mailbox
- "examine mailbox" → "A fairly ordinary mailbox, painted red."

### Movement
- "go north" or "n" → Move to north of house
- "go south" or "s" → Enter the forest
- "go east" or "enter house" → "The door is boarded shut."

### Other
- "look" or "l" → Redescribe room
- "examine house" → "The house is a beautiful colonial house..."

## State Changes
- `mailbox_opened`: false → true when opened first time (awards 5 points)
```

### Universal Combat System

**shared/mmoirl-platform/core-mechanics/combat.md**:
```markdown
# Universal Combat Mechanics

## Core Combat Rules

### Damage Calculation
- Base damage = Attacker's power × skill modifier
- Critical hit chance = 5% + (luck stat / 100)
- Critical damage multiplier = 2.0×

### Elemental Interactions
| Element  | Strong Against | Weak Against    |
|----------|---------------|-----------------|
| Fire     | Wood, Ice     | Water, Earth    |
| Water    | Fire, Earth   | Electric, Ice   |
| Earth    | Electric, Fire| Wood, Water     |
| Air      | Earth, Wood   | Fire, Electric  |
| Wood     | Water, Earth  | Fire, Air       |
| Electric | Water, Air    | Earth, Wood     |
| Ice      | Water, Air    | Fire, Electric  |

### Status Effects
- **Burn**: 10% HP damage over 3 turns
- **Freeze**: Skip next turn, 50% defense reduction
- **Poison**: 5% HP damage over 5 turns
- **Stun**: Skip next turn
- **Slow**: Action speed reduced by 50%
- **Blind**: Accuracy reduced by 30%

### Defense Mechanics
- Block chance = (defense stat / 200) × 100%
- Dodge chance = (agility stat / 150) × 100%
- Damage reduction = defense × 0.5%

## Combat Flow
1. Initiative determined by speed stat
2. Player selects action (attack, skill, item, flee)
3. Calculate hit chance: base 85% + (accuracy - target evasion)
4. If hit: apply damage calculation
5. Check for status effects
6. Process turn-end effects
```

## KB Agent Behavior

### Architecture Overview

```
User Query
  ↓
Agent Endpoint (agent_endpoints.py)
  ↓
KB Agent (kb_agent.py)
  ↓
Load Context (_load_context)
  ├─ KB MCP Server (kb_mcp_server.py)
  │   ├─ List directory (ripgrep)
  │   ├─ Read markdown files
  │   └─ Parse frontmatter & wiki links
  ↓
Build Prompt (mode-specific)
  ↓
LLM Service (MultiProviderChatService)
  ├─ Model selection (Haiku vs Sonnet)
  └─ Direct API call to Claude/OpenAI
  ↓
Interpret & Respond
  ↓
Cache Result
  ↓
Return to User
```

### Context Loading Process

When agent processes a query:

**1. Directory Scan**
```python
# From kb_agent.py _load_context()
list_result = await kb_server.list_kb_directory(
    path="/experiences/rock-paper-scissors",
    pattern="*.md"
)
```

**2. Recursive File Discovery**
```python
# Finds all markdown files in tree
for file_info in list_result.get("files", []):
    file_result = await kb_server.read_kb_file(file_path)
    files[file_path] = file_result["content"]

# Also checks subdirectories
for dir_info in list_result.get("directories", []):
    subdir_files = await self._load_context(dir_info["path"])
    files.update(subdir_files)
```

**3. Content Assembly**
```python
# For /experiences/rock-paper-scissors, loads:
{
  "/experiences/rock-paper-scissors/GAME.md": "# LLM Game...",
  "/experiences/rock-paper-scissors/+game.md": "# Game Index...",
  "/experiences/rock-paper-scissors/rules/+rules.md": "# Rules...",
  "/experiences/rock-paper-scissors/rules/core/basic-play.md": "# Basic...",
  "/experiences/rock-paper-scissors/rules/core/win-conditions.md": "# Win...",
  "/experiences/rock-paper-scissors/rules/meta/ai-behavior.md": "# AI..."
}
```

### Prompt Construction

**Decision Mode Example**:
```
Based on the following knowledge base content, make a decision
or provide guidance for this query:

**Query:** I choose rock

**Available Knowledge:**

## /experiences/rock-paper-scissors/GAME.md
[full content of GAME.md]

## /experiences/rock-paper-scissors/rules/core/basic-play.md
[full content of basic-play.md]

## /experiences/rock-paper-scissors/rules/core/win-conditions.md
[full content of win-conditions.md]

Please provide a clear decision or recommendation based on
the available knowledge.
```

### Model Selection

```python
def _select_model_for_query(self, query: str, mode: str) -> str:
    if mode == "validation":
        return "claude-3-5-haiku-20241022"  # Fast
    elif len(query) > 1000 or mode == "synthesis":
        return "claude-sonnet-4-5"  # Powerful
    else:
        return "claude-3-5-haiku-20241022"  # Default
```

**Model Strategy**:
- **Haiku**: Fast validation, simple decisions (~1-2 seconds)
- **Sonnet**: Complex synthesis, workflows (~3-6 seconds)

### Test Results

**Query**: "I choose rock"
**Context**: `/experiences/rock-paper-scissors`
**Mode**: `decision`

**Response** (6 seconds, Claude-3.5-Haiku):
```json
{
  "status": "success",
  "result": {
    "interpretation": "Based on the knowledge base content,
    here's my guidance for 'I choose rock':

    The system should:
    1. Recognize the player's choice of 'rock'
    2. Generate an AI choice (paper, rock, or scissors)
    3. Apply standard Rock Paper Scissors rules
    4. Provide a narrative result

    Recommendation: Proceed with the game by selecting
    a computer choice and resolving the round according
    to standard Rock Paper Scissors rules.",

    "model_used": "claude-3-5-haiku-20241022",
    "context_files": 2,
    "mode": "decision",
    "cached": false
  },
  "metadata": {
    "user_id": "jason@aeonia.ai",
    "context_path": "/experiences/rock-paper-scissors",
    "mode": "decision"
  }
}
```

**Performance Metrics**:
- Response time: ~6 seconds
- Files loaded: 2 markdown files from context path
- Model: Fast model (Haiku) for simple decisions
- Context loading: Recursive directory scan with file reading

## Agent API Endpoints

**Base Path**: `/agent/`

### POST /agent/interpret
Interpret knowledge and generate intelligent response.

**Request**:
```json
{
  "query": "I choose rock",
  "context_path": "/experiences/rock-paper-scissors",
  "mode": "decision",  // decision, synthesis, validation
  "model_hint": null   // optional model override
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "interpretation": "...",
    "model_used": "claude-3-5-haiku-20241022",
    "context_files": 2,
    "mode": "decision",
    "cached": false
  },
  "metadata": {
    "user_id": "jason@aeonia.ai",
    "context_path": "/experiences/rock-paper-scissors",
    "mode": "decision"
  }
}
```

### POST /agent/workflow
Execute markdown-defined workflow.

**Request**:
```json
{
  "workflow_path": "/experiences/rock-paper-scissors/workflows/game-round.md",
  "parameters": {
    "player_choice": "rock",
    "ai_strategy": "random"
  }
}
```

### POST /agent/validate
Validate action against KB rules.

**Request**:
```json
{
  "action": "Player enters dark room without a light",
  "rules_path": "/experiences/west-of-house/world/creatures/grue.md",
  "context": {
    "has_light": false,
    "turns_in_darkness": 0
  }
}
```

### GET /agent/status
Check agent health and capabilities.

**Response**:
```json
{
  "status": "success",
  "agent_status": {
    "initialized": true,
    "cache_entries": 5,
    "capabilities": [
      "knowledge_interpretation",
      "workflow_execution",
      "rule_validation",
      "decision_making",
      "information_synthesis"
    ],
    "supported_modes": ["decision", "synthesis", "validation"]
  }
}
```

## Universal Experience System

From `/experiences/+experiences.md`:

### Concept

All MMOIRL experiences use a universal pattern:
1. **Detection**: Match command to experience triggers
2. **Loading**: Load interpreter rules for the experience
3. **Interpretation**: Apply rules to understand command
4. **Execution**: Generate narrative response
5. **State Update**: Return narrative + embedded JSON state

### State Structure

All experiences share this base:
```json
{
  "experience": "name-of-experience",
  "active": true,
  "started_at": "2025-10-03T15:30:00Z",
  "last_command": "user's last command",
  "experience_data": {
    // Experience-specific state
  }
}
```

### Adding New Experiences

To add a new game/experience:

1. Create folder structure:
```
/kb/experiences/your-experience/
├── GAME.md            # LLM meta-instructions
├── +game.md           # Navigation index
├── rules/             # Game mechanics
├── state/             # State management (optional)
└── world/             # Content/data
```

2. Define interpreter rules in `GAME.md`
3. Write game mechanics in natural language in `rules/*.md`
4. Update `/experiences/+experiences.md` with new entry

The system automatically detects and uses the new experience - **no code changes required**.

## Design Philosophy

### 1. Knowledge as Code

Game rules are written in plain English markdown and become executable via LLM interpretation. No Python game logic required.

**Traditional Approach**:
```python
def play_rock_paper_scissors(player_choice):
    if player_choice not in ['rock', 'paper', 'scissors']:
        return "Invalid choice"
    ai_choice = random.choice(['rock', 'paper', 'scissors'])
    # ... hardcoded game logic
```

**KB Agent Approach**:
```markdown
# rules/core/basic-play.md

## Valid Choices
Only rock, paper, or scissors are valid choices.

## AI Opponent
The AI makes a random choice from the three options.
```

### 2. Zero Hardcoding

New games are added by writing markdown files, not writing Python code. The LLM interprets natural language rules at runtime.

### 3. Context is Everything

Agent loads entire knowledge graphs (all files in directory trees) to understand the full domain before making decisions.

### 4. Markdown as DSL

The repository uses markdown as a domain-specific language:
- **Frontmatter**: Structured metadata
- **Wiki links**: Semantic relationships
- **Hashtags**: Keyword tagging
- **Index files** (`+name.md`): Navigation structure

### 5. Git-First, Container-Ephemeral

The source of truth is GitHub, not local filesystems. Containers clone on startup, ensuring local-remote parity and eliminating "works on my machine" issues.

## Development Workflow

### Local Testing

**1. Clone repository** (happens automatically on container start):
```bash
docker-compose up kb-service
# Logs show: "KB repository already exists with 118 files"
```

**2. Test agent directly**:
```bash
docker exec gaia-kb-service-1 curl -X POST "http://localhost:8000/agent/interpret" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I choose rock",
    "context_path": "/experiences/rock-paper-scissors",
    "mode": "decision"
  }'
```

**3. Inspect repository**:
```bash
# List files
docker exec gaia-kb-service-1 find /kb -name "*.md" | head -20

# Read content
docker exec gaia-kb-service-1 cat /kb/experiences/rock-paper-scissors/GAME.md

# Check git status
docker exec gaia-kb-service-1 git -C /kb log --oneline -5
```

### Adding Content

**To modify KB content**:

1. **Option A: Edit GitHub repository directly**
   - Changes appear after container restart (pulls latest)
   - Or trigger `/sync/from-git` endpoint

2. **Option B: Edit via KB API**
   ```bash
   POST /kb/write
   {
     "path": "/experiences/new-game/GAME.md",
     "content": "# New Game...",
     "message": "Add new game"
   }
   ```
   - Creates git commit automatically
   - Can push to GitHub with `/sync/to-git`

### Debugging

**Check agent initialization**:
```bash
docker logs gaia-kb-service-1 | grep -i "agent\|initialize"
# Should see: "KB Intelligent Agent initialized and ready"
```

**Check repository status**:
```bash
docker exec gaia-kb-service-1 sh -c '
  echo "Files: $(find /kb -name "*.md" | wc -l)"
  echo "Size: $(du -sh /kb)"
  echo "Git: $(git -C /kb log --oneline -1)"
'
```

**Test context loading**:
```bash
curl -X POST "http://localhost:8000/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "rock paper scissors"}'
```

## Environment Variables

```bash
# Repository source
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/gaia-knowledge-base
KB_GIT_AUTH_TOKEN=github_pat_xxx  # For private repos
KB_GIT_AUTO_CLONE=true

# Storage configuration
KB_STORAGE_MODE=git  # git, database, hybrid
KB_PATH=/kb  # Inside container

# Performance
KB_CACHE_TTL=300  # 5 minutes

# Agent behavior
KB_MCP_ENABLED=true
```

## Related Documentation

- **Architecture**: [`/docs/architecture/kb-agent-architecture.md`](../../architecture/kb-agent-architecture.md) - Technical design patterns
- **Overview**: [`/docs/kb/kb-agent-overview.md`](../kb-agent-overview.md) - User-facing capabilities
- **API Reference**: [`/docs/kb/reference/kb-http-api-reference.md`](../reference/kb-http-api-reference.md) - Complete API docs
- **Git Sync**: [`/docs/kb/developer/kb-git-sync-learnings.md`](./kb-git-sync-learnings.md) - Production deployment patterns
- **Container Storage**: [`/docs/kb/developer/kb-container-storage-migration.md`](./kb-container-storage-migration.md) - Storage architecture

## Summary

The KB system is a **markdown-to-execution interpreter** that:
- ✅ Sources content from GitHub (not local filesystem)
- ✅ Clones repository into ephemeral container storage
- ✅ Uses ripgrep for fast search
- ✅ Loads entire knowledge graphs for context
- ✅ Interprets natural language rules via Claude
- ✅ Executes player commands without hardcoded game logic
- ✅ Enables adding new games by writing markdown, not code

This is a true **"knowledge-driven game engine"** where games are data, not code.
