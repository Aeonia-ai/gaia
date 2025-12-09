# Documentation Verification Prompt

Use this prompt to verify docs accurately across sessions.

---

## ⚠️ CRITICAL: Use 7-Stage Anti-Hallucination Protocol

**Previous verification was unreliable** (~40% false positive rate).

The new protocol achieves **0% false positives** by forcing exact citations.

**Full protocol:** `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md`

---

## The Goal

**Make docs useful for developers building on GAIA.**

- Verify docs accurately describe code behavior
- Code is the source of truth
- 0 false positives (claiming issues that don't exist is WORSE than missing issues)

---

## The Three Phases

### Phase 1: Verify (CURRENT - RESTART REQUIRED)
- Previous "verification" used unreliable method
- Must re-verify all 390 docs using 7-stage protocol
- Currently verified: **2 of 390** (0.5%)

### Phase 2: Fix
- Fix docs that have verified issues
- Don't fix without verifying first

### Phase 3: Integrate (AFTER VERIFICATION)
- Group related docs by topic
- Merge overlapping content
- Target: 390 → ~100 well-organized docs

---

## Quick Start

When user says "verify docs" or "continue verification":

1. Check `docs/_planning/DOC-VERIFICATION-TRACKER.md` for progress
2. Pick next doc from priority queue
3. Run 7-stage verification
4. Update tracker with results

---

## How To Verify a Doc

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
You are verifying documentation accuracy against source code. The CODE is the SOURCE OF TRUTH.

## ANTI-HALLUCINATION PROTOCOL v2

You MUST complete ALL 7 STAGES in order.

### STAGE 1: PREMISE VERIFICATION
Verify doc's foundational assumptions (file structure, naming, architecture).

### STAGE 2: CITATION EXTRACTION
For EVERY factual claim:
```
CLAIM #N: [description]
DOC SAYS (file:line): "[exact quote]"
CODE LOCATION: [file:line]
```

### STAGE 3: CITATION VALIDATION
Actually READ each code location. Quote the actual code.

### STAGE 4: SEMANTIC VERIFICATION
Does code SUPPORT the claim (not just exist)?
```
DOC CLAIMS: [what doc says]
CODE DOES: [what code does]
MATCH: YES | NO | PARTIAL
```

### STAGE 5: NEGATION HANDLING
For "NOT/NEVER/WITHOUT" claims, require POSITIVE EVIDENCE of absence.

### STAGE 6: CROSS-CLAIM CONSISTENCY
Check for contradictions BETWEEN claims.

### STAGE 7: CONFIDENCE CALIBRATION
Assign: HIGH | MEDIUM | LOW | UNCERTAIN
Mark LOW/UNCERTAIN for human review.

## FORBIDDEN BEHAVIORS
1. NO GUESSING - Say "UNCERTAIN"
2. NO WEASEL WORDS - "probably", "likely" FORBIDDEN
3. NO CLAIMS WITHOUT CITATIONS
4. FALSE POSITIVE = FAILURE

## YOUR TASK

Verify: [DOC_PATH]

Against code in:
- [list relevant code files]

Complete all 7 stages. List FILES VERIFIED at the end.
"""
)
```

---

## After Verification

Update `DOC-VERIFICATION-TRACKER.md`:

1. Add doc to appropriate category (ACCURATE / NEEDS_UPDATE / CRITICALLY_WRONG)
2. List specific issues found (with line numbers)
3. Update progress counts

---

## Verification Priority

### Priority 1: Core Architecture
- docs/reference/chat/chat-service-implementation.md
- docs/reference/services/llm-service.md
- docs/reference/services/kb-agent-overview.md
- docs/reference/database/database-architecture.md

### Priority 2: API Reference
- docs/reference/api/api-contracts.md
- docs/reference/api/kb-endpoints.md

### Priority 3: Everything Else
- Remaining 384 docs

---

## Key Rules

| Rule | Why |
|------|-----|
| **NO CLAIMS WITHOUT CITATIONS** | Can't fabricate if you must quote exact text |
| **NO GUESSING** | Say "UNCERTAIN" instead of making things up |
| **NEGATION REQUIRES PROOF** | "Does NOT" needs evidence of absence |
| **FALSE POSITIVE = FAILURE** | Claiming fake issues wastes time fixing nothing |
| **TRACK FILES READ** | Can't claim you verified what you didn't read |

---

## ⚠️ Anti-Patterns

### DON'T skip the 7 stages
```
# ❌ WRONG:
"I checked the doc and it looks accurate"

# ✅ RIGHT:
Complete all 7 stages with exact citations
```

### DON'T guess about code
```
# ❌ WRONG:
"The code probably does X"

# ✅ RIGHT:
"CODE SAYS (file:line): '[exact quote]'"
```

### DON'T claim issues without evidence
```
# ❌ WRONG:
"This doc has issues with caching behavior"

# ✅ RIGHT:
"DOC SAYS (line 76): 'cached for 1 hour'
CODE SAYS (file.py:220): 'ex=300' (5 minutes)
DISCREPANCY: YES"
```

---

## Remember

- **Code is truth** — If doc disagrees with code, doc is wrong
- **Citation or nothing** — No quotes = no claim
- **Uncertainty is okay** — "UNCERTAIN" is better than wrong
- **Update tracker** — Progress only counts when recorded
