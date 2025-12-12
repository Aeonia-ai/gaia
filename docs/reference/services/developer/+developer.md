# Developer Reference for KB Services

This section provides in-depth technical documentation for developers working with the Knowledge Base (KB) services, covering architecture, implementation details, operational learnings, and UI integration.

---

## KB Developer Documents

**[kb-architecture-guide.md](kb-architecture-guide.md)**
*   **Summary**: This document provides a comprehensive guide to the KB storage architecture, detailing the current Git-based storage (and its limitations for multi-user scenarios) and outlining future architecture options. It recommends a PostgreSQL + JSONB solution for multi-user support, also discussing MongoDB and a hybrid Git+Database approach. The document covers schema design, a virtual filesystem abstraction, multi-user features (namespaces, permissions, conflict prevention), and outlines the implementation status of various storage modes (Git-only, Database, Hybrid) and RBAC support.

**[kb-container-storage-migration.md](kb-container-storage-migration.md)**
*   **Summary**: This document describes the migration of the KB service from local volume mounts to container-only storage, aimed at achieving true local-remote parity. It explains the "before" (volume mount) and "after" (container-only) states, detailing why the change was made (testing accuracy, simplified deployment) and providing migration steps. The document also outlines the new development workflow, benefits for development/testing/operations, and troubleshooting tips.

**[kb-feature-discovery.md](kb-feature-discovery.md)**
*   **Summary**: This document proposes a `/features` endpoint for the KB service to enable external agents and developers to discover implemented, enabled, and available KB features without needing to read extensive documentation or code. It details the structure of the JSON response (covering storage modes, features like multi-user and caching, API endpoints, and configuration), and provides use cases for external agents and continuing development. It also describes an enhancement to the `/health` endpoint to hint at the features endpoint.

**[kb-git-clone-learnings.md](kb-git-clone-learnings.md)**
*   **Summary**: This document details key learnings from implementing Git repository cloning for the KB service, covering challenges like service timeouts, volume sizing, mount point restrictions, and the unreliability of async background tasks. It highlights solutions such as provisioning larger volumes, cloning to temporary directories, adding manual trigger endpoints for debugging, and ensuring health endpoints report data initialization status. The document also summarizes the final architecture, deployment checklist, and what would be done differently in retrospect.

**[kb-git-sync-learnings.md](kb-git-sync-learnings.md)**
*   **Summary**: This document captures key learnings from implementing Git repository synchronization for the KB service. It covers the use of a deferred initialization pattern to prevent startup timeouts during `git clone`, the implementation of a manual clone trigger endpoint for reliability, and important considerations for volume sizing and container-only storage for local-remote parity. The document also discusses path configuration, authentication token management, deployment automation, health check integration, common issues, and best practices.

**[kb-web-ui-integration.md](kb-web-ui-integration.md)**
*   **Summary**: This document outlines the design for integrating a KB wiki interface into the existing FastHTML web service, allowing users to seamlessly switch between chat and wiki modes. It details navigation integration (main bar, URL structure), page layouts for the wiki home, file browser, wiki page view, edit mode (with live preview and markdown editor features), search results, and a knowledge graph visualization. It also covers CSS styling, JavaScript enhancements for real-time features, integration with chat (cross-references and quick actions), and mobile responsive design.

**[kb-wiki-interface-design.md](kb-wiki-interface-design.md)**
*   **Summary**: This document explains the design principles behind the KB wiki interface, highlighting the natural match between wiki features (links, revision history, collaboration, search, categories) and the existing KB architecture. It details core wiki features like wiki-link navigation, automatic backlinks, and wiki-style URLs. The implementation design covers an enhanced KB schema, a Wiki Parser service, various Wiki UI components (page view, edit mode, special pages, categories), and advanced features like transclusion, templates, smart tables of contents, and wiki graphs.