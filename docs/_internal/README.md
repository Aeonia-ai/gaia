# Claude Code Agents

This directory contains specialized agent descriptions for Claude Code when working on the Gaia platform. Each agent has specific expertise and follows defined patterns for their domain.

## Available Agents

### 🧪 [Tester](tester.md)
Specializes in writing tests, test execution, debugging, and distributed systems troubleshooting.
- Writes tests following established patterns
- Creates appropriate unit/integration/E2E tests
- Runs tests in correct environments
- Diagnoses persistence issues
- Analyzes logs and traces execution
- Follows systematic debugging approaches

### 🏗️ [Builder](builder.md) *(coming soon)*
Focuses on implementing new features and services.
- Creates microservices following patterns
- Implements API endpoints
- Manages database migrations
- Follows architectural guidelines

### 🚀 [Deployer](deployer.md) *(coming soon)*
Handles deployment, monitoring, and operations.
- Manages Fly.io deployments
- Configures environment variables
- Monitors service health
- Implements rollback procedures

### 📚 [Documenter](documenter.md) *(coming soon)*
Maintains documentation and knowledge capture.
- Creates postmortems
- Updates technical guides
- Maintains API documentation
- Captures architectural decisions

## How to Use These Agents

1. **Identify the Task Type**: Is it testing, building, deploying, or documenting?
2. **Load the Appropriate Agent**: Reference the specific agent guide
3. **Follow the Patterns**: Each agent has proven approaches for their domain
4. **Use the Tools**: Agents know which scripts and commands to use

## Agent Design Principles

1. **Environment Aware**: Agents understand Docker vs local contexts
2. **Tool Proficient**: Know which existing tools to use
3. **Pattern Recognition**: Identify common issues and solutions
4. **Systematic Approach**: Follow proven debugging/building flows
5. **Knowledge Capture**: Document findings and solutions

## Creating New Agents

When creating a new agent:
1. Define clear purpose and competencies
2. Document key commands and tools
3. Include common patterns and solutions
4. Provide example workflows
5. List best practices and anti-patterns