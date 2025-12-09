# Phase 3: Technical Debt Audit

**Analysis Date:** 2025-11-20

---

## Executive Summary

The codebase contains **60 TODOs**, **33 MVP/KLUDGE markers**, and **7,231 lines of archived dead code**. The most significant debt is the NPC interaction system which routes through chat service (double-hop) and hardcoded game values. Immediate wins include deleting archived code and legacy files.

---

## Debt Inventory Overview

| Category | Count | Impact |
|----------|-------|--------|
| TODO markers | 60 | Medium - deferred features |
| MVP/KLUDGE markers | 33 | High - known architectural issues |
| Archived dead code | 7,231 lines | Low - cleanup needed |
| Hardcoded game values | ~30 instances | High - blocks extensibility |
| Temporary code markers | ~25 instances | Medium - tech debt |

---

## Priority 1: MVP Kludges (High Impact)

### 🔴 NPC Talk Handler Double-Hop
**Location:** `app/services/kb/handlers/talk.py`

**Current Flow:**
```
Unity → WebSocket → KB Service → HTTP → Chat Service → HTTP → KB Service → Unity
```

**Problem:**
- Double-hop adds latency
- Chat service has game mechanic knowledge (quest IDs, bottle IDs)
- Tight coupling between services

**Files Affected:**
- `talk.py` (entire file is kludge)
- `experience_endpoints.py:277-500` (MVP endpoints)
- `kb/main.py:173-188` (registration)
- `chat/kb_tools.py` (NPC tools)
- `chat/unified_chat.py` (tool filtering)

**Proper Solution:**
Move NPC dialogue generation INTO KB service using MultiProviderChatService directly.

---

### 🔴 Hardcoded Persona ID
**Location:** `app/services/kb/handlers/talk.py:103`

```python
"persona_id": "louisa",  # MVP: Hardcoded persona ID
```

**Problem:** Can only talk to Louisa, not other NPCs

**Solution:** Look up persona from NPC definition in KB markdown

---

### 🔴 MVP Quest State Endpoints
**Location:** `app/services/kb/experience_endpoints.py:277-500`

Four endpoints marked as MVP kludge:
```python
@router.post("/{experience}/quest/state")      # Check quest state
@router.post("/{experience}/npc/accept_item")  # Accept item from player
@router.post("/{experience}/quest/reward")     # Grant reward
@router.get("/{experience}/player/inventory")  # Get inventory
```

**Problem:** These are HTTP endpoints for what should be internal state operations

**Solution:** Move logic into KB state manager, expose through unified API

---

## Priority 2: Hardcoded Game Values (Blocks Extensibility)

### Hardcoded Experience Names
| Location | Value | Fix |
|----------|-------|-----|
| `shared/events.py:31` | `"wylding-woods"` | Use config or parameter |
| `experience_connection_manager.py:81` | `"wylding-woods"` default | Should require explicit |
| `websocket_experience.py:53` | `"wylding-woods"` default | Should require explicit |

### Hardcoded NPC Names
| Location | Value | Fix |
|----------|-------|-----|
| `kb_agent.py:214-216` | `"louisa"` examples | Fine for examples |
| `kb_agent.py:3024` | `"louisa"` comment | Fine for comments |
| `kb_agent.py:3670` | `"louisa"` docstring | Fine for docs |
| `talk.py:103` | `"louisa"` hardcoded | **Must fix** |

### Hardcoded Quest Values
| Location | Value | Fix |
|----------|-------|-----|
| `websocket_experience.py:294,304` | `"bottle_quest"` | Load from config |

---

## Priority 3: Dead Code (Easy Wins)

### 🟡 Chat Archive Directory
**Location:** `app/services/chat/_archive_2025_01/`
**Size:** 26 files, 7,231 lines

**Files:**
```
custom_orchestration.py
dynamic_tool_system.py
efficient_orchestration.py
enhanced_mcp_handler.py
hierarchical_agent_system.py
hybrid_mcp_strategy.py
intelligent_chat.py
intelligent_mcp_router.py
intelligent_router.py
lightweight_chat_db.py
lightweight_chat_simple.py
lightweight_chat.py
mcp_direct_example.py
orchestrated_chat_better.py
orchestrated_chat_fixed.py
orchestrated_chat_minimal_fix.py
orchestrated_chat.py
orchestration_examples.py
persistent_memory.py
production_orchestration_system.py
redis_chat_history.py
semantic_mcp_router.py
ultrafast_chat.py
ultrafast_redis_chat.py
ultrafast_redis_optimized.py
ultrafast_redis_parallel.py
```

**Recommendation:** Move to `docs/archive/` or delete entirely

---

### 🟡 Legacy Game Commands
**Location:** `app/services/kb/game_commands_legacy_hardcoded.py`
**Size:** 3,326 lines

**Analysis:** This file contains the pre-refactor game command logic. All functionality has been moved to handler modules.

**Recommendation:** Delete after confirming no imports

---

### 🟡 Disabled Files
| File | Size | Status |
|------|------|--------|
| `kb_multiagent_orchestrator.py.disabled` | ~500 lines | Should delete |

---

