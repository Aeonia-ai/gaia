# KB Multi-Instance Architecture Proposal



**Date**: October 2025  
**Status**: Proposal - Seeking Team Input  
**Author**: Code Investigation & Analysis  

## Executive Summary

Investigation of the current KB service reveals it contains **four distinct, sophisticated capabilities** that would benefit from architectural separation. This proposal outlines a multi-KB instance pattern that would unlock specialized optimization, better scaling, and clearer architectural boundaries.

## Current State Analysis

### What We Discovered

The KB service is far more sophisticated than documented. Code investigation reveals:

#### 1. **Embedded LLM Agent** (`app/services/kb/kb_agent.py`)
- **Knowledge Interpretation**: Converts static markdown into actionable intelligence
- **Workflow Execution**: Executes step-by-step game procedures from markdown
- **Rule Validation**: Validates player actions against KB-defined rules
- **Decision Making**: Real-time gameplay decisions based on knowledge context
- **Model Selection**: Automatic Haiku/Sonnet selection based on task complexity

#### 2. **MMOIRL Game Engine** (`app/services/kb/waypoints_api.py`)
- **AR/GPS Integration**: 37+ waypoints for real-world location gaming
- **Experience Management**: Structured game content (e.g., "wylding-woods")
- **Unity JSON Pipeline**: YAML-to-Unity transformation for AR clients
- **Location Intelligence**: Haversine distance calculations for proximity

#### 3. **Git-Synchronized Content** (External Obsidian Vault)
- **Repository**: `https://github.com/Aeonia-ai/Obsidian-Vault.git`
- **Auto-Sync**: Hourly synchronization with live content
- **Structure**: `/experiences/`, `/rules/`, `/workflows/`, `/shared/`
- **Format**: Markdown with embedded YAML for structured data

#### 4. **Chat Service Integration** (`app/services/chat/kb_tools.py`)
- **6 KB Tools**: search, context_loading, file_reading, synthesis, etc.
- **Intelligent Routing**: Tool selection based on user intent
- **Multi-Provider Auth**: API keys + JWT for inter-service communication

### Documentation Gap Analysis

**Well Documented** (23 documents):
- ✅ Infrastructure setup, Git sync, RBAC, deployment
- ✅ Storage architecture options (Git, Database, Hybrid)
- ✅ Multi-user patterns and permissions

**Missing from Documentation**:
- ❌ KB Agent intelligent capabilities (decision making, workflows)
- ❌ MMOIRL integration (AR waypoints, game mechanics)
- ❌ LLM-driven workflow execution
- ❌ Chat service tool integration patterns
- ❌ Multi-KB architectural patterns

## Proposed Multi-KB Architecture

### Problem Statement

The current monolithic KB service contains four distinct responsibilities:

1. **Game Logic & Rules** - Real-time decision making for MMOIRL
2. **Documentation & Knowledge** - Traditional document storage/search  
3. **AI Context & Memory** - Agent conversations and persona management
4. **Asset Metadata** - 3D models, textures, audio relationships

Each has different performance requirements, scaling patterns, and optimization needs.

### Proposed Architecture

#### **Specialized KB Instances**

```yaml
# Architectural Overview
kb-game:     # Game logic, rules, waypoints
  ├── Performance: Sub-second rule validation
  ├── Content: /experiences/, /rules/, /workflows/
  ├── Agent Mode: decision, validation, workflow
  └── Storage: PostgreSQL (ACID for game state)

kb-docs:     # Documentation, wikis, guides  
  ├── Performance: Complex semantic search
  ├── Content: /docs/, /guides/, /references/
  ├── Agent Mode: synthesis, search
  └── Storage: Vector DB + Git backup

kb-context:  # AI memory, conversations, personas
  ├── Performance: Ultra-fast context retrieval
  ├── Content: /sessions/, /agents/, /personas/
  ├── Agent Mode: memory, synthesis
  └── Storage: Redis + Database hybrid

kb-assets:   # 3D models, textures, metadata
  ├── Performance: Asset dependency tracking
  ├── Content: /models/, /textures/, /scenes/
  ├── Agent Mode: relationship, validation
  └── Storage: S3 + PostgreSQL metadata
```

#### **Service Communication Pattern**

```python
# Gateway routing by content type
KB_ROUTING_MAP = {
    "/experiences/**": "kb-game",
    "/rules/**": "kb-game", 
    "/waypoints/**": "kb-game",
    "/workflows/**": "kb-game",
    
    "/docs/**": "kb-docs",
    "/guides/**": "kb-docs",
    "/wikis/**": "kb-docs",
    
    "/sessions/**": "kb-context",
    "/agents/**": "kb-context", 
    "/personas/**": "kb-context",
    
    "/models/**": "kb-assets",
    "/textures/**": "kb-assets",
    "/scenes/**": "kb-assets"
}
```

#### **Chat Integration Updates**

```python
# Specialized KB tools by domain
GAME_KB_TOOLS = [
    "validate_game_action",
    "execute_game_workflow", 
    "get_nearby_waypoints",
    "check_game_rules"
]

DOCS_KB_TOOLS = [
    "search_documentation",
    "synthesize_knowledge",
    "load_context",
    "find_related_docs"
]

CONTEXT_KB_TOOLS = [
    "load_conversation_context",
    "get_agent_memory",
    "update_persona_state",
    "synthesize_interactions"
]
```

