# Documentation Consolidation Protocol

## Purpose

Reduce documentation sprawl by merging overlapping docs, resolving conflicts, and organizing into a coherent structure.

**Goal:** 390 docs → ~100 well-organized docs

---

## Overview

Consolidation is a 5-phase process:

1. **Discovery** - Find related docs on the same topic
2. **Analysis** - Identify overlaps, gaps, and conflicts
3. **Resolution** - Resolve conflicts (may invoke verification)
4. **Merge** - Combine into unified doc
5. **Cleanup** - Archive/delete originals, update links

---

## Phase 1: Discovery

Find all docs related to a topic or area.

**Methods:**
- Glob for filenames: `docs/**/*auth*.md`
- Grep for content: search for key terms
- Check cross-references: what links to what

**Output:**
```
TOPIC: [topic name]

RELATED DOCS:
1. [path] - [one-line summary]
2. [path] - [one-line summary]
...

RELATIONSHIP MAP:
- [doc A] overlaps with [doc B] on: [topics]
- [doc C] is outdated version of [doc D]
- [doc E] is deep-dive of section in [doc F]
```

---

## Phase 2: Analysis

For each group of related docs, analyze:

### Content Overlap
```
OVERLAP ANALYSIS:

DUPLICATED CONTENT:
- "[exact quote]" appears in: [doc A line X], [doc B line Y]
- "[exact quote]" appears in: [doc C line X], [doc D line Y]

UNIQUE CONTENT:
- [doc A] uniquely covers: [topics]
- [doc B] uniquely covers: [topics]
```

### Freshness Assessment
```
FRESHNESS:
| Doc | Last Modified | References Current Code? |
|-----|---------------|-------------------------|
| [path] | [date] | YES/NO/PARTIAL |
```

### Conflict Detection
```
CONFLICTS DETECTED:

CONFLICT #1:
- Doc A says: "[quote]" (line X)
- Doc B says: "[quote]" (line Y)
- Type: FACTUAL | VERSION | OPINION | SCOPE
- Resolution needed: [describe]
```

---

## Phase 3: Resolution

Resolve each conflict before merging. See `conflict-resolution.md` for detailed handling.

**Quick reference:**

| Conflict Type | Resolution Method |
|---------------|-------------------|
| Factual (doc vs doc) | Invoke verification - check code |
| Version (old vs new) | Keep newer, archive older |
| Scope (overview vs detail) | Hierarchical merge |
| Opinion (approach A vs B) | Flag for human decision |
| Duplicate (same content) | Keep one, delete others |

**Format:**
```
CONFLICT #1 RESOLUTION:
- Type: [type]
- Method: [method used]
- Winner: [which doc/content is correct]
- Evidence: [if verification used, cite code]
- Action: [what to do]
```

---

## Phase 4: Merge

Combine docs into unified structure.

### Merge Strategies

**1. Absorb** - One doc absorbs content from others
```
MERGE STRATEGY: ABSORB
- Primary doc: [path] (most complete/current)
- Absorbing from: [list of docs]
- Sections to add: [list]
```

**2. Synthesize** - Create new doc from multiple sources
```
MERGE STRATEGY: SYNTHESIZE
- New doc: [proposed path]
- Sources: [list of docs]
- Structure:
  1. [section] - from [doc]
  2. [section] - from [doc]
  ...
```

**3. Hierarchical** - Create overview + detail docs
```
MERGE STRATEGY: HIERARCHICAL
- Overview doc: [path]
- Detail docs:
  - [path] - covers [topic]
  - [path] - covers [topic]
- Links: overview links to details
```

### Merge Execution

```markdown
## Merged Doc: [path]

### Source Documents
- [doc A] - [what was taken]
- [doc B] - [what was taken]

### Content

[merged content here]

### Archived/Deleted
- [doc X] - reason: [duplicate of section Y]
- [doc Z] - reason: [outdated, replaced by this doc]
```

---

## Phase 5: Cleanup

After merging:

1. **Archive originals** - Move to `docs/_archive/` with date prefix
2. **Update links** - Find and fix all references to old paths
3. **Update tracker** - Record consolidation in tracker
4. **Verify result** - Run verification on merged doc

**Link update process:**
```bash
# Find all references to old doc
grep -r "old-doc-name.md" docs/

# Update each reference
# (manual or scripted)
```

---

## Output Format

```markdown
## Consolidation Report: [topic]

### Discovery
[Phase 1 output]

### Analysis
[Phase 2 output]

### Conflicts & Resolutions
[Phase 3 output]

### Merge Plan
[Phase 4 strategy]

### Cleanup Actions
- [ ] Archive [doc A]
- [ ] Archive [doc B]
- [ ] Update links in [list of files]
- [ ] Verify merged doc

### Result
- Docs before: [N]
- Docs after: [M]
- Reduction: [percentage]
```

---

## When to Invoke Verification

Consolidation should invoke verification (from `verify-protocol.md`) when:

1. **Factual conflict** - Two docs disagree on what code does
2. **Uncertainty** - Unsure which doc is current/correct
3. **After merge** - Verify the merged doc is accurate

**Invocation:**
```
This consolidation has a factual conflict. Invoking verification protocol...

[Run verify-protocol.md on relevant code]

Verification result: [doc A / doc B] is correct because [citation]
```

---

## Priority Queue

Suggested consolidation order:

1. **High duplication areas** - auth docs, deployment docs
2. **Core architecture** - chat, kb, database docs
3. **API reference** - endpoint documentation
4. **Guides** - how-to documents
5. **Scratchpad** - temporary notes (mostly archive/delete)

---

## Anti-Patterns

1. **DON'T merge without resolving conflicts** - Creates confused docs
2. **DON'T delete without archiving** - May lose valuable content
3. **DON'T skip link updates** - Creates broken references
4. **DON'T merge unverified docs** - May propagate errors
5. **DON'T create mega-docs** - Keep docs focused and scannable
