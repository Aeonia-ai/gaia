# Experience Platform Architecture

> **Purpose**: Architecture for interactive experiences (AR games, text adventures, simulations)
> **Status**: DESIGN PHASE
> **Created**: 2025-10-24
> **Updated**: 2025-10-24 (Reorganized by system layer)
> **Related**:
> - [Game Command Developer Guide](./runtime-execution/game-command-developer-guide.md) - Runtime command execution
> - [KB-Driven Command Processing Spec](./runtime-execution/kb-driven-command-processing-spec.md) - Game command spec
> - [KB LLM Content Creation](./content-creation/kb-llm-content-creation.md) - Content creation via LLM
> - [AI Character Integration](./ai-systems/ai-character-integration.md) - Dynamic NPC system

## Overview

The Experience Platform enables creation and runtime execution of interactive experiences:
- **AR location-based games** (Wylding Woods) - GPS waypoints with AR interactions
- **Text adventures** (West of House) - Room-based narrative exploration
- **Turn-based games** (Rock Paper Scissors) - Multiplayer game mechanics
- **Interactive simulations** - Educational or training experiences

## Architecture Components

### 1. Content Storage (KB Service)
Static game content stored as markdown files with YAML frontmatter in `/kb/experiences/`:
- **Waypoints** - AR location markers with interactions
- **Rooms** - Text adventure locations
- **Items** - Collectible objects, tools, power-ups
- **NPCs** - Characters with dialogue trees
- **Quests** - Multi-step missions

**See:** [KB Repository Structure](../../kb/developer/kb-repository-structure-and-behavior.md)

### 2. Progress Tracking (PostgreSQL + Redis)
Player state, history, and analytics:
- **Active sessions** - Redis (fast, temporary)
- **Progress state** - PostgreSQL (durable, queryable)
- **Event history** - PostgreSQL (analytics, auditing)

**See:** [Player Progress Storage](./storage/player-progress-storage.md)

### 3. Runtime Execution (Game Command System)
Natural language command processing:
- LLM interprets commands against KB content
- Returns structured responses (narrative + actions + state changes)
- Supports both text and AR gameplay

**See:** [Game Command Developer Guide](./runtime-execution/game-command-developer-guide.md)

### 4. Design Tools (Experience Tools)
LLM-powered conversational content creation:
- 20 tools for discovering, creating, editing experiences
- Template-based learning from existing content
- Git-backed version control

**See:** [Experience Tools API](./content-creation/experience-tools-api.md)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EXPERIENCE PLATFORM                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Content    │  │   Progress   │  │   Runtime    │      │
│  │   Storage    │  │   Tracking   │  │   Execution  │      │
│  │              │  │              │  │              │      │
│  │  KB Service  │  │ PostgreSQL + │  │ Game Command │      │
│  │  (markdown)  │  │    Redis     │  │    System    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                  │
│                    ┌──────▼───────┐                         │
│                    │  Experience  │                         │
│                    │    Tools     │                         │
│                    │   (20 LLM    │                         │
│                    │    tools)    │                         │
│                    └──────────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Content Creation (Designer Workflow)
```
Designer (Web Chat)
    ↓
"Create a waypoint for Wylding Woods"
    ↓
LLM calls: get_content_template("waypoint")
    ↓
KB Service returns: Example waypoints (template learning)
    ↓
LLM asks: "What should we call it?"
    ↓
Multi-turn conversation (gather all fields)
    ↓
LLM calls: create_experience_content(...)
    ↓
KB Service: Generates markdown → Git commit → Auto-sync
```

### Gameplay (Player Workflow)
```
Player (Unity/Web)
    ↓
"Go north"
    ↓
execute_game_command(command="go north", experience="west-of-house")
    ↓
KB Service: Load game rules → LLM interprets → Return structured response
    ↓
Response: {
  narrative: "You walk to the north side of the house.",
  actions: [{type: "move", direction: "north"}],
  state_changes: {current_room: "north_of_house"}
}
    ↓
Client updates: UI, game state, player position
    ↓
Player Progress Service: Log event to PostgreSQL
```

## Implementation Phases

### Phase 1: Content Creation (Current Focus)
**Goal:** Enable conversational content creation via web chat

- [x] Design 12 core experience tools
- [ ] Implement template discovery endpoints
- [ ] Add KB write/edit capabilities
- [ ] Build multi-turn conversation flow
- [ ] Demo: Create waypoint through conversation

**Timeline:** 4-6 hours implementation

### Phase 2: Player Progress Tracking (CURRENT - October 2025)
**Goal:** Track player state and progress
**Status:** ✅ Design Complete, Implementation Starting

