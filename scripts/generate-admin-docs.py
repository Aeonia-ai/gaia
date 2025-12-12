#!/usr/bin/env python3
"""Generate admin command documentation from code docstrings.

Usage:
    python scripts/generate-admin-docs.py

This extracts structured docstrings from _admin_* methods in kb_agent.py
and generates a markdown reference document.
"""

import ast
import re
from pathlib import Path
from datetime import datetime


def parse_docstring(docstring: str) -> dict:
    """Parse structured docstring into components."""
    result = {
        'summary': '',
        'command': '',
        'category': 'Other',
        'destructive': False,
        'syntax': [],
        'examples': [],
        'side_effects': [],
        'requires_confirm': False
    }

    if not docstring:
        return result

    lines = docstring.strip().split('\n')
    result['summary'] = lines[0].strip() if lines else ""

    # Extract Command: @xxx
    if match := re.search(r'Command:\s*@(\w+)', docstring):
        result['command'] = match.group(1)

    # Extract Category
    if match := re.search(r'Category:\s*(\w+)', docstring):
        result['category'] = match.group(1)

    # Extract Destructive
    if match := re.search(r'Destructive:\s*(yes|no)', docstring, re.IGNORECASE):
        result['destructive'] = match.group(1).lower() == 'yes'

    # Extract Syntax block
    if match := re.search(r'Syntax:\s*\n((?:[ \t]+.+\n?)+)', docstring):
        result['syntax'] = [
            line.strip() for line in match.group(1).strip().split('\n')
            if line.strip()
        ]

    # Extract Examples block
    if match := re.search(r'Examples:\s*\n((?:[ \t]+.+\n?)+)', docstring):
        result['examples'] = [
            line.strip() for line in match.group(1).strip().split('\n')
            if line.strip()
        ]

    # Extract Side Effects
    if match := re.search(r'Side Effects:\s*\n((?:[ \t]+[-*].+\n?)+)', docstring):
        result['side_effects'] = [
            line.strip().lstrip('-* ')
            for line in match.group(1).strip().split('\n')
            if line.strip()
        ]

    # Extract Requires CONFIRM
    if 'Requires: CONFIRM' in docstring:
        result['requires_confirm'] = True

    return result


def extract_admin_methods(filepath: Path) -> list:
    """Extract all _admin_* methods with their docstrings."""
    source = filepath.read_text()
    tree = ast.parse(source)

    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('_admin_'):
            # Skip sub-methods like _admin_list_waypoints
            if node.name.count('_') > 2:
                continue

            docstring = ast.get_docstring(node) or ""
            parsed = parse_docstring(docstring)

            # Default command name from method name
            if not parsed['command']:
                parsed['command'] = node.name.replace('_admin_', '')

            methods.append({
                'name': node.name,
                'lineno': node.lineno,
                'parsed': parsed
            })

    # Sort by command name
    methods.sort(key=lambda m: m['parsed']['command'])
    return methods


def generate_markdown(methods: list) -> str:
    """Generate markdown documentation from extracted methods."""
    lines = [
        "# Admin Command Reference",
        "",
        "> **Auto-generated** from code docstrings in `app/services/kb/kb_agent.py`",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ">",
        "> Run `python scripts/generate-admin-docs.py` to regenerate.",
        "",
        f"**{len(methods)} commands** for world-building. All start with `@` and execute instantly (<30ms).",
        "",
        "## Quick Reference",
        "",
        "| Command | Description |",
        "|---------|-------------|",
    ]

    for m in methods:
        p = m['parsed']
        confirm = " ⚠️" if p['requires_confirm'] else ""
        lines.append(f"| `@{p['command']}`{confirm} | {p['summary'][:50]}{'...' if len(p['summary']) > 50 else ''} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed sections
    for m in methods:
        p = m['parsed']

        lines.append(f"## @{p['command']}")
        lines.append("")
        lines.append(p['summary'] or f"Handle @{p['command']} command.")
        lines.append("")

        if p['requires_confirm'] or p['destructive']:
            lines.append("> ⚠️ **Destructive operation** - requires `CONFIRM` keyword.")
            lines.append("")

        if p['syntax']:
            lines.append("**Syntax:**")
            lines.append("```bash")
            lines.extend(p['syntax'])
            lines.append("```")
            lines.append("")

        if p['examples']:
            lines.append("**Examples:**")
            lines.append("```bash")
            lines.extend(p['examples'])
            lines.append("```")
            lines.append("")

        if p['side_effects']:
            lines.append("**Side Effects:**")
            for effect in p['side_effects']:
                lines.append(f"- {effect}")
            lines.append("")

        # Source reference
        lines.append(f"*Implementation: `{m['name']}()` in kb_agent.py*")
        lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    # Find kb_agent.py relative to script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    kb_agent_path = project_root / 'app' / 'services' / 'kb' / 'kb_agent.py'
    output_path = project_root / 'docs' / 'reference' / 'api' / 'admin-commands-reference.md'

    if not kb_agent_path.exists():
        print(f"Error: {kb_agent_path} not found")
        return 1

    print(f"Extracting from {kb_agent_path}...")
    methods = extract_admin_methods(kb_agent_path)
    print(f"Found {len(methods)} admin commands")

    markdown = generate_markdown(methods)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)
    print(f"Generated {output_path} ({len(markdown)} bytes)")

    # Show status
    print("\nDocstring coverage:")
    for m in methods:
        p = m['parsed']
        has_syntax = "✓" if p['syntax'] else "○"
        has_examples = "✓" if p['examples'] else "○"
        print(f"  @{p['command']:<12} syntax:{has_syntax} examples:{has_examples}")

    return 0


if __name__ == '__main__':
    exit(main())
