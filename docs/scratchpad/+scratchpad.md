# Scratchpad

This directory is a collection of working documents, session notes, ad-hoc analyses, and temporary files used during the development of the Gaia platform. It represents the "work in progress" and contains raw, unfiltered insights and plans.

---

## Key Documents

**Design & Implementation Plans**
*   **[aoi-websocket-design-2025-11-10.md](aoi-websocket-design-2025-11-10.md)**: Outlines the design for the Area of Interest (AOI) WebSocket system, where the client sends its location and the server responds with nearby world objects.
*   **[fast-commands-implementation-plan.md](fast-commands-implementation-plan.md)**: Proposes adding fast-path Python handlers for common game commands to bypass the slow LLM path, targeting a <100ms response time.
*   **[command-system-refactor-proposal.md](command-system-refactor-proposal.md)**: Proposes a unified `ExperienceCommandProcessor` to centralize command handling for both HTTP and WebSocket endpoints, eliminating divergent logic.
*   **[admin-command-system-comprehensive-design.md](admin-command-system-comprehensive-design.md)**: A design document and gap analysis for the Admin Command System, proposing a unified `@edit` command to provide full administrative control over all game objects.
*   **[intelligent-admin-introspection-design.md](intelligent-admin-introspection-design.md)**: A design document for an intelligent admin command system. It proposes `@examine` to view the JSON structure of any game object and a powerful `@edit` command that uses dot-notation to modify any nested property with type inference and validation.
*   **[npc-llm-dialogue-system.md](npc-llm-dialogue-system.md)**: A design document for a proper NPC dialogue system, proposing to move the LLM call directly into a fast-path `talk` handler within the KB service, eliminating the "MVP kludge".
*   **[quest-driven-dynamic-spawning-system.md](quest-driven-dynamic-spawning-system.md)**: A design document proposing a system for dynamically showing or hiding items based on player quest status.
*   **[structured-command-parameters-proposal.md](structured-command-parameters-proposal.md)**: Proposes adding support for structured parameters to the WebSocket protocol to enable a "fast path" that bypasses slow LLM processing for common commands.
*   **[gateway-websocket-proxy-implementation-plan.md](gateway-websocket-proxy-implementation-plan.md)**: The design document for the Gateway WebSocket proxy, which was implemented to provide a single, secure entry point for all client WebSocket connections.
*   **[testing-organization-plan.md](testing-organization-plan.md)**: A proposal to consolidate manual and scripted tests into a more organized structure under `tests/manual/`, categorized by feature (experience, infrastructure) rather than by protocol.
*   **[websocket-migration-plan.md](websocket-migration-plan.md)**: A historical planning document that outlines the migration from SSE to WebSocket for real-time communication to enable persistent connections and autonomous world events.
*   **[websocket-world-state-sync-proposal.md](websocket-world-state-sync-proposal.md)**: A design document proposing a complete world state synchronization protocol for WebSockets, including initial state delivery, delta updates with versioning, and a full Area of Interest (AOI) payload structure.

