# Dynamic Experiences

This directory contains the documentation for the "dynamic experiences" feature, a platform for creating and running interactive experiences like AR games, text adventures, and simulations.

## Subdirectories

- [[phase-1-mvp/+phase-1-mvp.md]]: **Phase 1: MVP** - Phase 1 established the foundational architecture for creating interactive experiences. It includes the Unified State Model, a content-driven command system (for both players and admins), natural language NPC interactions with a trust/memory system, and the initial V0.3 streaming API for real-time client integration.
- [[phase-2-scale/+phase-2-scale.md]]: **Phase 2: Scale** - Phase 2 focuses on scaling the platform, detailing robust PostgreSQL-based instance and player progress management, hybrid caching strategies with Redis, and the architecture for embedding intelligent LLM agents within the KB service.
- [[phase-3-future-work/+phase-3-future-work.md]]: **Phase 3: Future Work** - Phase 3 outlines future work, focusing on advanced multi-agent orchestration for complex AI coordination, integration strategies for MCP/FastAPI services, and the long-term vision for dynamic experiences.

## Files

**[000-architectural-philosophies.md](000-architectural-philosophies.md)**
*   **Summary**: This document analyzes four core philosophies underpinning the GAIA "dynamic experiences" feature: "The Intelligent Front Door" (LLM as a router), "Content as Code" (markdown-driven logic), "Imperative & Deterministic Control" (admin toolkit), and "Decoupled State Management" (source of truth). It explains how these philosophies interact to balance flexibility, performance, and user experience.