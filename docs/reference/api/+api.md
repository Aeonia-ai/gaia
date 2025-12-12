# API Reference

This section provides detailed documentation for the Gaia Platform API, covering endpoints, contracts, authentication, streaming, client specifications, and knowledge base integration.

---

## Directories

- [[authentication/+authentication.md]]: Covers API key usage, JWT validation, and the future OAuth 2.0 specification.
- [[chat/+chat.md]]: Explains the numerous chat endpoint variants and the plan for their future consolidation.
- [[clients/+clients.md]]: Provides usage guides and examples for different client applications, including a CLI.
- [[reference/+reference.md]]: Core API reference documents, including the client-facing v0.3 API, advanced platform developer APIs, and a comprehensive map of all endpoints.
- [[streaming/+streaming.md]]: Provides comprehensive documentation for GAIA's Streaming API, covering SSE implementation, message formats, and client integration guides.
- [[v03/+v03.md]]: Provides comprehensive documentation for the GAIA v0.3 API, detailing its clean interface, client integration specifications, and usage best practices.

## Files

**[admin-commands-reference.md](admin-commands-reference.md)**
*   **Summary**: This document provides a quick reference and detailed syntax for 12 auto-generated admin commands used for world-building in the game, such as `@connect`, `@create`, `@delete`, `@edit`, `@inspect`, `@list`, `@reset`, `@spawn`, `@stats`, and `@where`. It includes examples, side effects, and implementation notes (referencing `kb_agent.py`), highlighting destructive operations with a `CONFIRM` keyword requirement.

**[api-contracts.md](api-contracts.md)**
*   **Summary**: This document defines API contracts for Gaia Platform services, specifying public and authenticated endpoints. It notes incomplete documentation coverage (primarily focusing on authentication) and outlines the need to document KB, Chat, Gateway, Web, and Auth services. It details API versioning (v0.3 and v1), public endpoints, protected endpoints, inter-service communication guidelines, contract testing, and a breaking changes policy.

**[conversation-id-delivery-patterns.md](conversation-id-delivery-patterns.md)**
*   **Summary**: This document explains how conversation IDs are delivered to clients in both streaming (Server-Sent Events) and non-streaming (JSON) responses. It justifies this dual-method approach by protocol constraints and alignment with industry best practices (e.g., OpenAI, Anthropic), emphasizing the "metadata priming event" for streaming. It also provides client implementation guidance, technical rationale, and a migration guide.

**[kb-driven-command-processing-spec.md](kb-driven-command-processing-spec.md)**
*   **Summary**: This specification defines a general-purpose `execute_game_command` tool that processes natural language commands for any game system by leveraging Knowledge Base content. It details a gameplay-first TDD strategy with a "security envelope" pattern, outlining the tool's interface, response format, processing architecture (including code-enforced RBAC), service integration patterns, and KB content requirements.

**[kb-endpoints.md](kb-endpoints.md)**
*   **Summary**: This document outlines Knowledge Base (KB) API endpoints, detailing core KB operations (search, read, write, delete, move), navigation and context endpoints, Git integration, cache management, and health monitoring. It highlights the automatic integration with AI-enhanced chat for natural language access to KB functions, and specifies authentication requirements, performance metrics, and storage modes. It notes that documentation coverage is incomplete for several categories.

**[README.md](README.md)**
*   **Summary**: This is the main API Reference & Contracts document for the Gaia Platform. It outlines the API documentation structure, organizing content into sections like Reference Documentation, Authentication, Chat API, Streaming API, Client Libraries, and v0.3 API. It also includes cross-cutting documentation on API Contracts, KB Endpoints, Chat Endpoints, Client Usage Guide, and API Versioning Strategy, along with testing guidelines and API metrics.