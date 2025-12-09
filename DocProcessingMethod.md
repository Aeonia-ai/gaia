# Documentation Verification Process

## Overview

This document describes the complete process for verifying technical documentation accuracy against source code. The process was developed after discovering that manual LLM verification had a ~40% false positive rate (claiming issues that didn't exist).

**Goal:** Make docs useful for developers by ensuring they accurately describe code behavior.

**Key Principle:** Code is the source of truth. If doc disagrees with code, doc is wrong.

---

## Current Results

| Metric | Value |
|--------|-------|
| Total docs to verify | 390 |
| Verified with 7-stage protocol | 4 |
| False positive rate | 0% (0/5 findings were fake) |
| Issues found | 5 real issues across 2 docs |

---

## The 7-Stage Anti-Hallucination Protocol

### Why This Protocol Exists

In testing, we found:
- **Manual LLM verification**: ~40% false positive rate
- **Basic subagent verification**: ~15% false positive rate
- **7-Stage Protocol**: **0% false positive rate**

The problem: LLMs confidently claim discrepancies without actually reading the code. The protocol forces exact citations from BOTH doc AND code.

### The 7 Stages

#### Stage 1: Premise Verification
Check doc's foundational assumptions (file structure, naming conventions, architecture) before examining specific claims.

#### Stage 2: Citation Extraction
For EVERY factual claim, provide exact quotes:
```
CLAIM #N: [description]
DOC SAYS (file:line): "[exact quote]"
CODE LOCATION TO CHECK: [file:line]
```

#### Stage 3: Citation Validation
Actually READ each code location. Confirm file exists, lines are valid, code is relevant.

#### Stage 4: Semantic Verification
Does code SUPPORT the claim (not just exist)?
```
DOC CLAIMS: [what doc says]
CODE DOES: [what code does]
MATCH: YES | NO | PARTIAL
```

#### Stage 5: Negation Handling
For "NOT/NEVER/WITHOUT" claims, require POSITIVE EVIDENCE of absence:
```
NEGATED CLAIM: "Function does NOT validate input"
POSITIVE EVIDENCE REQUIRED: Code showing input passed without validation
STATUS: VERIFIED | UNVERIFIED | CONTRADICTED
```

#### Stage 6: Cross-Claim Consistency
Check for contradictions BETWEEN claims in the same doc.

#### Stage 7: Confidence Calibration
Assign confidence: HIGH | MEDIUM | LOW | UNCERTAIN
Mark LOW/UNCERTAIN for human review.

### Forbidden Behaviors

1. **NO GUESSING** - Say "UNCERTAIN" instead
2. **NO WEASEL WORDS** - "probably", "likely", "seems" are FORBIDDEN
3. **NO CLAIMS WITHOUT CITATIONS** - Every discrepancy needs exact quotes
4. **FALSE POSITIVE = FAILURE** - Claiming fake issues wastes time

---

## Process Workflow

### Current Process (Fix-As-You-Go)

1. **Verify doc** with reviewer subagent using 7-stage protocol
2. **Manual review** of findings (currently done, may skip if 0% false positive rate holds)
3. **Fix confirmed issues** immediately
4. **Update tracker** with results
5. **Move to next doc**

### Why Fix-As-You-Go

Research recommends this over batch verification:
- Context is fresh - you just verified the issues
- Prevents backlog - 390 docs × 3 issues = 1000+ fixes to remember later
- Validates the fix - can confirm it addresses the actual issue

---

## File Organization

### Current Structure (6 files - scattered)

| File | Purpose |
|------|---------|
| `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md` | Full 7-stage prompt |
| `docs/_planning/DOC-VERIFICATION-PROMPT.md` | How to use the protocol |
| `docs/_planning/DOC-VERIFICATION-TRACKER.md` | Progress tracking |
| `docs/_planning/CONTINUE-VERIFICATION.md` | Session continuation prompt |
| `.claude/agents/reviewer.md` | Agent with doc verification section |
| `CLAUDE.md` | Summary reference |

### Recommended Structure (3 files - consolidated)

Based on [Anthropic's Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices):
> "For repeated workflows, store prompt templates in `.claude/commands` folder."

| File | Purpose |
|------|---------|
| `.claude/commands/verify-doc.md` | **Skill** - Entry point with full 7-stage protocol |
| `.claude/agents/reviewer.md` | **Agent** - General review capabilities |
| `docs/_planning/DOC-VERIFICATION-TRACKER.md` | **State** - Progress tracking only |

**Rationale:**
- Skill (`/verify-doc`) is the repeatable workflow entry point
- Agent stays lean and general-purpose
- Tracker is just state, not instructions

---

## Research Basis

### Hallucination Reduction Techniques

From [Voiceflow](https://www.voiceflow.com/blog/prevent-llm-hallucinations):
> "When consistency and accuracy matter, set the model's temperature low (~0)."

From [Turing](https://www.turing.com/resources/minimize-llm-hallucinations-strategy):
> "Use multiple LLMs with different architectures to evaluate the same output. Consensus across models increases confidence."
> "Human-in-the-Loop Oversight: Retain domain experts to review critical judgments."

From [Master of Code](https://masterofcode.com/blog/hallucinations-in-llms-what-you-need-to-know-before-integration):
> "Teaching uncertainty acknowledgment - include examples of saying 'I don't know' as an acceptable response."

### Agent Workflow Best Practices

From [Medium - AI Coding Agents](https://medium.com/@elisheba.t.anderson/building-with-ai-coding-agents-best-practices-for-agent-workflows-be1d7095901b):
> "Start small and focused: begin with single-responsibility agents; each with one clear goal and narrow scope."

From [Augment Code](https://www.augmentcode.com/blog/best-practices-for-using-ai-coding-agents):
> "If you repeat yourself during development, encode it in rules."

From [SkyWork AI](https://skywork.ai/blog/agentic-ai-examples-workflow-patterns-2025/):
> "A planner creates a task list; one or more executors carry out steps... Modularity and easier debugging."

### Academic Research on Citation Enforcement

- Citation enforcement: 5-105% improvement in grounding [arxiv 2305.13252]
- Premise verification: 94.3% accuracy when false premises detected [arxiv 2504.06438]
- Multi-agent debate: 2.6-5.8% improvement over single-agent [arxiv 2507.19090]
- Negation failures: Known LLM weakness requiring special handling [arxiv 2406.05494]

---

## How to Invoke Verification

### Current Method (Direct Task Call)

```python
Task(
    subagent_type="reviewer",
    model="sonnet",
    prompt="""
    [Full 7-stage protocol from ENHANCED_VERIFICATION_PROTOCOL.md]

    Verify: docs/path/to/doc.md

    Against code in:
    - app/relevant/file1.py
    - app/relevant/file2.py
    """
)
```

### Future Method (Skill Invocation)

After consolidation:
```
/verify-doc docs/reference/services/kb-agent-overview.md
```

---

## Tracking Progress

Progress is tracked in `docs/_planning/DOC-VERIFICATION-TRACKER.md`:

- **NEEDS_UPDATE**: Doc has verified issues that need fixing
- **ACCURATE**: Doc verified with no issues found
- **CRITICALLY_WRONG**: Major architectural mismatches

### Priority Queue

1. Core Architecture docs (chat, llm, kb, database)
2. API Reference docs
3. Everything else (384 remaining)

---

## Key Learnings

### What Went Wrong Initially

1. **I (Claude) fabricated ~40% of findings** - Claimed issues without reading code
2. **Examples of false positives:**
   - Claimed `JSONB` was stored as "JSON string" - but migration clearly shows `JSONB`
   - Claimed `/current` vs `/me` endpoint mismatch - but code says `/current`
   - Claimed `{tools_section}` wasn't in prompt when it clearly was

### What Fixed It

1. **Forcing exact citations** - Can't fabricate if you must quote exact text
2. **Tracking files actually read** - Can't claim you verified what you didn't read
3. **Negation handling** - "NOT" claims require positive evidence
4. **Confidence calibration** - Mark uncertain findings for human review

### Anti-Patterns to Avoid

1. **DON'T add verification timestamps to docs** - They rot faster than content
2. **DON'T batch fixes to the end** - Fix immediately while context is fresh
3. **DON'T skip manual review** - Until false positive rate is proven at 0%
4. **DON'T put verification metadata in doc content** - Track in tracker file only

---

## Next Steps

1. **Consolidate files** into skill + agent + tracker structure
2. **Continue verification** of remaining 386 docs
3. **Consider automation** - CI/CD integration to verify docs on code changes

---

## References

- [Anthropic Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Building With AI Coding Agents - Medium](https://medium.com/@elisheba.t.anderson/building-with-ai-coding-agents-best-practices-for-agent-workflows-be1d7095901b)
- [Best Practices for AI Coding Agents - Augment Code](https://www.augmentcode.com/blog/best-practices-for-using-ai-coding-agents)
- [Agentic AI Workflow Patterns 2025 - SkyWork AI](https://skywork.ai/blog/agentic-ai-examples-workflow-patterns-2025/)
- [How to Prevent LLM Hallucinations - Voiceflow](https://www.voiceflow.com/blog/prevent-llm-hallucinations)
- [Minimize LLM Hallucinations - Turing](https://www.turing.com/resources/minimize-llm-hallucinations-strategy)
- [LLM Hallucinations - Master of Code](https://masterofcode.com/blog/hallucinations-in-llms-what-you-need-to-know-before-integration)
