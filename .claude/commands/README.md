# Claude Code Commands

This directory contains slash commands for the GAIA platform.

## Commands vs Agents

### Key Differences

| Aspect | Commands | Agents |
|--------|----------|---------|
| **Invoked by** | Humans via `/command` | Humans via `/agents:name` |
| **Purpose** | Quick shortcuts | Interactive assistants |
| **Can use tools** | No (just prompts) | Yes (bash, file operations, etc.) |
| **State** | Stateless | Maintain conversation state |
| **Can invoke other** | Can suggest agent usage | Don't invoke commands |

### How They Work Together

1. **Commands for Humans**
   - `/morning` - Human runs this to start their day
   - `/test-all` - Human runs this to execute tests
   - `/pr-prep` - Human runs this before creating PR

2. **Agents for Complex Tasks**
   - Agents have access to tools (bash, file operations)
   - Agents maintain context during conversation
   - Agents can execute the same actions as commands, but interactively

### Example: Testing Workflow

**Using a Command:**
```bash
/test-all
# Claude executes the prompt, suggests running tests
# Human must run the actual commands
```

**Using the Tester Agent:**
```bash
/agents:tester
Run all tests for the platform

# Agent can actually execute:
# - ./scripts/pytest-for-claude.sh
# - Parse results
# - Debug failures
# - Modify test files
```

## Current Commands

### Development Workflow
- `morning.md` - Start of day setup
- `pr-prep.md` - Pre-PR checklist
- `test-all.md` - Run all tests
- `debug-timeout.md` - Debug timeout issues

### Agent Orchestration
- `tdd-workflow.md` - Guides TDD process with agents

## Creating New Commands

Commands are best for:
- Checklists and reminders
- Workflow guidance
- Quick prompts that don't need tool access
- Orchestrating human actions

Agents are best for:
- Actually executing tasks
- Complex debugging
- Writing/modifying code
- Running tests and analyzing results