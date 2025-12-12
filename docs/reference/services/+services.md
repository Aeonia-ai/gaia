# Services Reference

This section provides in-depth documentation for each of the Gaia Platform's microservices, covering their architecture, implementation, API specifications, scaling strategies, and troubleshooting guides.

---

## Directories

- [[developer/+developer.md]]: Developer-focused documentation.
- [[guides/+guides.md]]: Guides for using the services.
- [[reference/+reference.md]]: General service reference.
- [[troubleshooting/+troubleshooting.md]]: Troubleshooting guides for the services.

## Files

**[+kb.md](+kb.md)**
*   **Summary**: This document serves as the main index for the Knowledge Base (KB) system documentation. It organizes information into subdirectories (guides, developer, reference, troubleshooting) and lists key files within each, providing a human-readable overview of the KB's various aspects, including quick setup, storage configuration, Git synchronization, API reference, and deployment. It also outlines the status of different storage modes (Git, Database, Hybrid) and multi-user RBAC.

**[+web-ui.md](+web-ui.md)**
*   **Summary**: This document serves as the main index for the FastHTML web frontend documentation. It lists key files related to the web UI architecture, HTMX debugging, authentication layout isolation, web service standardization, testing strategy, CSS patterns, async patterns, and layout requirements, providing a central point for understanding the web UI's design and implementation.

**[adding-new-microservice.md](adding-new-microservice.md)**
*   **Summary**: This guide details the simplified process for adding new microservices to the Gaia Platform, leveraging automated tooling (`create-new-service.sh`) to generate boilerplate code and deployment configurations. It outlines the manual steps still required (updating `service_registry.py` and `app/gateway/main.py`), provides deployment instructions for Fly.io, offers service development tips, and discusses common issues and their solutions.

**[auth-layout-isolation.md](auth-layout-isolation.md)**
*   **Summary**: This document emphasizes the critical rule of never mixing authentication content with layout elements in the web UI, particularly for email verification or password reset pages. It presents "RIGHT" vs. "WRONG" examples, standard auth layout patterns (email verification, password reset, error states), HTMX target rules for complete form replacement, and a layout validation checklist. The document stresses the importance of `auth_page_replacement()` for major state changes and includes code review and testing requirements to prevent recurring layout bugs.

**[css-style-guide.md](css-style-guide.md)**
*   **Summary**: This guide documents the CSS class system and layout patterns used in the web UI to prevent UI breakages. It outlines critical rules for main container layout and loading indicator placement, provides standard layout patterns for pages, forms, and cards, defines a consistent color palette and spacing scale, and highlights common mistakes to avoid. The document also includes requirements for testing UI changes (layout tests, responsive behavior, HTMX interactions), a mobile-first approach, and visual regression testing.

**[fasthtml-ft-async-guide.md](fasthtml-ft-async-guide.md)**
*   **Summary**: This critical guide addresses the `TypeError: object FT can't be used in 'await' expression` error in FastHTML, which occurs when an async function attempts to return a FastHTML FT object. It establishes clear rules: use synchronous handlers for returning FT objects (UI components) and asynchronous handlers for JSON data or async API calls. The guide provides patterns for handling async operations within synchronous handlers, a prevention checklist, and quick fix instructions, emphasizing the "Golden Rule": if it returns HTML components, it cannot be async.

**[fasthtml-web-service.md](fasthtml-web-service.md)**
*   **Summary**: This document provides an overview of the FastHTML Web Service, detailing its architecture (FastHTML frontend, Gateway, Auth Service, Chat Service, NATS, Asset Service), key features (server-side rendering, HTMX, real-time chat, unified auth), and development commands. It outlines the directory structure, API integration patterns via the Gateway, conversation management, real-time integration, session management, and comprehensive testing. The document also covers deployment integration, design system integration, and benefits like service reuse and visual parity.

**[htmx-fasthtml-debugging-guide.md](htmx-fasthtml-debugging-guide.md)**
*   **Summary**: This guide documents critical lessons learned while debugging HTMX issues in the Gaia FastHTML web interface. It addresses key problems and solutions related to loading indicator placement, CSS for HTMX indicators (using `display` instead of `opacity`), HTMX swap types (`outerHTML` for full replacement), route response structure (including target ID), and a recurring auth form replacement bug. The guide also provides debugging techniques (logging, server-side checks), a checklist for common issues, and FastHTML best practices.

**[kb-agent-overview.md](kb-agent-overview.md)**
*   **Summary**: This document provides an overview of the KB Agent, an embedded LLM agent within the Knowledge Base service that transforms it into an intelligent knowledge interpreter. It details key capabilities such as knowledge interpretation, workflow execution, rule validation, decision-making, and information synthesis, highlighting its architecture (direct LLM integration, universal knowledge loading, intelligent model selection, multi-mode operation) and quick start examples for basic interpretation, workflow execution, and action validation. It also covers use cases, integration points, and performance characteristics.

**[kb-multi-instance-architecture-proposal.md](kb-multi-instance-architecture-proposal.md)**
*   **Summary**: This proposal outlines a multi-KB instance pattern to address the four distinct capabilities identified within the current monolithic KB service: Game Logic & Rules, Documentation & Knowledge, AI Context & Memory, and Asset Metadata. It proposes specialized KB instances for each, with tailored performance, scaling, and content strategies. The document analyzes current architectural gaps, details service communication patterns and chat integration updates, and outlines an implementation strategy and questions for team discussion, recommending documentation of existing capabilities first.

**[layout-constraints.md](layout-constraints.md)**
*   **Summary**: This document defines critical, mandatory layout constraints for the web UI, which must never be violated to prevent UI breakages. It specifies rules for the main container, full-width content, sidebar dimensions, and page-specific rules (e.g., login pages must not contain chat elements). The document also outlines a layout protection checklist (integrity tests, visual regression, nested containers, HTMX navigation) and discusses common layout bugs and their fixes (e.g., "Mobile Width on Desktop").

