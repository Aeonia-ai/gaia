# 🏠 Gaia Platform Documentation

Welcome to the Gaia Platform documentation! This directory contains comprehensive guides for understanding, deploying, and scaling the Gaia microservices architecture.

## 🚦 Quick Start by Role

### 👩‍💻 **For Developers** → [`development/`](development/)
Get started with local development, testing, and command reference.

### 🚀 **For DevOps** → [`deployment/`](deployment/)  
Deploy to production with Fly.io, database setup, and smart scripts.

### 🏗️ **For Architects** → [`architecture/`](architecture/)
Understand the microservices architecture, scaling patterns, and database design.

**🎯 KEY**: [**Chat Routing & KB Architecture**](architecture/chat/chat-routing-and-kb-architecture.md) - Complete guide to how intelligent chat routing and Knowledge Base integration work

### 🗄️ **For Knowledge Base** → [`kb/`](kb/)
Access and manage the Knowledge Base service with Git sync and RBAC.

**💡 TIP**: KB is auto-integrated with chat! Use `POST /api/v1/chat` with natural language like "search my notes on X" instead of direct KB endpoints.

### 🎮 **For Game Development** → New Revolutionary System!
Build games using only markdown documentation - no code required!

**🚀 BREAKTHROUGH**: Games run directly from documentation through AI interpretation:
- [**Game State JSON Blocks**](game-state-json-blocks.md) - Technical specification
- [**Executable Documentation Pattern**](executable-documentation-pattern.md) - The paradigm shift
- [**Game Implementation Guide**](game-system-implementation-guide.md) - How to build games
- [**CLI Game Interaction**](cli-game-interaction-guide.md) - Playing games via terminal

### 🌐 **For Web UI** → [`web-ui/`](web-ui/)
FastHTML frontend development, HTMX patterns, and debugging guides.

### 🔮 **For Roadmap** → [`roadmap/`](roadmap/)
See what's coming next and current development status.

## 📋 Complete Documentation Map

```
docs/
├── 📚 api/              ← API REFERENCE & CONTRACTS
│   ├── reference/       ← Complete API references
│   ├── chat/           ← Chat endpoint documentation
│   └── authentication/ ← Auth patterns and endpoints
├── 🏗️ architecture/    ← SYSTEM DESIGN & PATTERNS
│   ├── patterns/       ← Service discovery, initialization
│   ├── chat/          ← Chat routing architecture
│   ├── database/      ← Database design
│   └── services/      ← Service specifications
├── 🔐 authentication/  ← SECURITY & AUTH
├── 🚀 deployment/      ← PRODUCTION DEPLOYMENT
├── 💻 development/     ← LOCAL DEVELOPMENT
├── 🗄️ kb/             ← KNOWLEDGE BASE (OPERATIONAL)
│   ├── guides/        ← User guides and setup
│   ├── developer/     ← Technical documentation
│   ├── reference/     ← API reference
│   └── troubleshooting/ ← Problem solving
├── 🌐 web-ui/         ← FASTHTML FRONTEND
├── 🧪 testing/        ← TESTING GUIDES
│   └── TESTING_GUIDE.md ← Main testing documentation
├── 🔮 roadmap/        ← FUTURE PLANS
└── 📦 _archive/       ← HISTORICAL DOCS
```

## 🆕 **Latest Documentation (August 2025)**

### Web Service Improvements
- **[Web Service Standardization Specification](./web-service-standardization-spec.md)** - Comprehensive standards for accessibility, testability, and UX improvements
- **[Web Testing Strategy Post-Standardization](./web-testing-strategy-post-standardization.md)** - How testing will be transformed with semantic HTML and data-testid attributes

These documents outline the transformation of our web service from brittle CSS-based testing to robust, accessible, standards-compliant patterns.

## 🎯 **Implementation Status Legend**
- 🟢 **CURRENT** - Fully implemented and tested (main branch)
- 🟡 **FUTURE** - Planned, in-development, or branch-specific
- 🔴 **ARCHIVE** - Historical, deprecated, or lessons learned

## 🚀 Quick Commands

### For Developers
```bash
# Quick start local development
cd /path/to/gaia
docker compose up
./scripts/test.sh --local all

# Smart environment testing
./scripts/test.sh --staging health     # Test staging deployment
./scripts/test.sh --prod all           # Full production tests

# See main development guide
cat ../CLAUDE.md
```

### For DevOps/SRE
```bash
# Complete deployment pipeline
cat deployment/deployment-best-practices.md

# Environment-specific deployments
./scripts/deploy.sh --env dev --services all         # Dev: Full microservices
./scripts/deploy.sh --env staging --services all     # Staging: Full microservices
./scripts/deploy.sh --env production --services all  # Production: Full microservices

# Platform management
./scripts/manage.sh status             # Environment overview
./scripts/manage.sh monitor production # Real-time monitoring
```

## 🎉 Key Achievements

- **78+ Endpoints** implemented with full LLM Platform compatibility
- **100% Backward Compatibility** - all existing clients work unchanged
- **Microservices Architecture** with independent scaling and fault isolation
- **Smart Operations** - Environment-aware testing, deployment, and management
- **Production Deployed** - Live staging environment on Fly.io
- **Comprehensive Testing** - 80+ endpoint tests with intelligent failure handling

## 📊 Architecture Overview

```
Gaia Platform Microservices
├─ Gateway Service (8666) - API routing & authentication
├─ Auth Service - JWT validation via Supabase  
├─ Chat Service - LLM interactions & streaming
├─ Asset Service - Image/3D generation
├─ KB Service - Knowledge Base with Git sync & RBAC ✅ OPERATIONAL
├─ Web Service (8080) - FastHTML frontend
└─ Shared Infrastructure (PostgreSQL, NATS, Redis)
```

## 🏗️ **Additional Architecture Resources**
- **[Architecture Overview](architecture-overview.md)** - Comprehensive platform architecture with diagrams, service responsibilities, and data flow
- **[Architecture Recent Updates](architecture-recent-updates.md)** - Latest architectural improvements and changes
- **[Architecture Decision Records (ADRs)](adr/)** - Key architectural decisions and their rationale

## 🔗 External Resources

- [Main Development Guide](../CLAUDE.md) - Primary development documentation
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Fly.io Documentation](https://fly.io/docs/)