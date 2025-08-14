# How to Invoke and Use Agents in Claude Code

> A practical guide for humans using Claude Code agents effectively.

## Quick Reference

### Basic Agent Commands
```bash
/agents                    # List all available agents
/agents:<AGENT-NAME>       # Switch to a specific agent
/agents:tester            # Example: Switch to Tester Agent
```

### Session Management
```bash
/clear                    # Reset conversation (keep project state)
/compact                  # Summarize long conversations
/resume <session_id>      # Resume a previous session
/continue                 # Continue last session
```

## Invocation Patterns

### 1. Direct Agent Invocation
```bash
# Switch to the Tester Agent
/agents:tester

# Then provide your task
Write integration tests for the new user preferences endpoint
```

### 2. Context-Rich Invocation
```bash
/agents:tester

I've just implemented a new endpoint at /api/v1/preferences.
The implementation is in services/web/routes/preferences.py.
Please write comprehensive tests including:
- Happy path tests
- Authentication tests
- Validation error cases
- Rate limiting tests
```

### 3. Multi-Agent Workflow
```bash
# Step 1: Write tests
/agents:tester
Write tests for a new bulk user import feature

# Step 2: Implement (when Builder Agent is available)
/agents:builder
Implement the bulk import to make the tests pass

# Step 3: Validate
/agents:tester
Run all tests and verify they pass
```

## Best Practices

### 1. Provide Clear Context
**❌ Bad:**
```bash
/agents:tester
Fix the tests
```

**✅ Good:**
```bash
/agents:tester
The test_chat_streaming test is failing with a timeout error.
It's located in tests/integration/test_chat_api.py.
Please debug why the streaming response isn't completing.
```

### 2. Use Structured Requests
```bash
/agents:tester

TASK: Write E2E tests for user registration flow
CONTEXT: New registration UI was added to /register
REQUIREMENTS:
- Test successful registration
- Test validation errors
- Test duplicate email handling
- Use real Supabase authentication
FILES: services/web/routes/auth.py, templates/register.html
```

### 3. Manage Long Conversations
```bash
# After multiple interactions
/compact

# Or start fresh for new task
/clear

# Then continue with new task
/agents:tester
Now let's work on testing the payment system
```

### 4. Chain Agent Tasks Effectively
```bash
# Provide explicit handoffs
/agents:tester
=== TASK COMPLETE ===
I've written 10 tests for the preferences API.
All tests are failing as expected (no implementation).
Test file: tests/integration/test_preferences_api.py

# Switch to next agent with context
/agents:builder
The Tester Agent has written tests for the preferences API.
Please implement the endpoints to make the tests pass.
Tests are in: tests/integration/test_preferences_api.py
```

## Common Invocation Scenarios

### Scenario 1: Test-Driven Development
```bash
# 1. Start with tests
/agents:tester
Write tests for a new feature: user profile picture upload
Requirements: 
- Max 5MB file size
- Only JPEG/PNG allowed
- Automatic thumbnail generation

# 2. After tests are written
/agents:builder
Implement the profile picture upload to pass the tests

# 3. Verify
/agents:tester
Run all tests and confirm they pass
```

### Scenario 2: Debugging Failed Tests
```bash
/agents:tester
The E2E tests in test_real_auth_e2e.py are failing.
Error: "TimeoutError: waiting for selector"
Please investigate and fix the issue.
Don't change the tests unless they have actual bugs.
```

### Scenario 3: Code Review Request
```bash
/agents:reviewer
Review the recent changes to services/chat/chat.py
Focus on:
- Security vulnerabilities
- Performance issues
- Code quality
Check git diff for the latest changes
```

## Managing Agent State

### Preserving Context
```bash
# Context automatically transfers when switching agents
/agents:tester
Write tests for feature X

/agents:builder
# Agent still has context about feature X
Implement feature X
```

### Resetting for New Tasks
```bash
# Clear context when starting unrelated work
/clear

/agents:tester
Now let's work on a completely different feature
```

### Resuming Work
```bash
# List recent sessions
claude --list-sessions

# Resume specific session
/resume abc-123-def

# Or continue last session
/continue
```

