# Continue Documentation Verification

**Copy this prompt to continue in a new chat:**

---

```
Continue documentation verification using the 7-stage anti-hallucination protocol.

Context:
- 390 docs need verification
- 2 verified so far (persona-system-guide.md, prompt-manager.md)
- Previous verification was unreliable (~40% false positives)
- New protocol achieves 0% false positives

Read these files first:
1. docs/_planning/DOC-VERIFICATION-TRACKER.md (progress)
2. scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md (full protocol)
3. .claude/agents/reviewer.md (agent instructions)

Then verify the next priority doc:
- docs/reference/services/llm-service.md

Use Task(subagent_type="reviewer", model="sonnet") with the full 7-stage protocol.
Update the tracker after each verification.
```

---

## Quick Reference

**Protocol location:** `scripts/doc-verify/ENHANCED_VERIFICATION_PROTOCOL.md`

**Tracker location:** `docs/_planning/DOC-VERIFICATION-TRACKER.md`

**Priority queue:**
1. ~~persona-system-guide.md~~ ✅
2. ~~prompt-manager.md~~ ✅
3. llm-service.md ← NEXT
4. chat-service-implementation.md
5. kb-agent-overview.md
6. database-architecture.md
7. api-contracts.md
8. ...remaining 383 docs

**Key rule:** NO CLAIMS WITHOUT EXACT CITATIONS from both doc AND code.
