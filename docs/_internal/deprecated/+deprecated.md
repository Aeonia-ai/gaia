# Deprecated Documents

This directory contains documents that are deprecated, outdated, or describe architectural decisions and implementations that have been superseded. These documents are retained for historical context and reference but should not be considered current or authoritative.

---

## Deprecated Documents

**[bug-orchestrated-endpoint.md](bug-orchestrated-endpoint.md)**
*   **Summary**: This document reports a bug in the `/api/v1/chat/orchestrated` endpoint, where a format mismatch between the API contract (expecting `message: str`) and service implementation (looking for `messages: List[Dict]`) led to 400 errors. The document specifies that a fix is required to align the service with the standard `message` field used across other chat endpoints.

**[claude-2025-01-25-thinking.md](claude-2025-01-25-thinking.md)**
*   **Summary**: This document captures the thought process and debugging efforts from January 25, 2025, focused on fixing service discovery for auto-route registration in the chat service. It identifies an initialization order issue and inconsistent patterns as root causes for the gateway failing to discover chat service endpoints. The document also highlights the discovery of an excessive number of chat routes, revealing early technical debt from rapid experimentation.

**[kos-documentation-updates.md](kos-documentation-updates.md)**
*   **Summary**: This document summarizes updates made to the Gaia platform documentation to properly represent KOS (Knowledge Operating System) as the "living proof of MMOIRL principles." It details the addition of new sections and a dedicated document (`/docs/kos-mmoirl-connection.md`) to establish KOS's credibility, map its features to MMOIRL equivalents, and demonstrate proven consciousness tech patterns in daily use since June 2024.

**[kos-mmoirl-connection.md](kos-mmoirl-connection.md)**
*   **Summary**: Titled "KOS as MMOIRL: The Living Proof of Consciousness Technology," this document asserts that the Knowledge Operating System (KOS) and its Knowledge Base (KB) validate every MMOIRL principle through daily production use since June 2024. It draws direct parallels between KOS concepts (e.g., persistent memory, context switching) and MMOIRL gameplay elements, presenting KOS as a proven, text-based prototype ready to scale to spatial VR/AR experiences.

**[missing-gateway-endpoints.md](missing-gateway-endpoints.md)**
*   **Summary**: This document identifies several useful endpoints existing in the chat service (e.g., for conversations management, searching history, and orchestration metrics) that were not exposed through the API Gateway. It proposes specific Gateway routes to add, highlighting the benefits of a complete API surface, proper authentication, API documentation, security, and centralized monitoring that the Gateway provides.

**[mmoirl-cluster-architecture.md](mmoirl-cluster-architecture.md)**
*   **Summary**: This document proposes an archived "cluster-per-game" deployment strategy for MMOIRL games, advocating for complete isolation and customization capabilities for each game, leveraging the proven principles of the Knowledge Operating System (KOS). It details the benefits of this architecture (data security, performance, customization) and a phased implementation strategy using infrastructure templates and deployment automation for rapid game launches.

**[multitenancy-migration-guide.md](multitenancy-migration-guide.md)**
*   **Summary**: This guide outlines a strategy for migrating from a "cluster-per-game" architecture to a multi-tenant architecture, to be considered when business needs (cost optimization, unified management) or technical indicators (many small games, shared player base) demand it. It details a phased approach covering database multi-tenancy, authentication enhancement, Redis key namespacing, and service isolation, while emphasizing the importance of maintaining reversibility.

**[quick-reference.md](quick-reference.md)**
*   **Summary**: This document provides a quick reference guide to the Gaia Platform, covering development environments (Local Docker, cloud dev), the authentication system (user-associated API keys, database schema), service architecture (ports, URLs, core API endpoints), database management, testing, deployment, and key files. It also outlines common tasks and troubleshooting steps for rapid onboarding and system overview.

**[redis-chat-architecture.md](redis-chat-architecture.md)**
*   **Summary**: This document details a deprecated Redis-based chat history management system. It outlines how Redis was used for storing chat history as LIST data structures with TTL, explaining Redis operations, performance characteristics (sub-millisecond operations), and its integration with other chat endpoints. The architecture provided enterprise-grade chat history with automatic memory management and fault tolerance, representing a 60-75% performance improvement over traditional database-backed history.

**[remote-auth-setup.md](remote-auth-setup.md)**
*   **Summary**: This document addresses the setup of remote authentication, specifically the challenge of inconsistent API keys across different environments (local vs. dev/staging/prod) because API keys were stored in environment-specific PostgreSQL databases. It suggests solutions such as creating API keys per environment, using Supabase JWT authentication, or leveraging a portable database initialization script.