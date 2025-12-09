# Web UI Scripts - Quick Start

Get started with interactive web UI testing in 5 minutes.

## Setup

### 1. Install Playwright
```bash
pip install playwright
playwright install chromium
```

### 2. Set Environment Variables
```bash
# In your .env file
export TEST_EMAIL="test@example.com"
export TEST_PASSWORD="testpass123"
export WEB_URL="http://localhost:8080"  # Optional, defaults to this
```

### 3. Start Services
```bash
docker compose up
```

### 4. Verify Web Service
```bash
curl http://localhost:8080/health
# Should return: {"status":"healthy"}
```

## Your First Scripts

### Test Login
```bash
# Headless (fast)
python scripts/webui/patterns/login.py

# See the browser (slower, shows you what's happening)
python scripts/webui/patterns/login.py --headful
```

**Expected output:**
```
🔐 Logging in as: test@example.com
✅ Login successful: test@example.com

📍 Current URL: http://localhost:8080/chat
📊 Session cookies: 2 cookies
✅ Login pattern complete
```

### Send a Message
```bash
# Send message and capture AI response
python scripts/webui/patterns/send_message.py --message "Hello!" --capture-response
```

**Expected output:**
```
💬 Sending message: Hello!
⏳ Waiting for response...
✅ Response received

--- AI Response ---
Hello! How can I help you today?
--- End Response ---

✅ Send message pattern complete
```

### Debug a Page
```bash
# Inspect the chat page
python scripts/webui/debug/inspect_page.py --url /chat --login --check-layout
```

**Expected output:**
```
🔍 Inspecting page: /chat
✅ Page loaded: http://localhost:8080/chat

🔍 HTMX Setup Check:
  ✅ HTMX loaded: True
  📦 HTMX version: 1.9.10
  📊 HTMX elements: 5

📋 Form Inspection:
  Form 1:
    Method: post
    HTMX Post: /chat/send
    HTMX Target: #messages-container
    Inputs: 1

🎨 Layout Inspection:
  ✅ No problematic flex patterns found
  📊 Loading indicators: 1
  ✅ Error messages visible: 0

✅ Inspection complete
```

### Take a Screenshot
```bash
# Screenshot the login page
python scripts/webui/capture/screenshot.py --url /login --output login.png

# Screenshot chat page (requires login)
python scripts/webui/capture/screenshot.py --url /chat --login --output chat.png
```

## Common Use Cases

### "Show me what the login page looks like"
```bash
python scripts/webui/capture/screenshot.py --url /login --output login.png
open login.png  # macOS
```

### "Debug why messages aren't sending"
```bash
# Watch the flow in slow motion
python scripts/webui/patterns/send_message.py \
  --message "Test" \
  --headful \
  --slow 500 \
  --wait
```

### "Check if HTMX is configured correctly"
```bash
python scripts/webui/debug/inspect_page.py --url /chat --login --dump-htmx
```

### "Record a full chat session for debugging"
```bash
python scripts/webui/capture/record_flow.py --flow chat_session

# View the recording
playwright show-trace traces/flow_chat_session_*.zip
```

## Debugging Tips

### Script Fails with "Element not found"

**Headful mode** shows you what's actually on the page:
```bash
python scripts/webui/patterns/login.py --headful --wait
```

**Dump structure** to see actual element IDs:
```bash
python scripts/webui/debug/inspect_page.py \
  --url /login \
  --dump-structure login_structure.json

cat login_structure.json | jq '.children'
```

### Script Times Out

**Slow mode** gives elements time to load:
```bash
python scripts/webui/patterns/send_message.py --message "Test" --slow 1000
```

### Want to See Network Requests

**Record a trace** captures everything:
```bash
python scripts/webui/capture/record_flow.py --flow login --screenshots

# View with Playwright trace viewer
playwright show-trace traces/flow_login_*.zip
```

## Next Steps

1. **Read the full README**: `scripts/webui/README.md`
2. **Explore available scripts**: `ls scripts/webui/{patterns,debug,capture}/`
3. **Use the Claude Code skill**: See `.claude/skills/webui.md`
4. **Create custom flows**: Modify `capture/record_flow.py` for your needs

## Cheat Sheet

```bash
# Login
python scripts/webui/patterns/login.py [--headful] [--wait]

# Send message
python scripts/webui/patterns/send_message.py --message "text" [--capture-response]

# Inspect page
python scripts/webui/debug/inspect_page.py --url /path [--check-layout]

# Screenshot
python scripts/webui/capture/screenshot.py --url /path [--login] --output file.png

# Record flow
python scripts/webui/capture/record_flow.py --flow <flow_name>
```

## Common Flags

- `--headful` - Show browser window
- `--slow <ms>` - Slow down actions
- `--wait` - Keep browser open
- `--screenshot <file>` - Auto-screenshot
- `--login` - Login before action

## Need Help?

- Check the main README: `scripts/webui/README.md`
- View script help: `python scripts/webui/patterns/login.py --help`
- Read related docs: `docs/web-ui/`
- Ask Claude: The webui skill understands these scripts!
