# Enhanced Anti-Hallucination Documentation Verification Protocol v2

Based on academic research on LLM hallucination reduction, citation enforcement, and verification systems.

## Overview

This protocol implements **7 stages** of verification to catch different failure modes:

1. **Premise Verification** - Check foundational assumptions before claims
2. **Citation Extraction** - Force exact quotes from doc AND code
3. **Citation Validation** - Verify cited code EXISTS at stated location
4. **Semantic Verification** - Verify code actually SUPPORTS the claim
5. **Negation Handling** - Special protocol for "NOT" claims
6. **Cross-Claim Consistency** - Check for contradictions between claims
7. **Confidence Calibration** - Route uncertain claims to human review

## The Complete Prompt

```markdown
You are verifying documentation accuracy against source code. The CODE is the SOURCE OF TRUTH.

## ANTI-HALLUCINATION PROTOCOL v2

You MUST complete ALL 7 STAGES in order. Do not skip stages.

---

### STAGE 1: PREMISE VERIFICATION

Before checking specific claims, identify and verify the documentation's foundational assumptions.

**Task**: List assumptions the documentation makes about:
- Codebase structure (directories, file organization)
- Naming conventions (function names, variable patterns)
- Dependencies (libraries, services, databases)
- Architecture (microservices, monolith, patterns)

**For each assumption**:
```
PREMISE: [what the doc assumes]
VERIFICATION: [how you verified it - cite specific evidence]
STATUS: VALID | INVALID | UNCERTAIN
```

If ANY premise is INVALID, flag it prominently - all downstream claims may be affected.

---

### STAGE 2: CITATION EXTRACTION

For EVERY factual claim in the documentation:

**Rule**: You MUST provide EXACT quotes (copy-paste) from BOTH:
- The documentation text
- The source code

**Format for each claim**:
```
CLAIM #[N]: [brief description]

DOC SAYS (file:line):
"[exact copy-paste from documentation]"

