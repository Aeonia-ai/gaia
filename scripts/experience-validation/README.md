# Testing Scripts

Manual test scripts for end-to-end functionality testing.

## 📚 Documentation

**[Testing Experience Changes Guide](../../docs/experiences/testing-experience-changes.md)**
- How to test markdown-based experience logic changes
- Test script structure and patterns
- State validation techniques
- Common issues and solutions

## Directory Structure

```
testing/
├── wylding-woods/          # Wylding Woods experience tests
│   ├── test_player_commands_wylding_woods.py  # Player gameplay tests
│   ├── test_reset_commands.py                 # Admin reset command tests
│   └── test_instance_management_complete.py   # Instance management tests
└── [other-experience]/     # Tests for other experiences
```

## Usage

### Wylding Woods Tests

**Reset & Collection Validation** (NEW - 2025-11-02):
```bash
# Comprehensive reset + collection test
python3 scripts/experience-validation/wylding-woods/validate_reset_and_collection.py

# Quick collection test only
python3 scripts/experience-validation/wylding-woods/quick_collection_test.py
```

**Player Commands** (17 tests):
```bash
cd /Users/jasonasbahr/Development/Aeonia/Server/gaia
python3 scripts/testing/wylding-woods/test_player_commands_wylding_woods.py
```

**Admin Reset Commands** (8 tests):
```bash
python3 scripts/testing/wylding-woods/test_reset_commands.py
```

**Instance Management** (5 tests):
```bash
python3 scripts/testing/wylding-woods/test_instance_management_complete.py
```

## User Identity in Tests

### Default User

All test scripts run as: **`jason@aeonia.ai`**

This means:
- Your inventory is stored under this user ID
- Your quest progress is tracked separately from other users
- Your NPC relationships (trust, conversation history) are personal
- All player state is isolated per user

### Player State Files

When you run tests, your state is stored in:

```
/kb/experiences/wylding-woods/players/jason@aeonia.ai/
├── progress.json      # Inventory, quest progress, location
└── npcs/
    └── louisa.json    # Relationship with Louisa (trust, conversations)
```

### Viewing Your State

**Check your inventory:**
```bash
cat /kb/experiences/wylding-woods/players/jason@aeonia.ai/progress.json
```

**Check your relationship with NPCs:**
```bash
cat /kb/experiences/wylding-woods/players/jason@aeonia.ai/npcs/louisa.json
```

**Sample output:**
```json
{
  "player_id": "jason@aeonia.ai",
  "trust_level": 52,
  "total_conversations": 1,
  "conversation_history": [
    {
      "timestamp": "2025-10-27T17:30:00Z",
      "player": "Hello Louisa",
      "npc": "Oh! You can see me? I wasn't expecting a human to notice."
    }
  ]
}
```

### Changing the User

**Option 1: Edit the test script directly**

In `test_player_commands_wylding_woods.py`, change line 37:
```python
"user_context": {
    "user_id": "your-user@example.com",  # Change this
    "waypoint": waypoint,
    "sublocation": sublocation,
    "role": "player"
}
```

**Option 2: Environment variable (requires script modification)**

Modify the script to accept `TEST_USER_ID`:
```python
import os
USER_ID = os.getenv("TEST_USER_ID", "jason@aeonia.ai")
```

Then run:
```bash
TEST_USER_ID="alice@example.com" python3 scripts/testing/wylding-woods/test_player_commands_wylding_woods.py
```

### Multi-User Testing

To test how different users experience the game:

```python
# Each user gets their own state
player_cmd("Hello Louisa", user_id="alice@example.com")  # Trust: 50
player_cmd("Hello Louisa", user_id="bob@example.com")    # Trust: 50

# Alice talks more
player_cmd("What's wrong?", user_id="alice@example.com")  # Trust: 52

# Bob's trust is still 50 - Louisa remembers each player separately
```

### Resetting Your Progress

Use admin commands to reset state:

```bash
# Reset just your progress (inventory, quests)
curl -X POST http://localhost:8001/game/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "command": "@reset player jason@aeonia.ai CONFIRM",
    "experience": "wylding-woods",
    "user_context": {"role": "admin"}
  }'

# Or use the reset test script
python3 scripts/testing/wylding-woods/test_reset_commands.py
```

## Test Categories

### Player Commands
- Exploration (look around, examine locations)
- Inventory management
- Item collection
- NPC dialogue
- Quest completion
- Symbol validation
- Error handling
- Natural language understanding

### Admin Commands
- World management (@list, @inspect, @create, @edit, @delete)
- Reset operations (@reset instance/player/experience)
- Statistics and search (@stats, @where, @find)

### Instance Management
- Location-based filtering
- Item collection mechanics
- Quest progress tracking
- State persistence
- Symbol validation

## Requirements

- Local GAIA services running (`docker compose up`)
- Valid API key in test scripts
- KB repository available at `/kb`

## Adding New Tests

1. Create experience-specific directory: `scripts/testing/{experience-name}/`
2. Add test scripts following naming convention: `test_{feature}_*.py`
3. Update this README with test descriptions
4. Ensure tests are self-contained and don't require manual setup

## Best Practices

- ✅ Test scripts should be runnable independently
- ✅ Include pre-setup (reset state) in test scripts
- ✅ Print clear output with section headers
- ✅ Use consistent formatting (see existing tests)
- ✅ Document what each test validates
- ❌ Don't hardcode production credentials
- ❌ Don't leave services in broken state after tests