## Tracking Progress

### In Terminal/CLI
```bash
# Verbose output
claude -p "Run all integration tests" --verbose

# Structured output
claude -p "List failing tests" --output-format json

# Save results
claude -p "Generate test report" > test-report.md
```

### In Conversation
```bash
/agents:tester
Run all tests and provide a summary of:
- Total tests run
- Passed/Failed breakdown
- Any flaky tests
- Coverage report
```

## Common Mistakes to Avoid

### 1. Wrong Agent Name
```bash
# ❌ This won't work
/agents:test-writer

# ✅ Use correct name
/agents:tester

# Check available agents
/agents
```

### 2. Insufficient Context
```bash
# ❌ Too vague
/agents:tester
Write tests

# ✅ Specific and detailed
/agents:tester
Write unit tests for the calculate_discount function in services/pricing/utils.py
Include edge cases for:
- Negative values
- Zero values
- Percentages over 100
```

### 3. Overloaded Context
```bash
# If conversation gets too long
/compact

# Or for truly fresh start
/clear
```

### 4. Not Using Agent Boundaries
```bash
# ❌ Asking Tester to implement
/agents:tester
Fix the implementation to make tests pass

# ✅ Respecting agent role
/agents:tester
Run the tests and report which ones are failing
```

## Advanced Patterns

### Parallel Agent Work
Open multiple Claude Code sessions:
```bash
# Session 1
/agents:tester
Write unit tests for the auth module

# Session 2 (different window)
/agents:documentation
Update the API documentation for v2 endpoints
```

### Automated Workflows
```bash
# Using CLI for automation
claude -p "Use the Tester Agent to run all E2E tests" \
  --output-format json | \
  jq '.failed_tests' | \
  xargs -I {} claude -p "Debug test failure: {}"
```

### Custom Agent Creation
```bash
# Create new agent
/agents

# Select "Create New Agent"
# Define:
# - Name: security-scanner
# - Role: Scan code for vulnerabilities
# - Tools: grep, read, bash
# - Boundaries: No code modification
```

## Quick Tips

1. **Be Explicit**: Always state exactly what you want the agent to do
2. **Provide Files**: Mention specific file paths when relevant
3. **Set Boundaries**: Remind agents of their limitations
4. **Check First**: Use `/agents` to see available agents
5. **Manage Context**: Use `/compact` and `/clear` appropriately
6. **Track State**: Note what each agent has done for smooth handoffs
7. **Batch Tasks**: Give agents complete task lists, not piecemeal
8. **Verify Understanding**: Ask agents to confirm their understanding

## Example: Complete Feature Development

```bash
# 1. Define the feature
I need to add a user notification system. Let's start with tests.

# 2. Write tests
/agents:tester
Write comprehensive tests for a notification system with these requirements:
- Email and SMS notifications
- User preferences for notification types
- Rate limiting (max 10 per hour)
- Delivery status tracking
Create tests in tests/integration/test_notifications.py

# 3. Review test output
# [Agent provides test code and summary]

# 4. Implement feature
/agents:builder
Implement the notification system to pass all tests in tests/integration/test_notifications.py
Follow existing patterns in services/notifications/

# 5. Validate implementation
/agents:tester
Run all notification tests and verify they pass

# 6. Code review
/agents:reviewer
Review the notification system implementation for:
- Security issues
- Performance concerns
- Code quality
Files: services/notifications/, tests/integration/test_notifications.py
```

## Troubleshooting

### Agent Not Responding as Expected
1. Check agent name: `/agents`
2. Verify context: Ask agent to summarize understanding
3. Clear if needed: `/clear`
4. Provide more specific instructions

### Context Getting Lost
1. Use `/compact` to summarize
2. Explicitly state important context
3. Reference specific files and locations

### Wrong Agent Behavior
1. Check agent definition
2. Remind agent of boundaries
3. Switch to correct agent if needed

---

Remember: Agents are specialized tools. Use them for their intended purpose and provide clear, contextual instructions for best results.