CODE LOCATION TO CHECK: [file:line range]
```

If you cannot identify which code to check, write:
```
CLAIM #[N]: [brief description]
DOC SAYS: "[quote]"
CODE LOCATION: COULD NOT IDENTIFY - [reason]
```

---

### STAGE 3: CITATION VALIDATION

For each claim from Stage 2, verify the code EXISTS:

**Task**: Actually read each file:line you identified. Confirm:
1. The file exists
2. The line numbers are valid
3. The code at those lines is relevant to the claim

**Format**:
```
CLAIM #[N] VALIDATION:
- File exists: YES/NO
- Lines valid: YES/NO
- Code found: "[exact copy-paste from code]"
- Relevant to claim: YES/NO/PARTIALLY
```

If you claimed a file:line but cannot find it, you MUST correct:
```
CLAIM #[N] VALIDATION:
- CORRECTION: File/line does not contain expected code
- Actual content at [file:line]: "[what's actually there]"
- Revised code location: [new file:line] or COULD NOT LOCATE
```

---

### STAGE 4: SEMANTIC VERIFICATION

For each validated citation, determine if the code SUPPORTS the documentation claim:

**Question to answer**: Does the code actually do what the documentation says?

**Format**:
```
CLAIM #[N] SEMANTIC CHECK:
DOC CLAIMS: [restate what doc says]
CODE DOES: [describe what code actually does based on your citation]
MATCH: YES | NO | PARTIAL
EXPLANATION: [why they match or don't]
```

**CRITICAL**: A citation can be ACCURATE (code exists) but UNSUPPORTIVE (code doesn't do what doc claims). These are different failures.

---

### STAGE 5: NEGATION HANDLING

For ANY claim containing negation words (not, never, doesn't, won't, cannot, without, absence, lack, etc.):

**Special Protocol**:
Negated claims require POSITIVE EVIDENCE of absence, not just absence of evidence.

**Examples**:
- "Function does NOT validate input" → Must cite code showing input passed without validation
- "This endpoint requires NO authentication" → Must cite code handling unauthenticated requests
- "Will NEVER modify the database" → Must cite code showing read-only operations

**Format for negated claims**:
```
NEGATED CLAIM #[N]: [the claim]
NEGATION TYPE: [does not / never / without / etc.]
POSITIVE EVIDENCE REQUIRED: [what code would prove this]
EVIDENCE FOUND: [cite specific code] or INSUFFICIENT EVIDENCE
STATUS: VERIFIED | UNVERIFIED | CONTRADICTED
```

If you cannot find positive evidence for a negated claim, mark as UNVERIFIED, not as verified.

---

### STAGE 6: CROSS-CLAIM CONSISTENCY

After verifying individual claims, check for contradictions BETWEEN claims:

**Task**: Review all verified claims. Identify any pairs that contradict each other.

**Look for**:
- Function A "calls" function B, but function B is "never called"
- Service X "requires" service Y, but service Y "is optional"
- Parameter "must be" value A in one place, "defaults to" value B elsewhere
- Timing claims that conflict (sync vs async, immediate vs deferred)

**Format**:
```
CONSISTENCY CHECK:

POTENTIAL CONTRADICTION #[N]:
- Claim A: [quote]
- Claim B: [quote]
- Conflict: [explain the contradiction]
- Resolution: [ACTUAL CONTRADICTION | FALSE ALARM - explain]
```

If no contradictions found:
```
CONSISTENCY CHECK: No contradictions detected between verified claims.
```

---

### STAGE 7: CONFIDENCE CALIBRATION

For each finding, assign a confidence level:

**Confidence Levels**:
- HIGH: Citation exists, code clearly supports/contradicts claim, no ambiguity
- MEDIUM: Citation exists, interpretation required, reasonable confidence
- LOW: Citation unclear, multiple interpretations possible, or partial evidence
- UNCERTAIN: Could not locate code, or evidence is ambiguous

**Format for final findings**:
```
FINDING #[N]: [title]
SEVERITY: CRITICAL | MODERATE | MINOR
CONFIDENCE: HIGH | MEDIUM | LOW | UNCERTAIN
EVIDENCE QUALITY: [brief assessment]
RECOMMENDATION: [what to do - fix doc, verify with human, etc.]
```

**CRITICAL RULE**: LOW and UNCERTAIN findings MUST be flagged for human review. Do not present them as definitive.

---

## OUTPUT STRUCTURE

Your response MUST follow this structure:

### 1. PREMISE VERIFICATION
[Stage 1 output]

### 2. CLAIMS IDENTIFIED
[Stage 2 output - list all claims]

### 3. CITATION VALIDATION
[Stage 3 output - verify each citation]

### 4. SEMANTIC VERIFICATION
[Stage 4 output - check if code supports claims]

### 5. NEGATION ANALYSIS
[Stage 5 output - special handling for NOT claims]

### 6. CONSISTENCY CHECK
[Stage 6 output - cross-claim analysis]

### 7. FINAL FINDINGS

[List each discrepancy with confidence level]

### 8. FILES VERIFIED

[Complete list of every file you actually read, with line ranges]

### 9. CLAIMS MARKED FOR HUMAN REVIEW

[List any LOW or UNCERTAIN confidence findings]

---

## FORBIDDEN BEHAVIORS

1. **NO GUESSING**: If you don't know, say "UNCERTAIN"
2. **NO WEASEL WORDS**: "probably", "likely", "seems", "appears" are FORBIDDEN
3. **NO CLAIMS WITHOUT CITATIONS**: Every claim needs exact quotes
4. **NO FALSE CONFIDENCE**: LOW confidence findings are not failures - hiding uncertainty IS a failure
5. **NO SKIPPING STAGES**: Complete all 7 stages even if early stages find no issues

---

## YOUR TASK

Verify: [DOC_PATH]

Against code in: [CODE_FILES]

Complete all 7 stages. Be thorough. Be honest about uncertainty.
```

## Usage

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    [PASTE PROTOCOL ABOVE]

    Verify: docs/reference/services/persona-system-guide.md

    Against code in:
    - app/services/chat/persona_service_postgres.py
    - app/services/chat/personas.py
    - app/shared/prompt_manager.py
    - migrations/005_create_personas_tables.sql
    - app/services/chat/unified_chat.py
    - app/models/persona.py
    """
)
```

## Why 7 Stages?

| Stage | Failure Mode Caught |
|-------|---------------------|
| 1. Premise | Doc's foundational assumptions are wrong |
| 2. Citation Extraction | Claims identified but not grounded |
| 3. Citation Validation | Citations are fabricated/wrong locations |
| 4. Semantic Verification | Code exists but doesn't support claim |
| 5. Negation Handling | "NOT" claims verified by absence (wrong) |
| 6. Cross-Claim Consistency | Individual claims ok but contradict each other |
| 7. Confidence Calibration | Uncertain findings presented as certain |

## Research Basis

- Citation enforcement: 5-105% improvement in grounding [arxiv 2305.13252]
- Premise verification: 94.3% accuracy when false premises detected [arxiv 2504.06438]
- Multi-agent debate: 2.6-5.8% improvement over single-agent [arxiv 2507.19090]
- Negation failures: Known LLM weakness requiring special handling [arxiv 2406.05494]
- Confidence calibration: Prevents overconfident errors [MIT Thermometer research]
- Temperature=0 for accuracy: "When consistency and accuracy matter, set temperature low (~0)" [Voiceflow 2024]
- Human-in-the-loop: "Retain domain experts to review critical judgments" [Turing 2024]

## Process Recommendations (Added 2025-12-04)

Based on web research on hallucination reduction:

1. **Fix as you go** - Don't batch fixes to the end. Fix each doc immediately after verification.
2. **Temperature=0** - Use low temperature for accuracy-focused tasks.
3. **Human review required** - Every subagent finding needs manual verification before acting.
4. **1-3 docs per batch** - Verify small batches with human review between.
