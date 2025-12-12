# KB Service Guides

This section provides practical guides and how-to documentation for setting up, configuring, and working with the Gaia Platform's Knowledge Base (KB) service, including multi-user features, Git synchronization, and editing strategies.

---

## KB Guides

**[kb-editing-strategy.md](kb-editing-strategy.md)**
*   **Summary**: This document outlines a strategy for safely editing Knowledge Base content, recommending direct Git integration for full version control and audit trails. It details an editing workflow for single and batch file edits, content validation (pre-commit checks), Git integration (configuration, commit strategy), conflict resolution (auto-merge, manual), audit logging, and security measures (access control, path validation). It also outlines implementation phases and considers a CMS-style alternative for user-friendly editing.

**[kb-git-sync-guide.md](kb-git-sync-guide.md)**
*   **Summary**: This guide covers the Git synchronization functionality for the Knowledge Base (KB) service, enabling automatic sync between a local Git repository and the KB service. It details quick setup steps, configuration reference (environment variables, GitHub PAT), and the container-only storage architecture. The guide explains the daily workflow for developers, manual sync commands, different storage modes (Git, Database, Hybrid), API endpoints for sync status and operations, troubleshooting common issues, performance notes, AI agent integration, and security considerations.

**[kb-integration-implementation.md](kb-integration-implementation.md)**
*   **Summary**: This document describes the HTTP-based Knowledge Base (KB) integration with Gaia Platform, enabling KOS capabilities through direct HTTP calls to the KB service. It details the architecture (Gateway, Chat Service, KB Service, KB Volume), key implemented files (KB tools for LLM use, Unified Chat Handler for intelligent routing, KB Service for HTTP endpoints), authentication and request flow, and configuration via Docker Compose and environment variables. Usage examples, testing strategies, performance characteristics, integration benefits, and security models are also covered.

**[kb-quick-setup.md](kb-quick-setup.md)**
*   **Summary**: This document provides a quick setup guide for the Aeonia team to integrate their Obsidian Vault with the KB service using Git synchronization. It details three main steps: adding specific environment variables (`KB_STORAGE_MODE`, `KB_GIT_REPO_URL`, `KB_GIT_AUTH_TOKEN`, `KB_GIT_AUTO_CLONE`) to the `.env` file, starting the service via Docker Compose, and verifying the setup. It also includes instructions for obtaining a GitHub Personal Access Token, troubleshooting common issues like "Git Not Found" and "Volume Mount Error," and outlines a daily workflow for developers.

**[kb-storage-configuration.md](kb-storage-configuration.md)**
*   **Summary**: This guide details how to configure and enable different Knowledge Base (KB) storage backends within the KB service, emphasizing that Git storage is the default, with database and hybrid modes also fully implemented. It provides a "simple configuration" for getting started, outlines Git, Database, and Hybrid storage modes with their respective configurations, use cases, and limitations. The document also covers multi-user support (RBAC) configuration, switching storage modes, performance considerations, and extensive troubleshooting for common issues.

**[multi-user-kb-guide.md](multi-user-kb-guide.md)**
*   **Summary**: This guide details the Gaia Platform's multi-user Knowledge Base (KB) system, covering its architecture, features, and implementation for collaborative knowledge management. It explains user namespaces (personal, teams, workspaces), sharing mechanisms (private, selective, published), and a granular permission model. The document provides an implementation guide with steps to enable multi-user mode and apply database migrations, an API reference for document and sharing operations, best practices for namespace organization and permission management, and troubleshooting tips.