## Priority 4: TODOs by Category

### Unimplemented Features (23)
| Location | TODO |
|----------|------|
| `kb_agent.py:394` | Implement markdown-driven execution |
| `kb_agent.py:867` | Get role from JWT claims |
| `use_item.py:163` | Implement unlock logic |
| `use_item.py:169` | Implement custom use behavior system |
| `kb_storage_manager.py:322` | Database to Git export |
| `kb_storage_manager.py:340` | Git to database import |
| `unified_state_manager.py:1565` | Handle multiple overlapping zones |
| `admin_where.py:162` | Get NPCs from world state |
| `game_commands_api.py:243` | Implement KB experience listing |

### Health Check Stubs (10)
All in `app/services/asset/router*.py`:
```python
"database": "pending",  # TODO: Actual health check
"nats": "pending",      # TODO: Actual health check
"storage": "pending",   # TODO: Actual health check
```

### Search/ML Features (8)
| Location | TODO |
|----------|------|
| `kb_mcp_server.py:259` | Implement relevance scoring |
| `asset_search_service.py:174` | Implement embedding generation |
| `asset_search_service.py:202` | Implement database search with pgvector |
| `asset_search_service.py:225` | Implement Poly Haven API |
| `asset_search_service.py:238` | Implement Freesound API |

### Asset Generation (4)
| Location | TODO |
|----------|------|
| `generation_service.py:390` | Implement animation generation |
| `generation_service.py:516` | Implement actual modification logic |
| `webhooks.py:195` | Download model and store in Supabase |

---

## Priority 5: RBAC Confusion

**Problem:** Three RBAC implementations exist:

| File | Lines | Status |
|------|-------|--------|
| `rbac.py` | ~300 | Original, complex |
| `rbac_simple.py` | ~150 | Simplified version |
| `rbac_fixed.py` | ~200 | Bug fix version |

**Current Usage:**
```bash
$ grep -r "from.*rbac" app/ --include="*.py" | grep import
app/services/kb/kb_storage_with_rbac.py:from app.shared.rbac import RBACManager
app/services/kb/kb_rbac_integration.py:from app.shared.rbac_simple import SimpleRBACMiddleware
```

**Recommendation:** Consolidate to one implementation, delete others

---

## Priority 6: Temporary Code Markers

### "For Now" Patterns (12 instances)
| Location | Issue |
|----------|-------|
| `rbac_simple.py:55` | "skip team/workspace lookups for now" |
| `rbac_simple.py:89` | "permissive - for now" |
| `rbac_simple.py:100,103` | "skip checks for now" |
| `llm/registry.py:162` | "return basic model info for now" |
| `kb_semantic_search.py:669` | "trigger full reindex for now" |
| `kb_agent.py:310,395,916,922` | Various "for now" workarounds |

### "Should Be" Patterns (5 instances)
| Location | Issue |
|----------|-------|
| `websocket_experience.py:283` | "Quest logic should be a proper command" |
| `jwt_service.py:83,101` | "keys should be mounted" |
| `api/v0_2/endpoints/chat.py:32` | "should be in proper database" |

---

## Technical Debt Heat Map

```
High Impact | Low Effort
─────────────────────────
• Delete _archive_2025_01/   [7,231 lines saved]
• Delete legacy_hardcoded.py [3,326 lines saved]
• Delete .disabled files     [~500 lines saved]
• Consolidate RBAC           [~450 lines saved]

High Impact | High Effort
─────────────────────────
• NPC talk refactor          [Eliminate double-hop]
• Remove hardcoded values    [Enable new experiences]
• Implement markdown-driven  [Data-driven game logic]

Low Impact | Low Effort
─────────────────────────
• Fix health check TODOs     [Better monitoring]
• Add missing docstrings     [Better maintenance]

Low Impact | High Effort
─────────────────────────
• Asset search features      [Future capability]
• Animation generation       [Future capability]
```

---

## Recommended Cleanup Order

### Phase A: Easy Wins (1-2 hours)
1. Delete `app/services/chat/_archive_2025_01/` (7,231 lines)
2. Delete `app/services/kb/game_commands_legacy_hardcoded.py` (3,326 lines)
3. Delete `kb_multiagent_orchestrator.py.disabled`
4. Consolidate RBAC to single file

**Total lines removed: ~11,000**

### Phase B: Hardcoded Values (2-4 hours)
1. Create experience config loader
2. Replace hardcoded experience names
3. Replace hardcoded persona IDs
4. Replace hardcoded quest values

### Phase C: Architecture (1-2 days)
1. Move NPC dialogue to KB service
2. Remove MVP kludge endpoints
3. Implement proper quest state management

---

## Debt Metrics Summary

| Metric | Value | Target |
|--------|-------|--------|
| TODO count | 60 | <20 |
| KLUDGE count | 33 | 0 |
| Dead code lines | 11,000+ | 0 |
| Hardcoded values | ~30 | 0 |
| RBAC versions | 3 | 1 |

---

## Next: Phase 4 - Complexity Analysis

Will analyze:
- Cyclomatic complexity
- Function lengths
- Import coupling
- Large file decomposition opportunities
