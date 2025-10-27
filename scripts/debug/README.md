# Debug Scripts

Scratch scripts and debugging tools for development and troubleshooting.

## Purpose

This directory contains:
- Quick debugging scripts
- API exploration tools
- Response inspection utilities
- Experimental test code
- One-off investigation scripts

**These are NOT production tests** - they're temporary tools for debugging specific issues.

## Current Scripts

### API Inspection
- `show_api_io.py` - Display API request/response details
- `show_chat_io.py` - Show chat endpoint I/O

### Chat Testing
- `test_chat_realistic.py` - Realistic chat scenarios
- `test_chat_simple.py` - Simple chat tests
- `test_game_chat.py` - Game chat endpoint tests

### Instance Testing
- `test_instance_api.py` - Instance API tests
- `test_instance_detailed.py` - Detailed instance testing
- `test_instance_management.py` - Instance management tests

### Utility
- `test_location_extraction.py` - Location parsing tests

## Usage

These scripts are meant to be run directly for debugging:

```bash
cd /Users/jasonasbahr/Development/Aeonia/Server/gaia
python3 scripts/debug/show_chat_io.py
```

## Guidelines

### When to add scripts here:
- ✅ Quick debugging tools
- ✅ One-off investigation scripts
- ✅ API exploration utilities
- ✅ Temporary test code

### When NOT to add scripts here:
- ❌ Production test suites (use `scripts/testing/`)
- ❌ Deployment scripts (use main `scripts/`)
- ❌ Monitoring tools (use `scripts/monitoring/`)

## Maintenance

Scripts in this directory can be:
- Modified freely without review
- Deleted when no longer needed
- Moved to `scripts/testing/` if they become permanent tests

**Note**: These scripts are NOT automatically run in CI/CD.
