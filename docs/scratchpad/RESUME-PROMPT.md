# Resume Prompt for NATS World Updates Implementation

**If you are Claude Code with blank context, use this to resume work:**

---

## Quick Start

I need to continue implementing NATS world updates for the GAIA platform's December 15, 2025 demo.

**Read this file for complete context:**
```
docs/scratchpad/2025-11-03-1538-nats-implementation-progress.md
```

That file contains:
- Complete project context (MMOIRL, Wylding Woods demo)
- What's been completed (Phase 1A + Phase 1B)
- Architecture diagrams
- All files created/modified
- Next steps (testing, Phase 3, etc.)
- Technical decisions and patterns
- Resume instructions

---

## Current Status Summary

✅ **Phase 1A Complete**: KB Service publishes state changes to NATS
✅ **Phase 1B Complete**: Chat Service subscribes and forwards to Unity via SSE
❌ **Phase 1B Tests Pending**: Unit tests for stream multiplexing

---

## What to Do Next

After reading the progress file, ask the user:

**"What should I do next?"**

Options:
1. Write Phase 1B unit tests (Tester Agent)
2. Manual test with NATS subscriber
3. Code review (Reviewer Agent)
4. Git commit Phase 1A + 1B
5. Proceed to Phase 3 (integration testing with Unity)

---

## Key Files to Read First

1. `docs/scratchpad/2025-11-03-1538-nats-implementation-progress.md` ← **START HERE**
2. `docs/scratchpad/nats-world-updates-implementation-analysis.md` (implementation guide)
3. `app/shared/stream_utils.py` (stream multiplexing)
4. `app/services/chat/unified_chat.py` (SSE with NATS)
5. `app/services/kb/unified_state_manager.py` (NATS publishing)

---

## Architecture in 30 Seconds

```
Player Action (Unity)
    ↓
KB Service: Updates state → Publishes to NATS
    ↓
NATS: world.updates.user.{user_id}
    ↓
Chat Service: Subscribes → Merges with LLM narrative → SSE to Unity
    ↓
Unity Client: Visual update (<100ms) → Narrative arrives (2-3s later)
    ↓
Result: Magic feels instant ✨
```

---

## Demo Context

**What**: Wylding Woods AR/VR experience at Woander's Magical Shop
**When**: December 15, 2025
**Goal**: Player takes bottle → bottle vanishes instantly → feels like real magic
**Tech**: GPS/VPS positioning + AI-powered narratives + real-time event streaming

---

**Read the progress file above for full context, then ask the user what to do next.**
