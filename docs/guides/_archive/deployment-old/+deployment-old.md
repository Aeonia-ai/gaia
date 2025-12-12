# Old Deployment Guides and Strategies

This directory contains archived documentation related to previous deployment strategies and best practices for the Gaia Platform. While some concepts may still be relevant, these guides represent older approaches and configurations that have likely been superseded by more current methods.

---

## Archived Deployment Documents

**[database-migration-strategy.md](database-migration-strategy.md)**
*   **Summary**: This document outlines a proposed, now potentially superseded, strategy for managing database schema synchronization. It addresses issues like the lack of migration tracking and inconsistent manual application by proposing a `schema_migrations` table, timestamp-based naming conventions, and a Python migration script (`scripts/migrate.py`). It covers the structure for `up` and `down` migrations, seed data management, and CI/CD integration.

**[deployment-best-practices.md](deployment-best-practices.md)**
*   **Summary**: Details archived deployment best practices focused on achieving local-remote parity across development, staging, and production environments. Key principles include configuration consistency, secrets management (using `.env` locally and `sync-secrets.sh` remotely), and inter-service communication via Docker/Fly.io internal DNS. The document outlines a deployment workflow involving initial setup, service deployment, and verification using scripts like `deploy-service.sh` and `test-parity.sh`.

**[deployment-pipeline.md](deployment-pipeline.md)**
*   **Summary**: Describes a previous iteration of the complete development-to-production deployment pipeline for the Gaia Platform. It defines four environments (Local, Dev, Staging, Production) hosted on Docker and Fly.io, detailing their purpose, infrastructure, database, and NATS configurations. The document outlines the deployment workflow for feature development, testing, and release, including environment-specific configurations and testing strategies.

**[deployment-runbook.md](deployment-runbook.md)**
*   **Summary**: A step-by-step runbook for deploying and troubleshooting the Gaia Platform. It includes a pre-deployment checklist covering environment, code quality, and infrastructure validation. The document provides detailed procedures for local and remote environment setup, health checks, and troubleshooting common issues related to authentication, service communication, and database connections. It also outlines emergency recovery procedures and monitoring guidelines.

**[deployment-validation-checklist.md](deployment-validation-checklist.md)**
*   **Summary**: Provides a comprehensive checklist for validating deployments, primarily focusing on secret management and environment consistency. It covers pre-deployment checks for `secrets` synchronization, post-deployment verification of health endpoints, authentication flow testing, and common issues like "Invalid API key" errors. The document also suggests prevention strategies like automated secret synchronization and enhanced deployment scripts.

**[production-deployment.md](production-deployment.md)**
*   **Summary**: This guide details an older strategy for deploying the Gaia Platform to production using a "cluster-per-game" architecture on Fly.io. It covers prerequisites, database setup for individual games, creating game-specific configurations, manual and scripted deployment steps, and post-deployment verification for health and core functionality. The document also touches upon scaling, rollback procedures, and security considerations relevant to that specific deployment model.

**[smart-scripts-deployment.md](smart-scripts-deployment.md)**
*   **Summary**: Showcases a collection of "smart scripts" designed to streamline environment-aware testing, deployment, and management. This includes `curl_wrapper.sh` for standardized HTTP testing, `test.sh` for environment-aware API testing with smart failure handling, `deploy.sh` for intelligent deployments, and `manage.sh` for comprehensive platform management. The document also provides critical lessons learned for handling long deployments and cached Docker images in Claude Code.

**[supabase-configuration.md](supabase-configuration.md)**
*   **Summary**: Explains the configuration of Supabase Site URL and Redirect URLs for a single Supabase project (`gaia-platform-v2`) to support multiple deployment environments (Local, Dev, Staging, Production). This strategy was employed due to free-tier project limitations and details how each environment's URLs are configured within the Supabase dashboard and the application's environment variables.

**[supabase-multi-environment-setup.md](supabase-multi-environment-setup.md)**
*   **Summary**: This guide outlines a strategy for setting up **separate Supabase projects** for each environment (dev, staging, production) to ensure better isolation. It details the specific project names (`gaia-dev`, `gaia-staging`, `gaia-production`) and their respective URL configurations for Site URL and Redirect URLs. The document covers updating local `.env` and cloud secrets with the correct project-specific credentials.

**[supabase-single-project-setup.md](supabase-single-project-setup.md)**
*   **Summary**: Explains a strategy for configuring a single Supabase project (`gaia-platform-v2`) to serve **all** deployment environments (local, dev, staging, production). This approach was adopted to circumvent free-tier limitations. It details how to set up Site URLs and Redirect URLs in the Supabase dashboard to accommodate all environments, along with the necessary environment variable configurations.