**[llm-service.md](llm-service.md)**
*   **Summary**: This document provides an overview of the LLM module (`app/services/llm/`), an internal, provider-agnostic library used by the Chat service for interacting with multiple Large Language Model providers (Claude, OpenAI, etc.). It describes the architecture's core components (base abstractions, provider registry, provider implementations, multi-provider selection, Chat Service Helper), emphasizing that it is not a microservice but a shared library. It details its usage, configuration via environment variables, and integration points within the Chat service.

**[microservice-quick-reference.md](microservice-quick-reference.md)**
*   **Summary**: This document provides a quick reference for microservices in the Gaia Platform, detailing a streamlined process for creating new services using `create-new-service.sh`. It outlines automated and manual setup steps (updating service registry and gateway routes), lists automatically created files, and offers common service patterns (basic endpoint, gateway forward, service-to-service call). The document also includes troubleshooting tips, useful commands for local testing and deployment, and a service checklist.

**[microservices-communication-solution.md](microservices-communication-solution.md)**
*   **Summary**: This document explains the implementation of a service discovery pattern to solve communication issues between microservices, eliminating the need for manual gateway updates. It illustrates the "before" (manual, error-prone) and "after" (automatic, seamless) scenarios, detailing how services expose their routes via enhanced health endpoints and how the gateway dynamically discovers and routes requests. The document highlights the benefits for developers and operations, with a real example of intelligent chat routing.

**[microservices-scaling.md](microservices-scaling.md)**
*   **Summary**: This document outlines the Gaia Platform's microservices scaling architecture, highlighting its advantages over a monolithic LLM Platform. It details independent service scaling, workload-specific scaling, and technology-specific optimization for services like Chat, Auth, and Asset. The document covers real-world scaling scenarios, performance scaling multipliers (database, caching), cost efficiency gains, reliability/fault isolation, and performance metrics comparison. It also discusses future scaling possibilities and current scaling configuration for Fly.io.

**[persona-system-guide.md](persona-system-guide.md)**
*   **Summary**: This guide outlines the Gaia persona system, providing customizable AI personalities that shape user interactions. It details the system's components, including a PostgreSQL database layer (`personas` and `user_persona_preferences` tables), a `PostgresPersonaService` with Redis caching, a `PromptManager` for chat integration, and REST API endpoints. The guide covers how system prompts are assembled (using a `{tools_section}` placeholder), provides examples of personas (Mu, Sage, Spark), and discusses use cases, performance, and future enhancements.

**[pgvector-migration-plan.md](pgvector-migration-plan.md)**
*   **Summary**: This document outlines a plan to migrate the semantic search backend from ChromaDB to pgvector, recommending the switch for architectural simplicity, improved performance, and transactional consistency. It details a seven-phase plan covering enabling the pgvector extension, adding an embeddings column via migration, updating semantic search code to use pgvector, updating indexing logic for incremental updates, removing ChromaDB dependencies, testing, and deployment. The plan emphasizes persistent storage and significantly faster indexing.

**[README.md](README.md)**
*   **Summary**: This is the main documentation for the Knowledge Base (KB) service, serving as an index to its various aspects. It organizes documentation into User Guides, Developer Documentation, API Reference, and Troubleshooting, listing key files within each category. It provides a quick start guide for local development, Git integration, and production deployment, and offers an overview of the KB's architecture and statistical data on its documentation coverage.

**[scaling-architecture.md](scaling-architecture.md)**
*   **Summary**: This document outlines the Gaia Platform's microservices scaling architecture, emphasizing a "cluster-per-game" deployment strategy for MMOIRL. It compares this to a monolithic approach, detailing independent service scaling, workload-specific scaling, and technology-specific optimization. The document covers real-world scaling scenarios, performance scaling multipliers (database, caching), cost efficiency gains, reliability/fault isolation, and performance metrics. It also discusses future scaling possibilities and current scaling configuration for Fly.io, along with monitoring, load testing, and deployment strategies.

**[semantic-search-guide.md](semantic-search-guide.md)**
*   **Summary**: This guide introduces the KB semantic search feature, an AI-powered natural language search using pgvector and sentence-transformers for conceptual matching and persistent, incremental indexing. It highlights features like natural language queries, namespace isolation, persistent storage, and high performance. The document details configuration via environment variables and API endpoints for semantic search, reindexing, and stats. It also explains the pgvector integration, indexing and search processes, performance considerations, best practices, troubleshooting, and future enhancements.

**[web-service-standardization-spec.md](web-service-standardization-spec.md)**
*   **Summary**: This specification outlines improvements for the GAIA web service to enhance accessibility, testability, and user experience, based on integration test analysis. It addresses issues like inconsistent error display, missing loading states, test brittleness, and mixed response patterns. The document details standardization requirements for semantic HTML, loading state management, consistent error handling, testing attributes (with standard test IDs), and SSE response standardization. It provides an implementation plan, success metrics, security considerations, and a migration guide.

**[web-testing-strategy-post-standardization.md](web-testing-strategy-post-standardization.md)**
*   **Summary**: This document outlines how web testing will be improved and simplified after implementing the Web Service Standardization Specification. It compares "before" and "after" scenarios for element selection, form interaction, loading states, and error detection, emphasizing the shift from brittle CSS/text-based selectors to robust, semantic testing patterns using `data-testid` and ARIA attributes. The document introduces new testing patterns (Page Object Model, accessibility-first, SSE testing, progressive enhancement) and discusses test organization, best practices, and a migration strategy.
