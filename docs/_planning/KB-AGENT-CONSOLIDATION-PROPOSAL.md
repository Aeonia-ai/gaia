# KB-Agent Documentation Consolidation Proposal

**Created:** 2025-12-11
**Status:** PROPOSAL - Awaiting verification of source docs

## Problem Statement

The kb-agent documentation is severely fragmented:
- **Reference doc**: `docs/reference/services/kb-agent-overview.md` (148 lines, 30% complete)
- **Sprint logs**: `docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/` (46 docs, 25,632 lines)

The reference doc describes the KB Agent as an "intelligent knowledge interpreter" but:
- Doesn't document the **game command system** (commands like `look`, `pick up`, `drop`)
- Doesn't document the **admin command system** (`@list`, `@create`, `@inspect`)
- Doesn't document the **NPC interaction system** (`talk` command, trust tracking)
- Doesn't document the **unified state model** (shared vs isolated state)
- Doesn't document the **experience system** (wylding-woods, AR waypoints)

All this "missing" documentation exists - it's just scattered across 46 sprint logs.

---

## Source Documentation Analysis

### Current Structure (46 docs, 25,632 lines)

| Category | Doc Count | Total Lines | Key Docs |
|----------|-----------|-------------|----------|
| KB Agent Core | 4 | ~2,500 | 001, 002, 004, 005 |
| Game Commands | 8 | ~4,200 | 009, 021, 028, 029, 030, 031 |
| Admin Commands | 6 | ~3,100 | 000-quick-start, 023, 024, 025, 033, 036 |
| Chat Integration | 10 | ~4,800 | 010-019, 032 |
| NPC/AI System | 4 | ~2,800 | 006, 027, 034 |
| State Model | 3 | ~1,900 | 030-unified, 100, 101 |
| Development Guides | 6 | ~3,500 | 003, 007, 008, 018, 020, 035 |
| Miscellaneous | 5 | ~2,800 | 026, 028-waypoint, 029-wylding, 030-archival, 102 |

### Document Type Analysis

Many of these are **sprint logs** not reference documentation:
- `023-admin-commands-implementation-guide.md` - Sprint log with implementation steps
- `032-chat-integration-complete.md` - Completion announcement
- `030-game-command-archival-report.md` - Archival report
- `102-symphony-collaboration.md` - Multi-agent design session log

These contain valuable information but are **not structured as reference docs**.

---

## Proposed Consolidated Structure

### Target: 5 Reference Documents (~2,700 lines total)

| Proposed Doc | Source Docs | Est. Lines |
|--------------|-------------|------------|
| `kb-agent-architecture.md` | 001, 002, 004, 005, 100, 101 | ~600 |
| `game-command-system.md` | 009, 021, 028, 029, 030-archival, 031 | ~700 |
| `admin-command-reference.md` | 000-quick-start, 023, 024, 025, 033, 036 | ~500 |
| `npc-interaction-system.md` | 006, 027, 034 | ~400 |
| `unified-state-model.md` | 030-unified, existing docs | ~500 |

**Reduction: 46 docs → 5 docs (89% reduction)**
**Line count: 25,632 → ~2,700 (89% reduction)**

---

## Detailed Mapping

### 1. `kb-agent-architecture.md` (NEW)

**Purpose:** Complete architectural reference for the KB Agent service

**Source docs to consolidate:**
- `001-kb-agent-api.md` - API reference
- `002-kb-agent-architecture.md` - Architecture overview
- `004-kb-repository-structure.md` - Repository structure
- `005-experiences-overview.md` - Experience architecture
- `100-instance-management-implementation.md` - Instance management
- `101-design-decisions.md` - ADRs

**What to extract:**
- API endpoints (from 001)
- Architecture diagrams (from 002)
- File structure conventions (from 004)
- Design decisions (from 101)

**What to omit:**
- Implementation step-by-step logs
- Sprint retrospectives
- Superseded designs

---

### 2. `game-command-system.md` (NEW)

**Purpose:** Complete reference for player-facing game commands

**Source docs to consolidate:**
- `009-game-command-developer-guide.md` - Developer guide (**KEY**)
- `021-kb-command-processing-spec.md` - Processing spec
- `028-game-command-markdown-migration.md` - Migration to markdown
- `029-game-command-architecture-comparison.md` - Architecture comparison
- `030-game-command-archival-report.md` - What was archived
- `031-markdown-command-system.md` - Markdown command system (**KEY**)

**What to extract:**
- Command syntax and examples
- Available commands (look, pick up, drop, inventory, etc.)
- How to create new commands (markdown format)
- Processing pipeline

**What to omit:**
- Migration planning details
- Comparison with deprecated systems

