# Reference

This section provides technical reference material, including API documentation, service specifics, and in-depth details on security policies.

## Directories

- [[api/+api.md]]: Comprehensive API documentation for all Gaia Platform APIs.
- [[chat/+chat.md]]: Provides comprehensive documentation for the GAIA Chat Service, detailing its architecture, implementation, intelligent routing, persistence mechanisms, and integration with personas and VR/AR directives.
- [[database/+database.md]]: Provides comprehensive documentation for the Gaia Platform's database architecture, implementation, portability, and lessons learned from its development.
- [[gateway/+gateway.md]]: Provides comprehensive documentation for the Gaia Platform's Gateway service, focusing on its authentication proxying patterns and critical HTTP protocol compliance.
- [[modules/+modules.md]]: Provides documentation for reusable modules within the Gaia Platform, covering instrumentation, prompt management, and tool provisioning.
- [[patterns/+patterns.md]]: Architectural patterns.
- [[services/+services.md]]: In-depth documentation for each service.

## Files

**[security.md](security.md)**
*   **Summary**: This document provides a consolidated overview of the Gaia Platform's authentication and security mechanisms. It covers primary authentication methods (Supabase JWT, API Key, Service-to-Service mTLS+JWT), security best practices (credential management, API key/session security), and mTLS certificate management (architecture, generation, rotation). The document also includes troubleshooting steps for common authentication issues and debugging guidance.

**[shared-modules.md](shared-modules.md)**
*   **Summary**: This document provides an overview of the shared modules (`app/shared/`) used across all Gaia microservices, categorizing them into Critical Modules (Authentication & Security, Database, Service Infrastructure, AI/LLM Support, Monitoring & Logging, Access Control). It details the status of each module (Active, Legacy, Deprecated, Unknown), highlights key implementation details (database compatibility, RBAC evolution, service discovery), and provides usage examples for importing various functionalities.

**[unified-state-model-deep-dive.md](unified-state-model-deep-dive.md)**
*   **Summary**: This document offers a deep architectural dive into the Gaia Platform's dual state models (`shared` and `isolated`), which support different player experiences from a single codebase. It introduces the Content Entity System (Blueprints, Templates, Instances), details the core philosophy of "Players as Views," and visually explains the data flow for both models. The document also provides critical debugging guidance for common issues related to the local Docker environment and content loading, and refines concepts for rich descriptors in templates and quests as instantiable classes for personalized, replayable storylines.
