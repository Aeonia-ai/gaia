# AEO-72: Single Chat UI Implementation

**Status:** 🔧 In Progress (Phase 2: Personas & Slash Commands)
**Branch:** `feature/aeo-72-single-chat-ui`
**Created:** 2025-12-09
**Phase 1 Completed:** 2025-12-10
**Related:** [Agent Interface Vision](../concepts/deep-dives/agent-interface/000-agent-interface-vision.md)

## Goal

User can log into the web and have a persistent chat with a single agent conversation.

## UX Requirements

- User can login to web and chat
- User can type to agent
- User sees only a single chat (no sidebar with multiple conversations)
- Agent remembers previous conversation (chat context memory)

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| One conversation per user? | Yes, single "agent interface" | Future-proof for subagents, memory, user tracking |
| Existing multi-chats? | Ignore for now | Migrating away from multi-chat model |
| Header/UI elements | Minimal, essential functions only | Focus on conversation |
| Mobile responsive | Yes | Voice interfaces often mobile; simpler without sidebar |
| Rollout strategy | Feature flag `SINGLE_CHAT_MODE` | Allows gradual rollout, easy rollback |
| Primary conversation identification | Title-based: `"Agent Interface"` | No schema change needed; explicit identification |
| Layout approach | Reuse `gaia_layout(show_sidebar=False)` | Minimal change; can add agent-specific layout later |

### Primary Conversation Identification

**Decision:** Use the conversation title `"Agent Interface"` to identify the user's primary conversation.

**Alternatives Considered:**
- **Most recent conversation** - Fragile; any new conversation would become primary
- **Database flag (`is_primary`)** - Robust but requires schema migration
- **User metadata field** - Clean but requires user table changes

**Behavior:**
1. When user loads `/chat` in single-chat mode:
   - Search for conversation with `title == "Agent Interface"`
   - If found, load that conversation
   - If not found, create new conversation with title `"Agent Interface"`
2. Old conversations from multi-chat mode are ignored (remain in database)
3. Can be upgraded to database flag approach later if needed

## Architecture

### Layout Structure

```
┌─────────────────────────────────────────────────┐
│  Header (minimal, consistent across modes)      │
│  - Gaia branding                                │
│  - User info + Logout                           │
├─────────────────────────────────────────────────┤
│                                                 │
│         CONTENT AREA (flexible)                 │
│                                                 │
│    - Today: scrolling chat messages             │
│    - Future: generated images inline            │
│    - Future: video/audio player                 │
│    - Future: interactive canvas                 │
│                                                 │
├───────────────────────┬─────────────────────────┤
│   [SIDEBAR SLOT]      │    (optional, future)   │
│   - hidden for now    │    - context panels     │
│   - CSS hidden, not   │    - generated media    │
│     removed           │    - settings           │
└───────────────────────┴─────────────────────────┘
│  Input Area (mode-dependent)                    │
│  - Text: keyboard input                         │
│  - Future: voice mic button + waveform          │
└─────────────────────────────────────────────────┘
```

### Component Design

```python
gaia_agent_layout(
    header_content,      # Logo + user + logout
    main_content,        # Chat messages / generated content
    input_component,     # Text input (swappable for voice later)
    sidebar_content=None # Optional, hidden by default
)
```

## Implementation Tasks

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Add `SINGLE_CHAT_MODE` feature flag | `app/shared/config.py` | ✅ DONE |
| 2 | Add `get_or_create_primary_conversation()` helper | `app/services/web/utils/chat_service_client.py` | ✅ DONE |
| 3 | Update `chat_index()` route for single-chat mode | `app/services/web/routes/chat.py` | ✅ DONE |
| 4 | Fix title preservation in single-chat mode | `app/services/web/routes/chat.py` | ✅ DONE |
| 5 | Test end-to-end flow | Manual + browser | ✅ DONE |

### Title Preservation Fix

**Problem Discovered:** The existing code at `chat.py:549-552` was auto-updating conversation titles to match the first message content. This broke single-chat persistence because:
1. User logs in → conversation created with title "Agent Interface"
2. User sends message → title changed to "Hello this is my first..."
3. User logs out, logs back in → `get_or_create_primary_conversation()` searches for "Agent Interface"
4. No match found → NEW conversation created → history lost