**Validated Design** (File-Based MVP):
- [x] Design complete and validated (2 Claude agents + Perplexity research)
- [x] Incremental IDs validated superior to UUIDs for LLM systems
- [x] GPS-to-waypoint resolution strategy defined
- [x] Atomic file operations pattern established
- [ ] Create file structure (manifest.json, instance files, player progress)
- [ ] Implement KB Agent methods (_load_manifest, _load_player_state, _collect_item)
- [ ] Update execute_game_command() with GPS resolution
- [ ] Demo: "Collect dream bottle" at Mill Valley Library

**Approach:**
- File-based storage (JSON files in KB) - appropriate for 1-10 player MVP
- Dictionary-based implementation - refactor to classes when scaling
- Migration to PostgreSQL planned at 20-50+ concurrent players

**See**: [Instance Management Implementation](./100-instance-management-implementation.md)

**Timeline:** 6-9 hours implementation (validated estimate)

### Phase 3: Live Operations (Future)
**Goal:** Hot-patching, rollbacks, scheduling

- [ ] Implement patch_experience_content
- [ ] Implement rollback_experience_content
- [ ] Add content scheduling (time-gated waypoints)
- [ ] Version/variant management (A/B testing)

**Timeline:** 1-2 weeks

### Phase 4: Analytics & Quality (Future)
**Goal:** Engagement metrics, automated testing

- [ ] Track content engagement (visit counts, completion rates)
- [ ] Experience flow testing (reachability analysis)
- [ ] Content review workflows
- [ ] Analytics dashboards

**Timeline:** 2-3 weeks

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Content Storage** | Markdown + YAML + Git | Version-controlled game data |
| **Progress Database** | PostgreSQL + JSONB | Flexible player state storage |
| **Session Cache** | Redis | Fast active session access |
| **Content Server** | KB Service (FastAPI) | Serve game content via API |
| **Progress Service** | Future Game Service | Manage player state/history |
| **LLM Tools** | Chat Service | Conversational design interface |
| **Runtime** | Game Command System | Execute gameplay commands |

## Security & RBAC

**Planned role system:**
- **Players** - Play experiences, progress tracked
- **Designers** - Create/edit content via tools
- **Lead Designers** - Approve content, manage workflows
- **Admins** - All permissions, system configuration

**Not implemented yet** - Phase 1 focuses on content creation, RBAC deferred.

## Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| **Content query** | <100ms | Redis caching, indexed JSONB |
| **Player state read** | <50ms | Redis-first, PostgreSQL fallback |
| **State write** | <200ms | Async PostgreSQL writes |
| **Tool execution** | <3s | Template caching, LLM optimization |
| **Concurrent players** | 10K+ | Horizontal scaling, Redis clustering |

## Documentation Map

### 📁 By System Layer

#### Content Creation (Designer Tools)
- [KB LLM Content Creation](./content-creation/kb-llm-content-creation.md) - Conversational content creation workflow
- [Experience Tools API](./content-creation/experience-tools-api.md) - 20 LLM tools specification

#### Runtime Execution (Player Gameplay)
- [Game Command Developer Guide](./runtime-execution/game-command-developer-guide.md) - How to use the system
- [KB-Driven Command Processing Spec](./runtime-execution/kb-driven-command-processing-spec.md) - Complete technical spec

#### AI Systems (Dynamic Characters)
- [AI Character Integration](./ai-systems/ai-character-integration.md) - Multi-agent NPC architecture

#### Storage (Data Persistence)
- [Player Progress Storage](./storage/player-progress-storage.md) - PostgreSQL + Redis design
- [Experience Data Models](./storage/experience-data-models.md) - Database schemas and migrations

### 🔗 Related Platform Documentation
- [Database Architecture](../database/database-architecture.md) - Overall database strategy
- [PostgreSQL Simplicity Lessons](../database/postgresql-simplicity-lessons.md) - Design principles
- [KB Repository Structure](../../kb/developer/kb-repository-structure-and-behavior.md) - Content organization

### 🎮 External Game Design Documentation
- **[Wylding Woods Action Vocabulary](../../../../Vaults/KB/users/jason@aeonia.ai/mmoirl/experiences/wylding-woods/action-vocabulary.md)** - Production action types (kb-frantz-gemini)

## Questions & Decisions

**Q: Why separate tools for game design vs gameplay?**
A: Different users, different needs. Designers create content conversationally. Players execute commands for gameplay.

**Q: Why hybrid PostgreSQL + Redis for player progress?**
A: PostgreSQL for durability/analytics. Redis for real-time performance. Industry standard pattern.

**Q: Can experiences be cross-platform (AR + text)?**
A: Yes! Same KB content, different client interpretations. Text adventure can become AR game by adding location data.

**Q: How does this scale to multiplayer?**
A: Phase 1 is single-player. Multiplayer requires real-time sync service (future Phase 5+).

---

**Next:** Explore documentation by system layer above, or start with [Content Creation Tools](./content-creation/experience-tools-api.md) for Phase 1 implementation.
