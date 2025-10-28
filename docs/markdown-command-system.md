# Markdown Command System

## Overview

The GAIA platform uses a **markdown-driven command system** where game commands are content, not code. Commands are automatically discovered from `.md` files in the experience's `game-logic/` directory.

## Architecture

### Auto-Discovery

The system automatically scans for command files at runtime:

```python
# No hardcoded command lists!
# Commands are discovered from: /kb/experiences/{experience}/game-logic/*.md
```

**Benefits**:
- ✅ Add new commands by creating `.md` files - no code changes required
- ✅ Different experiences can have different command sets
- ✅ Content creators can add commands without touching Python code
- ✅ Single source of truth (markdown files)

### Command Detection Flow

1. User sends message: `"go to counter"`
2. `_discover_available_commands()` scans game-logic directory
3. Parses frontmatter from all `.md` files to build command registry
4. LLM analyzes user intent against available commands
5. Routes to appropriate command markdown for execution

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

### look.md
- **Aliases**: observe, examine, see, search, explore
- **Purpose**: Observe surroundings and items
- **State Updates**: None

### inventory.md
- **Aliases**: inv, i, check inventory
- **Purpose**: View items in player inventory
- **State Updates**: None

### collect.md
- **Aliases**: take, pick up, get, grab
- **Purpose**: Pick up items from location
- **State Updates**: Moves item from location to inventory

### go.md
- **Aliases**: move, walk, travel, head, enter
- **Purpose**: Navigate between locations/sublocations
- **State Updates**: Updates `player.current_location` or `player.current_sublocation`

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
async def _discover_available_commands(experience: str) -> dict[str, list[str]]:
    """
    Discover available commands by scanning game-logic directory for .md files.

    Returns:
        Dictionary mapping command name to list of aliases/synonyms
    """
    kb_root = Path(settings.KB_PATH)
    game_logic_dir = kb_root / "experiences" / experience / "game-logic"

    commands = {}

    # Scan for .md files
    for md_file in game_logic_dir.glob("*.md"):
        content = md_file.read_text()

        # Parse frontmatter
        if content.startswith("---"):
            frontmatter_end = content.find("---", 3)
            if frontmatter_end != -1:
                frontmatter = content[3:frontmatter_end].strip()

                # Extract command name and aliases
                command_name = None
                aliases = []

                for line in frontmatter.split("\n"):
                    if line.startswith("command:"):
                        command_name = line.split(":", 1)[1].strip()
                    elif line.startswith("aliases:"):
                        aliases_str = line.split(":", 1)[1].strip()
                        if aliases_str.startswith("[") and aliases_str.endswith("]"):
                            aliases = [a.strip() for a in aliases_str[1:-1].split(",")]

                if command_name:
                    commands[command_name] = [command_name] + aliases

    return commands
```

### _detect_command_type()

```python
async def _detect_command_type(kb_agent_instance, message: str, experience: str) -> str:
    """
    Use LLM to detect which command type the user is trying to execute.
    """
    # Discover available commands from markdown files
    command_mappings = await _discover_available_commands(experience)
    available_commands = list(command_mappings.keys())

    # Build command mapping text for LLM
    mapping_lines = []
    for cmd, keywords in command_mappings.items():
        mapping_lines.append(f"- {cmd}: {', '.join(keywords)}")

    detection_prompt = f"""You are a command parser for a text adventure game.

User message: "{message}"
Available commands: {", ".join(available_commands)}

Command mappings:
{chr(10).join(mapping_lines)}

Respond with ONLY the command name (one word, lowercase).
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

    return response["response"].strip().lower()
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

## Related Documentation

- [Unified State Model](./unified-state-model.md) - Player views and state management
- [Experience Configuration](./experience-configuration.md) - Experience setup
- [KB Service API](./api/kb-endpoints.md) - API reference
