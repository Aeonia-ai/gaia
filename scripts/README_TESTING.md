# 🧪 Gaia Platform Test Scripts Guide

## 🤖 For Claude Code Users (IMPORTANT!)

When running tests in Claude Code, **ALWAYS use our wrapper scripts** to avoid 2-minute timeouts:

### Primary Test Commands:
```bash
# Full test suite (runs in background, no timeout)
./scripts/pytest-for-claude.sh

# Specific test categories (quick, no timeout issues)
./scripts/test-automated.py health         # Quick health check
./scripts/test-automated.py integration    # Integration tests
./scripts/test-automated.py e2e           # Browser tests
./scripts/test-automated.py unit          # Unit tests
```

### ❌ NEVER Use These (Will Timeout):
```bash
pytest                                    # Will timeout!
docker compose run test pytest            # Will timeout!
docker compose exec test pytest           # Will timeout!
python -m pytest                         # Will timeout!
```

## 📚 Test Runner Scripts

### Main Test Runners:
1. **`pytest-for-claude.sh`** - Async test runner for Claude Code (avoids timeouts)
2. **`test-automated.py`** - Docker-based test runner with categories
3. **`test.sh`** - Smart API testing for local/remote environments
4. **`test-host-only.sh`** - Tests requiring host Docker access

### Test Categories (via test-automated.py):
- `all` - Run everything
- `health` - Quick system health checks
- `integration` - Service integration tests
- `e2e` / `browser` - Browser-based UI tests
- `unit` - Unit tests with mocks
- `chat`, `kb`, `auth` - Feature-specific tests
- `v03` - New v0.3 API tests
- `comprehensive` - Full integration suite

## 🏃 Running Tests

### Quick Start:
```bash
# Check system health
./scripts/test-automated.py health

# Run all tests (background, no timeout)
./scripts/pytest-for-claude.sh

# Run specific category
./scripts/test-automated.py integration
```

### Monitor Background Tests:
```bash
# Check test progress
./scripts/check-test-progress.sh

# View test logs
tail -f test-run-*.log
```

## 🎯 Best Practices

1. **Use wrapper scripts** - Don't run pytest directly in Claude Code
2. **Start with health checks** - Verify services are running
3. **Run categories separately** - Easier to debug failures
4. **Check logs for details** - Background tests write to log files

## 🔧 Troubleshooting

### Tests timing out?
Use `./scripts/pytest-for-claude.sh` instead of direct pytest commands.

### Need to run specific tests?
Use test-automated.py with specific categories or test paths.

### Services not healthy?
Run `./scripts/test-automated.py health` first to diagnose.

## 📋 Script Inventory

See `TEST_LAUNCHER_INVENTORY.md` for complete list of all test-related scripts.