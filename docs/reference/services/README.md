# Knowledge Base (KB) Documentation

The Knowledge Base service provides Git-synchronized document storage with vector search capabilities for AI agents.

## 📚 Documentation Structure

### [User Guides](guides/)
Start here if you want to use the KB service
- [Main Guide](guides/README.md) - Comprehensive overview
- [Quick Setup](guides/kb-quick-setup.md) - 5-minute setup
- [Git Sync Guide](guides/kb-git-sync-guide.md) - Configure Git synchronization
- [Multi-User Guide](guides/multi-user-kb-guide.md) - Teams and workspaces
- [Editing Strategy](guides/kb-editing-strategy.md) - Content management workflow
- [Integration Guide](guides/kb-integration-implementation.md) - HTTP-based integration

### [Developer Documentation](developer/)
Implementation details and technical decisions
- [Git Sync Learnings](developer/kb-git-sync-learnings.md) - Deferred init patterns
- [Git Clone Learnings](developer/kb-git-clone-learnings.md) - Volume sizing solutions
- [Storage Architecture](developer/kb-storage-architecture-analysis.md) - Git vs PostgreSQL analysis
- [Multi-User Architecture](developer/multi-user-kb-architecture.md) - Technical design
- [Container Storage](developer/kb-container-storage-migration.md) - Container patterns
- [UI Design](developer/kb-wiki-interface-design.md) - FastHTML implementation

### [API Reference](reference/)
Technical specifications and APIs
- [HTTP API Reference](reference/kb-http-api-reference.md) - REST endpoints
- [RBAC System Guide](reference/rbac-system-guide.md) - Role-based access control
- [RBAC Examples](reference/rbac-role-examples.md) - Practical RBAC patterns
- [User Account Integration](reference/user-account-rbac-integration.md) - Authentication

### [Troubleshooting](troubleshooting/)
Deployment and operational guides
- [Deployment Checklist](troubleshooting/kb-deployment-checklist.md) - Step-by-step deployment
- [Git Secrets Setup](troubleshooting/kb-git-secrets-setup.md) - Fix missing secrets
- [Remote Deployment Auth](troubleshooting/kb-remote-deployment-auth.md) - Production Git auth
- [Remote Hosting Strategy](troubleshooting/kb-remote-hosting-strategy.md) - Production hosting

## 🚀 Quick Start

1. **Local Development**: Start with [Quick Setup](guides/kb-quick-setup.md)
2. **Git Integration**: Follow [Git Sync Guide](guides/kb-git-sync-guide.md)
3. **Production**: Use [Deployment Checklist](troubleshooting/kb-deployment-checklist.md)

## 🏗️ Architecture

The KB service provides:
- Git repository synchronization (Obsidian, GitHub, etc.)
- Vector search capabilities
- Multi-user workspaces
- RBAC permissions
- HTTP API for integrations

## 📊 Documentation Stats

- **User Guides**: 6 documents
- **Developer Docs**: 9 documents  
- **Reference**: 4 documents
- **Troubleshooting**: 4 documents
- **Total**: 23 documents (organized from 24)