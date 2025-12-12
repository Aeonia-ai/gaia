# Troubleshooting Guides for KB Services

This section provides guides and checklists for troubleshooting common issues encountered with the Knowledge Base (KB) service, covering deployment, Git synchronization, authentication, and search functionality.

---

## KB Troubleshooting Documents

**[kb-deployment-checklist.md](kb-deployment-checklist.md)**
*   **Summary**: This document provides a comprehensive checklist for deploying the Knowledge Base (KB) service to staging and production environments. It covers pre-deployment requirements (GitHub PAT, configuration files), step-by-step deployment instructions (creating persistent volumes, setting secrets, deploying the service, triggering initial clone), and post-deployment verification (health checks, functional tests, log monitoring). It also includes troubleshooting tips, environment-specific configurations, security considerations, and monitoring/maintenance advice.

**[kb-git-secrets-setup.md](kb-git-secrets-setup.md)**
*   **Summary**: This document addresses an issue where the KB service failed to clone its Git repository due to missing secrets in the Fly.io deployment. It identifies the root cause (secrets not set in Fly.io), provides solution commands to set the `KB_GIT_REPO_URL` and `KB_GIT_AUTH_TOKEN` secrets and redeploy, and outlines the expected outcome.

**[kb-remote-deployment-auth.md](kb-remote-deployment-auth.md)**
*   **Summary**: This guide explains how to handle Git authentication for KB sync in remote deployments using Personal Access Tokens (PATs) for GitHub, GitLab, and Bitbucket. It details PAT creation, configuration for Fly.io, AWS/Docker, and security best practices (minimal scope, rotation, environment isolation, secret detection prevention). Alternative authentication methods like GitHub App Authentication, Deploy Keys, and Machine User Accounts are also discussed. The document emphasizes security, troubleshooting, and token management automation.

**[kb-remote-hosting-strategy.md](kb-remote-hosting-strategy.md)**
*   **Summary**: This document outlines a strategy for hosting Knowledge Base content in production environments, recommending a Git-based approach with caching. It details primary storage using a private Git repository, deployment configuration via environment variables and Docker, a sync script for cloning/updating the KB, and performance optimization through Redis caching. It also covers platform-specific configurations (Fly.io, AWS ECS/Fargate), security considerations, and an update workflow.

**[kb-search-troubleshooting.md](kb-search-troubleshooting.md)**
*   **Summary**: This guide provides a quick reference for resolving common Knowledge Base (KB) search issues. It recommends using a simple configuration (Git storage, multi-user disabled) as a primary fix. The document details common problems like "relation kb_search_index does not exist" and "search returns 0 results," providing specific causes, diagnosis steps, and solutions. It also covers Redis cache errors, environment variable issues, a testing chain, architecture overview, and logs to check for debugging.