**Completion Reports & Session Notes**
*   **[2025-11-03-1538-nats-implementation-progress.md](2025-11-03-1538-nats-implementation-progress.md)**: Details the completed NATS implementation for real-time world updates, split into Phase 1A (KB publishing) and Phase 1B (Chat forwarding via SSE).
*   **[IMPLEMENTATION-UNIFIED-INSTANCE-ID.md](IMPLEMENTATION-UNIFIED-INSTANCE-ID.md)**: Details the completed fix for a critical field name mismatch, normalizing item data to use `instance_id` and `template_id`.
*   **[admin-commands-implementation-complete.md](admin-commands-implementation-complete.md)**: Reports the completion of the intelligent admin command system, including handlers for `@examine`, `@where`, and `@edit-item`.
*   **[command-system-refactor-completion.md](command-system-refactor-completion.md)**: Summarizes the successful refactor to a unified `ExperienceCommandProcessor`, centralizing all command routing.
*   **[fast-drop-command-complete.md](fast-drop-command-complete.md)**: Reports the completion of the `drop_item` fast handler, achieving a 6.7ms response time.
*   **[fast-go-command-complete.md](fast-go-command-complete.md)**: Reports the completion of the `go` fast handler, achieving a 6ms response time and fixing a key terminology mismatch ("area" vs. "sublocation").
*   **[PHASE-1B-ACTUAL-COMPLETION.md](PHASE-1B-ACTUAL-COMPLETION.md)**: Clarifies the *actual* implementation of the NATS integration, which involved creating per-request SSE subscriptions in the Chat service as a temporary step.
*   **[TEMPLATE-INSTANCE-IMPLEMENTATION-COMPLETE.md](TEMPLATE-INSTANCE-IMPLEMENTATION-COMPLETE.md)**: Reports the completion of the `instance_id`/`template_id` refactor, resolving a critical Unity integration blocker.
*   **[2025-11-13-unity-bottle-fix-session.md](2025-11-13-unity-bottle-fix-session.md)**: Documents the fix for a critical bug where the `build_aoi()` function was failing due to expecting item objects but receiving strings.
*   **[gateway-websocket-proxy.md](gateway-websocket-proxy.md)**: Describes the implemented WebSocket proxy in the Gateway service, which acts as a single, secure entry point for all client WebSocket connections.
*   **[semantic-search-pgvector-debugging-2025-11-03.md](semantic-search-pgvector-debugging-2025-11-03.md)**: A session log detailing the debugging of a pgvector semantic search issue caused by an incorrect schema name.
*   **[visibility-toggle-system-implementation.md](visibility-toggle-system-implementation.md)**: Details the Phase 1 implementation of a system to dynamically show or hide items by toggling a `visible` flag, enabling quests to make items appear in the world.

**Analyses & Troubleshooting**
*   **[CRITICAL-AOI-FIELD-NAME-ISSUE.md](CRITICAL-AOI-FIELD-NAME-ISSUE.md)**: Details a resolved critical issue caused by a mismatch between documented (`instance_id`) and implemented (`id`) field names for items in the AOI response.
*   **[command-formats-comparison.md](command-formats-comparison.md)**: Analyzes the four distinct command/response formats used in GAIA: Player Commands, CommandResult, JSON-RPC Directives, and Symbolic NATS Directives.
*   **[CURRENT-STATUS-2025-11-09.md](CURRENT-STATUS-2025-11-09.md)**: A historical snapshot of the platform's status, noting that world state discovery on client connection is a critical missing feature.
*   **[nats-world-updates-implementation-analysis.md](nats-world-updates-implementation-analysis.md)**: An analysis document justifying the use of NATS for real-time world updates to decouple the KB and Chat services.
*   **[npc-interaction-mvp-kludge.md](npc-interaction-mvp-kludge.md)**: This document details the temporary, demo-focused implementation for NPC dialogue, which uses a circular `KB -> Chat -> KB` HTTP call pattern.
*   **[simulation-architecture-overview.md](simulation-architecture-overview.md)**: Outlines a high-level architecture where the GAIA server acts as the "symbolic" authority and the Unity client as the "concrete" authority.
*   **[terminology-sublocation-vs-area-analysis.md](terminology-sublocation-vs-area-analysis.md)**: An analysis that identified and resolved a terminology mismatch between "area" and "sublocation" in the codebase.
*   **[waypoint-to-location-architecture-analysis.md](waypoint-to-location-architecture-analysis.md)**: An analysis of the evolution from a linear waypoint system to a more flexible, location-based architecture with a 4-tier spatial hierarchy.
*   **[websocket-and-kb-content-analysis.md](websocket-and-kb-content-analysis.md)**: Details the WebSocket authentication flow and the organization of game commands for the `wylding-woods` experience.
*   **[websocket-world-state-discovery.md](websocket-world-state-discovery.md)**: A design document that explores the problem of initial world state synchronization for clients connecting via WebSocket and proposes different strategies for state delivery.
*   **[WORLD-UPDATE-AOI-ALIGNMENT-ANALYSIS.md](WORLD-UPDATE-AOI-ALIGNMENT-ANALYSIS.md)**: Documents the resolution of a format mismatch between `world_update` messages and the `Area of Interest` (AOI) data structure, aligning them on the v0.4 `instance_id`/`template_id` standard.
*   **[world-vs-locations-json-architecture.md](world-vs-locations-json-architecture.md)**: An architectural analysis clarifying the distinct roles of `world.json` (active, mutable game state) and `locations.json` (legacy, static waypoint templates), concluding that `world.json` is the source of truth for all gameplay logic.

