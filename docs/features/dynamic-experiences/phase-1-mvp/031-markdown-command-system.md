# Markdown Command System

## Overview

The GAIA platform uses a **markdown-driven command system** where game commands are content, not code. Commands are automatically discovered from `.md` files in the experience's `game-logic/` directory.

## Architecture

### Dual Directory Structure

The system supports **two types of commands** with separate directories:

```
/kb/experiences/{experience}/
├── game-logic/      # Player commands (look, go, collect, talk)
└── admin-logic/     # Admin commands (@list, @inspect, @edit, @delete)
```

**Key Distinction:**
- **game-logic/** - Commands available to all players (no @ prefix)
- **admin-logic/** - Admin-only commands (requires @ prefix)

### Auto-Discovery

The system automatically scans **both directories** for command files at runtime:

```python
# No hardcoded command lists!
# Player commands: /kb/experiences/{experience}/game-logic/*.md
# Admin commands: /kb/experiences/{experience}/admin-logic/*.md
```

**Benefits**:
- ✅ Add new commands by creating `.md` files - no code changes required
- ✅ Different experiences can have different command sets
- ✅ Content creators can add commands without touching Python code
- ✅ Single source of truth (markdown files)
- ✅ Admin commands separated from player commands

### Command Detection Flow

1. User sends message: `"go to counter"` or `"@list waypoints"`
2. `_discover_available_commands()` scans **both** game-logic and admin-logic directories
3. Parses frontmatter from all `.md` files to build command registry
4. Detects admin commands by @ prefix
5. LLM analyzes user intent against available commands
6. Routes to appropriate command markdown for execution

**Admin Command Detection:**
- Commands starting with @ are routed to admin-logic handlers
- `requires_admin: true` flag checked in frontmatter
- Permission enforcement (future feature - placeholder currently)

## Creating a New Command

### 1. Create Markdown File

Create `/kb/experiences/{experience}/game-logic/{command_name}.md`:

```markdown
---
command: examine
aliases: [inspect, study, investigate, scrutinize]
description: Examine an object in detail
requires_location: true
requires_target: true
state_model_support: [shared, isolated]
---

# Examine Command

## Intent Detection

This command handles:
- Detailed inspection: "examine mailbox", "inspect bottle"
- Natural language: "look closely at the sign", "study the map"

Natural language patterns:
- examine [object]
- inspect [object]
- look closely at [object]
- what is [object]

## Input Parameters

Extract from user message:
- `target`: Object name to examine

## State Access

Required from player view:
- `player.current_location` - Player's current location
- `player.current_sublocation` (optional) - Current sublocation

Required from world state:
- `locations[current_location].items` - Items at location
- `locations[current_location].sublocations[sublocation].items` - Items at sublocation

## Execution Logic

1. **Parse target object name** from user message
2. **Get current position** (location + sublocation if any)
3. **Find matching item** in current location/sublocation
4. **Check visibility** - item must have `visible: true`
5. **Generate detailed description** from item metadata
6. **Return narrative** with no state changes

## Response Format

Success response:
```json
{
  "success": true,
  "narrative": "You examine the brass lantern closely...\n\nA sturdy brass lantern with intricate engravings. It feels slightly warm to the touch and you can see a small switch on the side.",
  "available_actions": [
    "take brass lantern",
    "turn on lantern",
    "look around"
  ],
  "state_updates": null,
  "metadata": {
    "command_type": "examine",
    "target": "brass_lantern",
    "location": "west_of_house"
  }
}
```

Error response (item not found):
```json
{
  "success": false,
  "error": {
    "code": "item_not_found",
    "message": "You don't see that here"
  },
  "narrative": "You don't see a 'telescope' here. Try 'look around' to see what's available.",
  "available_actions": ["look around"],
  "state_updates": null
}
```

## Examples

### Example 1: Examine visible item
**Input**: "examine brass lantern"
**State**: Player at west_of_house, lantern is visible
**Output**: Detailed description of lantern with available actions
**State Updates**: None (examine doesn't change state)
```

### 2. Frontmatter Fields

Required fields:
- `command` - Primary command name (used for routing)
- `description` - Human-readable description

Optional fields:
- `aliases` - List of synonyms (e.g., `[move, walk, travel]`)
- `requires_location` - Does command need location context?
- `requires_target` - Does command need a target object/direction?
- `state_model_support` - Which state models support this? `[shared, isolated]`
- `requires_admin` - **Admin commands only** - Set to `true` for admin-logic commands

### 3. LLM Instructions

The markdown content is sent to the LLM with:
- Current world state
- Player view state
- User's message

The LLM must return **pure JSON** with:
- `success` - Boolean
- `narrative` - User-facing text
- `available_actions` - List of suggested next actions
- `state_updates` - State changes (or null)
- `metadata` - Command metadata

## State Updates

### Update Format

```json
{
  "player": {
    "path": "player.inventory",
    "operation": "append",
    "item": {
      "id": "brass_lantern",
      "type": "light_source",
      "semantic_name": "brass lantern"
    }
  },
  "world": {
    "path": "locations.west_of_house.items",
    "operation": "remove",
    "item_id": "brass_lantern"
  }
}
```

### Operations

- `update` - Replace value at path
- `append` - Add item to array (creates marker `{"$append": item}`)
- `remove` - Remove item from array (creates marker `{"$remove": item}`)

**Note**: The `_merge_updates()` function interprets these markers and performs the actual array operations.

## Existing Commands

### Player Commands (game-logic/)

#### look.md
- **Aliases**: observe, examine, see, search, explore
- **Purpose**: Observe surroundings and items
- **State Updates**: None

#### inventory.md
- **Aliases**: inv, i, check inventory
- **Purpose**: View items in player inventory
- **State Updates**: None

#### collect.md
- **Aliases**: take, pick up, get, grab
- **Purpose**: Pick up items from location
- **State Updates**: Moves item from location to inventory

#### go.md
- **Aliases**: move, walk, travel, head, enter
- **Purpose**: Navigate between locations/sublocations
- **State Updates**: Updates `player.current_location` or `player.current_sublocation`

#### talk.md
- **Aliases**: talk, speak, chat, greet, say, ask, tell
- **Purpose**: Engage in natural conversation with NPCs
- **State Updates**: Updates NPC relationship state (trust, conversation history)
- **See**: [NPC Interaction System](./npc-interaction-system.md) for full documentation

### Admin Commands (admin-logic/)

#### @list-waypoints.md
- **Aliases**: @list waypoints, @show waypoints, @waypoints
- **Purpose**: List all GPS waypoints (admin only)
- **Requires**: @ prefix, admin role (future)
- **State Updates**: None

#### @inspect-waypoint.md
- **Purpose**: View detailed waypoint information
- **Requires**: @ prefix, waypoint ID
- **State Updates**: None

#### @edit-waypoint.md
- **Purpose**: Modify waypoint properties
- **Requires**: @ prefix, waypoint ID, property, value
- **State Updates**: Updates waypoint metadata

#### @create-waypoint.md
- **Purpose**: Create new GPS waypoint
- **Requires**: @ prefix, waypoint ID, name, coordinates
- **State Updates**: Creates new waypoint file

#### @delete-waypoint.md
- **Purpose**: Delete waypoint (requires CONFIRM)
- **Requires**: @ prefix, waypoint ID, CONFIRM keyword
- **State Updates**: Removes waypoint file

#### @list-items.md
- **Aliases**: @show items, @items
- **Purpose**: List all item instances (admin only)
- **State Updates**: None

#### @inspect-item.md
- **Purpose**: View detailed item instance information
- **Requires**: @ prefix, instance ID
- **State Updates**: None

**See**: [Admin Command System](./admin-command-system.md) for complete documentation

## Testing Commands

### Direct KB Endpoint

```bash
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "examine the mailbox",
    "experience": "west-of-house"
  }'
```

### Via Chat Service

```bash
curl -X POST "http://localhost:8666/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "message": "I want to play west-of-house. Look around.",
    "stream": false
  }'
```

## Command Discovery Implementation

Location: `app/services/kb/experience_endpoints.py`

### _discover_available_commands()

```python
async def _discover_available_commands(experience: str) -> tuple[dict[str, list[str]], dict[str, bool]]:
    """
    Discover available commands by scanning both game-logic and admin-logic directories.

    Returns:
        Tuple of (command_mappings, admin_required_dict)
        - command_mappings: Dictionary mapping command name to list of aliases/synonyms
        - admin_required_dict: Dictionary mapping command name to requires_admin boolean
    """
    kb_root = Path(settings.KB_PATH)

    commands = {}
    admin_required = {}

    # Scan game-logic directory (player commands)
    game_logic_dir = kb_root / "experiences" / experience / "game-logic"
    for md_file in game_logic_dir.glob("*.md"):
        command_name, aliases, is_admin = _parse_command_frontmatter(md_file)
        if command_name:
            commands[command_name] = [command_name] + aliases
            admin_required[command_name] = False  # Player commands

    # Scan admin-logic directory (admin commands)
    admin_logic_dir = kb_root / "experiences" / experience / "admin-logic"
    if admin_logic_dir.exists():
        for md_file in admin_logic_dir.glob("*.md"):
            command_name, aliases, is_admin = _parse_command_frontmatter(md_file)
            if command_name:
                commands[command_name] = [command_name] + aliases
                admin_required[command_name] = is_admin or True  # Admin commands

    return commands, admin_required

def _parse_command_frontmatter(md_file: Path) -> tuple[str, list[str], bool]:
    """Parse frontmatter from markdown file."""
    content = md_file.read_text()

    if not content.startswith("---"):
        return None, [], False

    frontmatter_end = content.find("---", 3)
    if frontmatter_end == -1:
        return None, [], False

    frontmatter = content[3:frontmatter_end].strip()

    # Extract command name, aliases, and admin flag
    command_name = None
    aliases = []
    requires_admin = False

    for line in frontmatter.split("\n"):
        if line.startswith("command:"):
            command_name = line.split(":", 1)[1].strip()
        elif line.startswith("aliases:"):
            aliases_str = line.split(":", 1)[1].strip()
            if aliases_str.startswith("[") and aliases_str.endswith("]"):
                aliases = [a.strip().strip("'\"") for a in aliases_str[1:-1].split(",")]
        elif line.startswith("requires_admin:"):
            admin_str = line.split(":", 1)[1].strip().lower()
            requires_admin = admin_str == "true"

    return command_name, aliases, requires_admin
```

### _detect_command_type()

```python
async def _detect_command_type(kb_agent_instance, message: str, experience: str) -> tuple[str, bool]:
    """
    Use LLM to detect which command type the user is trying to execute.

    Returns:
        Tuple of (command_type, requires_admin)
    """
    # Discover available commands from markdown files
    command_mappings, admin_required_dict = await _discover_available_commands(experience)
    available_commands = list(command_mappings.keys())

    # Build command mapping text for LLM
    mapping_lines = []
    for cmd, keywords in command_mappings.items():
        admin_marker = " [ADMIN]" if admin_required_dict.get(cmd, False) else ""
        mapping_lines.append(f"- {cmd}{admin_marker}: {', '.join(keywords)}")

    detection_prompt = f"""You are a command parser for a text adventure game.

User message: "{message}"
Available commands: {", ".join(available_commands)}

Command mappings:
{chr(10).join(mapping_lines)}

Respond with ONLY the command name (one word, lowercase).
If the message starts with @, it's an admin command.
"""

    response = await kb_agent_instance.llm_service.chat_completion(
        messages=[
            {"role": "system", "content": "You are a command parser."},
            {"role": "user", "content": detection_prompt}
        ],
        model="claude-haiku-4-5",
        user_id="system",
        temperature=0.1
    )

    command_type = response["response"].strip().lower()
    requires_admin = admin_required_dict.get(command_type, False)

    return command_type, requires_admin
```

## Best Practices

### 1. Clear Intent Detection
- List all natural language patterns the command should match
- Include common synonyms and variations
- Be specific about what the command does vs. doesn't do

### 2. Comprehensive Examples
- Provide at least 3 examples with different scenarios
- Show both success and error cases
- Include actual JSON state updates

### 3. Defensive State Checks
- Always validate item existence before state changes
- Check item visibility (`visible: true`)
- Verify location context before operations
- Handle missing/null values gracefully

### 4. Meaningful Narratives
- Describe what happened, not just success/failure
- Suggest next actions to guide player
- Use consistent tone and style for the experience

### 5. Minimal State Updates
- Only update what changed
- Use `null` for commands that don't change state (look, inventory)
- Keep metadata separate from state changes

## Troubleshooting

### Command Not Detected

**Symptom**: LLM defaults to "look" for your new command

**Causes**:
- Frontmatter parsing failed (check YAML syntax)
- Command file not in `game-logic/` directory
- Missing `command:` field in frontmatter

**Solution**:
```bash
# Check logs for discovery
docker logs gaia-kb-service-1 2>&1 | grep "Discovered command"

# Verify frontmatter format
cat /kb/experiences/{experience}/game-logic/{command}.md | head -10
```

### State Not Persisting

**Symptom**: State changes work but don't persist across requests

**Causes**:
- LLM returning wrong field name (`data` vs. `item`)
- Merge operation markers not being interpreted
- Missing array in template (for append operations)

**Solution**: Check logs for state update details:
```bash
docker logs gaia-kb-service-1 2>&1 | grep "MERGE\|APPLY"
```

### Command Execution Fails

**Symptom**: "I had trouble understanding that command"

**Causes**:
- LLM couldn't parse command intent
- Markdown file has invalid JSON examples
- Missing required state data

**Solution**: Enable diagnostic logging and check LLM response format

## Performance

### Caching (Future Enhancement)

Command discovery is currently run on every request. For production, consider caching:

```python
# Cache command mappings per experience
_command_cache: dict[str, dict[str, list[str]]] = {}

async def _get_commands_cached(experience: str):
    if experience not in _command_cache:
        _command_cache[experience] = await _discover_available_commands(experience)
    return _command_cache[experience]
```

**When to invalidate cache**:
- Experience content updated
- Service restart
- Manual cache clear endpoint

## Admin vs Player Commands

### Player Commands
- **Location**: `/kb/experiences/{exp}/game-logic/`
- **Prefix**: None (e.g., `look`, `go`, `talk`)
- **Access**: All players
- **Execution**: LLM interprets intent, generates narrative response
- **Response Time**: 1-3 seconds (LLM latency)
- **Examples**: look, go, collect, inventory, talk

### Admin Commands
- **Location**: `/kb/experiences/{exp}/admin-logic/`
- **Prefix**: @ symbol (e.g., `@list`, `@inspect`, `@edit`)
- **Access**: Admins only (future RBAC enforcement)
- **Execution**: Direct file system operations
- **Response Time**: <30ms (no LLM)
- **Examples**: @list-waypoints, @inspect-item, @edit-waypoint, @delete-waypoint

**See**: [Admin Command System](./admin-command-system.md) for complete admin command documentation

## Related Documentation

- [Admin Command System](./admin-command-system.md) - Complete admin command reference
- [NPC Interaction System](./npc-interaction-system.md) - Talk command and NPC conversations
- [Unified State Model](./unified-state-model/experience-config-schema.md) - Player views and state management
- [Experience Configuration](./unified-state-model/config-examples.md) - Experience setup
- [Chat Integration Complete](./chat-integration-complete.md) - Chat service integration
