# Documentation Fix Protocol

## Purpose

Apply human-approved documentation fixes with precision. You are a focused editor - your only job is to make the specific edits in the approval manifest.

---

## Input: Approval Manifest

You will receive a JSON array of approved issues:

```json
[
  {
    "issue_id": "doc-001",
    "file_path": "docs/reference/services/example.md",
    "line_range": [42, 45],
    "affected_text": "const result = function_v1(options);",
    "replacement_text": "const result = function_v2(options);",
    "approved": true,
    "reviewer_notes": "Confirmed v2 is current API"
  }
]
```

**Only process issues where `approved: true`.**

---

## Fix Process

For each approved issue:

### Step 1: Read the File
```
Read [file_path] to verify current state
```

### Step 2: Locate the Text
Find `affected_text` in the file. If not found exactly:
- Check for whitespace differences
- Check if text was already changed
- Report SKIP if text cannot be located

### Step 3: Apply the Edit
```
Edit [file_path]:
  old_string: [affected_text]
  new_string: [replacement_text]
```

### Step 4: Verify the Change
Re-read the section to confirm the edit was applied correctly.

### Step 5: Report Result
```json
{
  "issue_id": "doc-001",
  "status": "FIXED" | "SKIPPED" | "FAILED",
  "file_path": "docs/reference/services/example.md",
  "change_applied": {
    "before": "[old text]",
    "after": "[new text]"
  },
  "error": null | "[error message if failed]"
}
```

---

## Constraints

1. **ONLY make specified edits** - Do not fix other issues you notice
2. **ONLY process approved issues** - Skip issues where `approved: false`
3. **EXACT replacements** - Use the exact `replacement_text` provided
4. **Report everything** - Success, skips, and failures all get reported
5. **No interpretation** - Don't "improve" the replacement text

---

## Error Handling

### Text Not Found
```json
{
  "issue_id": "doc-001",
  "status": "SKIPPED",
  "error": "affected_text not found in file - may have been edited since verification"
}
```

### File Not Found
```json
{
  "issue_id": "doc-001",
  "status": "FAILED",
  "error": "file not found: docs/reference/services/example.md"
}
```

### Edit Failed
```json
{
  "issue_id": "doc-001",
  "status": "FAILED",
  "error": "edit tool returned error: [details]"
}
```

---

## Output Format

Return a JSON array of results:

```json
{
  "summary": {
    "total": 5,
    "fixed": 4,
    "skipped": 1,
    "failed": 0
  },
  "results": [
    {"issue_id": "doc-001", "status": "FIXED", ...},
    {"issue_id": "doc-002", "status": "FIXED", ...},
    {"issue_id": "doc-003", "status": "SKIPPED", "error": "text not found"},
    {"issue_id": "doc-004", "status": "FIXED", ...},
    {"issue_id": "doc-005", "status": "FIXED", ...}
  ]
}
```

---

## Invocation

```python
Task(
    subagent_type="coder",  # or "builder"
    model="sonnet",
    prompt="""
    Read .claude/skills/doc-health/fix-protocol.md and follow it exactly.

    Apply these approved fixes:
    [PASTE APPROVAL MANIFEST JSON]

    Return structured JSON results.
    """
)
```
