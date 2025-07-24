# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the Gaia Platform. ADRs document significant architectural decisions, the context in which they were made, and their consequences.

## What is an ADR?

An Architecture Decision Record captures:
- **Context**: The situation and forces at play
- **Decision**: What we decided to do
- **Rationale**: Why we made this decision
- **Consequences**: What happens as a result

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-supabase-first-authentication.md) | Supabase-First Authentication | Implemented | Jan 2025 |
| [002](002-microservice-automation.md) | Microservice Creation Automation | Implemented | Jan 2025 |
| [003](003-postgresql-simplicity.md) | PostgreSQL Direct Usage Over ORM | Adopted | Jan 2025 |

## ADR Template

When creating a new ADR, use this template:

```markdown
# ADR-XXX: Title

**Date**: YYYY-MM-DD  
**Status**: Proposed | Accepted | Implemented | Deprecated  
**Decision**: One-line summary

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Rationale
Why is this the right decision? What are the benefits?

## Consequences
What becomes easier or more difficult as a result?

### Positive
- Benefits gained

### Negative  
- Trade-offs accepted

### Neutral
- Changes that are neither good nor bad

## Implementation
Code examples or implementation details

## Alternatives Considered
What else did we consider?

## Lessons Learned
What insights did we gain?

## References
Links to related documentation
```

## Why ADRs?

1. **Historical Context**: Understand why decisions were made
2. **Onboarding**: Help new team members understand the architecture
3. **Avoid Revisiting**: Document why alternatives were rejected
4. **Evolution**: Track how architecture changes over time

## Creating a New ADR

1. Copy the template above
2. Number it sequentially (e.g., 004-your-decision.md)
3. Fill in all sections
4. Update this index
5. Commit and push

## Guidelines

- **Be Concise**: ADRs should be readable in 5-10 minutes
- **Be Honest**: Document real trade-offs, not just benefits
- **Be Specific**: Include code examples where helpful
- **Be Timely**: Write ADRs when decisions are made, not months later