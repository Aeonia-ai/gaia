# Testing Scripts

Manual test scripts for end-to-end functionality testing.

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
