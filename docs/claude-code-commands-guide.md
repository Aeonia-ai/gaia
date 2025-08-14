# Claude Code Commands Guide for GAIA Platform

## Overview

Claude Code commands (slash commands) are reusable shortcuts that automate common tasks. They differ from agents by being single-action, stateless operations rather than interactive, stateful assistants.

## Built-in Commands

Claude Code provides these built-in commands:

```bash
/help      # List all available commands
/clear     # Start fresh session (keeps project state)
/compact   # Compress chat history to save tokens
/exit      # End current session
/mcp       # Show MCP server information
/ide       # IDE integration info
```

## Custom Commands vs Agents

| Feature | Commands | Agents |
|---------|----------|---------|
| Purpose | Single-action shortcuts | Interactive assistants |
| State | Stateless | Maintain conversation state |
| Complexity | Simple prompts | Complex workflows |
| Location | `.claude/commands/` | `.claude/agents/` |
| Invocation | `/command-name` | `/agents:agent-name` |

## Creating Custom Commands

### 1. File Structure
Commands are Markdown files in `.claude/commands/`:

```
.claude/
└── commands/
    ├── test-all.md
    ├── morning.md
    ├── security-review.md
    └── deploy-check.md
```

### 2. Command Syntax
- Filename (without `.md`) becomes the command name
- Use `$ARGUMENTS` to accept parameters
- Commands execute in current context

### 3. Example Commands

#### Test All Command
`.claude/commands/test-all.md`:
```markdown
Run comprehensive tests for the GAIA platform:

1. Run unit tests
2. Run integration tests  
3. Run E2E tests
4. Check code style
5. Generate coverage report

Execute:
- ./scripts/pytest-for-claude.sh tests/unit -v
- ./scripts/pytest-for-claude.sh tests/integration -v
- ./scripts/pytest-for-claude.sh tests/e2e -v
- ruff check app/
- Generate coverage summary

Report any failures with specific error messages.
```

#### Morning Setup Command
`.claude/commands/morning.md`:
```markdown
Perform morning setup routine:

1. Git status and pull latest changes
2. Check if Docker services are running
3. Run quick health checks
4. List any failing tests from last session
5. Show current TODO items

Provide a summary of the project state and any issues that need attention.
```

#### Security Review Command
`.claude/commands/security-review.md`:
```markdown
Review the following code for security vulnerabilities:

$ARGUMENTS

Check for:
- SQL injection risks
- XSS vulnerabilities
- Authentication/authorization issues
- Hardcoded secrets
- Input validation gaps
- Insecure data handling
- OWASP Top 10 issues

Provide specific line numbers and remediation suggestions.
```

#### Deploy Check Command
`.claude/commands/deploy-check.md`:
```markdown
Pre-deployment checklist for GAIA platform:

1. All tests passing?
   - Unit: ./scripts/pytest-for-claude.sh tests/unit
   - Integration: ./scripts/pytest-for-claude.sh tests/integration
   - E2E: ./scripts/pytest-for-claude.sh tests/e2e

2. Code quality checks:
   - Linting: ruff check app/
   - Type checking: mypy app/

3. Security scan:
   - No hardcoded secrets
   - Dependencies up to date

4. Database migrations ready?
   - Check migrations/

5. Environment variables documented?
   - Check .env.example

Report GO/NO-GO for deployment.
```

## Usage Examples

```bash
# Run all tests
/test-all

# Morning setup
/morning

# Security review specific file
/security-review app/services/auth/auth.py

# Pre-deployment check
/deploy-check
```

## Best Practices

### 1. Naming Conventions
- Use verb-noun format: `test-all`, `deploy-check`
- Keep names short and memorable
- Use hyphens, not underscores

### 2. Organization
```
commands/
├── testing/
│   ├── test-unit.md
│   ├── test-integration.md
│   └── test-e2e.md
├── deployment/
│   ├── deploy-check.md
│   └── rollback.md
└── daily/
    ├── morning.md
    └── end-of-day.md
```

### 3. Command Design
- **Single Purpose**: Each command does one thing well
- **Clear Output**: Provide structured, actionable results
- **Error Handling**: Include what to do if something fails
- **Context Aware**: Use current directory and project state

### 4. Parameterization
```markdown
# In analyze-performance.md
Analyze performance of: $ARGUMENTS

Run performance profiling and identify:
- Bottlenecks
- Memory leaks
- Slow queries
- Inefficient algorithms
```

## Common GAIA Commands

### Development Commands
- `/test-all` - Run all test suites
- `/test-quick` - Run only unit tests
- `/lint` - Check code style
- `/format` - Auto-format code

### Debugging Commands
- `/debug-timeout` - Debug test timeout issues
- `/debug-auth` - Check authentication flow
- `/debug-docker` - Verify Docker services

### Deployment Commands
- `/deploy-check` - Pre-deployment validation
- `/deploy-staging` - Deploy to staging
- `/rollback` - Rollback deployment

### Daily Workflow Commands
- `/morning` - Morning setup routine
- `/pr-prep` - Prepare pull request
- `/end-of-day` - End of day summary

## Debugging Commands

### Check Command Registration
```bash
/help
# Look for your command marked as "(project)"
```

### Common Issues
1. **Command not found**: Check file location and `.md` extension
2. **No output**: Ensure command has clear instructions
3. **Wrong behavior**: Edit the .md file and retry

### Testing Commands
1. Create command file in `.claude/commands/`
2. Run `/help` to verify registration
3. Test with and without arguments
4. Refine prompt based on results

## Integration with Agents

Commands can invoke agents for complex workflows:

```markdown
# In review-pr.md
Review the current pull request:

1. Use the Tester Agent to run all tests
2. Use the Reviewer Agent to check code quality
3. Generate a summary report

Provide GO/NO-GO recommendation for merging.
```

## Summary

Claude Code commands provide powerful automation for repetitive tasks. They complement agents by offering quick, focused actions that can be combined into larger workflows. Start with simple commands and gradually build a library tailored to your development process.