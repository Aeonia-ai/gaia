---
name: doc-health
description: |
  Documentation health management: verification against code and consolidation of overlapping docs.
  Use when: user asks to verify docs, consolidate docs, check doc accuracy, merge duplicate docs,
  or resolve documentation conflicts. Also use proactively when you notice doc/code mismatches.
---

# Doc Health Skill

Manages documentation accuracy and organization through two core capabilities:

## Capabilities

### 1. Verification (`/doc-health verify`)
Verify documentation claims against source code using the 7-stage anti-hallucination protocol.

**When to use:**
- User asks "is this doc accurate?"
- User asks to verify a doc against code
- You notice a doc claim that seems wrong
- Before consolidating docs (to resolve factual conflicts)

**Invoke:** Read `verify-protocol.md` for the full protocol.

### 2. Consolidation (`/doc-health consolidate`)
Merge overlapping docs, resolve conflicts, and organize into coherent structure.

**When to use:**
- User asks to merge or consolidate docs
- User asks to reduce doc count
- User asks to organize documentation
- Multiple docs cover the same topic

**Invoke:** Read `consolidate-protocol.md` for the full protocol.

## How to Invoke

### ⚠️ CRITICAL: Always Use a Subagent

**DO NOT verify docs yourself in the main conversation.** Cognitive load from managing context, todos, and conversation leads to missed issues.

**ALWAYS delegate to a focused subagent:**

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    Read .claude/skills/doc-health/verify-protocol.md and follow it exactly.

    Verify: [DOC_PATH]

    Against code in:
    - [relevant code directory or files]

    Return a structured verification report with:
    1. All 7 stages completed
    2. Findings table with severity and confidence
    3. Specific code citations for every claim
    """
)
```

### Why Subagent is Required

| Approach | False Positive Rate | Issues Missed |
|----------|--------------------:|-------------:|
| Main conversation | ~15% | High (distracted) |
| Dedicated subagent | ~0% | Low (focused) |

The subagent has ONE job: verify this doc. No todos, no conversation history, no distractions.

## Quick Reference

| Task | Method | Protocol File |
|------|--------|---------------|
| Verify doc against code | **Task(reviewer)** - always | `verify-protocol.md` |
| Consolidate docs | **Task(reviewer)** - always | `consolidate-protocol.md` |
| Check doc health report | Ask (simple lookup) | Uses tracker |

## Complete Workflow: Verify → Review → Fix → Track

### Step 1: Verify (Reviewer Subagent)
```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    Read .claude/skills/doc-health/verify-protocol.md and follow it exactly.
    Verify: [DOC_PATH]
    Against code in: [CODE_PATHS]

    Output BOTH:
    1. Human-readable markdown report
    2. Structured JSON for fix pipeline
    """
)
```

**Output:** Markdown report + JSON with `affected_text` and `replacement_text` for each issue.

### Step 2: Human Review (User)
Present the JSON issues to user. They approve/reject each:
```json
{"issue_id": "001", "approved": true}
{"issue_id": "002", "approved": false, "reviewer_notes": "false positive"}
```

### Step 3: Fix (Coder Subagent)
```python
Task(
    subagent_type="coder",
    model="sonnet",
    prompt="""
    Read .claude/skills/doc-health/fix-protocol.md and follow it exactly.

    Apply these approved fixes:
    [PASTE APPROVED ISSUES JSON]
    """
)
```

**Output:** JSON with status (FIXED/SKIPPED/FAILED) for each issue.

### Step 4: Update Tracker
Add entry to `docs/_planning/DOC-VERIFICATION-TRACKER.md`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOC-HEALTH WORKFLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐      │
│  │  REVIEWER   │────▶│    HUMAN     │────▶│   CODER     │      │
│  │  Subagent   │     │   REVIEW     │     │  Subagent   │      │
│  │             │     │              │     │             │      │
│  │ verify-     │     │ approve/     │     │ fix-        │      │
│  │ protocol.md │     │ reject JSON  │     │ protocol.md │      │
│  └─────────────┘     └──────────────┘     └─────────────┘      │
│        │                                        │               │
│        ▼                                        ▼               │
│   Markdown +                              FIXED/SKIPPED/        │
│   JSON issues                             FAILED JSON           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MAIN CLAUDE                           │   │
│  │  • Orchestrates workflow                                 │   │
│  │  • Presents findings to user                             │   │
│  │  • Updates tracker after fixes                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Step | Subagent | Why Separate? |
|------|----------|---------------|
| Verify | reviewer | Focused on finding issues, no distraction |
| Fix | coder | Focused on applying edits precisely |
| Main | you | Coordinates, presents to user, updates tracker |

**Key insight:** Each subagent has ONE job. Less cognitive load = higher quality.

## Key Principles

1. **Code is truth** - When doc disagrees with code, doc is wrong
2. **No guessing** - Say "UNCERTAIN" instead of fabricating
3. **Citation required** - Every claim needs exact quotes from source
4. **Fix as you go** - Don't batch fixes, fix immediately after user confirms
5. **Track progress** - Update `docs/_planning/DOC-VERIFICATION-TRACKER.md`

## Files in This Skill

| File | Purpose | Used By |
|------|---------|---------|
| `SKILL.md` | Overview and workflow | Main Claude |
| `verify-protocol.md` | 7-stage verification + JSON output | reviewer subagent |
| `fix-protocol.md` | Apply approved edits | coder subagent |
| `consolidate-protocol.md` | Merge overlapping docs | reviewer subagent |
| `conflict-resolution.md` | Handle doc conflicts | reviewer subagent |

## Progress Tracking

All progress tracked in: `docs/_planning/DOC-VERIFICATION-TRACKER.md`

## Background

This skill was developed after discovering that naive LLM verification had ~40% false positive rate (claiming issues that didn't exist). The 7-stage protocol achieves 0% false positives by forcing exact citations.

See `DocProcessingMethod.md` in project root for full rationale and research basis.
