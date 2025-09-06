# 🟡 Future Features & Roadmap

📍 **Location:** [Home](../README.md) → Future

## 🔮 What's Coming

These features are planned, in development, or exist in feature branches.

### 🚧 In Development (Branches)

#### KB Integration (feature/kb-integration branch)
- **Knowledge Base Service** - Git repository sync with Obsidian vaults
- **RBAC System** - Role-based access control for KB and platform resources  
- **Multi-User KB** - Team workspaces and granular permissions
- **Container Storage** - Ephemeral KB data with Git persistence

**Status:** 🟡 Active development in feature branch  
**Documentation:** Will be moved to `current/` when branch merges

#### Advanced Authentication
- **Token Refresh** - Automatic JWT token renewal
- **Phase 4 Cleanup** - Remove legacy API key authentication
- **Certificate Rotation** - Automated mTLS certificate management

### 📋 [Roadmap](roadmap/)

#### High Priority (Next 1-2 Sprints)
- **[Implementation Status](roadmap/implementation-status.md)** - Detailed progress tracking
- **[Web UI Development](roadmap/web-ui-development-status.md)** - Frontend feature timeline
- **[Feature Roadmap](roadmap/feature-roadmap.md)** - Complete feature pipeline

#### Priority Systems
1. **Asset Pricing System** (18 endpoints) - Revenue and cost management
2. **Persona Management** (15 endpoints) - Character and behavior management  
3. **Performance Monitoring** - Real-time metrics and alerting
4. **Advanced Chat Features** - Conversation search, export, sharing

### 🔬 [Research](research/)

#### Experimental Features
- **[Orchestration System](research/orchestration-system.md)** - Multi-agent workflow coordination
- **[Multi-Agent Architecture](research/multiagent-orchestration.md)** - Complex AI task coordination
- **[N8N Integration](research/n8n-integration.md)** - Workflow automation platform
- **[MCP Integration](research/mcp-integration-strategy.md)** - Model Context Protocol implementation

#### Advanced Architecture
- **[Orchestrated Endpoints](research/orchestrated-endpoint-design.md)** - Intelligent request routing
- **[Integration Proposals](research/orchestrated-integration-proposal.md)** - Third-party service connections
- **[FastAPI MCP](research/mcp-fastapi-integration.md)** - Deep MCP framework integration

## 🎯 Implementation Timeline

### Q3 2025
- ✅ mTLS + JWT authentication migration (COMPLETE)
- 🟡 KB service integration (feature branch)
- 🔄 Asset pricing system implementation

### Q4 2025  
- 🔄 Persona management system
- 🔄 Performance monitoring dashboard
- 🔄 Advanced chat features

### 2026
- 🔄 Multi-agent orchestration
- 🔄 N8N workflow integration
- 🔄 Advanced RBAC features

## 📊 Development Metrics

### Branch Activity
- **feature/kb-integration** - 1074+ files, Git sync, RBAC implementation
- **main** - Stable production code
- **staging** - Integration testing environment

### Research Progress
- **Orchestration System** - Proof of concept complete
- **Multi-Agent Workflows** - Architecture designed
- **MCP Integration** - Initial implementation tested

## ⚠️ Important Notes

**Branch-Specific Features:** Features in development branches are extensively documented but not available in main branch until merge.

**Documentation Status:** Some features are marked "COMPLETE" in documentation but represent branch implementations, not main branch status.

**Implementation Priority:** Focus on completing current branch features before starting new experimental work.

## 🔗 See Also

- **🟢 [Current Features](../current/README.md)** - What works now
- **📚 [API Reference](../api/)** - Complete API documentation
- **🗄️ [Archive](../archive/)** - Historical development phases
- **🏠 [Documentation Home](../README.md)** - Main index