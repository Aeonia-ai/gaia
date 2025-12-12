# Service Reference Documentation

This section provides general technical reference documentation for the Gaia Platform's microservices, including API specifications, RBAC system details, and user account integration.

---

## Service Reference Documents

**[kb-http-api-reference.md](kb-http-api-reference.md)**
*   **Summary**: This document provides an HTTP API reference for the KB Service, detailing various endpoints like `/search`, `/read`, `/list`, `/context`, `/synthesize`, and `/threads`. Each endpoint's request/response format is specified, along with its usage in KB Tools. It also covers error handling, authentication, KB Tools integration flow (LLM calls KB tools which make HTTP requests), testing, and service architecture, emphasizing separation of concerns and scalability.

**[rbac-role-examples.md](rbac-role-examples.md)**
*   **Summary**: This document showcases the flexibility of the RBAC system by providing various examples of role definitions for the Gaia Platform. It categorizes roles into industry-specific (healthcare, finance, gaming), time-based/temporary, hierarchical/inherited, feature-based, cross-functional, dynamic context-based, composite, and AI agent roles. Each example includes a set of permissions for different resource types (KB, API, Asset, Chat) and actions (read, write, admin, access, create). The document also covers implementation examples and best practices for custom roles.

**[rbac-system-guide.md](rbac-system-guide.md)**
*   **Summary**: This guide provides a comprehensive overview of the Gaia Platform's Role-Based Access Control (RBAC) system, outlining its core concepts (resources, actions, roles, contexts) and architecture (RBAC Manager, Redis Cache, PostgreSQL Database). It details the database schema for roles and permissions, implementation specifics (Python RBAC Manager, FastAPI integration), and current deployment status (implemented in code but not enabled by default). Usage examples cover custom role creation, team-based access, temporary access, and resource sharing.

**[user-account-rbac-integration.md](user-account-rbac-integration.md)**
*   **Summary**: This document explains the integration of user accounts with the RBAC system in the multi-user KB system. It covers user authentication sources (JWT, user-associated API keys, global API keys), user account storage in the `users` table, and the role assignment process (automatic for new users, manual for admins). The document details the permission check flow, how user context influences KB operations (user namespaces, team/workspace access), and provides API integration examples for FastAPI endpoints and sharing functionalities. It also outlines default role hierarchy and testing examples.
