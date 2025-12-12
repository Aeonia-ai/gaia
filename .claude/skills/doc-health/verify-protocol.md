# Documentation Verification Protocol

## Purpose

Verify documentation **accuracy AND completeness** against source code with **zero false positives**.

This protocol has two phases:
1. **Doc → Code**: Does what's documented actually exist? (Accuracy)
2. **Code → Doc**: Is what exists actually documented? (Completeness)

A doc can be 100% accurate but only 50% complete. We check BOTH.

---

## Phase 1: Accuracy (Doc → Code)

The 7 stages below verify that documented claims are correct.

### Stage 1: Premise Verification

Before checking specific claims, verify the doc's foundational assumptions.

**Check:**
- File structure (directories, file organization)
- Naming conventions (function names, variable patterns)
- Dependencies (libraries, services)
- Architecture (patterns, relationships)

**Format:**
```
PREMISE: [what doc assumes]
VERIFICATION: [evidence - cite specific files/code]
STATUS: VALID | INVALID | UNCERTAIN
```

**If ANY premise is INVALID**, flag prominently - downstream claims may all be affected.

---

### Stage 2: Citation Extraction

For EVERY factual claim in the documentation:

**Rule:** Provide EXACT quotes (copy-paste) from the documentation.

**Format:**
```
CLAIM #[N]: [brief description]

DOC SAYS (file:line):
"[exact copy-paste from documentation]"

CODE LOCATION TO CHECK: [file:line range]
```

If you cannot identify which code to check:
```
CLAIM #[N]: [brief description]
DOC SAYS: "[quote]"
CODE LOCATION: COULD NOT IDENTIFY - [reason]
```

---

### Stage 3: Citation Validation

For each claim, verify the code EXISTS:

**Task:** Actually READ each file:line. Confirm:
1. File exists
2. Line numbers are valid
3. Code at those lines is relevant

**Format:**
```
CLAIM #[N] VALIDATION:
- File exists: YES/NO
- Lines valid: YES/NO
- Code found: "[exact copy-paste from code]"
- Relevant to claim: YES/NO/PARTIALLY
```

If citation was wrong, CORRECT it:
```
CLAIM #[N] VALIDATION:
- CORRECTION: File/line does not contain expected code
- Actual content at [file:line]: "[what's actually there]"
- Revised code location: [new file:line] or COULD NOT LOCATE
```

---

### Stage 4: Semantic Verification

Does code SUPPORT the claim (not just exist)?

**Format:**
```
CLAIM #[N] SEMANTIC CHECK:
DOC CLAIMS: [restate what doc says]
CODE DOES: [describe what code actually does]
MATCH: YES | NO | PARTIAL
EXPLANATION: [why they match or don't]
```

