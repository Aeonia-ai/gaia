# Conceptual Documentation Verification

## The Problem

Documentation drifts from code. But the REAL problem isn't line numbers being wrong—
it's developers getting the **wrong mental model** of how the system works.

A doc that says "uses session-based auth" when the code uses JWTs will cause
developers to make wrong assumptions, even if every line number is correct.

## Our Approach

### Why Not Just Ask "Does This Match?"

Research shows LLMs have ~70% accuracy when asked directly "does this doc match
this code?" They tend toward confirmation bias—finding ways to say "yes."

### The Solution: Separate Description from Comparison

```
Step 1: LLM reads ONLY the code (no doc)
        → Outputs description of what code actually does

Step 2: LLM reads ONLY the doc (no code)
        → Outputs what the doc claims

Step 3: Adversarial comparison
        → "What would a developer MISUNDERSTAND?"
```

This avoids confirmation bias by never showing both together initially.

## What We Check

### DO Care About:
- **Architectural accuracy**: Doc says "microservices" but it's a monolith
- **Behavioral accuracy**: Doc says "caches responses" but caching was removed
- **API accuracy**: Doc shows `/api/v1/users` but endpoint is `/api/v2/accounts`
- **Security model**: Doc says "sessions in Redis" but code uses stateless JWTs
- **Data flow**: Doc says "synchronous" but code is fully async
- **Integration points**: Doc says "calls Auth service" but code calls different service

### DON'T Care About:
- Line numbers being wrong (they shouldn't be in docs anyway)
- Exact code snippets not matching
- Precise counts being off
- Minor wording differences
- Formatting issues

## Severity Levels

- **CRITICAL**: Developer would build something fundamentally wrong
  - Example: Doc says REST, code is GraphQL

- **MODERATE**: Developer would be confused or inefficient
  - Example: Doc says 3 services, there are actually 5

- **MINOR**: Imprecise but not misleading
  - Example: Doc says "fast" but doesn't specify latency

## Usage

```bash
# Verify a single doc
python scripts/doc-verify/conceptual_verify.py docs/path/to/doc.md

# JSON output for automation
python scripts/doc-verify/conceptual_verify.py docs/path/to/doc.md --output json

# Specify code directory
python scripts/doc-verify/conceptual_verify.py docs/api/auth.md --code-dir app/services/auth
```

## Integration with Claude Code Agents

For batch verification, use the Reviewer agent with this prompt:

```
Verify docs/path/to/doc.md conceptually:

1. Identify which code files this doc describes
2. Read the code and describe what it ACTUALLY does
3. Read the doc and extract what it CLAIMS
4. Find conceptual misalignment where developers would get wrong mental model
5. Return: ACCURATE | NEEDS_UPDATE | CRITICALLY_WRONG + specific discrepancies
```

## Example Discrepancies Found

### Critical: Wrong Authentication Model
- **Doc claims**: "Uses session-based authentication with cookies stored in Redis"
- **Code does**: Stateless JWT validation with bearer tokens, no Redis
- **Developer impact**: Would try to find session management code that doesn't exist

### Moderate: Outdated Service Architecture
- **Doc claims**: "Chat service forwards requests to LLM service"
- **Code does**: Chat service calls LLM providers directly via unified client
- **Developer impact**: Would look for non-existent LLM service

### Minor: Imprecise Description
- **Doc claims**: "Fast response times"
- **Code does**: p50 ~200ms, p99 ~2s with circuit breaker
- **Developer impact**: Vague but not wrong
