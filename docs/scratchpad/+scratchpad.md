# scratchpad

Temporary notes and architectural outlines.

## Files

### Architecture & Analysis
- `simulation-architecture-overview.md` - Architectural Overview: KB's Distributed Simulation & State Management
- `kb-experience-architecture-deep-dive.md` - KB Experience Endpoints and State Logic: An Architectural Deep Dive
- `world-vs-locations-json-architecture.md` - Architectural analysis clarifying the roles of `world.json` and `locations.json`.
- `command-formats-comparison.md` - Comparison of WebSocket commands, CommandResult responses, and JSON-RPC directives.
- `command-bus-industry-references.md` - Industry references and validation for the Command Bus architecture pattern.
- `testing-organization-plan.md` - A plan to reorganize the manual testing structure for better clarity and discoverability.

### NATS & WebSocket
- `nats-world-updates-implementation-analysis.md` - **NATS-Based Real-Time World Updates: Implementation Analysis** (2025-11-02) - Codebase analysis, latency optimization focus, and 4-phase implementation roadmap for NATS pub/sub integration
- `websocket-and-kb-content-analysis.md` - **WebSocket and KB Content Analysis for Wylding Woods** (2025-11-06) - Detailed trace of WebSocket authentication, message flow, game command organization, and experience capabilities for 'wylding-woods'.
- `websocket-architecture-decision.md` - Architectural decision document for the WebSocket implementation, choosing a hybrid approach.
- `websocket-migration-plan.md` - Migration plan from SSE to WebSocket for real-time communication.
- `websocket-world-state-discovery.md` - Design document for world state discovery and synchronization over WebSocket.
- `websocket-world-state-sync-proposal.md` - Proposal for synchronizing world state over WebSocket on initial connection.
- `gateway-websocket-proxy.md` - Implementation details of the Gateway WebSocket proxy.

### Command System
- `command-system-refactor-proposal.md` - **Command System Refactor Proposal: Unified ExperienceCommandProcessor** (2025-11-06) - Proposal for a unified command processing architecture, including hybrid command execution and refined LLM roles.
- `command-system-refactor-completion.md` - Completion summary of the unified command processing system refactor.

### Task Tracking & Progress

**⚠️ IMPORTANT**: Two different NATS implementation approaches exist in these files!

**Original Plan** (KB Publishing → Chat Forwarding - NOT completed):
- `TODO.md` - **Phase 1A-3 Task Checklist** - Original 4-phase plan with KB publishing
- `nats-implementation-todo.md` - **Active Implementation Tracking** (2025-11-02) - Original plan task tracking
- `2025-11-03-1538-nats-implementation-progress.md` - Progress on original plan (partially complete)

**Actual Implementation** (Per-Request Subscriptions - ✅ COMPLETE):
- `PHASE-1B-ACTUAL-COMPLETION.md` - **✅ What Was Actually Built** (2025-11-04) - Clarifies Phase 1B completion: per-request NATS subscriptions, bug fixes, testing, limitations, and future roadmap

### Debugging & Testing
- `semantic-search-pgvector-debugging-2025-11-03.md` - Debugging session notes for fixing pgvector semantic search issues.
- `websocket-test-results.md` - Test results for the WebSocket experience endpoint.

### Game Content
- `wylding-woods-knowledge-base-inventory.md` - Inventory of the `wylding-woods` experience, including commands, NPCs, items, and quests.

### Documentation & Guides
- `documentation-update-plan.md` - **Documentation Update Plan for `experience/interact` Endpoint** (2025-11-05) - Outlines necessary updates to reflect the current GAIA platform architecture, focusing on the `POST /experience/interact` endpoint and its two-pass LLM architecture.
- `resume-prompt-doc-update.md` - **Resume Prompt: Documentation Update for GAIA Architecture** - A prompt for future me to continue the documentation update process.
- `RESUME-PROMPT.md` - Simple prompt to restore context from progress file for future Claude sessions.