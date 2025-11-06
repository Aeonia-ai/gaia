# scratchpad

Temporary notes and architectural outlines.

## Files

### Architecture & Analysis
- `simulation-architecture-overview.md` - Architectural Overview: KB's Distributed Simulation & State Management
- `kb-experience-architecture-deep-dive.md` - KB Experience Endpoints and State Logic: An Architectural Deep Dive
- `nats-world-updates-implementation-analysis.md` - **NATS-Based Real-Time World Updates: Implementation Analysis** (2025-11-02) - Codebase analysis, latency optimization focus, and 4-phase implementation roadmap for NATS pub/sub integration

### Task Tracking & Progress

**⚠️ IMPORTANT**: Two different NATS implementation approaches exist in these files!

**Original Plan** (KB Publishing → Chat Forwarding - NOT completed):
- `TODO.md` - **Phase 1A-3 Task Checklist** - Original 4-phase plan with KB publishing
- `nats-implementation-todo.md` - **Active Implementation Tracking** (2025-11-02) - Original plan task tracking
- `2025-11-03-1538-nats-implementation-progress.md` - Progress on original plan (partially complete)

**Actual Implementation** (Per-Request Subscriptions - ✅ COMPLETE):
- `PHASE-1B-ACTUAL-COMPLETION.md` - **✅ What Was Actually Built** (2025-11-04) - Clarifies Phase 1B completion: per-request NATS subscriptions, bug fixes, testing, limitations, and future roadmap

**Quick Resume**:
- `RESUME-PROMPT.md` - Simple prompt to restore context from progress file for future Claude sessions
- `documentation-update-plan.md` - **Documentation Update Plan for `experience/interact` Endpoint** (2025-11-05) - Outlines necessary updates to reflect the current GAIA platform architecture, focusing on the `POST /experience/interact` endpoint and its two-pass LLM architecture.
- `resume-prompt-doc-update.md` - **Resume Prompt: Documentation Update for GAIA Architecture** - A prompt for future me to continue the documentation update process.
