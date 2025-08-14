---
name: tdd-workflow
description: Execute Test-Driven Development workflow with agents
version: 1.0.0
---

# TDD Workflow Command

This command orchestrates a Test-Driven Development workflow using multiple agents.

## How It Works

This is a **human-invoked command** that coordinates agents:
1. Human runs `/tdd-workflow`
2. Command instructs human to use agents in sequence
3. Human switches between agents as directed

## Usage
```
/tdd-workflow [feature-description]
```

## Workflow Steps

1. **Test Writing Phase**
   - Invoke Tester agent
   - Write comprehensive tests for the feature
   - Verify tests fail (no implementation)

2. **Implementation Phase**
   - Invoke Builder agent
   - Implement code to make tests pass
   - Follow existing patterns

3. **Validation Phase**
   - Invoke Tester agent
   - Run all tests
   - Verify implementation correctness

4. **Review Phase**
   - Invoke Reviewer agent
   - Review code quality and security
   - Provide feedback

## Example
```
/tdd-workflow "user preferences API with CRUD operations"
```

This will:
1. Write tests for GET/POST/PUT/DELETE /api/v1/preferences
2. Implement the preferences API
3. Verify all tests pass
4. Review the implementation

## Agent Handoff Pattern
Each agent passes structured data to the next:
- Tester → Builder: Test files and requirements
- Builder → Tester: Implementation files
- Tester → Reviewer: Test results and coverage
- Reviewer → User: Final assessment