# Architectural Decision Records (ADRs)

This directory houses Architectural Decision Records (ADRs), which are documents that capture significant architectural decisions, their context, the options considered, the rationale behind the chosen solution, and its consequences. ADRs serve as a historical log of design choices, providing clarity and context for future development.

---

## Architectural Decision Records

**[001-supabase-first-authentication.md](001-supabase-first-authentication.md)**
*   **Summary**: This ADR documents the decision to use Supabase exclusively for authentication when `AUTH_BACKEND=supabase` is configured, removing all PostgreSQL fallback logic. This simplifies the architecture by establishing Supabase as the single source of truth for authentication data, improving clarity, performance, and consistency, though it requires a migration of existing API keys.

**[002-microservice-automation.md](002-microservice-automation.md)**
*   **Summary**: This ADR details the decision to automate microservice creation using a `create-new-service.sh` script for scaffolding and a service registry pattern for centralized configuration. The goal is to reduce friction, ensure consistency, prevent manual configuration errors, and capture best practices in service creation, cutting creation time from hours to minutes.

**[003-postgresql-simplicity.md](003-postgresql-simplicity.md)**
*   **Summary**: This ADR documents the decision to use `asyncpg` directly for simple PostgreSQL queries, foregoing the SQLAlchemy ORM for such cases. This approach aims to improve simplicity, performance, and maintainability by removing ORM overhead and avoiding compatibility issues, while retaining SQLAlchemy for more complex operations involving intricate relationships or migration management.

**[004-enabling-personas-with-tdd.md](004-enabling-personas-with-tdd.md)**
*   **Summary**: This ADR outlines the Test-Driven Development (TDD) approach for enabling personas (AI personality profiles) in the Gaia chat service. The decision is to initially expose persona management directly via chat service endpoints (`/personas/*`), encapsulating persona logic within the chat service. The document details a phased TDD implementation plan covering API, chat integration, and caching.

**[008-user-deletion-cascade-cleanup.md](008-user-deletion-cascade-cleanup.md)**
*   **Summary**: This ADR addresses a critical data cleanup bug where deleting users from Supabase left orphaned data in the PostgreSQL database. The decision is to implement cascade deletion for user accounts using database foreign key constraints (`ON DELETE CASCADE`) to automatically remove associated conversations and user preferences. The database-level CASCADE is implemented, but service-level cleanup is still pending.

**[009-kb-ephemeral-storage.md](009-kb-ephemeral-storage.md)**
*   **Summary**: This ADR documents the decision to use ephemeral container storage for the KB (Knowledge Base) repository, cloning it from GitHub on container startup rather than using a persistent Docker volume. The primary rationale is to achieve production parity, ensuring a clean state on every restart and simplifying debugging, given the KB's small size (828KB, ~1s clone) and infrequent changes.

**[010-api-key-to-jwt-exchange.md](010-api-key-to-jwt-exchange.md)**
*   **Summary**: This ADR proposes implementing an API Key to JWT Exchange Pattern to resolve systematic authentication inconsistencies. API keys will be validated only at the edge (gateway/auth service) and immediately exchanged for short-lived JWTs. All internal services will then exclusively handle JWTs with standardized claims, simplifying user ID extraction and enhancing security and performance.