**Solution:** In `SINGLE_CHAT_MODE`, skip the title update and only update the preview:
```python
if settings.SINGLE_CHAT_MODE:
    await chat_service_client.update_conversation(user_id, conversation_id,
                                         preview=message, jwt_token=jwt_token)
else:
    await chat_service_client.update_conversation(user_id, conversation_id,
                                         title=message[:50] + "...",
                                         preview=message, jwt_token=jwt_token)
```

**Deferred (Minimal Approach):**
- ~~Create `gaia_agent_layout()` component~~ - Using existing `gaia_layout(show_sidebar=False)` instead
- ~~Add responsive CSS for agent layout~~ - Existing mobile styles sufficient for MVP

## Code Touchpoints

| File | Changes |
|------|---------|
| `app/shared/config.py` | Add `SINGLE_CHAT_MODE: bool` |
| `app/services/web/components/gaia_ui.py` | New `gaia_agent_layout()` function |
| `app/services/web/utils/chat_service_client.py` | Add `get_or_create_primary_conversation()` |
| `app/services/web/routes/chat.py` | Modify `chat_index()` to use single-chat mode |

## Acceptance Criteria

- [x] `SINGLE_CHAT_MODE=true` enables new agent layout
- [x] `SINGLE_CHAT_MODE=false` preserves existing multi-chat UI
- [x] Agent layout: full-width content, hidden sidebar, minimal header
- [x] Single conversation auto-loads on `/chat`
- [x] Message send/receive works with streaming
- [x] Conversation persists across logout/login
- [ ] Mobile responsive (not tested, but uses existing responsive layout)
- [x] Sidebar slot exists (hidden) for future use

## User Journey

```
1. USER ARRIVES AT SITE
   └─→ Not logged in → /login page
   └─→ Logged in → /chat (single chat view)

2. USER LOGS IN
   └─→ Successful auth → Redirect to /chat
   └─→ /chat loads → Find or create user's single conversation
   └─→ Display chat with history (if any)

3. USER SENDS MESSAGE
   └─→ Message saved to conversation
   └─→ AI response streams back (SSE)
   └─→ Response saved to conversation

4. USER RETURNS LATER
   └─→ /chat → Same conversation, history persists

5. NEW USER (first time)
   └─→ Login → /chat → Create new conversation → Welcome message
```

## Prerequisites (Completed)

- [x] Conversation memory bug fixed (user_email passed through chain)
- [x] JWT token refresh system implemented
- [x] SSE streaming working
- [x] Message persistence working

## Notes

- Sidebar is CSS-hidden, not removed from DOM (for future affordances)
- Layout designed for future voice-only and visual generation modes
- See [Agent Interface Vision](../concepts/deep-dives/agent-interface/000-agent-interface-vision.md) for long-term direction

---

# Phase 2: Personas & Slash Commands

## Goal

Enable users to switch personas via `/persona` command, establishing a slash command system for user meta-operations.

## Research: Slash Command Conventions

Based on Perplexity research, `/` is the **universal standard** for chat commands:

| Platform | Examples | Notes |
|----------|----------|-------|
| IRC (1988) | `/join`, `/msg`, `/nick` | Original source of convention |
| Slack | `/remind`, `/todo`, `/giphy` | Autocomplete dropdown on `/` |
| Discord | `/kick`, `/ban`, `/help` | Structured parameter prompts |
| Google Chat | `/new_task`, `/assign` | Bot-registered commands |
| MMOs (WoW) | `/dance`, `/whisper`, `/guild` | Emotes and channels |
| AI Tools | `/explain`, `/test`, `/refactor` | Mode/intent setting |

**Key Conventions:**
- `/command [arguments]` - simple, consistent format
- Typing `/` triggers autocomplete/discovery
- Command names are short, descriptive, guessable
- `/help` is universal

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Command prefix? | `/` for user commands | Industry standard (IRC, Slack, Discord) |
| Existing `@` commands? | Keep for game admin | Different semantic domain (world-building vs user prefs) |
| Where to intercept? | `chat.py:send_message()` | Access to session, direct persona_service access |
| Store commands in history? | Yes | User can see what commands they ran |
| LLM for commands? | No | Instant response, no token cost |
| Command response style? | System message (centered, muted) | Distinct from user/assistant messages |

