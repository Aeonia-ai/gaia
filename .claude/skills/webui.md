---
name: webui
version: 1.0.0
description: Interactive web UI testing and debugging with Playwright
dependencies:
  - python>=3.10
  - playwright
  - docker compose (for services)
triggers:
  - "webui"
  - "web ui"
  - "debug web"
  - "screenshot"
  - "test login"
  - "visual test"
  - "ui test"
  - "inspect page"
---

# Web UI Interactive Testing Skill

Execute interactive web UI scripts for debugging, testing, and exploration.

## Prerequisites

This skill requires:
- Python 3.10+ with Playwright installed (typically in a venv)
- Docker services running (`docker compose up`)
- Test credentials in `.env` file (TEST_EMAIL, TEST_PASSWORD)
- Web service accessible at `http://localhost:8080`

**Note**: We assume your Python environment is properly set up. Scripts will fail with clear error messages if something is missing.

**If you encounter errors**, they'll indicate what's missing:
- `ModuleNotFoundError: playwright` → Install: `pip install playwright && playwright install chromium`
- `Connection refused` or `Cannot connect` → Start services: `docker compose up`
- `Login failed` or `401 Unauthorized` → Check TEST_EMAIL/TEST_PASSWORD in `.env`
- `Element not found` → Page may have changed, use `--dump-structure` to inspect

## When to Use This Skill

Activate this skill when the user wants to:
- Login to the web UI and inspect state
- Send test messages and capture responses
- Debug layout or HTMX issues
- Take screenshots of pages
- Record user flows for debugging
- Inspect page structure and elements

## How This Skill Works

When you invoke a webui command:
1. **I run the script directly** (no pre-flight checks)
2. **Report any errors** with clear error messages
3. **Suggest fixes** based on what went wrong
4. **Capture output** (screenshots, traces, inspection data) when requested

## Command Mapping

Quick reference for translating user intent to commands:

| User Intent | Command |
|-------------|---------|
| Login to web UI | `python scripts/webui/patterns/login.py` |
| Send test message | `python scripts/webui/patterns/send_message.py --message "text"` |
| Debug chat page | `python scripts/webui/debug/inspect_page.py --url /chat --check-layout` |
| Screenshot page | `python scripts/webui/capture/screenshot.py --url /path --output file.png` |
| Inspect HTMX setup | `python scripts/webui/debug/inspect_page.py --url /chat --dump-htmx` |
| Record user flow | `python scripts/webui/capture/record_flow.py --flow <name>` |
| Show browser interaction | Add `--headful` flag to any command |
| Slow down for debugging | Add `--slow 500` flag to any command |

## Available Commands

### Patterns (User Actions)

**Login**
```bash
# Basic login
python scripts/webui/patterns/login.py --email test@example.com

# Login and show browser
python scripts/webui/patterns/login.py --email test@example.com --headful

# Login and screenshot
python scripts/webui/patterns/login.py --email test@example.com --screenshot after_login.png

# Login and keep browser open
python scripts/webui/patterns/login.py --email test@example.com --headful --wait
```

**Send Message**
```bash
# Send message (logs in automatically)
python scripts/webui/patterns/send_message.py --message "Hello!"

# Send message and capture response
python scripts/webui/patterns/send_message.py --message "Test" --capture-response

# Send message with visible browser
python scripts/webui/patterns/send_message.py --message "Debug" --headful --slow 500
```

### Debug (Inspection)

**Inspect Page**
```bash
# Inspect chat page
python scripts/webui/debug/inspect_page.py --url /chat

# Inspect with layout check
python scripts/webui/debug/inspect_page.py --url /chat --check-layout

# Inspect with login
python scripts/webui/debug/inspect_page.py --url /chat --login --headful

# Dump page structure to JSON
python scripts/webui/debug/inspect_page.py --url /chat --dump-structure chat_structure.json
```

### Capture (Screenshots & Recording)

**Screenshot**
```bash
# Screenshot a page
python scripts/webui/capture/screenshot.py --url /login --output login.png

# Screenshot with login
python scripts/webui/capture/screenshot.py --url /chat --login --output chat.png

# Full page screenshot
python scripts/webui/capture/screenshot.py --url /chat --full-page --output full_chat.png

# Screenshot specific element
python scripts/webui/capture/screenshot.py --url /chat --selector '[data-testid="messages-container"]'
```

