# Current Plan: Documentation Verification & Platform Improvement

**Last Updated:** 2025-12-04
**Status:** Active

---

## Primary Goal

Verify and fix 386 documentation files using AI agent-based review, with reorganization deferred to a later integration pass.

---

## Documentation Verification

### ⚠️ CRITICAL: Use the 7-Stage Anti-Hallucination Protocol

**Why this matters (learned 2025-12-04):**
- Manual LLM verification: **~40% false positive rate** (claimed issues that didn't exist)
- Basic LLM subagent: **~15% false positive rate**
- Enhanced 7-Stage Protocol: **0% false positive rate**

**Root cause**: LLMs confidently claim discrepancies without actually reading code. The protocol forces exact citations.

### Protocol Location

- Full protocol: `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md`
- Updated reviewer agent: `.claude/agents/reviewer.md`
- CLAUDE.md section: "Documentation Verification"

### The 7 Stages (Summary)

1. **Premise Verification** - Check doc's foundational assumptions first
2. **Citation Extraction** - Identify ALL claims with exact doc quotes
3. **Citation Validation** - Verify cited code EXISTS at stated locations
4. **Semantic Verification** - Verify code SUPPORTS the claim
5. **Negation Handling** - "NOT" claims require positive evidence of absence
6. **Cross-Claim Consistency** - Check for contradictions BETWEEN claims
7. **Confidence Calibration** - Mark uncertain findings for human review

### Key Rules

- **NO CLAIMS WITHOUT CITATIONS** - Exact quotes from BOTH doc AND code
- **NO GUESSING** - Say "UNCERTAIN" or "COULD NOT LOCATE"
- **FALSE POSITIVE = FAILURE** - Worse than missing a real issue

### How To Verify a Doc

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    [Use protocol from scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md]

    Verify: docs/path/to/doc.md

    Against code in:
    - [list relevant code files]
    """
)
```

### Verdict Categories

- **ACCURATE** - No significant discrepancies, doc matches code
- **NEEDS_UPDATE** - Valuable but has issues (then fix them)
- **CRITICALLY_WRONG** - Major architectural/behavioral mismatches
- **DELETE** - Redundant or obsolete

### Decisions from Testing

| Doc | Decision | Confidence | Action |
|-----|----------|------------|--------|
| README-FIRST.md | PROMOTE | 0.95 | Fix 1 broken link |
| command-reference.md | NEEDS_UPDATE | 0.85 | Fix script references |
| command-system-refactor-proposal.md | PROMOTE | 0.95 | Convert to ADR later |

### Progress

| Directory | Total | Verified | Fixed | Deleted |
|-----------|-------|----------|-------|---------|
| analysis/ | 11 | 11 | 0 | 0 |
| root level | 12 | 1 | 0 | 0 |
| guides/ | 53 | 1 | 0 | 0 |
| scratchpad/ | 58 | 1 | 0 | 0 |
| reference/ | 98 | 0 | 0 | 0 |
| concepts/ | 58 | 0 | 0 | 0 |
| _internal/ | 86 | 0 | 0 | 0 |
| **TOTAL** | **386** | **14** | **0** | **0** |

### Future: Integration & Reorganization Pass

After all docs are verified and fixed:
- Consolidate duplicates
- Create logical folder structure
- Build index/navigation
- Target: <100 well-organized docs

---

## Platform Improvements (from Analysis)

### Sprint 1: Cleanup (1-2 days)
- [ ] Delete `_archive_2025_01/` directory (~7,231 lines)
- [ ] Delete `game_commands_legacy_hardcoded.py` (~3,326 lines)
- [ ] Delete `.disabled` files (~500 lines)
- [ ] Consolidate RBAC implementations

### Sprint 2: NPC Refactor (2-3 days)
- [ ] Create `npc_dialogue.py` handler in KB service
- [ ] Move persona definitions to KB markdown
- [ ] Remove hardcoded persona_id="louisa"
- [ ] Deprecate `talk.py` HTTP kludge

### Sprint 3: kb_agent.py Decomposition (3-5 days)
- [ ] Extract `prompts/prompt_builder.py`
- [ ] Create `agents/knowledge_agent.py`
- [ ] Create `agents/game_agent.py`
- [ ] Thin out kb_agent.py to facade

### Sprint 4: Live Transform Editing (2-3 days)
- [ ] Add transform to spot schema
- [ ] Implement `@edit spot` admin command
- [ ] Unity: Handle transform updates

---

## Key Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total docs | 386 | <100 (after reorg) |
| Verified docs | 14 | 386 |
| kb_agent.py lines | 3,932 | <500 |
| Dead code lines | 11,000+ | 0 |

---

## References

- Analysis: `docs/analysis/2025-11-nov/`
- Features: `docs/analysis/2025-11-nov/08-features.md`
- Synthesis: `docs/analysis/2025-11-nov/07-SYNTHESIS.md`