---

### 3. `admin-command-reference.md` (NEW)

**Purpose:** Complete reference for world-building admin commands

**Source docs to consolidate:**
- `000-admin-commands-quick-start.md` - Quick start (**KEY**)
- `023-admin-commands-implementation-guide.md` - Implementation details
- `024-crud-navigation-implementation.md` - CRUD operations
- `025-complete-admin-command-system.md` - Complete reference (**KEY**)
- `033-admin-command-system.md` - System overview
- `036-experience-reset-guide.md` - Reset procedures

**What to extract:**
- All @ commands with syntax and examples
- CRUD operations (@create, @delete, @update)
- Navigation commands (@list, @inspect)
- Reset and maintenance commands

**What to omit:**
- Implementation sprint logs
- Superseded command formats

---

### 4. `npc-interaction-system.md` (NEW)

**Purpose:** Complete reference for NPC conversations and AI characters

**Source docs to consolidate:**
- `006-ai-character-integration.md` - AI character integration (**KEY**)
- `027-npc-communication-system.md` - Communication system
- `034-npc-interaction-system.md` - Interaction system (**KEY**)

**What to extract:**
- `talk` command usage
- Trust/relationship tracking
- NPC personality configuration
- Conversation history management
- Quest integration

**What to omit:**
- Sprint planning details
- Superseded interaction models

---

### 5. `unified-state-model.md` (NEW)

**Purpose:** Complete reference for state management (shared vs isolated)

**Source docs to consolidate:**
- `030-unified-state-model-implementation.md` (**KEY**)
- Related content from other docs

**What to extract:**
- Shared state model (world state, NPCs, items)
- Isolated state model (player inventory, progress)
- Configuration format
- State persistence

**What to omit:**
- Implementation debugging logs

---

## What Happens to Chat Integration Docs?

The 10 chat-related docs (010-019, 032) should be consolidated separately into:
- `docs/reference/chat/` - already exists, should absorb relevant content

These are **not KB Agent specific** - they're about the chat service architecture.

---

## Consolidation Prerequisites

Before consolidating, we must verify which source docs are accurate:

### Priority 1: Key Source Docs (must verify)
- [ ] `025-complete-admin-command-system.md` - Admin command reference
- [ ] `030-unified-state-model-implementation.md` - State model
- [ ] `031-markdown-command-system.md` - Command system
- [ ] `034-npc-interaction-system.md` - NPC interactions

### Priority 2: Architecture Docs
- [ ] `002-kb-agent-architecture.md` - Architecture
- [ ] `009-game-command-developer-guide.md` - Developer guide
- [ ] `006-ai-character-integration.md` - AI characters

### Already Verified
- [x] `kb-agent-overview.md` - 30% complete, needs expansion

---

## Verification Approach

Use the **full bidirectional verification protocol** (not abbreviated prompts):

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    Read .claude/skills/doc-health/verify-protocol.md and follow it exactly.

    Verify: docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/025-complete-admin-command-system.md

    Against code in:
    - app/services/kb/game_engine/
    - app/services/kb/main.py
    - app/services/kb/kb_storage.py

    Return:
    1. All 7 stages completed
    2. Phase 2 completeness check
    3. Findings table with severity and confidence
    4. Specific code citations for every claim
    """
)
```

---

## Success Criteria

After consolidation:
1. **5 comprehensive docs** replace 46 fragmented docs
2. **Each doc is 95%+ accurate** against code
3. **Each doc is 80%+ complete** for its scope
4. **kb-agent-overview.md** updated to reference new docs
5. **Sprint logs archived** (moved to `docs/_archive/phase-1-mvp/`)

---

## Timeline Estimate

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Verify 4 key source docs | 2-3 hours |
| 2 | Create consolidated docs | 4-6 hours |
| 3 | Verify new docs | 2-3 hours |
| 4 | Update references | 1 hour |
| 5 | Archive sprint logs | 30 min |

**Total: ~10-13 hours of focused work**

---

## Open Questions

1. **Should sprint logs be deleted or archived?**
   - Recommendation: Archive to `docs/_archive/phase-1-mvp/`
   - They have historical value but shouldn't be in main docs

2. **Should kb-agent-overview.md be replaced or updated?**
   - Recommendation: Keep as executive summary, link to detailed docs
   - Update to reflect actual capabilities (game engine, not just "knowledge interpreter")

3. **How to handle duplicate content across sources?**
   - Take most recent version as truth
   - Verify against code before including

---

## Next Steps

1. **Verify Priority 1 docs** using full protocol
2. **Create first consolidated doc** (admin-command-reference.md)
3. **Iterate** based on verification findings