**Record Flow**
```bash
# Record login flow
python scripts/webui/capture/record_flow.py --flow login

# Record chat session
python scripts/webui/capture/record_flow.py --flow chat_session --output my_trace.zip

# Record with screenshots
python scripts/webui/capture/record_flow.py --flow send_message --screenshots
```

## Common Options

All scripts support these flags:

- `--headful` - Show browser window (not headless)
- `--slow <ms>` - Slow down actions for debugging
- `--screenshot <file>` - Take screenshot after completion
- `--wait` - Keep browser open after script completes
- `--base-url <url>` - Override base URL (default: http://localhost:8080)

## Example Usage Scenarios

### Debugging a Layout Issue

```bash
# 1. Login and navigate to problem area
python scripts/webui/patterns/login.py --email test@example.com --headful

# 2. Inspect the page structure
python scripts/webui/debug/inspect_page.py --url /chat --check-layout

# 3. Take screenshot for comparison
python scripts/webui/capture/screenshot.py --url /chat --login --output issue.png

# 4. Dump structure to JSON for analysis
python scripts/webui/debug/inspect_page.py --url /chat --login --dump-structure chat_structure.json
```

### Testing HTMX Behavior

```bash
# Inspect HTMX setup
python scripts/webui/debug/inspect_page.py --url /chat --login --dump-htmx

# Send message and observe (headful + slow)
python scripts/webui/patterns/send_message.py --message "Test HTMX" --headful --slow 500 --wait
```

### Capturing User Flows

```bash
# Record complete chat session
python scripts/webui/capture/record_flow.py --flow chat_session --screenshots

# View the trace
playwright show-trace traces/flow_chat_session_*.zip
```

### Before/After Comparison

```bash
# Capture baseline
python scripts/webui/capture/screenshot.py --url /chat --login --output before.png

# Make code changes...

# Capture after changes
python scripts/webui/capture/screenshot.py --url /chat --login --output after.png

# Compare (using external tool or manual inspection)
```

## Claude Code Integration

When user says things like:
- "login to the web ui" → Run login.py
- "send a test message" → Run send_message.py
- "debug the chat page" → Run inspect_page.py with --check-layout
- "screenshot the login page" → Run screenshot.py
- "show me the chat page" → Run login.py + screenshot.py with --headful

Always use `--headful` when the user wants to "see" or "show" the browser.

## Tips for Claude

1. **Chain commands**: You can run multiple scripts sequentially
2. **Use --wait**: When user wants to interact, add --wait to keep browser open
3. **Screenshot everything**: When debugging, always offer to screenshot
4. **Headful for demos**: Use --headful when showing the user what's happening
5. **Slow down**: Use --slow 500 or higher when user wants to observe behavior

## Environment Requirements

- Docker services running: `docker compose up`
- Web service accessible at localhost:8080
- Playwright installed: `pip install playwright && playwright install`
- Test user credentials in .env: `TEST_EMAIL` and `TEST_PASSWORD`

## Common Error Patterns

When scripts fail, I'll help diagnose based on the error:

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `ModuleNotFoundError: playwright` | Playwright not installed | `pip install playwright && playwright install chromium` |
| `Connection refused` / `Cannot connect to localhost:8080` | Services not running | `docker compose up` |
| `Login failed` / `401 Unauthorized` | Bad credentials | Check TEST_EMAIL/TEST_PASSWORD in `.env` |
| `Element not found` / `Timeout waiting for selector` | Page structure changed | Run with `--dump-structure` to inspect page |
| `Web service not responding` | Service down or unhealthy | Check `docker compose ps` and `curl localhost:8080/health` |

## Related Documentation

- [Web UI Testing Strategy](../../docs/web-ui/web-testing-strategy-post-standardization.md)
- [HTMX Debugging Guide](../../docs/web-ui/htmx-fasthtml-debugging-guide.md)
- [Playwright EventSource Issue](../../docs/troubleshooting/playwright-eventsource-issue.md)
