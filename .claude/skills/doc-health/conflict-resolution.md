# Conflict Resolution Guide

## Purpose

Handle conflicts between documentation sources during consolidation. This guide covers specific resolution strategies for different conflict types.

---

## Conflict Types

### 1. Factual Conflicts

**Definition:** Two docs make incompatible claims about what code does.

**Example:**
- Doc A: "Authentication uses JWT tokens"
- Doc B: "Authentication uses API keys"

**Resolution:**
```
FACTUAL CONFLICT RESOLUTION:

1. INVOKE VERIFICATION
   Use verify-protocol.md to check code

2. DETERMINE TRUTH
   - Check actual implementation
   - Cite specific code locations
   - Document which doc is correct

3. RESOLUTION
   - Winner: [doc with correct claim]
   - Evidence: [code citation]
   - Action: Merge winner's content, discard loser's claim
```

**Decision Matrix:**
| Evidence | Action |
|----------|--------|
| Code supports Doc A | Use Doc A's claim |
| Code supports Doc B | Use Doc B's claim |
| Code supports neither | Mark OUTDATED, investigate |
| Code supports both (different contexts) | Merge with context clarification |

---

### 2. Version Conflicts

**Definition:** One doc is clearly newer/older than another.

**Example:**
- Doc A: "Use `database.query()`" (old API)
- Doc B: "Use `db.execute()`" (new API)

**Resolution:**
```
VERSION CONFLICT RESOLUTION:

1. IDENTIFY VERSIONS
   - Check git history: git log --oneline [doc-path]
   - Check internal dates/timestamps
   - Check code for which API exists

2. DETERMINE CURRENT
   - Which version matches current codebase?
   - Is old version still supported?

3. RESOLUTION
   | Scenario | Action |
   |----------|--------|
   | New replaces old | Archive old, use new |
   | Both still valid | Document both with version notes |
   | New is incorrect | Flag for human review |
```

---

### 3. Scope Conflicts

**Definition:** Docs cover same topic at different levels of detail.

**Example:**
- Doc A: "Authentication overview" (high-level)
- Doc B: "JWT implementation details" (deep-dive)

**Resolution:**
```
SCOPE CONFLICT RESOLUTION:

1. IDENTIFY LEVELS
   - Overview/conceptual
   - Implementation/detailed
   - Reference/API

2. CREATE HIERARCHY
   - Overview links to details
   - Details reference overview for context
   - No duplicate content

3. RESOLUTION
   - Merge into hierarchical structure
   - Parent doc: overview + links
   - Child docs: deep-dives
```

**Structure Template:**
```markdown
# [Topic] (Overview)
Brief explanation...

## Subtopics
- [Subtopic A](./subtopic-a.md) - detailed guide
- [Subtopic B](./subtopic-b.md) - implementation

## Quick Reference
[Key points that don't need separate docs]
```

---

### 4. Opinion Conflicts

**Definition:** Docs recommend different approaches without clear "right" answer.

**Example:**
- Doc A: "Use Redis for caching"
- Doc B: "Use in-memory caching for simplicity"

**Resolution:**
```
OPINION CONFLICT RESOLUTION:

1. IDENTIFY AS OPINION
   - No single "correct" answer in code
   - Both approaches are valid
   - Choice depends on context

2. CHECK CURRENT PRACTICE
   - What does codebase actually use?
   - Is there a stated architectural decision?

3. RESOLUTION OPTIONS
   | Scenario | Action |
   |----------|--------|
   | One is current practice | Document current, note alternative |
   | No clear practice | Flag for human decision |
   | Context-dependent | Document when to use each |
```

**Human Decision Required Format:**
```markdown
## Decision Needed: [Topic]

### Options
1. **Option A**: [description]
   - Pros: [list]
   - Cons: [list]

2. **Option B**: [description]
   - Pros: [list]
   - Cons: [list]

### Current State
[What the code currently does, if anything]

### Recommendation
[Your analysis, but clearly marked as needing human decision]
```

---

### 5. Duplicate Conflicts

**Definition:** Same content appears in multiple places.

**Example:**
- Doc A: Contains "## Authentication" section
- Doc B: Contains identical "## Authentication" section

**Resolution:**
```
DUPLICATE CONFLICT RESOLUTION:

1. IDENTIFY CANONICAL LOCATION
   - Where should this content live?
   - Which doc is more focused on this topic?

2. CONSOLIDATE
   - Keep content in canonical location
   - Remove from other locations
   - Add cross-references if needed

3. UPDATE REFERENCES
   - Find all links to removed content
   - Update to point to canonical location
```

---

### 6. Missing Information Conflicts

**Definition:** One doc has information the other lacks.

**Example:**
- Doc A: Covers features X and Y
- Doc B: Covers features X and Z

**Resolution:**
```
MISSING INFO RESOLUTION:

1. IDENTIFY UNIQUE CONTENT
   - What does each doc uniquely cover?
   - Is any content truly redundant?

2. MERGE UNIQUE CONTENT
   - Combine non-overlapping sections
   - Verify merged content is consistent

3. VERIFY COMPLETENESS
   - Does merged doc cover all original topics?
   - Are there gaps that need filling?
```

---

## Resolution Process

### Step 1: Classify the Conflict

```
CONFLICT CLASSIFICATION:

Conflict: [description]
Type: FACTUAL | VERSION | SCOPE | OPINION | DUPLICATE | MISSING

Evidence:
- Doc A says: "[quote]" (line X)
- Doc B says: "[quote]" (line Y)

Classification reasoning: [why this type]
```

### Step 2: Apply Resolution Strategy

Use the appropriate strategy from above.

### Step 3: Document Resolution

```
RESOLUTION APPLIED:

Conflict: [description]
Type: [type]
Strategy: [which resolution used]
Result: [what was decided]
Action taken:
- [specific action 1]
- [specific action 2]
```

### Step 4: Verify Resolution

After merging:
1. Re-read merged content for consistency
2. If factual claims involved, verify against code
3. Check for orphaned references

---

## When to Escalate to Human

**Always escalate when:**
1. Opinion conflicts with no clear winner
2. Architectural decisions needed
3. Multiple valid interpretations exist
4. You're uncertain about the resolution
5. Resolution would significantly change documented behavior

**Escalation Format:**
```
## Human Decision Required

### Conflict
[Description of the conflict]

### Options
[List of possible resolutions]

### My Analysis
[Your recommendation with reasoning]

### Why Escalating
[Why this needs human input]
```

---

## Anti-Patterns

1. **DON'T guess** - When uncertain, escalate
2. **DON'T merge contradictions** - Resolve first, then merge
3. **DON'T lose information** - Archive before deleting
4. **DON'T skip verification** - Factual conflicts need code checks
5. **DON'T create mega-docs** - Keep docs focused, use hierarchy

---

## Quick Reference

| Conflict Type | First Step | Key Action |
|---------------|------------|------------|
| Factual | Verify code | Use code truth |
| Version | Check dates | Use current |
| Scope | Identify levels | Create hierarchy |
| Opinion | Check practice | Escalate if unclear |
| Duplicate | Find canonical | Remove copies |
| Missing | List unique | Merge all |