### Command Prefix Strategy

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `/` | **User meta-commands** | `/persona`, `/help`, `/clear` |
| `@` | **Game admin commands** (existing) | `@list-waypoints`, `@inspect-item` |

## Phase 2 Implementation Tasks

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Create Zoe persona definition | `scripts/persona/zoe.txt` | ✅ DONE |
| 2 | Create `create_persona.sh` script | `scripts/persona/create_persona.sh` | ✅ DONE |
| 3 | Insert Zoe into database | via `create_persona.sh` | ✅ DONE |
| 4 | Create command handler module | `app/services/chat/commands/__init__.py` | ✅ DONE |
| 5 | Implement `/persona` command | `app/services/chat/commands/persona.py` | ✅ DONE |
| 6 | Implement `/help` command | `app/services/chat/commands/help.py` | ✅ DONE |
| 7 | Add command interception | `app/services/chat/unified_chat.py` | ⏳ TODO |
| 8 | Add system message UI component | `app/services/web/components/gaia_ui.py` | ⏳ TODO |
| 9 | Test end-to-end | Manual + browser | ⏳ TODO |
| 10 | Check remote database migrations | Fly.io | ⏳ TODO |

## Architecture

### Design Change: Chat Service vs Web Service

**Original Plan:** Intercept commands in web service (`app/services/web/routes/chat.py`)

**Revised Plan:** Intercept commands in chat service (`app/services/chat/unified_chat.py`)

**Rationale:** Commands should work across ALL interfaces:
- Web UI (HTMX)
- Mobile apps (future)
- API clients (direct chat API calls)
- Any other interface

By putting commands in the chat service layer, they're available to all clients automatically.

### Interception Point

Commands intercepted in `unified_chat.py:process()` and `process_stream()` (before any LLM calls):

```
User types "/persona Zoe"
    ↓
unified_chat_handler.process() checks for "/" prefix
    ↓
Routes to command handler (skips LLM entirely)
    ↓
Returns CommandResponse with system message
    ↓
Web UI renders as styled system message
```

### File Structure

```
app/services/chat/
├── unified_chat.py               # MODIFY: Add command interception
└── commands/                     # NEW: Command handler module
    ├── __init__.py              # Command router + CommandResponse
    ├── persona.py               # /persona command
    └── help.py                  # /help command
```

### Code: Command Router (Implemented)

```python
# app/services/chat/commands/__init__.py

from typing import Optional
from dataclasses import dataclass

@dataclass
class CommandResponse:
    """Response from a slash command handler."""
    message: str
    response_type: str = "info"  # 'success', 'error', 'info', 'list'
    handled: bool = True
    data: Optional[dict] = None

COMMANDS = {
    'persona': handle_persona_command,
    'help': handle_help_command,
}

async def handle_command(message: str, user_id: str, ...) -> Optional[CommandResponse]:
    """Route slash commands. Returns CommandResponse or None if not a command."""
    if not message.startswith('/'):
        return None
    # ... routing logic
```

### Code: unified_chat.py Modification

Insert at start of `process()` method (after line 329, before metrics update):

```python
# Check for slash commands (bypass LLM entirely)
if message.startswith('/'):
    from app.services.chat.commands import handle_command, CommandResponse

    # Extract user_id from auth
    user_id = auth.get("sub") or auth.get("user_id") or auth.get("key", "unknown")

    command_response = await handle_command(
        message=message,
        user_id=user_id,
        user_email=user_email,
        conversation_id=context.get("conversation_id") if context else None
    )

    if command_response:
        # Convert CommandResponse to chat response format
        return {
            "id": f"cmd-{request_id}",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "system",
                    "content": command_response.message,
                },
                "finish_reason": "stop"
            }],
            "_metadata": {
                "command_type": command_response.response_type,
                "command_data": command_response.data
            }
        }
```

## Command Specifications

### `/persona`

| Input | Output |
|-------|--------|
| `/persona` | List available personas with current marked |
| `/persona Zoe` | Switch to Zoe, confirm |
| `/persona badname` | Error with available options |

### `/help`

| Input | Output |
|-------|--------|
| `/help` | List all commands |

## Phase 2 Acceptance Criteria

