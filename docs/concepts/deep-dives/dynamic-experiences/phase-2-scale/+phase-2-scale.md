# Phase 2: Scale for Dynamic Experiences

This directory contains design documentation for scaling the Dynamic Experiences platform, focusing on robust data management, performance optimization, and intelligent agent integration to support a growing number of players and increasingly complex game worlds.

---

## Core Scalability Documents

**[000-scale-instance-management-design.md](000-scale-instance-management-design.md)**
*   **Summary**: This document details the architectural design for scaling MMOIRL game instance management. It establishes a clear separation between **templates** (design-time definitions in KB files) and **instances** (runtime state stored in PostgreSQL with JSONB columns). The choice of PostgreSQL JSONB with GIN and PostGIS indexes is justified for its flexibility, schema-agnostic evolution, and 10-100x performance improvement over file-based storage for queries like spatial lookups. It outlines query patterns and UUID management, emphasizing server-side resolution of semantic names from LLMs.

**[001-scale-database-schema.md](001-scale-database-schema.md)**
*   **Summary**: Defines the comprehensive database schema for tracking player progress across experiences. It introduces three core SQLAlchemy models: `PlayerProfile` (for global player data and cross-experience stats), `ExperienceProgress` (for per-experience progress, containing flexible `JSONB` state data), and `PlayerProgressEvent` (an immutable, append-only event log for detailed analytics and audit trails). The document includes full SQL migration scripts for these tables and discusses JSONB indexing strategies.

**[002-scale-player-progress.md](002-scale-player-progress.md)**
*   **Summary**: Outlines the hybrid storage architecture combining **PostgreSQL** (for durable cold storage of history, analytics, and permanent progress) and **Redis** (for sub-millisecond hot state of active sessions and real-time data). It details Redis key patterns for various cached player data (sessions, inventory, visited waypoints) and demonstrates cache operations for dual-write updates and read-through caching. The document also provides storage capacity planning estimates, showing scalability to millions of players.

**[003-scale-kb-agent-implementation.md](003-scale-kb-agent-implementation.md)**
*   **Summary**: This proposal outlines the architecture for embedding an intelligent LLM agent directly within the KB service itself. The agent (implemented as `KBIntelligentAgent`) will interpret markdown files from the KB as executable rules, instructions, and knowledge. It supports modes for `decision-making`, `workflow execution`, and `rule validation`. A key architectural decision is **direct LLM integration** (importing `MultiProviderChatService` directly) to avoid inter-service latency, enhancing performance and reliability.

**[004-scale-chat-and-kb-architecture.md](004-scale-chat-and-kb-architecture.md)**
*   **Summary**: Provides a comprehensive guide to the **fully operational** intelligent chat routing system and KB integration. It explains the core innovation of a **single LLM call router** (`app/services/chat/intelligent_router.py`) that uses `tool_choice="auto"` to determine the optimal path for user queries (direct response, simple chat, KB+Tools, Multi-Agent). It details KB tools exposed to the LLM, the Git-only storage model, and the hot-loaded MCP agents for performance.
