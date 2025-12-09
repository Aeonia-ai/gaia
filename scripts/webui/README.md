# Web UI Interactive Scripts

Interactive Playwright scripts for debugging, testing, and exploring the web UI.
These are designed for **development and debugging**, not CI/CD validation (use pytest for that).

## Purpose

- **Interactive exploration**: Navigate, click, fill forms without writing tests
- **Debugging**: Inspect elements, capture state, screenshot issues
- **Pattern capture**: Reusable flows (login, send message, etc.)
- **Claude Code integration**: Scripts Claude can run to help debug UI issues

## Directory Structure

```
scripts/webui/
├── patterns/          # Reusable UI patterns (login, navigate, etc.)
│   ├── login.py       # Login to web UI
│   ├── send_message.py # Send a chat message
│   ├── create_conversation.py
│   └── switch_conversation.py
├── debug/             # Debugging and inspection tools
│   ├── inspect_page.py    # Dump page structure and state
│   ├── check_htmx.py      # Verify HTMX setup
│   ├── trace_request.py   # Monitor network requests
│   └── check_layout.py    # Verify layout integrity
├── capture/           # Screenshot and recording utilities
│   ├── screenshot.py      # Take screenshots
│   ├── record_flow.py     # Record user interactions
│   └── compare_layouts.py # Visual diff between pages
└── utils/             # Shared utilities
    ├── browser.py         # Browser setup utilities
    ├── auth.py            # Auth helpers
    └── selectors.py       # Common selectors
```

## Usage Patterns

### Basic Usage
```bash
# Login and return session info
python scripts/webui/patterns/login.py --email test@example.com

# Send a message and capture response
python scripts/webui/patterns/send_message.py --message "Hello!"

# Inspect current page state
python scripts/webui/debug/inspect_page.py --url http://localhost:8080/chat

# Take screenshot of a page
python scripts/webui/capture/screenshot.py --url /login --output login.png
```

### Advanced Usage
```bash
# Chain patterns together
python scripts/webui/patterns/login.py && \
  python scripts/webui/patterns/send_message.py --message "Test" && \
  python scripts/webui/capture/screenshot.py

# Debug with headful browser
python scripts/webui/debug/inspect_page.py --headful --slow

# Trace all HTMX requests
python scripts/webui/debug/trace_request.py --filter htmx
```

### Claude Code Skill Integration

Eventually these will be accessible via a `/webui` skill:

```bash
/webui login test@example.com           # Run login pattern
/webui debug /chat                       # Inspect chat page
/webui screenshot /login                 # Capture screenshot
/webui trace "send message"              # Trace a user flow
```

## Common Options

Most scripts support these flags:

- `--headful` - Show browser window (default: headless)
- `--slow` - Slow down actions for debugging
- `--screenshot` - Auto-screenshot on completion
- `--trace` - Enable Playwright trace
- `--wait` - Keep browser open after completion
- `--env {local|dev|staging}` - Environment to test

## Environment Variables

```bash
# Web service URL (default: http://localhost:8080)
export WEB_URL="http://localhost:8080"

# Supabase credentials (for real auth)
export SUPABASE_URL="..."
export SUPABASE_ANON_KEY="..."
export SUPABASE_SERVICE_KEY="..."  # For test user creation

# Test user credentials
export TEST_EMAIL="test@example.com"
export TEST_PASSWORD="testpass123"
```

## Design Principles

1. **Composable**: Each script does one thing well, can be chained
2. **Observable**: Clear output, optional screenshots/traces
3. **Reusable**: Shared utilities for common operations
4. **Debuggable**: Headful mode, slow mode, trace mode
5. **Self-contained**: Works independently, no complex setup

## Difference from Pytest Tests

| Feature | pytest tests | webui scripts |
|---------|-------------|---------------|
| Purpose | Validate correctness | Explore and debug |
| Assertions | Required | Optional |
| Output | Pass/Fail | Detailed inspection |
| CI/CD | Yes | No |
| Interactive | No | Yes |
| Headful mode | Rare | Common |
| Traces/Screenshots | On failure | Always available |

## Examples

### Debug a Layout Issue
```bash
# 1. Login and navigate to problem area
python scripts/webui/patterns/login.py --email test@example.com

# 2. Inspect the page
python scripts/webui/debug/inspect_page.py --url /chat --check-layout

# 3. Capture screenshot for comparison
python scripts/webui/capture/screenshot.py --url /chat --output issue.png

# 4. Check HTMX setup
python scripts/webui/debug/check_htmx.py
```

### Capture a User Flow
```bash
# Record the entire "send message" flow
python scripts/webui/capture/record_flow.py \
  --flow "login -> send_message -> check_response" \
  --output flows/chat_flow.zip
```

### Test a Specific Pattern
```bash
# Test login with different users
for email in user1@test.com user2@test.com; do
  python scripts/webui/patterns/login.py --email $email --screenshot
done
```

## Creating New Scripts

### When to Create a New Script

Create a new script when you have a:
- **Pattern** - Reusable user action (login, navigate, submit form)
- **Debug tool** - Inspection or diagnostic capability
- **Capture tool** - Screenshot, recording, or state capture

### Script Template

Here's a complete template for a new pattern script:

