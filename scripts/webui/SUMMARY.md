# Web UI Interactive Scripts - Summary

**Created**: October 27, 2025
**Purpose**: Interactive Playwright scripts for web UI debugging and exploration
**Claude Code Skill**: `.claude/skills/webui.md`

## What We Built

A complete interactive testing framework with:

### 1. Directory Structure
```
scripts/webui/
├── patterns/          # Reusable UI patterns
│   ├── login.py
│   └── send_message.py
├── debug/             # Inspection tools
│   └── inspect_page.py
├── capture/           # Screenshots & recording
│   ├── screenshot.py
│   └── record_flow.py
├── utils/             # Shared utilities
│   ├── browser.py
│   └── auth.py
├── README.md          # Full documentation
├── QUICKSTART.md      # 5-minute start guide
└── SUMMARY.md         # This file
```

### 2. Core Scripts

**Patterns (User Actions)**
- `login.py` - Login to web UI, capture session state
- `send_message.py` - Send chat messages, capture AI responses

**Debug (Inspection)**
- `inspect_page.py` - Inspect page structure, HTMX setup, layout issues

**Capture (Screenshots & Recording)**
- `screenshot.py` - Take screenshots with optional login/navigation
- `record_flow.py` - Record full user flows with Playwright traces

**Utilities (Shared)**
- `browser.py` - Browser session management with common patterns
- `auth.py` - Authentication helpers for login/session management

### 3. Claude Code Skill

**File**: `.claude/skills/webui.md`
**Version**: 1.0.0
**Status**: ✅ Follows Claude Code best practices

**Features**:
- ✅ Proper YAML frontmatter (name, version, description, dependencies, triggers)
- ✅ Command mapping table for quick intent → command translation
- ✅ Error pattern matching for intelligent troubleshooting
- ✅ "Fail fast" approach - assumes setup is complete, reports issues clearly
- ✅ Multiple trigger keywords for flexible activation

**Triggers**:
- "webui"
- "web ui"
- "debug web"
- "screenshot"
- "test login"
- "visual test"
- "ui test"
- "inspect page"

## Key Design Decisions

### 1. Separation from Pytest
- **Pytest**: Validates correctness, CI/CD integration
- **These scripts**: Interactive exploration and debugging
- **Why**: Developers need interactive tools, not just validation

### 2. Composable Scripts
- Each script does one thing well
- Can be chained together for complex workflows
- All support common flags (--headful, --slow, --wait, --screenshot)

### 3. Shared Utilities
- `BrowserSession` class handles browser lifecycle
- `auth.py` provides reusable login patterns
- Common argument parsing with `get_common_args()`

### 4. Fail Fast Philosophy
- Don't pre-check dependencies
- Run commands and report clear errors
- Trust the environment, verify through failure

### 5. Claude Code Integration
- Natural language triggers ("show me the login page")
- I translate intent to proper commands with flags
- Error messages guide troubleshooting

## Usage Examples

### As Scripts (Direct)
```bash
# Login and inspect
python scripts/webui/patterns/login.py --headful --wait

# Send message and capture response
python scripts/webui/patterns/send_message.py --message "Test" --capture-response

# Debug layout issues
python scripts/webui/debug/inspect_page.py --url /chat --check-layout --login

# Screenshot
python scripts/webui/capture/screenshot.py --url /chat --login --output debug.png

# Record flow
python scripts/webui/capture/record_flow.py --flow chat_session --screenshots
```

### Via Claude Code Skill
```
User: "webui login"
Claude: *runs login.py with appropriate flags*

User: "debug the chat page"
Claude: *runs inspect_page.py --url /chat --check-layout*

User: "show me what happens when I send a message"
Claude: *runs send_message.py --headful --slow 500 --wait*
```

## Comparison with Pytest

| Feature | Pytest Tests | WebUI Scripts |
|---------|--------------|---------------|
| **Purpose** | Validate correctness | Explore & debug |
| **Assertions** | Required | Optional |
| **Output** | Pass/Fail | Detailed inspection |
| **CI/CD** | Yes | No |
| **Interactive** | No | Yes |
| **Headful Mode** | Rare | Common |
| **When to Use** | Automated testing | Manual debugging |

## Next Steps

### Immediate
1. ✅ Test scripts manually to verify they work
2. ⬜ Try skill activation: "webui login"
3. ⬜ Add more patterns as needed (create_conversation, switch_conversation, etc.)

### Future Enhancements
- Add pattern for conversation management
- Add pattern for navigation flows
- Visual diff tool for screenshot comparison
- Integration with existing `capture-ui-snapshots.py` scripts
- Add more predefined flows to `record_flow.py`

## Benefits

### For Development
- **Fast debugging**: Run one command to inspect page state
- **Visual inspection**: `--headful` shows exactly what's happening
- **Reproducible flows**: Record and replay user interactions
- **Screenshot evidence**: Capture UI state for bug reports

### For Claude Code
- **Natural interaction**: "show me the chat page" → runs appropriate script
- **Intelligent chaining**: Login → Send message → Screenshot automatically
- **Error diagnosis**: Map error messages to solutions
- **Contextual help**: Suggest relevant flags based on user intent

### For the Team
- **Reusable patterns**: Login, send message, etc. become building blocks
- **Clear documentation**: README and QUICKSTART for onboarding
- **Consistent interface**: All scripts support common flags
- **No test pollution**: Debug without modifying test files

## Files Created

```
scripts/webui/README.md                    # Full documentation
scripts/webui/QUICKSTART.md                # 5-minute guide
scripts/webui/SUMMARY.md                   # This file
scripts/webui/patterns/login.py            # Login pattern
scripts/webui/patterns/send_message.py     # Send message pattern
scripts/webui/debug/inspect_page.py        # Page inspection
scripts/webui/capture/screenshot.py        # Screenshot capture
scripts/webui/capture/record_flow.py       # Flow recording
scripts/webui/utils/browser.py             # Browser utilities
scripts/webui/utils/auth.py                # Auth helpers
.claude/skills/webui.md                    # Claude Code skill
```

## Best Practices Followed

Based on Claude Code skill guidelines and Perplexity research:

1. ✅ **Specific, repeatable task** - Focused on web UI testing/debugging
2. ✅ **Proper YAML frontmatter** - name, version, description, dependencies, triggers
3. ✅ **Clear instructions** - Command mapping table and examples
4. ✅ **Executable scripts** - Python scripts with consistent interfaces
5. ✅ **Trigger criteria** - Clear "When to Use This Skill" section
6. ✅ **Context-agnostic** - Works anywhere via flags
7. ✅ **Error guidance** - Common Error Patterns table
8. ✅ **Fail fast philosophy** - Assume setup, report issues clearly

## Key Insight

> **The difference between pytest and these scripts**: pytest tells you IF something is broken. These scripts help you understand WHY and let you explore the UI interactively.

This framework makes Claude Code your debugging assistant, not just a test runner.
