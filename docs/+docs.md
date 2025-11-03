# docs

GAIA platform documentation root.

## Subdirectories

- `designs/` - Design Documents
- `guides/` - How-to's & Tutorials
- `reference/` - Technical Reference
- `concepts/` - High-level Explanations
- `_internal/` - Project Artifacts
- `scratchpad/` - Temporary notes and architectural outlines

## Files

- `README.md` - Human-readable overview
- `README-FIRST.md` - Quick start guide

## Key Documents

### Development & Debugging
- `development/cookbook-creating-experiences-and-commands.md` - **START HERE**: How to create new game content
- `architecture/unified-state-model-deep-dive.md` - State Model Deep Dive, Content Entity System, & Debugging Guide

### API
- `api/reference/CLIENT_API_REFERENCE.md` - v0.3 API for external devs
- `api/reference/GAIA_API_REFERENCE.md` - v1 API with advanced features
- `api/chat/intelligent-chat-routing.md` - Routing system documentation

### Architecture
- `architecture/chat/chat-service-implementation.md` - Complete chat service architecture
- `architecture/chat/intelligent-tool-routing.md` - Tool routing with 70-80% optimization
- `architecture/chat/directive-system-vr-ar.md` - VR/AR directive system for immersive experiences
- `architecture/services/persona-system-guide.md` - AI persona system architecture
- `architecture/chat/chat-routing-and-kb-architecture.md` - Complete routing and KB integration
- `architecture/patterns/service-discovery-guide.md` - Service discovery implementation
- `architecture/database/database-architecture.md` - Hybrid database design

### KB System
- `kb/guides/kb-quick-setup.md` - Quick KB setup
- `kb/guides/kb-storage-configuration.md` - Storage backend configuration
- `kb/developer/kb-architecture-guide.md` - Technical architecture

### Testing
- `testing/TESTING_GUIDE.md` - Main testing documentation
- `testing/TEST_INFRASTRUCTURE.md` - Test infrastructure

## Features

- `features/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md` - Admin Commands Quick Start Guide

## Status

- **Production**: Gateway, Auth, Chat (with personas & directives), KB (Git mode)
- **Implemented**: Persona system (Mu default), Tool routing intelligence, VR/AR directives
- **Available**: Database storage, Hybrid storage, RBAC
- **Development**: Web UI improvements, Advanced features

## Implementation

- **~231 files** - Organized documentation with comprehensive indexing
- **7 microservices** - Gateway, Auth, Chat, KB, Asset, Web, Database
- **2 API versions** - v0.3 (clean + directives), v1 (full metadata)
- **3 storage modes** - Git (default), Database, Hybrid
- **Persona system** - Mu (default cheerful robot) + custom personas
- **9 tools** - 6 KB tools + 3 routing tools with intelligent instructions
- **Directives** - JSON-RPC commands for VR/AR timing control