**Testing & Workflow Guides**
*   **[aoi-phase1-demo-guide.md](aoi-phase1-demo-guide.md)**: Provides a script and talking points for demonstrating the Area of Interest (AOI) system.
*   **[command-line-testing-drop-collect.md](command-line-testing-drop-collect.md)**: Provides command-line scripts for testing the `drop` and `collect` fast commands.
*   **[admin-command-workflow-walkthrough.md](admin-command-workflow-walkthrough.md)**: A conceptual walkthrough of using the proposed admin commands for various administrative tasks.
*   **[live-demo-commands-unity-integration.md](live-demo-commands-unity-integration.md)**: A demo script showcasing real-time Unity integration with sub-second command responses.
*   **[UNITY-LOCAL-TESTING-GUIDE.md](UNITY-LOCAL-TESTING-GUIDE.md)**: A guide for the Unity client team to connect to the local server for testing the v0.4 WorldUpdate implementation.
*   **[websocket-aoi-client-guide.md](websocket-aoi-client-guide.md)**: A comprehensive guide for client developers on how to integrate with the WebSocket Area of Interest (AOI) system, detailing message formats, connection flow, and the template/instance architecture.
*   **[websocket-fast-command-testing-scripts.md](websocket-fast-command-testing-scripts.md)**: A reference for the collection of bash scripts used to test WebSocket fast commands, including player actions and admin utilities.
*   **[websocket-test-results-v04.md](websocket-test-results-v04.md)**: The test results for the v0.4 WebSocket implementation, confirming that the infrastructure is ready for Unity integration.
*   **[websocket-test-results.md](websocket-test-results.md)**: Test results for the WebSocket experience endpoint, validating the protocol layer but identifying a blocker in the KB service's player view initialization logic.

**Meta & Planning**
*   **[documentation-update-plan.md](documentation-update-plan.md)**: Outlines the necessary documentation updates to reflect the new `POST /experience/interact` endpoint.
*   **[command-bus-industry-references.md](command-bus-industry-references.md)**: A comprehensive reference guide validating the Command Bus architecture pattern.
*   **[nats-implementation-todo.md](nats-implementation-todo.md)**: A historical task tracking document from early November 2025 for the NATS implementation.
*   **[TODO.md](TODO.md)**: A high-level task list for ongoing development.
*   **[RESUME-PROMPT.md](RESUME-PROMPT.md)**: A meta-document providing a "resume prompt" to help re-establish context for a new development session.
*   **[wylding-woods-knowledge-base-inventory.md](wylding-woods-knowledge-base-inventory.md)**: A complete inventory of the `wylding-woods` experience, detailing all player commands, admin commands, world state structure, NPCs, items, and quests.
*   **[websocket-architecture-decision.md](websocket-architecture-decision.md)**: Documents the decision to ship the AEO-65 demo with the WebSocket endpoint in the KB Service as a "fast path" with known technical debt, and to migrate to a dedicated Session Service post-demo.
*   **[websocket-world-state-sync-proposal.md](websocket-world-state-sync-proposal.md)**: A design document proposing a complete world state synchronization protocol for WebSockets, including initial state delivery, delta updates with versioning, and a full Area of Interest (AOI) payload structure.
*   **[resume-prompt-doc-update.md](resume-prompt-doc-update.md)**: A meta-document, likely for internal use, and does not contain project information.