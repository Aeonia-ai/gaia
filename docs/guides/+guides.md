# Guides

This section contains practical how-to guides, tutorials, and strategies for developing, deploying, and testing the Gaia platform.

## Key Guides

**[TESTING_GUIDE.md](TESTING_GUIDE.md)**
*   **Summary**: The canonical, consolidated testing guide for the GAIA platform. It emphasizes the core philosophy that "Tests Define Truth," details the test organization (unit, integration, e2e), and mandates the use of the `pytest-for-claude.sh` async runner. It also covers writing tests, using fixtures, and provides specific guidance for testing different API versions.

**[deployment-guide.md](deployment-guide.md)**
*   **Summary**: The complete guide for deploying the GAIA platform. It stresses the **critical importance of using `nohup`** for all deployments in Claude Code to avoid the 2-minute timeout. It provides a step-by-step workflow: test locally, deploy to dev, validate, and then deploy to production, with commands for each step.

**[cookbook-creating-experiences-and-commands.md](cookbook-creating-experiences-and-commands.md)**
*   **Summary**: A practical, step-by-step guide for developers and content creators. It explains how to create a new experience by copying an existing one and modifying its `config.json`, and how to add new player commands (markdown-driven) and admin commands (hybrid content-and-code approach).

---

## All Guides

