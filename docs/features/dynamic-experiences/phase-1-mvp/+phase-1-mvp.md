# Phase 1: MVP

This directory contains the design and implementation documentation for the Minimum Viable Product (MVP) of the "dynamic experiences" feature.

## Core Systems

- `000-mvp-file-based-design.md` - The original design for the file-based MVP.
- `001-kb-agent-api.md` - API reference for the KB Agent service.
- `002-kb-agent-architecture.md` - Architecture of the KB Intelligent Agent.
- `004-kb-repository-structure.md` - Details the Git-based KB repository structure.
- `005-experiences-overview.md` - High-level architecture for interactive experiences.
- `030-unified-state-model-implementation.md` - **KEY**: The config-driven unified state model (`shared` vs `isolated`).
- `031-markdown-command-system.md` - The markdown-driven command system (`game-logic`/`admin-logic`).
- `100-instance-management-implementation.md` - Validated design for the file-based instance management system.
- `101-design-decisions.md` - Architecture Decision Records (ADRs) for the instance management system.

## Game Commands & Player Interaction

- `009-game-command-developer-guide.md` - Developer guide for the game command system.
- `021-kb-command-processing-spec.md` - Specification for the general-purpose game command tool.
- `022-location-tracking-admin-commands.md` - Design for the hierarchical location tracking system.
- `028-game-command-markdown-migration.md` - Plan for migrating hardcoded commands to markdown.
- `029-game-command-architecture-comparison.md` - Compares the markdown-based agent system vs. the hardcoded game command system.

## Admin Commands

- `000-admin-commands-quick-start.md` - Quick start guide for the admin command system.
- `023-admin-commands-implementation-guide.md` - Implementation guide for `@list` and `@stats` commands.
- `024-crud-navigation-implementation.md` - Implementation of `@create`, `@connect`, and `@disconnect`.
- `025-complete-admin-command-system.md` - **KEY**: Reference for the complete admin command set.
- `033-admin-command-system.md` - Overview of the admin command framework.
- `036-experience-reset-guide.md` - Guide for resetting game experiences.

## Chat & API Integration

- `010-chat-endpoint-execution-paths.md` - Analysis of all chat endpoint execution paths.
- `011-intelligent-chat-routing.md` - The intelligent chat routing system.
- `012-unified-chat-implementation.md` - The unified intelligent chat endpoint.
- `013-unified-intelligent-chat-spec.md` - Specification for the unified chat endpoint.
- `014-chat-request-response-flow.md` - The chat request/response flow from UI to service.
- `015-tool-routing-improvement-spec.md` - Specification for improving the tool routing system.
- `016-conversation-id-streaming.md` - The V0.3 Conversation ID Streaming API.
- `017-streaming-release-notes.md` - Release notes for the V0.3 streaming update.
- `019-conversation-id-delivery.md` - Technical details of the V0.3 streaming conversation ID delivery.
- `032-chat-integration-complete.md` - Confirmation of the markdown command system's integration with the chat service.

## AI & NPCs

- `006-ai-character-integration.md` - Architecture for integrating static KB content with dynamic AI character systems.
- `027-npc-communication-system.md` - The memory-aware NPC dialogue system.
- `034-npc-interaction-system.md` - The `talk` command and NPC conversation system.

## Development & Content Creation

- `003-developer-guide.md` - Index of KB technical implementation documentation.
- `007-experience-tools-api.md` - The 20 LLM tools for conversational experience design.
- `008-kb-llm-content-creation.md` - The 4-day sprint plan for LLM-powered content creation.
- `018-unity-client-guide.md` - Unity client implementation guide for V0.3 streaming.
- `020-mvp-migration-to-classes.md` - Plan for migrating the MVP from dictionaries to classes.
- `035-product-demo-guide.md` - Guide for demonstrating the content creation workflow.

## Miscellaneous

- `026-instance-management-verification.md` - Verification report for the instance management system.
- `028-waypoint-name-resolution.md` - Design for resolving waypoint names.
- `029-wylding-woods-starting-location.md` - Details on the starting location for `wylding-woods`.
- `030-game-command-archival-report.md` - Report on the archival of the hardcoded game command system.
- `102-symphony-collaboration.md` - Log of the multi-agent design validation for the instance management system.
