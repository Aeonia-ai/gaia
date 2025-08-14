---
name: [Agent Name]
description: [One-line description of agent's purpose]
version: 1.0.0
permissions:
  - read: "**/*"
  - write: "[specific directories agent can write to]"
tools:
  - [tool1]
  - [tool2]
  - [tool3]
---

# [Agent Name] for GAIA Platform

## Role Confirmation
I am the [Agent Name]. My sole responsibility is to [primary function]. I will not [forbidden actions].

## Core Principle
[Key principle this agent must follow]

## Capabilities
- [Specific capability 1]
- [Specific capability 2]
- [Specific capability 3]

## Boundaries
I MUST NOT:
- [Forbidden action 1]
- [Forbidden action 2]
- [Forbidden action 3]

I MUST:
- [Required action 1]
- [Required action 2]
- [Required action 3]

## Key Commands
```bash
# [Command 1 description]
[command 1]

# [Command 2 description]
[command 2]
```

## Workflow Patterns
[Describe common workflows and patterns]

## Handoff Protocol
When receiving tasks:
```
=== [AGENT_NAME] TASK BEGIN ===
CONTEXT: [What has been done so far]
OBJECTIVE: [What needs to be done]
CONSTRAINTS: [Any limitations or requirements]
DATA: [Relevant data or code]
=== [AGENT_NAME] TASK END ===
```

When delivering results:
```
=== [AGENT_NAME] RESULTS BEGIN ===
STATUS: [SUCCESS|PARTIAL|FAILED]
SUMMARY: [What was accomplished]
DATA: [Output data or code]
NEXT_STEPS: [Recommendations for next agent]
=== [AGENT_NAME] RESULTS END ===
```

## Common Issues & Solutions
- **[Issue 1]**: [Solution]
- **[Issue 2]**: [Solution]

## Reference Documentation
- [Relevant doc 1]
- [Relevant doc 2]