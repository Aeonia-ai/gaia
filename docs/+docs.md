# docs

GAIA platform documentation root.

## Subdirectories

- `designs/` - Design Documents
- `guides/` - How-to's & Tutorials
- `reference/` - Technical Reference
- `concepts/` - High-level Explanations
- `_internal/` - Project Artifacts
- `scratchpad/` - Temporary notes and architectural outlines

## Files

- `README.md` - Human-readable overview
- `README-FIRST.md` - Quick start guide

## Key Documents

### Development & Debugging
- `guides/cookbook-creating-experiences-and-commands.md` - **START HERE**: How to create new game content
- `reference/unified-state-model-deep-dive.md` - State Model Deep Dive, Content Entity System, & Debugging Guide

### API
- `reference/api/reference/CLIENT_API_REFERENCE.md` - v0.3 API for external devs
- `reference/api/reference/GAIA_API_REFERENCE.md` - v1 API with advanced features
- `concepts/deep-dives/dynamic-experiences/phase-1-mvp/011-intelligent-chat-routing.md` - Routing system documentation

### Architecture
- `reference/chat/chat-service-implementation.md` - Complete chat service architecture
- `reference/chat/intelligent-tool-routing.md` - Tool routing with 70-80% optimization
- `reference/chat/directive-system-vr-ar.md` - VR/AR directive system for immersive experiences
- `reference/services/persona-system-guide.md` - AI persona system architecture
- `chat-routing-and-kb-architecture.md` - **MISSING**: Complete routing and KB integration
- `reference/patterns/service-discovery-guide.md` - Service discovery implementation
- `reference/database/database-architecture.md` - Hybrid database design

### KB System
- `reference/services/guides/kb-quick-setup.md` - Quick KB setup
- `reference/services/guides/kb-storage-configuration.md` - Storage backend configuration
- `reference/services/developer/kb-architecture-guide.md` - Technical architecture

### Testing
- `guides/TESTING_GUIDE.md` - Main testing documentation
- `guides/TEST_INFRASTRUCTURE.md` - Test infrastructure

### Features

- `concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md` - Admin Commands Quick Start Guide

## Status

- **Production**: Gateway, Auth, Chat (with personas & directives), KB (Git mode)
- **Implemented**: Persona system (Mu default), Tool routing intelligence, VR/AR directives
- **Available**: Database storage, Hybrid storage, RBAC
- **Development**: Web UI improvements, Advanced features

## Implementation

- **~231 files** - Organized documentation with comprehensive indexing
- **7 microservices** - Gateway, Auth, Chat, KB, Asset, Web, Database
- **2 API versions** - v0.3 (clean + directives), v1 (full metadata)
- **3 storage modes** - Git (default), Database, Hybrid
- **Persona system** - Mu (default cheerful robot) + custom personas
- **9 tools** - 6 KB tools + 3 routing tools with intelligent instructions
- **Directives** - JSON-RPC commands for VR/AR timing control

## Verification Status

The following documents have been verified against the codebase, with detailed verification notes appended to each document.

