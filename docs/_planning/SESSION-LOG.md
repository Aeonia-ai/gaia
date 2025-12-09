# Session Log

Cross-session memory for Claude. Each session adds an entry summarizing what was done and what's next.

---

## 2025-12-04 Session: Anti-Hallucination Verification Protocol

**Duration:** Extended session

**Problem Discovered:**
- Manual doc verification had **~40% false positive rate** - claimed issues that didn't exist
- I (Claude) was confidently stating discrepancies without actually reading the code
- Example: Claimed `JSONB` was stored as "JSON string" - but migration clearly shows `JSONB`
- Example: Claimed `/current` vs `/me` endpoint mismatch - but code says `/current`

**Root Cause:**
LLMs pattern-match and generate plausible-sounding claims without grounding in actual code. This is the default behavior unless explicitly constrained.

**Solution Developed:**
Enhanced 7-Stage Anti-Hallucination Protocol that forces:
1. **Exact citations** - Must quote BOTH doc AND code (copy-paste)
2. **File tracking** - List all files actually read at end
3. **Negation handling** - "NOT" claims require positive evidence
4. **Cross-claim consistency** - Check for contradictions between claims
5. **Confidence calibration** - Mark uncertain findings for human review

**Test Results:**
| Approach | Issues Found | False Positives |
|----------|--------------|-----------------|
| My "manual" | 21 | ~8-10 (40%) |
| Basic Sonnet | 11 | ~1-2 (15%) |
| Anti-halluc v1 | 4 | 0 |
| **Enhanced v2** | **8** | **0** |

**Files Created/Updated:**
- `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md` - Full 7-stage protocol
- `scripts/doc-verify/ANTI_HALLUCINATION_PROMPT.md` - Simpler v1 prompt
- `scripts/doc-verify/CONCEPTUAL_VERIFICATION.md` - Research basis
- `.claude/agents/reviewer.md` - Added doc verification section
- `CLAUDE.md` - Updated Documentation Verification section
- `docs/_planning/PLAN.md` - Updated with new protocol

**Key Learnings:**
1. **Forcing citations works** - Can't fabricate if you must quote exact text
2. **Sonnet outperformed my manual verification** - I was the unreliable one
3. **Multi-stage catches more** - v2 found 8 real issues vs v1's 4
4. **Research validates approach** - Academic studies show 5-105% grounding improvement

**Next Steps:**
- Ready to verify all 386 docs using the protocol
- Each verification should use Sonnet subagent with full protocol
- Track: docs verified, issues found, files read

---

## 2025-11-20 Session

**Duration:** Extended session

**Completed:**
- Disabled Louisa's NPC tools for pure conversational testing
- Fixed tools_section pollution in unified_chat.py
- Committed and pushed: `8dbe2b2` feat(chat): Disable NPC tools
- Completed 7-phase codebase analysis:
  - Phase 1: Git History (95 commits)
  - Phase 2: Codebase Structure (164 files, 6 services)
  - Phase 3: Technical Debt (60 TODOs, 33 kludges)
  - Phase 4: Complexity (kb_agent.py God class)
  - Phase 5: Experience System (command/state architecture)
  - Phase 6: Data Flows (3 scenarios traced)
  - Phase 7: Synthesis (roadmap + recommendations)
- Created 08-features.md feature catalog
- Established docs consolidation strategy (two-tier system)
- Created _planning/ directory for cross-session persistence

**Key Findings:**
- 386 markdown files in docs/ — needs consolidation
- kb_agent.py at 3,932 lines — needs decomposition
- NPC double-hop adds 100ms latency — needs refactor
- 11,000+ lines dead code — ready to delete

**Files Created:**
- `docs/analysis/2025-11-nov/00-analysis-plan.md`
- `docs/analysis/2025-11-nov/01-git-history.md`
- `docs/analysis/2025-11-nov/02-codebase-structure.md`
- `docs/analysis/2025-11-nov/03-technical-debt.md`
- `docs/analysis/2025-11-nov/04-complexity-analysis.md`
- `docs/analysis/2025-11-nov/05-experience-system.md`
- `docs/analysis/2025-11-nov/06-data-flows.md`
- `docs/analysis/2025-11-nov/07-SYNTHESIS.md`
- `docs/analysis/2025-11-nov/08-features.md`
- `docs/_planning/PLAN.md`
- `docs/_planning/SESSION-LOG.md`

**Next Session:**
- Continue doc verification with Reviewer agent
- Fix issues found in verified docs
- Consider starting Sprint 1 (delete dead code)

---

## 2025-11-20 Session (Continued)

**Additional Work:**
- Tested agent-based doc verification approach
- Deleted bash script (too dumb for semantic verification)
- Tested Reviewer agent on 3 docs:
  - README-FIRST.md → PROMOTE (fix 1 broken link)
  - command-reference.md → NEEDS_UPDATE (fix script refs)
  - command-system-refactor-proposal.md → PROMOTE (convert to ADR)
- Key insight: Don't archive valid docs, fix them in place
- Reorganization deferred to later integration pass
- Updated PLAN.md with agent-based approach

**Files Modified:**
- `docs/_planning/PLAN.md` — Updated strategy
- `docs/_planning/DOC-VERIFICATION-TRACKER.md` — Created
- Deleted `docs/_planning/verify-doc.sh` — Script too simplistic

---

## 2025-12-04 Session

**Duration:** Extended session

**Completed:**
- Full verification pass: All 390 docs reviewed by Reviewer subagents
- Fix pass: ~62 files fixed (broken links, status headers, K8s→Fly.io, stale markers)
- Re-verified DELETE candidates: Only 1 file (empty designs/README.md) truly deletable
- Deep ADR audit: 7 ADRs verified, fixed duplicate numbering (ADR-003 → ADR-010)
- Fixed stale P0/CRITICAL markers in scratchpad/ (NATS gaps, AOI issue now marked RESOLVED)
- Sample audit: Calibrated false positive rate at 30-60% for PROMOTE designation

**Key Decisions:**
- DON'T add verification timestamps to docs (they rot faster than content)
- DON'T use two-pass verify-then-fix approach (fix issues immediately when found)
- Track verification status in tracker file only, not in doc content
- "PROMOTE" means "no critical blockers" not "perfectly accurate"

**Lessons Learned:**
- Added 116 timestamps, then removed them all — metadata doesn't belong in content
- Haiku model verifies "references exist" but not "references are current"
- ~100-170 docs have subtle issues (stale status, outdated examples) that weren't flagged
- Archive folder contents often valuable (ADRs, operational knowledge) — don't auto-delete

**Files Modified:**
- `docs/_planning/DOC-VERIFICATION-TRACKER.md` — Updated with final stats
- `docs/_planning/DOC-VERIFICATION-PROMPT.md` — Added anti-patterns section
- `docs/_internal/adrs/` — Fixed duplicate ADR-003, standardized index
- `docs/scratchpad/CRITICAL-AOI-FIELD-NAME-ISSUE.md` — Marked RESOLVED
- `docs/scratchpad/nats-world-updates-implementation-analysis.md` — P0 gaps marked DONE
- ~62 other docs with broken links, status headers, implementation clarity

**Next Session:**
- Consider starting Sprint 1 (delete dead code) from PLAN.md
- Or: Continue fixing remaining ~100 NEEDS_UPDATE docs incrementally
- Or: Begin docs reorganization (consolidate duplicates, build navigation)

---

## Template for Future Sessions

```
## YYYY-MM-DD Session

**Duration:**

**Completed:**
-

**Key Decisions:**
-

**Files Modified:**
-

**Next Session:**
-
```
