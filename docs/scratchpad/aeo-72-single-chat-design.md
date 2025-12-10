# AEO-72: Single Chat UI Implementation

**Status:** ✅ Complete
**Branch:** `feature/aeo-72-single-chat-ui`
**Created:** 2025-12-09
**Completed:** 2025-12-10
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