-   [`scratchpad/command-system-refactor-completion.md`](./scratchpad/command-system-refactor-completion.md#verification-status): **Core Claims Verified**
-   [`scratchpad/gateway-websocket-proxy-implementation-plan.md`](./scratchpad/gateway-websocket-proxy-implementation-plan.md#verification-status): **Core Claims Verified**
-   [`scratchpad/websocket-architecture-decision.md`](./scratchpad/websocket-architecture-decision.md#verification-status): **Core Claims Verified**
-   [`scratchpad/aoi-websocket-design-2025-11-10.md`](./scratchpad/aoi-websocket-design-2025-11-10.md#verification-status): **Core Claims Verified** (with noted discrepancy)
-   [`scratchpad/TEMPLATE-INSTANCE-IMPLEMENTATION-COMPLETE.md`](./scratchpad/TEMPLATE-INSTANCE-IMPLEMENTATION-COMPLETE.md#verification-status): **Core Claims Verified**
-   [`scratchpad/websocket-aoi-client-guide.md`](./scratchpad/websocket-aoi-client-guide.md#verification-status): **Partially Verified** (with noted discrepancy)
-   [`guides/cookbook-creating-experiences-and-commands.md`](./guides/cookbook-creating-experiences-and-commands.md#verification-status): **Partially Verified** (with noted discrepancy)
-   [`reference/unified-state-model-deep-dive.md`](./reference/unified-state-model-deep-dive.md#verification-status): **Partially Verified** (with noted discrepancies and unimplemented proposals)
-   [`reference/api/reference/CLIENT_API_REFERENCE.md`](./reference/api/reference/CLIENT_API_REFERENCE.md#verification-status): **Verified**
-   [`reference/api/reference/GAIA_API_REFERENCE.md`](./reference/api/reference/GAIA_API_REFERENCE.md#verification-status): **Partially Verified** (with noted discrepancies)
-   [`concepts/deep-dives/dynamic-experiences/phase-1-mvp/011-intelligent-chat-routing.md`](./concepts/deep-dives/dynamic-experiences/phase-1-mvp/011-intelligent-chat-routing.md#verification-status): **Outdated** (architecture has been refactored)
-   [`reference/chat/chat-service-implementation.md`](./reference/chat/chat-service-implementation.md#verification-status): **Verified**
-   [`reference/chat/intelligent-tool-routing.md`](./reference/chat/intelligent-tool-routing.md#verification-status): **Verified**
-   [`reference/chat/directive-system-vr-ar.md`](./reference/chat/directive-system-vr-ar.md#verification-status): **Verified**
-   [`reference/services/persona-system-guide.md`](./reference/services/persona-system-guide.md#verification-status): **Verified**
-   [`chat-routing-and-kb-architecture.md`](./chat-routing-and-kb-architecture.md#verification-status): **Verified**
-   [`reference/patterns/service-discovery-guide.md`](./reference/patterns/service-discovery-guide.md#verification-status): **Outdated** (Gateway not using service discovery)
-   [`reference/database/database-architecture.md`](./reference/database/database-architecture.md#verification-status): **Verified**
-   [`reference/services/guides/kb-quick-setup.md`](./reference/services/guides/kb-quick-setup.md#verification-status): **Verified**
-   [`reference/services/guides/kb-storage-configuration.md`](./reference/services/guides/kb-storage-configuration.md#verification-status): **Verified** (with minor discrepancy)
-   [`guides/TESTING_GUIDE.md`](./guides/TESTING_GUIDE.md#verification-status): **Partially Verified** (Test consolidation is incomplete)
-   [`guides/TEST_INFRASTRUCTURE.md`](./guides/TEST_INFRASTRUCTURE.md#verification-status): **Verified**
-   [`concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md`](./concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md#verification-status): **Verified**
-   [`scratchpad/+scratchpad.md`](./scratchpad/+scratchpad.md#verification-status): **Verified**
-   [`scratchpad/2025-11-03-1538-nats-implementation-progress.md`](./scratchpad/2025-11-03-1538-nats-implementation-progress.md#verification-status): **Partially Verified** (Minor discrepancies in WorldUpdateEvent version and unit test count)
-   [`scratchpad/2025-11-13-unity-bottle-fix-session.md`](./scratchpad/2025-11-13-unity-bottle-fix-session.md#verification-status): **Verified**
-   [`scratchpad/admin-command-system-comprehensive-design.md`](./scratchpad/admin-command-system-comprehensive-design.md#verification-status): **Partially Verified** (Discrepancies in command naming/syntax, property editing, and safety mechanisms)
-   [`scratchpad/admin-command-workflow-walkthrough.md`](./scratchpad/admin-command-workflow-walkthrough.md#verification-status): **Partially Verified** (Discrepancies in `@where` and `@examine` command behavior/output)
-   [`scratchpad/admin-commands-implementation-complete.md`](./scratchpad/admin-commands-implementation-complete.md#verification-status): **Partially Verified** (Markdown command specifications not found; NPC listing in `@where` is a TODO)
-   [`scratchpad/aoi-phase1-demo-guide.md`](./scratchpad/aoi-phase1-demo-guide.md#verification-status): **Verified**
-   [`scratchpad/command-bus-industry-references.md`](./scratchpad/command-bus-industry-references.md#verification-status): **Not Applicable** (Reference document)
-   [`scratchpad/command-system-refactor-proposal.md`](./scratchpad/command-system-refactor-proposal.md#verification-status): **Verified**
-   [`scratchpad/CURRENT-STATUS-2025-11-09.md`](./scratchpad/CURRENT-STATUS-2025-11-09.md#verification-status): **Verified** (with minor discrepancies noted)
-   [`scratchpad/documentation-update-plan.md`](./scratchpad/documentation-update-plan.md#verification-status): **Verified**
-   [`scratchpad/fast-commands-implementation-plan.md`](./scratchpad/fast-commands-implementation-plan.md#verification-status): **Not Applicable** (Implementation plan, not yet implemented)
-   [`scratchpad/fast-drop-command-complete.md`](./scratchpad/fast-drop-command-complete.md#verification-status): **Verified**
-   [`scratchpad/fast-go-command-complete.md`](./scratchpad/fast-go-command-complete.md#verification-status): **Verified**
-   [`scratchpad/gateway-websocket-proxy.md`](./scratchpad/gateway-websocket-proxy.md#verification-status): **Verified** (with minor discrepancy noted)
-   [`scratchpad/IMPLEMENTATION-UNIFIED-INSTANCE-ID.md`](./scratchpad/IMPLEMENTATION-UNIFIED-INSTANCE-ID.md#verification-status): **Verified**
-   [`scratchpad/intelligent-admin-introspection-design.md`](./scratchpad/intelligent-admin-introspection-design.md#verification-status): **Verified**
-   [`scratchpad/intelligent-admin-workflow-conceptual.md`](./scratchpad/intelligent-admin-workflow-conceptual.md#verification-status): **Partially Verified** (Discrepancies in `@where` command behavior/output)
-   [`scratchpad/kb-experience-architecture-deep-dive.md`](./scratchpad/kb-experience-architecture-deep-dive.md#verification-status): **Verified**
-   [`scratchpad/markdown-command-architecture.md`](./scratchpad/markdown-command-architecture.md#verification-status): **Verified**
-   [`scratchpad/nats-implementation-todo.md`](./scratchpad/nats-implementation-todo.md#verification-status): **Verified**
-   [`scratchpad/nats-world-updates-implementation-analysis.md`](./scratchpad/nats-world-updates-implementation-analysis.md#verification-status): **Verified**
-   [`scratchpad/npc-llm-dialogue-system.md`](./scratchpad/npc-llm-dialogue-system.md#verification-status): **Not Applicable** (Design proposal, not implemented)
-   [`scratchpad/PHASE-1B-ACTUAL-COMPLETION.md`](./scratchpad/PHASE-1B-ACTUAL-COMPLETION.md#verification-status): **Verified**
-   [`scratchpad/quest-driven-dynamic-spawning-system.md`](./scratchpad/quest-driven-dynamic-spawning-system.md#verification-status): **Not Applicable** (Design proposal, not implemented)
-   [`scratchpad/resume-prompt-doc-update.md`](./scratchpad/resume-prompt-doc-update.md#verification-status): **Not Applicable** (Meta-document)
-   [`scratchpad/RESUME-PROMPT.md`](./scratchpad/RESUME-PROMPT.md#verification-status): **Not Applicable** (Meta-document)
-   [`scratchpad/semantic-search-pgvector-debugging-2025-11-03.md`](./scratchpad/semantic-search-pgvector-debugging-2025-11-03.md#verification-status): **Verified**
-   [`scratchpad/simulation-architecture-overview.md`](./scratchpad/simulation-architecture-overview.md#verification-status): **Verified**
-   [`scratchpad/structured-command-parameters-proposal.md`](./scratchpad/structured-command-parameters-proposal.md#verification-status): **Verified**