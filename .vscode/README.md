# VS Code Configuration for GAIA Project

This directory contains VS Code workspace settings for the GAIA project.

## Setup

Copy the example settings to create your personal configuration:

```bash
cp .vscode/settings.json.example .vscode/settings.json
```

Your personal `settings.json` is gitignored and won't be committed.

## What's Configured

- **Python Interpreter**: Uses `.venv/bin/python3` (the CLI client virtual environment)
- **Terminal Activation**: Automatically activates venv when opening integrated terminal
- **Testing**: Configured for pytest with tests in `tests/` directory
- **Type Checking**: Basic type checking enabled
- **Code Formatting**: Black formatter (on-demand, not auto-save)

## Why Two Python Environments?

The GAIA project has two separate Python environments:

1. **Docker Services** (Gateway, Chat, Auth, KB, etc.)
   - Run in Docker containers
   - No local Python setup needed
   - Hot-reloading via volume mounts

2. **CLI Client** (`scripts/gaia_client.py`)
   - Standalone Python script
   - Uses `.venv` virtual environment
   - Requires local Python 3.8+

This VS Code configuration is for **CLI client development only**. The main GAIA services don't need this.

## Customization

Feel free to modify your personal `settings.json` with:
- Your preferred formatter settings
- Additional Python extensions
- Custom linting rules
- etc.

Just don't commit your personal settings—keep them local!
