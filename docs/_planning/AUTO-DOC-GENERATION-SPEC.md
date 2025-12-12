# Auto-Generated Documentation Spec

**Created:** 2025-12-11
**Status:** IMPLEMENTED

## Quick Start

```bash
# Regenerate admin command docs from code docstrings
python scripts/generate-admin-docs.py
```

**Output:** `docs/reference/api/admin-commands-reference.md`

---

## Problem

Documentation line numbers become stale as code evolves. The `025-complete-admin-command-system.md` doc had line numbers ~630 lines off from actual code.

**Root cause:** Manual documentation of implementation details that change frequently.

**Solution:** Generate documentation from code docstrings automatically.

---

## Approach

### 1. Enhance Code Docstrings

Add structured docstrings to admin command methods:

```python
async def _admin_create(
    self,
    target_type: Optional[str],
    args: List[str],
    experience: str,
    user_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new entity in the game world.

    Command: @create
    Category: CRUD

    Syntax:
        @create waypoint <waypoint_id> "<name>"
        @create location <waypoint_id> <location_id> "<name>"
        @create sublocation <waypoint_id> <location_id> <subloc_id> "<name>"

    Examples:
        @create waypoint forest_01 "Dark Forest"
        @create location forest_01 clearing "Forest Clearing"
        @create sublocation forest_01 clearing pond "Small Pond"

    Args:
        target_type: Entity type (waypoint, location, sublocation)
        args: Command arguments [id, name, ...]
        experience: Experience slug (e.g., "wylding-woods")
        user_context: Auth context with user info

    Returns:
        Dict with success, narrative, and created entity data

    Side Effects:
        - Creates new entry in locations.json
        - Sets metadata (created_at, created_by)
        - For sublocations: adds to parent location's sublocation list

    Requires: CONFIRM not required (non-destructive)
    """
```

### 2. Docstring Schema

Standardize docstring format for admin commands:

```
"""<One-line summary>

Command: @<command_name>
Category: CRUD | Navigation | Search | Stats | Reset
Destructive: yes | no

Syntax:
    @command <required> [optional]
    @command variant2

Examples:
    @command arg1 "value"

Args:
    <param>: <description>

Returns:
    <description of return dict>

Side Effects:
    - <what changes in the system>

Requires: CONFIRM | None
"""
```

### 3. Extraction Script

Create `scripts/generate-admin-docs.py`:

```python
#!/usr/bin/env python3
"""Generate admin command documentation from code docstrings."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any

def extract_admin_methods(filepath: Path) -> List[Dict[str, Any]]:
    """Extract all _admin_* methods with their docstrings."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('_admin_'):
            docstring = ast.get_docstring(node) or ""
            methods.append({
                'name': node.name,
                'lineno': node.lineno,
                'docstring': docstring,
                'parsed': parse_docstring(docstring)
            })
    return methods

def parse_docstring(docstring: str) -> Dict[str, Any]:
    """Parse structured docstring into components."""
    result = {
        'summary': '',
        'command': '',
        'category': '',
        'destructive': False,
        'syntax': [],
        'examples': [],
        'args': {},
        'returns': '',
        'side_effects': [],
        'requires_confirm': False
    }

    # Extract Command: @xxx
    if match := re.search(r'Command:\s*@(\w+)', docstring):
        result['command'] = match.group(1)

    # Extract Category
    if match := re.search(r'Category:\s*(\w+)', docstring):
        result['category'] = match.group(1)

    # Extract Syntax block
    if match := re.search(r'Syntax:\s*\n((?:\s+@.+\n?)+)', docstring):
        result['syntax'] = [line.strip() for line in match.group(1).strip().split('\n')]

    # Extract Examples block
    if match := re.search(r'Examples:\s*\n((?:\s+@.+\n?)+)', docstring):
        result['examples'] = [line.strip() for line in match.group(1).strip().split('\n')]

    # Extract Requires
    if 'Requires: CONFIRM' in docstring:
        result['requires_confirm'] = True

    return result

def generate_markdown(methods: List[Dict[str, Any]]) -> str:
    """Generate markdown documentation from extracted methods."""
    output = ["# Admin Command Reference (Auto-Generated)\n"]
    output.append("> This file is auto-generated from code docstrings.")
    output.append("> Do not edit manually. Run `scripts/generate-admin-docs.py` to update.\n")

    # Group by category
    by_category = {}
    for method in methods:
        cat = method['parsed'].get('category', 'Other')
        by_category.setdefault(cat, []).append(method)

    for category, cmds in sorted(by_category.items()):
        output.append(f"\n## {category}\n")
        for cmd in cmds:
            p = cmd['parsed']
            output.append(f"### @{p['command']}\n")
            output.append(f"{cmd['docstring'].split(chr(10))[0]}\n")  # First line

            if p['syntax']:
                output.append("**Syntax:**")
                output.append("```bash")
                output.extend(p['syntax'])
                output.append("```\n")

            if p['examples']:
                output.append("**Examples:**")
                output.append("```bash")
                output.extend(p['examples'])
                output.append("```\n")

            if p['requires_confirm']:
                output.append("> **Warning:** Requires `CONFIRM` keyword.\n")

    return '\n'.join(output)

