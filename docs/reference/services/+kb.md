# kb

Knowledge Base system documentation.

## Subdirectories

- `guides/` - User guides and configuration
- `developer/` - Technical implementation docs
- `reference/` - API and technical reference
- `troubleshooting/` - Deployment and problem-solving

## Files

- `README.md` - Human-readable overview

## Index

### guides/
- `kb-quick-setup.md` - Fast setup guide
- `kb-storage-configuration.md` - Storage backend configuration
- `kb-git-sync-guide.md` - Git synchronization setup
- `kb-integration-implementation.md` - Service integration
- `kb-editing-strategy.md` - Content management practices
- `multi-user-kb-guide.md` - Team workspaces and RBAC

### developer/
- `kb-architecture-guide.md` - Storage architecture design
- `kb-feature-discovery.md` - Feature discovery for agents
- `kb-container-storage-migration.md` - Container storage patterns
- `kb-git-clone-learnings.md` - Git operations details
- `kb-git-sync-learnings.md` - Production sync learnings
- `kb-web-ui-integration.md` - Web UI implementation
- `kb-wiki-interface-design.md` - Wiki interface specs

### reference/
- `kb-http-api-reference.md` - HTTP API documentation

### troubleshooting/
- `kb-deployment-checklist.md` - Deployment verification
- `kb-remote-deployment-auth.md` - Production auth setup
- `kb-git-secrets-setup.md` - Git credentials config
- `kb-remote-hosting-strategy.md` - Cloud deployment

## Status

- **Default**: Git storage mode
- **Available**: Database storage (`KB_STORAGE_MODE=database`)
- **Available**: Hybrid storage (`KB_STORAGE_MODE=hybrid`)
- **Available**: Multi-user RBAC (`KB_MULTI_USER_ENABLED=true`)

## Parent
[../+docs.md](../+docs.md)