### Benefits of Multi-KB Pattern

#### **1. Performance Specialization**
- **Game KB**: Optimized for sub-second rule validation (PostgreSQL ACID)
- **Docs KB**: Optimized for semantic search (Vector database)
- **Context KB**: Optimized for real-time access (Redis caching)
- **Assets KB**: Optimized for large file metadata (S3 + PostgreSQL)

#### **2. Independent Scaling**
- **Game KB**: Scales with player count and real-time demands
- **Docs KB**: Scales with team size and content volume
- **Context KB**: Scales with AI agent complexity and conversation history
- **Assets KB**: Scales with 3D content and media storage needs

#### **3. Technology Optimization**
Each KB can use the optimal stack for its use case:
- Game rules need ACID transactions
- Documentation needs full-text search
- Context needs millisecond retrieval
- Assets need blob storage

#### **4. Security & Access Control**
- **Game KB**: Secure, validated repository with strict change control
- **Docs KB**: Public/team repositories with collaborative editing
- **Context KB**: Encrypted, user-isolated storage
- **Assets KB**: CDN-backed with usage analytics

### Implementation Strategy

#### **Phase 1: Extract Game Logic KB**
```bash
# Create specialized game KB instance
./scripts/create-new-service.sh kb-game 8010

# Configure for game-specific capabilities
KB_SPECIALIZATION=game
KB_AGENT_MODE=decision,validation,workflow
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Game-Logic.git
```

#### **Phase 2: Specialize Current KB for Documentation**
```bash
# Reconfigure existing KB for documentation focus
KB_SPECIALIZATION=docs
KB_AGENT_MODE=synthesis,search
# Keep current Git repo for documentation content
```

#### **Phase 3: Add Context KB**
```bash
# Ultra-fast context management
./scripts/create-new-service.sh kb-context 8020
KB_SPECIALIZATION=context  
KB_STORAGE_MODE=hybrid  # Redis + PostgreSQL
KB_AGENT_MODE=memory,synthesis
```

#### **Phase 4: Gateway Intelligence**
```python
# Smart routing with fallback patterns
async def route_kb_request(path: str, operation: str):
    primary_service = KB_ROUTING_MAP.get(path_pattern(path))
    
    # Try primary service first
    try:
        return await forward_to_service(primary_service, path, operation)
    except ServiceUnavailable:
        # Fallback to docs KB for general queries
        return await forward_to_service("kb-docs", path, operation)
```

## Current Implementation Status

### **Fully Implemented But Undocumented**
- ✅ KB Agent with decision/synthesis/validation modes
- ✅ Waypoints API with Unity JSON transformation  
- ✅ Git synchronization with external Obsidian vault
- ✅ Chat service integration with 6 specialized tools
- ✅ Multi-storage backend support (Git/Database/Hybrid)

### **Ready for Multi-Instance Pattern**
- ✅ Microservice creation automation (`create-new-service.sh`)
- ✅ Service discovery and health checking
- ✅ Gateway routing patterns
- ✅ Authentication propagation (API keys + JWT)
- ✅ Docker containerization with hot reloading

## Questions for Team Discussion

### **1. Architecture Direction**
- **Option A**: Keep monolithic KB, improve documentation of existing capabilities
- **Option B**: Implement multi-KB pattern as proposed
- **Option C**: Hybrid approach - extract game KB only, keep rest monolithic

### **2. Priority & Timeline**
- Should we prioritize documenting current capabilities first?
- Is multi-KB separation needed for current use cases?
- What's the timeline for MMOIRL production requirements?

### **3. Repository Strategy**
- Should game logic be in a separate private repository?
- How do we handle content versioning across multiple KB instances?
- What's the backup/disaster recovery strategy for distributed KB?

### **4. Performance Requirements**
- What are the actual response time requirements for game logic validation?
- Do we need sub-100ms responses for AR waypoint queries?
- Are current single-KB performance characteristics sufficient?

### **5. Team Capabilities**
- Do we have capacity to maintain multiple specialized KB instances?
- Should we outsource some KB domains (e.g., asset metadata)?
- What's the operational complexity vs. benefit trade-off?

## Recommendation

**Start with Documentation**: Before architectural changes, document the sophisticated capabilities we already have. The KB Agent's intelligent workflow execution and game logic integration are production-ready but invisible to the team.

**Then Evaluate**: Once capabilities are documented, evaluate whether the multi-KB pattern addresses real performance/scaling needs or is premature optimization.

**Prototype Game KB**: If multi-KB is desired, start with extracting game logic as a proof-of-concept, since it has the clearest domain boundaries and performance requirements.

## Related Documentation

- [KB Agent Overview](kb-agent-overview.md) - Current intelligent capabilities
- [KB Architecture Guide](developer/kb-architecture-guide.md) - Storage and multi-user patterns  
- [Adding New Microservice](../architecture/services/adding-new-microservice.md) - Service creation automation
- [Service Discovery Guide](../architecture/patterns/service-discovery-guide.md) - Routing patterns

---

**Next Steps**: Present this analysis to the team for architectural direction before proceeding with implementation.