```python
#!/usr/bin/env python3
"""
[Script Name] Pattern Script

[Brief description of what this script does]

Usage:
    python scripts/webui/patterns/my_script.py [args]
    python scripts/webui/patterns/my_script.py --headful
    python scripts/webui/patterns/my_script.py --wait
"""
import sys
import os
import asyncio
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args, handle_post_actions
from utils.auth import ensure_logged_in, get_test_credentials


async def my_action(page, arg1, arg2):
    """Perform the main action"""
    print(f"🎯 Performing action with {arg1} and {arg2}")

    # Your logic here
    # Use page.locator('[data-testid="..."]') for elements
    # Print progress with emoji indicators

    return True


async def main():
    parser = argparse.ArgumentParser(description="My script description")

    # Add script-specific arguments
    parser.add_argument(
        "--my-arg",
        required=True,
        help="Description of my argument"
    )

    # Add common arguments (--headful, --slow, --wait, etc.)
    parser = get_common_args(parser)
    args = parser.parse_args()

    print(f"🚀 Starting my action...")

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Optionally login first
        # credentials = get_test_credentials()
        # await ensure_logged_in(page, credentials["email"], credentials["password"], args.base_url)

        # Perform your action
        success = await my_action(page, args.my_arg, "value")

        if not success:
            print("❌ Action failed")
            sys.exit(1)

        # Handle post-actions (screenshot, wait)
        await handle_post_actions(session, args)

    print("✅ Action complete")


if __name__ == "__main__":
    asyncio.run(main())
```

### Example: Creating a "Switch Conversation" Pattern

Let's create a real example - a script to switch between conversations:

```python
#!/usr/bin/env python3
"""
Switch Conversation Pattern Script

Switch to a different conversation in the chat UI.

Usage:
    python scripts/webui/patterns/switch_conversation.py --conversation-id abc123
    python scripts/webui/patterns/switch_conversation.py --conversation-id abc123 --headful
"""
import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args, handle_post_actions
from utils.auth import ensure_logged_in, get_test_credentials


async def switch_conversation(page, conversation_id: str):
    """Switch to a specific conversation"""
    print(f"🔄 Switching to conversation: {conversation_id}")

    # Click conversation in sidebar
    conversation = page.locator(f'[data-conversation-id="{conversation_id}"]')
    await conversation.click()

    # Wait for messages to load
    await page.wait_for_selector('[data-testid="messages-container"]', timeout=5000)

    print("✅ Conversation switched")
    return True


async def main():
    parser = argparse.ArgumentParser(description="Switch to a conversation")
    parser.add_argument(
        "--conversation-id",
        required=True,
        help="Conversation ID to switch to"
    )
    parser.add_argument(
        "--email",
        help="User email (default: TEST_EMAIL env var)"
    )

    parser = get_common_args(parser)
    args = parser.parse_args()

    # Get credentials and login
    credentials = get_test_credentials()
    email = args.email or credentials["email"]
    password = credentials["password"]

    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Login
        await ensure_logged_in(page, email, password, args.base_url)

        # Switch conversation
        success = await switch_conversation(page, args.conversation_id)

        if not success:
            sys.exit(1)

        await handle_post_actions(session, args)

    print("✅ Switch conversation complete")


if __name__ == "__main__":
    asyncio.run(main())
```

Save this as `scripts/webui/patterns/switch_conversation.py` and make it executable:
```bash
chmod +x scripts/webui/patterns/switch_conversation.py
```

### Best Practices

When creating new scripts:

1. **Use shared utilities** - Import from `utils/browser.py` and `utils/auth.py`
2. **Support common flags** - Always call `get_common_args(parser)` and `handle_post_actions()`
3. **Use data-testid selectors** - `page.locator('[data-testid="element"]')` for reliability
4. **Print progress** - Use emoji indicators (🚀 🔄 ✅ ❌ 💬 📸) for visual feedback
5. **Handle errors gracefully** - Use try/except and print clear error messages
6. **Document at the top** - Include docstring with description and usage examples
7. **Return boolean** - Main action function should return True/False for success
8. **Add to skill** - Update `.claude/skills/webui.md` with new command mapping

### Testing Your New Script

```bash
# Test headless (fast)
python scripts/webui/patterns/my_script.py --my-arg value

# Test headful (see what's happening)
python scripts/webui/patterns/my_script.py --my-arg value --headful

# Test with debugging
python scripts/webui/patterns/my_script.py --my-arg value --headful --slow 500 --wait

# Test with screenshot
python scripts/webui/patterns/my_script.py --my-arg value --screenshot result.png
```

### Adding to Claude Code Skill

After creating a new script, update `.claude/skills/webui.md`:

1. **Add to Command Mapping table**:
   ```markdown
   | Switch conversation | `python scripts/webui/patterns/switch_conversation.py --conversation-id <id>` |
   ```

2. **Add to Available Commands section** with examples

3. **Add natural language trigger** if needed:
   ```yaml
   triggers:
     - "switch conversation"
     - "change conversation"
   ```

4. **Update Claude Code Integration section**:
   ```markdown
   - "switch to conversation X" → Run switch_conversation.py --conversation-id X
   ```

## Future: Claude Code Skill

```python
# .claude/skills/webui.md - Future skill definition

When user says "/webui <command>", execute scripts from scripts/webui/

Patterns:
- /webui login [email] - Login to web UI
- /webui send [message] - Send chat message
- /webui debug [url] - Inspect page
- /webui screenshot [url] - Capture screenshot

Always use --headful when user wants to see the browser.
```
