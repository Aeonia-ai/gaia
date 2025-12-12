# Documentation Verification Tracker

**Purpose:** Track verification status of all 390 docs.

---

## ⚠️ CRITICAL: Previous Verification Was Unreliable

**2025-12-04 Discovery:** The previous verification pass used a method with **~40% false positive rate**.

Testing revealed:
- Manual LLM verification: ~40% false positives (claimed issues that didn't exist)
- Basic subagent verification: ~15% false positives
- **New 7-Stage Protocol: 0% false positives**

**Previous "Verified" counts are unreliable.** We need to re-verify using the new protocol.

---

## New Protocol: 7-Stage Anti-Hallucination

**Location:** `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md`

**Key Requirements:**
1. Force exact citations from BOTH doc AND code
2. Track all files actually read
3. Special handling for negation claims ("NOT", "NEVER")
4. Cross-claim consistency checking
5. Confidence calibration (mark uncertain findings for human review)

**Process:**
```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""[Full protocol from ENHANCED_VERIFICATION_PROTOCOL.md]

    Verify: docs/path/to/doc.md
    Against code in: [relevant files]"""
)
```

**Decisions:** ✅ ACCURATE | 🔧 NEEDS_UPDATE | ❌ CRITICALLY_WRONG | 🗑️ DELETE

---

## Re-Verification Progress (New Protocol)

| Directory | Total | Re-Verified | Accurate | NeedsUpdate | Critical |
|-----------|-------|-------------|----------|-------------|----------|
| reference/ | 98 | 8 | 0 | 8 | 0 |
| _internal/ | 86 | 0 | 0 | 0 | 0 |
| scratchpad/ | 58 | 0 | 0 | 0 | 0 |
| concepts/ | 58 | 0 | 0 | 0 | 0 |
| guides/ | 53 | 0 | 0 | 0 | 0 |
| analysis/ | 11 | 0 | 0 | 0 | 0 |
| root level | 11 | 0 | 0 | 0 | 0 |
| other | 15 | 0 | 0 | 0 | 0 |
| **TOTAL** | **390** | **8** | **0** | **8** | **0** |

---

## Verified with New Protocol

### 🔧 NEEDS_UPDATE

| Doc | Date | Issues | Severity | Fixed? |
|-----|------|--------|----------|--------|
| `reference/services/persona-system-guide.md` | 2025-12-04 | 8 | Minor | ❌ |
| `reference/modules/prompt-manager.md` | 2025-12-04 | 4 | Moderate | ❌ |
| `reference/services/llm-service.md` | 2025-12-04 | 3 | Moderate | ✅ |
| `reference/chat/chat-service-implementation.md` | 2025-12-06 | 2 | Minor | ✅ |
| `reference/services/kb-agent-overview.md` | 2025-12-06 | 2 | Minor | ✅ |
| `reference/database/database-architecture.md` | 2025-12-09 | 3 | Moderate | ✅ |
| `reference/api/api-contracts.md` | 2025-12-09 | 0 (but 15% complete) | N/A | ✅ (added TODO) |
| `reference/api/kb-endpoints.md` | 2025-12-10 | 2 (93% accurate, 33% complete) | Moderate | ✅ (added TODO) |

#### kb-endpoints.md (2 accuracy issues + major completeness gap)
1. **DELETE endpoint path wrong** - doc said `/api/v0.2/kb/delete`, code shows `/delete`
2. **Endpoint count wrong** - doc said "25+ endpoints", code has 45+
- **Completeness: 33%** - Only 15 of 45 endpoints documented
- Missing: Semantic search (4), KB Agent (5), Experience (8), Game (3), WebSocket (1), RBAC (5), Advanced (5)
- Added TODO section listing all undocumented endpoint categories
- Lesson learned: KB service has grown significantly - need dedicated docs for each endpoint category

#### persona-system-guide.md (8 issues)
1. Missing NPC persona tools_section exception
2. is_active field creation behavior unclear
3. Performance claims unverified (marked TODO - acceptable)
4. Cache invalidation triggers incomplete
5. List cache TTL (5 min) vs individual (1 hour) not documented
6. User preference cache TTL (10 min) not documented
7. PromptManager returns tuple, not just string
8. Dual Mu creation paths not explained

#### prompt-manager.md (4 issues)
1. Says "one method" but class has TWO methods
2. `get_system_prompt_and_persona()` completely undocumented
3. Production usage uses undocumented method
4. Return type tuple not documented

#### llm-service.md (3 issues)
1. **LLMProvider incorrectly described as "Base class"** - it's actually an Enum; the real base class is `LLMProviderInterface`
2. **Failover misattributed** - doc says Registry handles failover, but code shows failover is in chat_service.py
3. **Session management claim unclear** - only parameter passing found, no actual session lifecycle management (MEDIUM confidence - needs human review)

#### chat-service-implementation.md (2 issues)
1. **KB Tools count wrong** - doc said "Six" but code has 7 (missing `interact_with_experience`)
2. **Line number outdated** - doc cited "Line 262" but actual code is at lines 397 and 935

#### kb-agent-overview.md (2 issues)
1. **Haiku model inconsistency** - code uses BOTH `claude-haiku-4-5` and `claude-3-5-haiku-20241022` - added warning note in doc, needs CODE FIX to standardize
2. **Response time unqualified** - changed "1-3 seconds" to "Typically 1-3 seconds (varies by model load)"

#### database-architecture.md (3 issues) - MAJOR REWRITE
1. **Table count wrong** - doc said 29, then we wrongly changed to 40; actual DB has 19 tables
2. **RBAC tables listed as existing** - 13 RBAC tables in migrations but never applied; moved to "Planned" section
3. **Missing semantic search tables** - `kb_semantic_chunk_ids` and `kb_semantic_index_metadata` exist in DB but weren't documented
- Lesson learned: Always verify against actual running database, not just migration files

#### api-contracts.md (0 accuracy issues, major completeness gap)
- **Accuracy: 100%** - All documented endpoints exist and auth requirements are correct
- **Completeness: ~15%** - Only ~28 of ~180 endpoints documented
- Added TODO section listing services needing documentation (KB, Chat, Gateway non-auth, etc.)
- Lesson learned: Verification must be bidirectional (Doc→Code AND Code→Doc)

### ✅ ACCURATE (no changes needed)
<!-- Add docs here as verified accurate with new protocol -->

### ❌ CRITICALLY_WRONG
<!-- Add docs here if major architectural mismatches found -->

---

## Phase 2 Completeness Results (2025-12-10)

All 8 previously verified docs were re-checked with bidirectional protocol (Code → Doc).

| Doc | Accuracy | Completeness | Critical Gaps |
|-----|----------|--------------|---------------|
| `persona-system-guide.md` | ~92% | **65%** | Duplicate service implementations, chat integration unclear |
| `prompt-manager.md` | ~90% | **50%** | Missing `get_system_prompt_and_persona()` method entirely |
| `llm-service.md` | ~95% | **16%** | 0% config docs, 0% method docs, 138 items only 22 covered |
| `chat-service-implementation.md` | ~95% | **45%** | 0/9 conversation endpoints, 0/14 streaming endpoints |
| `kb-agent-overview.md` | ~95% | **30%** | Entire game engine undocumented (commands, NPCs, quests, state) |
| `database-architecture.md` | ~95% | **68%** | Missing personas tables (critical!), 60+ indexes undocumented |
| `api-contracts.md` | 100% | **15%** | Only 28 of 180 endpoints documented |
| `kb-endpoints.md` | 93% | **33%** | 30 endpoints missing across 8 categories |

### Key Insights from Phase 2

1. **Pattern: High Accuracy, Low Completeness**
   - Average accuracy: ~94% (docs are correct about what they cover)
   - Average completeness: **40%** (docs only cover 40% of what exists)

2. **Root Cause: Docs frozen at "Phase 0"**
   - Documentation written when features were planned/basic
   - Code evolved through multiple phases
   - Docs never updated to match implementation growth

3. **Most Critical Gaps**:
   - **kb-agent-overview.md** (30%): Describes "knowledge interpreter" but code is a full game engine
   - **llm-service.md** (16%): High-level overview, no configuration or usage details
   - **api-contracts.md** (15%): Only auth endpoints documented

4. **Architectural Issues Discovered**:
   - Duplicate persona service implementations (which is canonical?)
   - PromptManager not actually used in current chat flow?
   - Two RBAC migrations (003 vs 004) - which is planned?

### Recommended Actions

**Tier 1 - Critical (affects production understanding)**:
- [ ] Add personas tables to database-architecture.md
- [ ] Document game command system in kb-agent (or create new doc)
- [ ] Clarify which persona service implementation is canonical

**Tier 2 - High (developer productivity)**:
- [ ] Add llm-service.md configuration section
- [ ] Document conversation management endpoints
- [ ] Add streaming infrastructure docs

**Tier 3 - Moderate (completeness)**:
- [ ] Expand api-contracts.md per TODO section
- [ ] Expand kb-endpoints.md per TODO section
- [ ] Add index documentation to database-architecture.md

---

## Verification Queue (Priority Order)

### Priority 1: Core Architecture
- [x] docs/reference/chat/chat-service-implementation.md ✅ 2025-12-06 (2 issues)
- [x] docs/reference/services/llm-service.md ✅ 2025-12-04 (3 issues)
- [x] docs/reference/services/kb-agent-overview.md ✅ 2025-12-06 (2 issues, 1 CODE FIX needed)
- [ ] docs/reference/database/database-architecture.md

### Priority 2: API Reference
- [ ] docs/reference/api/api-contracts.md
- [ ] docs/reference/api/kb-endpoints.md

### Priority 3: Everything Else
- [ ] Remaining 384 docs

---

## Session Log

### 2025-12-04 (Protocol Development)
- Discovered previous verification had ~40% false positive rate
- Developed 7-stage anti-hallucination protocol
- Tested on 2 docs: 12 real issues found, 0 false positives
- Protocol validated and documented

### Previous Sessions (Unreliable)
Previous "verification complete" claims used unreliable method. Those results should not be trusted.

---

## guides/ (53 files) — PILOT CATEGORY

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| ⏳ | | | | |

*Run `ls docs/guides/*.md` and populate*

---

## reference/ (98 files)

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| ⏳ | | | | |

---

## concepts/ (58 files)

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| ⏳ | | | | |

---

## scratchpad/ (58 files)

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| ⏳ | | | | |

---

## _internal/ (86 files)

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| ⏳ | | | | |

---

## Root Level (11 files)

| File | Age | Status | Decision | Notes |
|------|-----|--------|----------|-------|
| README.md | | ⏳ | | |
| README-FIRST.md | | ⏳ | | Tested prev session - 1 broken link |
| +docs.md | | ✅ | PROMOTE | Fix file count 231→390, remove MISSING tag |
| chat-routing-and-kb-architecture.md | | 🔧 | NEEDS_UPDATE | Fix 2 method references |
| kb-fastmcp-claude-code-setup.md | | 🔧 | NEEDS_UPDATE | Invalid CLI cmds, fake REST endpoints |
| kb-fastmcp-integration-status.md | | ✅ | PROMOTE | Clean - no issues |
| kb-fastmcp-mcp-client-config.md | | ⏳ | | |
| kb-semantic-search-implementation.md | | ⏳ | | |
| nats-realtime-integration-guide.md | | ✅ | PROMOTE | Minor: update status label |
| persona-update-testing.md | | ⏳ | | |
| unity-chatclient-feedback-action-items.md | | ⏳ | | |

---

## analysis/ (11 files) — PRE-VERIFIED

| File | Status | Notes |
|------|--------|-------|
| 00-analysis-plan.md | ✅ Promoted | Created 2025-11-20 |
| 01-git-history.md | ✅ Promoted | Created 2025-11-20 |
| 02-codebase-structure.md | ✅ Promoted | Created 2025-11-20 |
| 03-technical-debt.md | ✅ Promoted | Created 2025-11-20 |
| 04-complexity-analysis.md | ✅ Promoted | Created 2025-11-20 |
| 05-experience-system.md | ✅ Promoted | Created 2025-11-20 |
| 06-data-flows.md | ✅ Promoted | Created 2025-11-20 |
| 07-SYNTHESIS.md | ✅ Promoted | Created 2025-11-20 |
| 08-features.md | ✅ Promoted | Created 2025-11-20 |

---

---

## Small Directories (11 files total)

### _planning/ (4 files) — PRE-VERIFIED (our tracking files)
| File | Status | Notes |
|------|--------|-------|
| PLAN.md | ✅ | Created 2025-11-20 |
| SESSION-LOG.md | ✅ | Created 2025-11-20 |
| DOC-VERIFICATION-TRACKER.md | ✅ | This file |
| DOC-VERIFICATION-PROMPT.md | ✅ | Created 2025-11-20 |

### unified-state-model/ (3 files)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### designs/ (2 files)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### experiences/ (2 files)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### fixes/ (1 file)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### personas/ (1 file)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### technical-design/ (1 file)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

### unity/ (1 file)
| File | Status | Notes |
|------|--------|-------|
| ⏳ | | |

---

## Batch Verification Notes

Use Reviewer agent in parallel batches of 3-5 docs:
```
Task(subagent_type="reviewer", prompt="Verify docs/path/file.md...")
```

See DOC-VERIFICATION-PROMPT.md for full instructions.