**Critical:** A citation can be ACCURATE (code exists) but UNSUPPORTIVE (code doesn't do what doc claims).

---

### Stage 5: Negation Handling

For claims with negation words (not, never, doesn't, won't, cannot, without):

**Special Rule:** Negated claims require POSITIVE EVIDENCE of absence.

**Examples:**
- "Function does NOT validate input" → Cite code showing input passed without validation
- "This endpoint requires NO authentication" → Cite code handling unauthenticated requests

**Format:**
```
NEGATED CLAIM #[N]: [the claim]
NEGATION TYPE: [does not / never / without / etc.]
POSITIVE EVIDENCE REQUIRED: [what code would prove this]
EVIDENCE FOUND: [cite specific code] or INSUFFICIENT EVIDENCE
STATUS: VERIFIED | UNVERIFIED | CONTRADICTED
```

If no positive evidence, mark as UNVERIFIED (not verified).

---

### Stage 6: Cross-Claim Consistency

Check for contradictions BETWEEN claims in the same document.

**Look for:**
- Function A "calls" function B, but function B is "never called"
- Service X "requires" service Y, but service Y "is optional"
- Parameter "must be" value A, but "defaults to" value B

**Format:**
```
CONSISTENCY CHECK: No contradictions detected.
```
OR
```
POTENTIAL CONTRADICTION #[N]:
- Claim A: [quote]
- Claim B: [quote]
- Conflict: [explain]
- Resolution: ACTUAL CONTRADICTION | FALSE ALARM - [explain]
```

---

### Stage 7: Confidence Calibration

Assign confidence to each finding:

| Level | Meaning |
|-------|---------|
| HIGH | Citation exists, code clearly supports/contradicts, no ambiguity |
| MEDIUM | Citation exists, interpretation required, reasonable confidence |
| LOW | Citation unclear, multiple interpretations possible |
| UNCERTAIN | Could not locate code, evidence is ambiguous |

**Format:**
```
FINDING #[N]: [title]
SEVERITY: CRITICAL | MODERATE | MINOR
CONFIDENCE: HIGH | MEDIUM | LOW | UNCERTAIN
EVIDENCE QUALITY: [brief assessment]
RECOMMENDATION: [fix doc / verify with human / etc.]
```

**Critical Rule:** LOW and UNCERTAIN findings MUST be flagged for human review.

---

## Phase 2: Completeness (Code → Doc)

After verifying accuracy, check if the doc is COMPLETE.

### Step 1: Inventory the Code

Based on the doc's scope, inventory what EXISTS in code:

**Examples by doc type:**
- API doc → List ALL endpoints (grep for `@app.get`, `@app.post`, etc.)
- Database doc → List ALL tables (query actual database)
- Config doc → List ALL settings (grep for env vars, config classes)
- Service doc → List ALL public methods/functions

**Format:**
```
CODE INVENTORY for [scope]:
Total items in code: [N]
- item1
- item2
- ...
```

### Step 2: Compare Coverage

Cross-reference code inventory against doc:

```
COMPLETENESS CHECK:
- Items in code: [N]
- Items documented: [M]
- Coverage: [M/N]%

UNDOCUMENTED ITEMS:
- [item1] - [brief description of what it does]
- [item2] - [brief description]
...
```

### Step 3: Assess Significance

Not every undocumented item is a problem. Categorize:

```
UNDOCUMENTED - CRITICAL (breaks developer understanding):
- [item] - [why it matters]

UNDOCUMENTED - MODERATE (should be added):
- [item] - [why]

UNDOCUMENTED - MINOR (nice to have):
- [item] - [why]

INTENTIONALLY OMITTED (internal/deprecated):
- [item] - [why it's okay to omit]
```

### Step 4: Completeness Verdict

```
COMPLETENESS ASSESSMENT:
- Accuracy: [X]% (Phase 1 result)
- Completeness: [Y]%
- Critical gaps: [N]
- Recommendation: COMPLETE | NEEDS_EXPANSION | RENAME_SCOPE
```

If completeness < 70%, flag for major revision or scope clarification.

---

## Forbidden Behaviors

1. **NO GUESSING** - Say "UNCERTAIN" instead
2. **NO WEASEL WORDS** - "probably", "likely", "seems" are FORBIDDEN
3. **NO CLAIMS WITHOUT CITATIONS** - Every discrepancy needs exact quotes
4. **FALSE POSITIVE = FAILURE** - Claiming fake issues wastes time
5. **NO SKIPPING STAGES** - Complete all 7 even if early stages find nothing
6. **NO PARTIAL FILE READS** - Always read COMPLETE files, never use offset/limit parameters

## ⚠️ CRITICAL: Full File Reads Required

**NEVER use partial file reads (offset/limit parameters) when verifying claims.**

**Why this matters:**
- Partial reads cause FALSE POSITIVES (claiming something doesn't exist when it's just outside your read window)
- Example: A table defined at line 86 will be missed if you only read lines 1-80
- This has caused real verification failures in production

**Rules:**
1. Always read files completely - do NOT pass `offset` or `limit` to Read tool
2. If a file is too large (>25K tokens), use Grep to search for specific patterns first
3. For large files, read in strategic sections but ALWAYS search the full file for the target
4. When claiming "X does not exist in file Y", you MUST have searched the ENTIRE file

**Handling Large Files:**
```
# Instead of partial read:
Read(file_path, offset=0, limit=100)  # ❌ WRONG - misses content after line 100

# Do this:
Grep(pattern="asset_usage", path="migrations/")  # ✅ Search entire directory
Read(file_path)  # ✅ Full file read (will truncate but shows all content)
```

---

## Output Structure

Your output has TWO parts:

### Part 1: Human-Readable Report (Markdown)

```markdown
## Verification Report: [doc path]

### Phase 1: Accuracy (Doc → Code)

#### Stage 1: Premises
[premise verification output]

#### Stage 2-3: Claims Identified & Validated
[claims with citations]

#### Stage 4: Semantic Verification
[match analysis]

#### Stage 5: Negation Analysis
[negated claims if any]

#### Stage 6: Consistency Check
[cross-claim analysis]

#### Stage 7: Accuracy Findings

| # | Issue | Severity | Confidence |
|---|-------|----------|------------|
| 1 | [issue] | [sev] | [conf] |

**Accuracy Score: [X]%** (documented items that are correct)

---

### Phase 2: Completeness (Code → Doc)

#### Code Inventory
[what exists in code within doc's scope]

#### Coverage Analysis
- Items in code: [N]
- Items documented: [M]
- Coverage: [M/N]%

#### Undocumented Items

| Item | Significance | Description |
|------|--------------|-------------|
| [item] | CRITICAL/MODERATE/MINOR | [what it does] |

**Completeness Score: [Y]%**

---

### Summary

| Metric | Score |
|--------|-------|
| Accuracy | [X]% |
| Completeness | [Y]% |
| Recommendation | ACCURATE | NEEDS_FIXES | NEEDS_EXPANSION | MAJOR_REWRITE |

### Files Read
[list every file actually read]

### Human Review Required
[LOW/UNCERTAIN findings]
```

### Part 2: Structured JSON for Fix Pipeline

After the markdown report, output a JSON block that can be used by the fixer subagent:

```json
{
  "doc_path": "docs/reference/services/example.md",
  "verification_date": "2025-12-06",
  "issues": [
    {
      "issue_id": "001",
      "file_path": "docs/reference/services/example.md",
      "line_range": [36, 38],
      "problem_type": "outdated|incorrect|incomplete|inconsistent",
      "severity": "critical|moderate|minor",
      "confidence": 0.95,
      "affected_text": "exact text from doc that needs changing",
      "replacement_text": "suggested replacement based on code",
      "code_evidence": "app/services/example.py:42 shows...",
      "reasoning": "why this is an issue"
    }
  ],
  "summary": {
    "total_issues": 2,
    "critical": 0,
    "moderate": 1,
    "minor": 1,
    "needs_human_review": 1
  }
}
```

**Important:**
- `affected_text` must be EXACT copy-paste from the doc (for find/replace)
- `replacement_text` should be ready to use (no placeholders)
- `confidence` is 0.0-1.0 (issues < 0.8 need human review)
- Include ALL issues, even LOW confidence ones

---

## Invocation

Use the reviewer agent with this protocol:

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    [Paste this entire protocol]

    Verify: [DOC_PATH]

    Against code in:
    - [relevant code files]
    """
)
```

---

## After Verification

### Step 1: Human Review
Present the JSON issues to the user. They mark each as approved or rejected:
```json
{"issue_id": "001", "approved": true, "reviewer_notes": "confirmed"}
{"issue_id": "002", "approved": false, "reviewer_notes": "not actually a problem"}
```

### Step 2: Apply Fixes
Pass approved issues to the fixer subagent:
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

### Step 3: Update Tracker
Add entry to `docs/_planning/DOC-VERIFICATION-TRACKER.md`
