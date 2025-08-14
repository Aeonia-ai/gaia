# Claude Code Configuration

This directory contains Claude Code agent definitions and configurations for the GAIA platform.

## Directory Structure

```
.claude/
├── agents/           # Agent definitions
│   ├── tester.md    # Test writing and debugging agent
│   ├── builder.md   # Code implementation agent
│   ├── reviewer.md  # Code review and security agent
│   └── AGENT_TEMPLATE.md  # Template for new agents
└── commands/        # Slash commands (future)
```

## Using Agents

To invoke an agent:
```bash
/agents           # List all available agents
/agents:tester    # Switch to the Tester agent
/agents:builder   # Switch to the Builder agent
/agents:reviewer  # Switch to the Reviewer agent
```

## Creating New Agents

1. Copy `AGENT_TEMPLATE.md` to a new file
2. Update the YAML frontmatter with agent metadata
3. Define the agent's role, capabilities, and boundaries
4. Save in `.claude/agents/` directory

## Agent Workflow Example

```bash
# 1. Write tests
/agents:tester
Write tests for the new user preferences feature

# 2. Implement code
/agents:builder
Implement the preferences API to make the tests pass

# 3. Review code
/agents:reviewer
Review the preferences implementation for security and quality
```

## Documentation

- [Agent Architecture](/docs/agents/agent-architecture.md)
- [How to Invoke Agents](/docs/agents/how-to-invoke-agents.md)
- [CLAUDE.md](/CLAUDE.md) - Main project instructions