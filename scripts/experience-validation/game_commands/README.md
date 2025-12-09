# Game Command Test Scripts

Test scripts for validating game command functionality during and after markdown migration.

## Purpose

These scripts test the game command system that powers text-based gameplay in experiences like:
- `wylding-woods` - AR walking tour with collectibles
- `west-of-house` - Classic Zork-style text adventure
- `rock-paper-scissors` - Simple rule-based game

## Available Tests

### test_player_cmd.py
**Tests**: Natural language player commands

```bash
python3 scripts/testing/game_commands/test_player_cmd.py
```

**What it tests**:
- "look around" - Observation commands
- "collect dream bottle" - Item pickup
- "return bottle to fairy house" - Quest completion
- "talk to Louisa" - NPC conversations
- "check inventory" - Inventory display

**Uses**: `/game/command` endpoint (currently hardcoded, will be markdown-driven)

### test_markdown_agent.py
**Tests**: Markdown-based knowledge interpretation

```bash
python3 scripts/testing/game_commands/test_markdown_agent.py
```

**What it tests**:
- `/agent/interpret` - LLM interprets markdown rules
- `/agent/workflow` - Execute markdown workflows
- `/agent/validate` - Validate actions against markdown rules
- Comparison with `/game/command` to show architectural differences

**Uses**: `/agent/*` endpoints (loads markdown from KB)

### test_admin_cmd.py
**Tests**: Admin commands for world management

```bash
python3 scripts/testing/game_commands/test_admin_cmd.py
```

**What it tests**:
- `@list waypoints` - List game locations
- `@list items at waypoint_28a` - List items at location
- `@inspect item dream_bottle_1` - Examine item details
- `@stats` - World statistics

**Uses**: Admin command system (no markdown, stays code-driven)

## Context

### Pre-Migration (Current)
- `/game/command` uses **hardcoded Python logic**
- Narratives are **hardcoded strings**
- Fast (~1-2s) but inflexible

### Post-Migration (Target)
- `/game/command` uses **markdown-driven content**
- Narratives **generated from templates**
- Slower (~2-4s) but flexible

### Comparison
- `/agent/interpret` already uses markdown (rock-paper-scissors)
- These tests help validate migration approach

## Running All Tests

```bash
# Run all game command tests
for test in scripts/testing/game_commands/*.py; do
    echo "Running $test..."
    python3 "$test"
    echo "---"
done
```

## Expected Results

### Successful Test Output
```
=== Testing Player Command: 'look around' ===
Response time: 1.23s
Narrative: You see:
- A dream bottle: A small glass bottle filled with swirling mist
✅ SUCCESS
```

### Failed Test Output
```
=== Testing Player Command: 'look around' ===
❌ ERROR: 500
{
  "success": false,
  "error": {"code": "execution_failed", "message": "..."}
}
```

## Troubleshooting

### Connection Refused
```
ConnectionError: Cannot connect to http://localhost:8001
```

**Solution**: Start services
```bash
docker compose up
```

### Authentication Failed
```
401 Unauthorized
```

**Solution**: Check API key in `.env`
```bash
grep GAIA_API_KEY .env
```

### Command Not Found
```
"error": {"code": "unknown_action"}
```

**Solution**: Check experience exists and command is valid
```bash
# List available experiences
ls ../../Vaults/gaia-knowledge-base/experiences/
```

## Related Documentation

- [Migration Plan](../../../docs/features/dynamic-experiences/phase-1-mvp/028-game-command-markdown-migration.md)
- [Architecture Comparison](../../../docs/features/dynamic-experiences/phase-1-mvp/029-game-command-architecture-comparison.md)
- [Archival Report](../../../docs/features/dynamic-experiences/phase-1-mvp/030-game-command-archival-report.md)
- [Game Command Developer Guide](../../../docs/features/dynamic-experiences/phase-1-mvp/009-game-command-developer-guide.md)

## Contributing

When adding new tests:
1. Follow the naming convention: `test_<feature>.py`
2. Add description to this README
3. Include example usage
4. Document expected output
