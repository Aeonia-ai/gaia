# Phase 1: MVP for Dynamic Experiences

This directory contains the design, implementation, and verification documentation for the Minimum Viable Product (MVP) of the Dynamic Experiences platform. The focus of Phase 1 was to establish a flexible, content-driven architecture for creating and managing interactive experiences like AR games and text adventures, with a heavy emphasis on rapid, conversation-driven content creation.

---

## Core Architecture & State Management

**[030-unified-state-model-implementation.md](030-unified-state-model-implementation.md)**
*   **Summary**: This document details the **implemented and production-ready** `UnifiedStateManager`. This core system uses a single `config.json` file within each experience to define the entire state architecture. The key setting, `state.model`, determines whether the experience is `"shared"` (multiplayer, with one central world file and file-locking for concurrency) or `"isolated"` (single-player, where each user gets their own copy of the world state). It also covers the `POST /experience/interact` endpoint, persistent player profiles that remember the user's current experience across sessions, and the bootstrap process for new players.

**[000-mvp-file-based-design.md](000-mvp-file-based-design.md)**
*   **Summary**: **(LEGACY)** This document describes the original, now-superseded design for the file-based MVP. It outlines the initial concepts of separating "templates" (design-time definitions in Markdown) from "instances" (live game objects in JSON) and a three-layer architecture (World Instances, Player Progress, Player World View). While the principles are still relevant, the implementation details have been replaced by the `Unified State Model`.

**[020-mvp-migration-to-classes.md](020-mvp-migration-to-classes.md)**
*   **Summary**: **(LEGACY / SUPERSEDED)** This document outlines a migration path from a simple dictionary-based data model to a more robust class-based structure. This migration was **never executed** because the system evolved directly to the more advanced `Unified State Model` which uses SQLAlchemy and a different architectural pattern. It is retained for historical context only.

---

## Command Systems (Player & Admin)

### Player Game Commands

**[031-markdown-command-system.md](031-markdown-command-system.md)**
*   **Summary**: Details the **implemented** markdown-driven command system. The system **auto-discovers** available commands by scanning for `.md` files in two separate directories: `game-logic/` for player commands (e.g., `look`, `go`) and `admin-logic/` for admin commands (e.g., `@list`). This allows new commands to be added simply by creating a new markdown file, with no code changes required. The frontmatter of each file defines its `command` name, `aliases`, and other properties.

**[021-kb-command-processing-spec.md](021-kb-command-processing-spec.md)**
*   **Summary**: **(Partially Implemented)** This specification defines the general-purpose `execute_game_command` tool. The spec proposes a "Security Envelope Pattern" where code-enforced Role-Based Access Control (RBAC) is applied *before* the LLM interprets the game logic from markdown files. While the infrastructure for this tool is in place, the core processor that loads markdown content is still a stub; the current implementation relies on hardcoded Python logic.

**[009-game-command-developer-guide.md](009-game-command-developer-guide.md)**
*   **Summary**: **(Partially Implemented)** A developer guide for the KB-driven game command system. It explains the core concept of using YAML blocks within markdown files as "training examples" for the LLM to generate structured JSON responses. It also contrasts the two main approaches: the `/agent/interpret` endpoint for narrative generation and the `/game/command` tool for structured game actions.

**[028-game-command-markdown-migration.md](028-game-command-markdown-migration.md)**
*   **Summary**: **(FUTURE PLAN)** A detailed planning document proposing a migration from the current hardcoded Python game commands to a fully markdown-driven system. It includes a **5-6 week effort estimate** and outlines the steps needed to create command definition files (e.g., `look.md`, `collect.md`) and modify the `execute_game_command` function to load and interpret them at runtime.

**[029-game-command-architecture-comparison.md](029-game-command-architecture-comparison.md)**
*   **Summary**: This document contrasts the two command processing systems in GAIA: the markdown-based `/agent/interpret` endpoint, which is content-driven and fully implemented, and the hardcoded `/game/command` endpoint, which is currently code-driven and does not yet load its logic from markdown files as intended by the design.

**[030-game-command-archival-report.md](030-game-command-archival-report.md)**
*   **Summary**: This report confirms the successful archival of the original, hardcoded game command implementation into a separate `game_commands_legacy_hardcoded.py` file. This was done to safely prepare for the planned migration to the markdown-driven system while keeping the working legacy code as a reference and rollback option.

### Admin Command System

**[033-admin-command-system.md](033-admin-command-system.md)**
*   **Summary**: Provides an overview of the admin command framework. It explains that admin commands are distinguished by an `@` prefix, are auto-discovered from the `admin-logic/` directory, and execute instantly (<30ms) via direct file system access, bypassing any LLM interpretation for speed and predictability.

