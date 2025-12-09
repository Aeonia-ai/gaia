# AEO-72: Single Chat UI Implementation

**Status:** In Progress
**Branch:** `feature/aeo-72-single-chat-ui`
**Created:** 2025-12-09
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
| 1 | Add `SINGLE_CHAT_MODE` feature flag | `app/shared/config.py` | TODO |
| 2 | Create `gaia_agent_layout()` component | `app/services/web/components/gaia_ui.py` | TODO |
| 3 | Add `get_or_create_primary_conversation()` helper | `app/services/web/utils/chat_service_client.py` | TODO |
| 4 | Update `chat_index()` route for single-chat mode | `app/services/web/routes/chat.py` | TODO |
| 5 | Add responsive CSS for agent layout | `app/services/web/components/gaia_ui.py` | TODO |
| 6 | Test end-to-end flow | Manual + browser | TODO |

## Code Touchpoints

| File | Changes |
|------|---------|
| `app/shared/config.py` | Add `SINGLE_CHAT_MODE: bool` |
| `app/services/web/components/gaia_ui.py` | New `gaia_agent_layout()` function |
| `app/services/web/utils/chat_service_client.py` | Add `get_or_create_primary_conversation()` |
| `app/services/web/routes/chat.py` | Modify `chat_index()` to use single-chat mode |

## Acceptance Criteria

- [ ] `SINGLE_CHAT_MODE=true` enables new agent layout
- [ ] `SINGLE_CHAT_MODE=false` preserves existing multi-chat UI
- [ ] Agent layout: full-width content, hidden sidebar, minimal header
- [ ] Single conversation auto-loads on `/chat`
- [ ] Message send/receive works with streaming
- [ ] Conversation persists across logout/login
- [ ] Mobile responsive
- [ ] Sidebar slot exists (hidden) for future use

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
