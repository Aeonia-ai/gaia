# Gaia Platform Documentation

Welcome to the consolidated documentation for the Aeonia Gaia Platform. This guide is designed to help you navigate the various facets of the platform efficiently.

---

## Documentation Structure

*   **[guides/](guides/)**: Contains practical how-to guides and tutorials for common tasks and workflows. This section is ideal for users looking for step-by-step instructions on developing, deploying, testing, and troubleshooting the platform.
*   **[reference/](reference/)**: Provides technical reference material, including API documentation, service specifics, and in-depth details on security policies. This section is for developers and architects seeking comprehensive technical specifications and explanations.
*   **[concepts/](concepts/)**: Explains the high-level concepts and architectural patterns that underpin the Gaia platform. This section is designed for anyone who wants to understand the foundational ideas and design philosophy behind the system, including deep dives into complex topics.
*   **[_internal/](_internal/)**: Houses internal project artifacts such as Architectural Decision Records (ADRs), post-mortems, reports, and other historical or administrative documents. This section is primarily for internal team members and contributors who need access to project-specific historical context.

---

## Core Documentation Files

**[chat-routing-and-kb-architecture.md](chat-routing-and-kb-architecture.md)**
*   **Summary**: This document provides a verified overview of the integrated chat routing and Knowledge Base (KB) architecture in the GAIA platform. It highlights the `UnifiedChatHandler` in `app/services/chat/unified_chat.py` as the core, implementing a single LLM call with `tool_choice="auto"` for intelligent routing. The data flow, tool aggregation (KB and routing tools), and response handling (direct or tool-driven) are detailed, emphasizing efficiency and architectural shift from multi-step chain-of-thought processing.

**[kb-fastmcp-claude-code-setup.md](kb-fastmcp-claude-code-setup.md)**
*   **Summary**: This guide explains how to set up Claude Code to access the GAIA KB service via FastMCP, enabling automatic tool discovery. It outlines the architecture for connecting Claude Code to `kb-docs` (documentation) and `kb-service` (game content) MCP endpoints, detailing the nine available MCP tools (search_kb, search_semantic, read_file, load_context, etc.). The document provides configuration methods for Claude Code, instructions for testing MCP endpoints (health check, tool discovery, tool execution), and examples of using these tools in Claude Code.

**[kb-fastmcp-integration-status.md](kb-fastmcp-integration-status.md)**
*   **Summary**: This document details the completed and production-ready FastMCP integration with pgvector, replacing ChromaDB for semantic search. It lists resolved issues (ChromaDB's ephemeral storage, FastMCP lifespan initialization, asyncpg vector type registration) and highlights key integration code (FastMCP helper function, FastAPI mounting). The document provides test results for health, MCP, semantic search endpoints, outlines next steps (applying migrations, deployment), and summarizes architectural insights into why pgvector migration and FastMCP integration were valuable.

**[kb-fastmcp-mcp-client-config.md](kb-fastmcp-mcp-client-config.md)**
*   **Summary**: This document provides instructions for configuring an MCP client (specifically Claude Code) to connect to a FastMCP server. It details two methods: manual configuration in `~/.claude/mcp_settings.json` or using an MCP HTTP client. The document explains how to verify the MCP endpoint, notes that FastMCP does not expose REST endpoints for health/tools (requiring JSON-RPC calls), lists the available tools, and offers troubleshooting tips for common issues like "Missing session ID" and timeouts.

**[kb-semantic-search-implementation.md](kb-semantic-search-implementation.md)**
*   **Summary**: This guide details the implementation of semantic search for the GAIA Knowledge Base using `pgvector` and `sentence-transformers`. It covers key features (natural language queries, persistent storage, incremental updates), architectural components (PostgreSQL, embedding models, asyncpg), and database schema for metadata and chunks. The document provides implementation details for `SemanticSearchIndexer` (indexing and querying logic), critical implementation notes (asyncpg type registration, embedding conversion, mtime tolerance), and troubleshooting for indexing/search issues.

**[nats-realtime-integration-guide.md](nats-realtime-integration-guide.md)**
*   **Summary**: This guide covers the GAIA Platform's NATS pub/sub messaging for real-time world state synchronization in AR/VR experiences. It details the Phase 1B architecture (per-request subscriptions with user-specific subjects), implementation specifics (NATS subjects, JSON event format), and server/client-side usage. The document also outlines testing procedures, known limitations (event loss between requests, no event replay) and their workarounds, and a migration path to Phase 2 (persistent WebSocket) and Phase 3 (JetStream event sourcing) for full real-time capabilities.

**[persona-update-testing.md](persona-update-testing.md)**
*   **Summary**: This guide details the solution to an issue where persona updates weren't immediately reflected in active conversations. The solution involves automatically calling a `/chat/reload-prompt` endpoint after a persona update, which fetches fresh system prompts and updates active in-memory chat histories. The document describes updated scripts (`iterate_louisa.sh`, `test_persona_update.sh`), typical workflows for iterating on persona prompts, technical details of the `/chat/reload-prompt` endpoint, cache invalidation flow, troubleshooting, and best practices.

**[README-FIRST.md](README-FIRST.md)**
*   **Summary**: This document provides a foundational overview of the GAIA Platform, a distributed AI platform for MMOIRL games and AI-powered experiences. It outlines GAIA's vision (seamless blend of digital/physical realities), rationale (evolution from monolith, solving AI interaction challenges), and technical innovations (Cluster-Per-Game, Hot-Loading AI, KOS Patterns, Backward Compatibility). It details who should use GAIA (game developers, XR/AR/VR developers, enterprise AI, knowledge workers), its current state, roadmap, and how to get started, emphasizing a future where digital and physical boundaries dissolve.

**[README.md](README.md)**
*   **Summary**: This document serves as the main entry point to the Aeonia Gaia Platform documentation. It outlines the documentation's structure, which is organized into four main sections: `guides/` (practical how-to guides), `reference/` (technical reference material), `concepts/` (high-level concepts and architectural patterns), and `_internal/` (internal project artifacts).

**[unity-chatclient-feedback-action-items.md](unity-chatclient-feedback-action-items.md)**
*   **Summary**: This document summarizes feedback and action items for the Unity ChatClient integration with GAIA, highlighting critical issues and their resolutions. It details the success of the v3 StreamBuffer in addressing streaming incompatibilities (word boundary preservation, JSON directive preservation, phrase batching), making the backend production-ready. The document also lists remaining high and medium priority action items for the ChatClient (removing local history, adding message type identification, diagnostic endpoint, directive parser), along with revised time estimates and a testing strategy.