**[025-complete-admin-command-system.md](025-complete-admin-command-system.md)**
*   **Summary**: A comprehensive guide to the **23+ implemented admin commands**, providing a full CRUD (Create, Read, Update, Delete) and search interface for world-building. It details the syntax for commands like `@list`, `@inspect`, `@create`, `@edit`, `@connect`, `@delete`, `@where`, `@find`, and `@reset`. It also covers the mandatory `CONFIRM` keyword for all destructive operations.

**[000-admin-commands-quick-start.md](000-admin-commands-quick-start.md)**
*   **Summary**: A rapid onboarding guide for the admin command system. It serves as a starting point by linking to essential documentation (like the "complete" guide), referencing the core implementation files (e.g., `kb_agent.py`), and listing the primary test suites (`test_new_admin_commands.py`, `test_crud_commands.py`) for validation.

**[023-admin-commands-implementation-guide.md](023-admin-commands-implementation-guide.md)**
*   **Summary**: This guide focuses on the implementation of the basic read-only admin commands: `@list` (with its variants for waypoints, locations, items, etc.) and `@stats`. It explains the command flow, where the `@` prefix is detected and routed to the `_execute_admin_command` parser in `kb_agent.py`.

**[024-crud-navigation-implementation.md](024-crud-navigation-implementation.md)**
*   **Summary**: Details the implementation of the world-building admin commands. This includes `@create` for waypoints, locations, and sublocations, as well as `@connect` and `@disconnect` for managing the **bidirectional navigation graph** between sublocations. It also covers the use of atomic file writes to ensure data integrity.

---

## Game Systems & Content

**[005-experiences-overview.md](005-experiences-overview.md)**
*   **Summary**: Presents the high-level architecture of the Experience Platform, broken down into four components: Content Storage (KB Service), Progress Tracking (PostgreSQL/Redis), Runtime Execution (Game Commands), and Design Tools. It confirms that Phase 1, the Unified State Model, is complete and production-ready.

**[034-npc-interaction-system.md](034-npc-interaction-system.md)** / **[027-npc-communication-system.md](027-npc-communication-system.md)** (Consolidated)
*   **Summary**: Details the **implemented** NPC conversation system, which is powered by the `talk` command. It uses a three-layer memory model: **1) NPC Template** (static personality/knowledge in a `.md` file), **2) NPC Instance** (shared world state like mood/location in a `.json` file), and **3) Player-NPC Relationship** (per-player private history, including a 0-100 trust level, in a separate `.json` file).

**[006-ai-character-integration.md](006-ai-character-integration.md)**
*   **Summary**: Describes the architecture for integrating static KB content (character templates in markdown) with dynamic AI systems. It proposes a three-layer AI response system (Immediate acknowledgment, Narrative Generation, and async World Evolution) and a hierarchical memory system (session, working, long-term) to provide NPCs with rich, persistent context.

**[026-instance-management-verification.md](026-instance-management-verification.md)**
*   **Summary**: A verification report confirming that the file-based instance management system is **fully implemented and working**. It verifies that the three-layer architecture (manifest, instance files, player state) is operational and that all 5/5 tests in `test_instance_management_complete.py` pass, validating item collection, inventory, and location awareness.

**[022-location-tracking-admin-commands.md](022-location-tracking-admin-commands.md)**
*   **Summary**: **(DESIGN SPEC)** A design document proposing a hierarchical location model (Waypoint → Location → Sublocation) to create a Zork-like AR experience. It specifies a comprehensive set of MUD-style `@` commands for admins and natural language commands for players to navigate this structure. This design is only partially implemented.

**[028-waypoint-name-resolution.md](028-waypoint-name-resolution.md)**
*   **Summary**: Details the **implemented** three-layer system for resolving human-friendly waypoint names. It describes the lookup strategy: 1) Exact case-insensitive match, 2) Fuzzy match on name/description, and as a final fallback, 3) LLM-based semantic resolution for complex natural language queries.

**[029-wylding-woods-starting-location.md](029-wylding-woods-starting-location.md)**
*   **Summary**: Documents the **implemented** change of the Wylding Woods starting location to the "Woander Store Area" (`waypoint_28a_store`) to improve the new player experience. It introduces the `starting_waypoint: true` convention in `locations.json` to mark an experience's default spawn point.

---

## Chat Service & API Integration

**[032-chat-integration-complete.md](032-chat-integration-complete.md)**
*   **Summary**: Announces that the markdown command system is **fully integrated** with the chat service. Users can now select experiences ("I want to play..."), execute player commands (`look`, `talk to...`), and use admin commands (`@list...`) seamlessly within a conversation, with state persisting correctly.

**[014-chat-request-response-flow.md](014-chat-request-response-flow.md)**
*   **Summary**: Provides a comprehensive overview of the end-to-end chat request flow, starting from the Web UI (using FastHTML with HTMX/SSE), through the Gateway (which handles authentication and adds the `_auth` object), to the Chat Service (which orchestrates the LLM call), and back.