if __name__ == '__main__':
    kb_agent = Path('app/services/kb/kb_agent.py')
    methods = extract_admin_methods(kb_agent)
    markdown = generate_markdown(methods)

    output_path = Path('docs/reference/api/admin-commands-reference.md')
    output_path.write_text(markdown)
    print(f"Generated {output_path} with {len(methods)} commands")
```

### 4. CI Integration

Add to GitHub Actions:

```yaml
# .github/workflows/docs.yml
name: Generate Docs

on:
  push:
    paths:
      - 'app/services/kb/kb_agent.py'

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Generate admin command docs
        run: python scripts/generate-admin-docs.py

      - name: Check for changes
        run: |
          if git diff --quiet docs/reference/api/admin-commands-reference.md; then
            echo "No doc changes"
          else
            echo "::warning::Admin command docs are out of date. Run scripts/generate-admin-docs.py"
            exit 1
          fi
```

---

## Output Structure

The generated doc would look like:

```markdown
# Admin Command Reference (Auto-Generated)

> This file is auto-generated from code docstrings.
> Do not edit manually. Run `scripts/generate-admin-docs.py` to update.

## CRUD

### @create

Create a new entity in the game world.

**Syntax:**
```bash
@create waypoint <waypoint_id> "<name>"
@create location <waypoint_id> <location_id> "<name>"
@create sublocation <waypoint_id> <location_id> <subloc_id> "<name>"
```

**Examples:**
```bash
@create waypoint forest_01 "Dark Forest"
@create location forest_01 clearing "Forest Clearing"
```

### @delete

Delete an entity from the game world.

**Syntax:**
```bash
@delete waypoint <waypoint_id> CONFIRM
@delete location <waypoint_id> <location_id> CONFIRM
```

> **Warning:** Requires `CONFIRM` keyword.

...
```

---

## Migration Plan

### Phase 1: Enhance Docstrings (1-2 hours)
- [ ] Add structured docstrings to all 12 `_admin_*` methods in `kb_agent.py`
- [ ] Follow the docstring schema above

### Phase 2: Create Extraction Script (1 hour)
- [ ] Create `scripts/generate-admin-docs.py`
- [ ] Test extraction on enhanced docstrings
- [ ] Generate initial `admin-commands-reference.md`

### Phase 3: CI Integration (30 min)
- [ ] Add GitHub Action to check docs are current
- [ ] Add pre-commit hook option

### Phase 4: Deprecate Manual Docs (30 min)
- [ ] Add deprecation notice to `025-complete-admin-command-system.md`
- [ ] Point to auto-generated reference as source of truth

---

## Benefits

1. **Always accurate** - Docs generated from code can't drift
2. **Single source of truth** - Docstrings in code, not separate files
3. **IDE integration** - Docstrings visible in code completion
4. **Enforced by CI** - PR fails if docs are stale
5. **Lower maintenance** - Update code, docs follow

## Trade-offs

1. **Less narrative** - Auto-generated docs are reference-style, not tutorial-style
2. **Docstring discipline** - Requires consistent docstring format
3. **Build step** - Adds complexity to doc workflow

---

## Recommendation

Keep two types of docs:
1. **Auto-generated reference** (`admin-commands-reference.md`) - Always accurate, exhaustive
2. **Hand-written guides** (`025-complete-admin-command-system.md`) - Narrative, tutorials, examples

The reference is the "what", the guide is the "why" and "how".
