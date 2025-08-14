Prepare for pull request submission:

1. **Run all tests**
   ```bash
   ./scripts/pytest-for-claude.sh tests/unit tests/integration -v
   ```

2. **Code quality checks**
   ```bash
   ruff check app/
   ruff format app/ --check
   ```

3. **Check for uncommitted changes**
   ```bash
   git status
   git diff
   ```

4. **Review changed files**
   List all modified files and check for:
   - Leftover debug prints
   - TODO comments that should be addressed
   - Proper error handling
   - Test coverage for new code

5. **Documentation updates**
   - Is README updated if needed?
   - Are new env vars documented?
   - Is CLAUDE.md updated for new patterns?

6. **Security check**
   - No hardcoded secrets
   - No exposed credentials
   - Proper input validation

7. **PR checklist**
   - [ ] All tests passing
   - [ ] Code follows project style
   - [ ] Documentation updated
   - [ ] No security issues
   - [ ] Changes are focused and atomic

**Generate PR description template:**
```
## Summary
[What does this PR do?]

## Changes
- [List key changes]

## Testing
- [How was this tested?]

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes
```