**[012-unified-chat-implementation.md](012-unified-chat-implementation.md)**
*   **Summary**: Details the **implementation** of the `UnifiedChatHandler`. This centralizes routing logic into a single `/chat/` endpoint that uses LLM tool-calling with `tool_choice="auto"` to decide whether to respond directly, route to an MCP agent for tool use, or trigger multi-agent orchestration.

**[013-unified-intelligent-chat-spec.md](013-unified-intelligent-chat-spec.md)**
*   **Summary**: The formal **specification** for the `UnifiedChatHandler`. It defines the routing tools provided to the LLM, such as `use_mcp_agent` and `use_multiagent_orchestration`, and outlines the system prompt designed to guide the LLM's routing decisions.

**[010-chat-endpoint-execution-paths.md](010-chat-endpoint-execution-paths.md)**
*   **Summary**: A performance analysis document comparing the various chat endpoints. It details the execution path and average response time for each, from the fastest `/ultrafast-redis-v3` (~400ms) to the most complex `/mcp-agent` (~3-5s), explaining the trade-offs between speed and features.

**[011-intelligent-chat-routing.md](011-intelligent-chat-routing.md)**
*   **Summary**: **(OUTDATED)** This document describes a previous, now-deprecated architecture for chat routing. It is retained for historical context but points to `app/services/chat/unified_chat.py` for the current, correct implementation.

### V0.3 Streaming API

**[016-conversation-id-streaming.md](016-conversation-id-streaming.md)**
*   **Summary**: The API reference for the `POST /api/v0.3/chat` streaming endpoint. It details the Server-Sent Events (SSE) protocol used, defining the `metadata` event (which always appears first and contains the `conversation_id`) and the `content` events that stream the response.

**[017-streaming-release-notes.md](017-streaming-release-notes.md)**
*   **Summary**: Release notes for the V0.3 streaming feature. The key feature is the immediate delivery of the `conversation_id` in the first SSE chunk, enabling real-time clients like Unity to manage conversation state without waiting for the full response, a 40-100x improvement in time-to-context.

**[019-conversation-id-delivery.md](019-conversation-id-delivery.md)**
*   **Summary**: A technical deep-dive into the implementation of V0.3 streaming. It highlights the conversation pre-creation strategy (`_get_or_create_conversation_id`) that allows the ID to be generated and sent before the LLM call, and the graceful server-side validation that handles invalid or missing IDs.

**[018-unity-client-guide.md](018-unity-client-guide.md)**
*   **Summary**: A practical guide for Unity developers. It provides C# code examples and best practices for consuming the V0.3 streaming API, including a thread-safe manager using coroutines, object pooling for VR performance, and robust error handling with exponential backoff.

---

## Future-Facing & Tooling

**[004-kb-repository-structure.md](004-kb-repository-structure.md)**
*   **Summary**: A verified walkthrough of the KB's Git-first architecture, clarifying that the `/kb` directory in the container is cloned from GitHub on startup, not mounted from a local volume. It also describes the file structure for experiences, including the `instances`, `templates`, and `players` directories.

**[007-experience-tools-api.md](007-experience-tools-api.md)**
*   **Summary**: **(DESIGN SPEC)** This document specifies a suite of 20 LLM-callable tools to enable conversational experience design. It outlines a vision where designers can `list_experiences`, `create_experience_content`, `edit_experience_content`, etc., through natural language, with the LLM learning content structure from examples via `get_content_template`.

**[008-kb-llm-content-creation.md](008-kb-llm-content-creation.md)**
*   **Summary**: **(DESIGN PROPOSAL / NOT IMPLEMENTED)** This document proposes a system for designers to create game content (waypoints, rooms, items) through a multi-turn conversation with an LLM. It includes a 4-day implementation plan and a demo script vision.

**[015-tool-routing-improvement-spec.md](015-tool-routing-improvement-spec.md)**
*   **Summary**: **(FUTURE ROADMAP)** A planning document for v0.3+ that proposes consolidating the 60+ chat endpoints down to 4, creating a new OpenAI-compliant `/completions` endpoint, and integrating KOS (Knowledge Operating System) intelligence for domain-aware orchestration and context loading.

**[035-product-demo-guide.md](035-product-demo-guide.md)**
*   **Summary**: A step-by-step guide for a 10-minute product demo. The demo flow is designed to highlight the "1,080x faster content creation" value proposition by contrasting the rich player experience with the instant, zero-latency `@create waypoint` admin command. It includes the ROI calculation and a demo prep checklist.

**[036-experience-reset-guide.md](036-experience-reset-guide.md)**
*   **Summary**: A practical guide detailing three methods for resetting a game experience to its pristine initial state: 1) The recommended `reset-experience.sh` CLI script, 2) The `@reset` admin command via the API, and 3) Manual file operations for emergency recovery. It covers automatic backups and state model differences.

**[003-developer-guide.md](003-developer-guide.md)**
*   **Summary**: A meta-document that serves as a directory, pointing to other key technical implementation documents within the Knowledge Base, such as `kb-architecture-guide.md` and `kb-llm-content-creation.md`.