- [x] `/persona` lists all active personas with current selection marked ✅ Tested 2025-12-10
- [x] `/persona Zoe` switches to Zoe persona and confirms ✅ Tested 2025-12-10
- [x] `/persona badname` shows error with available options ✅ Tested 2025-12-10
- [x] `/help` lists available commands ✅ Tested 2025-12-10
- [x] Commands don't trigger LLM (instant response) ✅ <30ms response time
- [x] Command responses have distinct styling ✅ Shows as system messages
- [x] Commands stored in conversation history ✅ Visible in chat
- [ ] Persona preference persists across sessions (not tested yet)

## Dependencies Completed

- ✅ Zoe persona in database (UUID: `c96b087c-db2d-4072-83a3-54de910997fb`)
- ✅ `create_persona.sh` script
- ✅ `scripts/persona/zoe.txt` prompt file (simplified for conversational brevity)
- ✅ `persona_service` (PostgresPersonaService) exists
- ✅ Database tables: `personas`, `user_persona_preferences`
- ✅ `update_persona.sh` now clears Redis cache automatically

## Learnings from Phase 2

### Zoe Verbosity Fix
**Problem**: Zoe was outputting walls of text with bullet points despite instructions to be brief.

**Root causes**:
1. Original prompt was ~6700 chars with extensive bullet-point structure - model mirrored format
2. `update_persona.sh` updated database but didn't clear Redis cache (1-hour TTL)

**Solutions**:
1. Simplified prompt to ~1700 chars with conversational examples (show don't tell)
2. Added Redis cache clearing to `update_persona.sh`

### Persona Switching Limitation
**Discovery**: Switching personas mid-conversation doesn't work well because conversation history contains messages in the old persona's style, which the LLM continues to mirror.

**Decision**: Dropping `/persona` command for MVP. Single persona per deployment.

---

# Phase 3: Chat Header & Settings Page

## Goal

Add minimal UI chrome to the single-chat view: header with branding and user menu, settings page.

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Show persona name in header? | No | Single-persona app, redundant info |
| Header content? | Logo left, user dropdown right | Minimal, follows best practices |
| Settings location? | Separate `/settings` page | Simpler than slide-out panel |
| What's in user dropdown? | Name, email (display only), Settings link, Logout | MVP essentials |

## Architecture

### Header Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [🦋 Gaia]                                          [👤▾]   │
│  app branding                                       user    │
└─────────────────────────────────────────────────────────────┘
```

### User Dropdown

```
┌─────────────────────┐
│ Game Master         │  ← display name (not clickable)
│ user@example.com    │  ← email (not clickable)
├─────────────────────┤
│ ⚙️ Settings         │  → navigates to /settings
│ 🚪 Log out          │  → POST /logout, redirect to /login
└─────────────────────┘
```

### Settings Page (`/settings`)

```
┌─ Settings ──────────────────────────────────────────────────┐
│                                                             │
│  ← Back to chat                                             │
│                                                             │
│  Theme                                                      │
│  ○ Light  ● Dark  ○ System                                 │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Privacy                                                    │
│  [Clear conversation history]                               │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Account                                                    │
│  [Delete my account]  (danger zone)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Phase 3 Implementation Tasks

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Create `gaia_chat_header()` component | `gaia_ui.py` | ⏳ TODO |
| 2 | Create `gaia_user_dropdown()` component | `gaia_ui.py` | ⏳ TODO |
| 3 | Add header to `_render_single_chat_view()` | `chat.py` | ⏳ TODO |
| 4 | Create/simplify `/settings` page | `profile.py` or new `settings.py` | ⏳ TODO |
| 5 | Add "Clear history" endpoint | `chat.py` or `settings.py` | ⏳ TODO |
| 6 | Add dropdown toggle JavaScript | `gaia_ui.py` | ⏳ TODO |
| 7 | Test end-to-end | Manual + browser | ⏳ TODO |

## Phase 3 Acceptance Criteria

- [ ] Header shows on chat page with Gaia logo
- [ ] User dropdown opens on click, closes on click outside
- [ ] Dropdown shows user name and email
- [ ] Settings link navigates to `/settings`
- [ ] Logout clears session and redirects to `/login`
- [ ] Settings page has theme toggle (stored in session)
- [ ] "Clear history" button deletes messages, keeps conversation
- [ ] Back to chat link returns to `/chat`