- **[BRANCH_NOTES.md](BRANCH_NOTES.md)**: Details the `feat/auth-spa-improvements` branch, which adds authentication protection and SPA-like navigation to the web UI.
- **[chat-game-testing-guide.md](chat-game-testing-guide.md)**: A comprehensive guide for testing the GAIA markdown command system's integration with the chat service.
- **[claude-code-commands-guide.md](claude-code-commands-guide.md)**: Explains how to use and create custom Claude Code slash commands (`/command-name`) in the `.claude/commands/` directory.
- **[command-reference.md](command-reference.md)**: A critical reference document for ensuring correct command syntax across different tools (Docker, Fly.io, Pytest, etc.).
- **[CRITICAL_TESTING_PRINCIPLE_TESTS_DEFINE_TRUTH.md](CRITICAL_TESTING_PRINCIPLE_TESTS_DEFINE_TRUTH.md)**: Establishes the core testing philosophy that tests define expected truth, and failing tests mean the code—not the test—should be fixed.
- **[database-initialization-guide.md](database-initialization-guide.md)**: Covers the complete database setup process, emphasizing the need to create core auth tables and the required persona tables via `scripts/create_persona_tables.sql`.
- **[database-migration-strategy.md](database-migration-strategy.md)**: A design proposal for a future database migration system using a `schema_migrations` table and timestamp-based naming.
- **[deployment-docs-comparison.md](deployment-docs-comparison.md)**: An analysis of 12 deployment documents, identifying overlaps and contradictions, and recommending consolidation into 4 essential guides.
- **[deployment-reference.md](deployment-reference.md)**: A quick lookup for deployment commands and troubleshooting, emphasizing the use of `nohup` for deployments.
- **[dev-environment-achievement.md](dev-environment-achievement.md)**: Celebrates the dev environment as the "shining exemplar" for deployments, highlighting its clean database architecture and user-associated authentication.
- **[dev-environment-setup.md](dev-environment-setup.md)**: Details the setup for a production-ready dev environment, including database initialization and service configuration.
- **[distributed-systems-debugging.md](distributed-systems-debugging.md)**: Outlines a systematic approach to debugging, prioritizing checking existing tests, using Docker, checking Git history, and simple log analysis.
- **[e2e-test-findings.md](e2e-test-findings.md)**: Identifies the root cause of hanging E2E tests as authentication failures due to hardcoded credentials and recommends using the `TestUserFactory`.
- **[flyio-deployment-config.md](flyio-deployment-config.md)**: Specifies the Fly.io configuration, recommending the modern `fly mpg` commands for managing PostgreSQL databases.
- **[flyio-setup.md](flyio-setup.md)**: A guide to the initial setup of Fly.io, covering CLI installation, authentication, app creation, database and volume setup, and secrets management.
- **[gaia-refactoring-requirements.md](gaia-refactoring-requirements.md)**: Outlines high-level requirements for refactoring the Gaia platform, focusing on a unified API gateway, "progressive complexity" deployment profiles, and improved developer experience.
- **[inter-service-communication.md](inter-service-communication.md)**: A troubleshooting guide for inter-service communication issues, highlighting transparent response compression (e.g., Brotli on Fly.io) as a common cause of "Invalid JSON response" errors.
- **[mcp-agent-hot-loading.md](mcp-agent-hot-loading.md)**: Describes the "hot loading" implementation for `mcp-agent`, which reduces response times by using a singleton `MCPApp` instance initialized at service startup.
- **[mobile-testing-guide.md](mobile-testing-guide.md)**: Documents methods for testing the mobile-responsive features of the Gaia FastHTML web interface, including browser developer tools, HTML test files, and simulators.
- **[optimization-guide.md](optimization-guide.md)**: Outlines performance optimization opportunities, prioritizing quick wins like database indexing, response compression, and connection pool enhancements.
- **[playwright-eventsource-issue.md](playwright-eventsource-issue.md)**: Documents a known Playwright limitation where EventSource (SSE) does not send cookies, causing authentication failures in E2E tests, and recommends testing chat features at the integration level instead.
- **[PROPOSED-CONSOLIDATION.md](PROPOSED-CONSOLIDATION.md)**: Proposes a plan to consolidate 12 redundant deployment documents into 4 essential guides to create a single source of truth and reduce maintenance.
- **[README.md](README.md)**: The main README for the `docs/guides` directory.
- **[redis-integration.md](redis-integration.md)**: A comprehensive guide to the Redis caching system used for authentication, persona data, and rate limiting, which provides a 97% performance improvement on some queries.
- **[remote-testing-strategy.md](remote-testing-strategy.md)**: Proposes a strategy for testing against remote deployments (dev, staging, prod) using environment-specific configurations and categorized tests.
- **[security-testing-strategy.md](security-testing-strategy.md)**: A design document for a security testing strategy focusing on OWASP Top 10 vulnerabilities, proposing tests for SQL injection, XSS, and authorization boundaries.
- **[sse-streaming-gotchas.md](sse-streaming-gotchas.md)**: Highlights a critical "gotcha" for SSE streaming: operations must be performed *before* yielding the `[DONE]` signal, as the browser will close the connection immediately upon receipt.
- **[streaming-chunk-boundary-test-strategy.md](streaming-chunk-boundary-test-strategy.md)**: A design document for a testing strategy for SSE streaming chunk boundaries, proposing a mock LLM provider to simulate various chunking scenarios.
- **[supabase-setup.md](supabase-setup.md)**: Details the setup of a single Supabase project to support multiple environments, including configuration of redirect URLs, email templates, and security settings.
- **[TEST_CONSOLIDATION_PLAN.md](TEST_CONSOLIDATION_PLAN.md)**: Outlines a plan to consolidate all testing into the automated pytest suite, deprecating standalone test scripts.
- **[TEST_INFRASTRUCTURE.md](TEST_INFRASTRUCTURE.md)**: A technical reference for the test infrastructure, detailing the `pytest-for-claude.sh` async runner and Docker test environment.
- **[test-execution-strategy.md](test-execution-strategy.md)**: Outlines the optimal test execution strategy: running unit and API integration tests in parallel, but browser-based E2E tests sequentially (`-n 1`) to avoid resource exhaustion.
- **[test-improvement-summary.md](test-improvement-summary.md)**: Summarizes the successful integration test suite improvements, which resulted in a pass rate increase from 72% to 98.9% by implementing a shared test user and cleaning up the test suite.
- **[troubleshooting-flyio-dns.md](troubleshooting-flyio-dns.md)**: A guide for troubleshooting Fly.io's unreliable internal `.internal` DNS, recommending the use of public URLs for service-to-service communication.

## Indexes
- [[+_debugging-guides.md]]: Index of debugging guides.
- [[+deployment.md]]: Index of deployment guides.
- [[+development.md]]: Index of development guides.
- [[+testing.md]]: Index of testing guides.
- [[+troubleshooting.md]]: Index of troubleshooting guides.
- [[_archive/+_archive.md]]: Contains archived versions of guides and documentation.
