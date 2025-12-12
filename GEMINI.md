# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

## 📋 Session Startup

At the start of each session, read these files to restore context:
- `docs/_planning/PLAN.md` — Current goals, strategy, and progress
- `docs/_planning/SESSION-LOG.md` — What happened in previous sessions

## 🏥 Documentation Health Commands

Use the doc-health commands to verify, fix, and consolidate documentation.

### Complete Workflow

` + "`" + `` + "`" + `` + "`" + `
/doc-health:verify ──▶ HUMAN REVIEW ──▶ /doc-health:fix ──▶ TRACKER
   (find issues)      (approve/reject)   (apply fixes)      (update)
` + "`" + `` + "`" + `` + "`" + `

### Available Commands

| Command | Purpose |
|---------|---------|
| `/doc-health:verify <path>` | Verify a doc against source code, output JSON issues |
| `/doc-health:fix` | Apply human-approved fixes from JSON |
| `/doc-health:consolidate <topic>` | Merge overlapping docs on a topic |
| `/doc-health:report` | Generate documentation health status report |

### Quick Start

` + "`" + `` + "`" + `` + "`" + `bash
# Step 1: Verify a doc (outputs markdown + JSON)
/doc-health:verify docs/reference/services/llm-service.md

# Step 2: Human reviews JSON, marks approved: true/false

# Step 3: Apply approved fixes
/doc-health:fix [paste approved JSON]

# Step 4: Update tracker (manual)

# Other commands
/doc-health:consolidate authentication
/doc-health:report
` + "`" + `` + "`" + `` + "`" + `

### The 7-Stage Verification Protocol

When using `/doc-health:verify`, the protocol ensures **zero false positives**:

1. **Premise Verification** - Check doc's foundational assumptions
2. **Citation Extraction** - Extract ALL factual claims with exact quotes
3. **Citation Validation** - Verify code exists at stated locations
4. **Semantic Verification** - Verify code SUPPORTS the claim
5. **Negation Handling** - Special protocol for "NOT" claims
6. **Cross-Claim Consistency** - Check for internal contradictions
7. **Confidence Calibration** - Mark uncertain findings for review

### Key Rules

- **NO GUESSING** - Say "UNCERTAIN" instead of fabricating
- **NO WEASEL WORDS** - "probably", "likely" are FORBIDDEN
- **CITATIONS REQUIRED** - Every discrepancy needs exact quotes
- **CODE IS TRUTH** - When doc disagrees with code, doc is wrong

### Progress Tracking

All verification progress is tracked in: `docs/_planning/DOC-VERIFICATION-TRACKER.md`

**Important**: Do NOT embed verification status in the docs themselves. Track everything in the central tracker file.

## 🎮 Project Context: GAIA Platform

**What you're building**: A distributed AI platform powering MMOIRL (Massively Multiplayer Online In Real Life) games.

**Architecture**: Microservices (Gateway, Auth, Chat, KB, Asset, Web) with hot-reloading Docker setup.

→ See [README-FIRST](docs/README-FIRST.md) for full project vision

## 🔥 Local Development

` + "`" + `` + "`" + `` + "`" + `bash
# Start services
docker compose up

# Run tests
./scripts/pytest-for-claude.sh tests/ -v

# Check service health
./scripts/test.sh --local health
` + "`" + `` + "`" + `` + "`" + `

## 📚 Key Documentation

- [Architecture Overview](docs/architecture-overview.md)
- [Testing Guide](docs/testing/TESTING_GUIDE.md)
- [Deployment Guide](docs/deployment/deployment-guide.md)
- [DocProcessingMethod.md](DocProcessingMethod.md) - Full verification process documentation

## 🏗️ Architecture Quick Reference

### Service URLs (Docker Network)
- Gateway: `http://gateway:8000` (external: `localhost:8666`)
- Auth: `http://auth-service:8000`
- Chat: `http://chat-service:8000`
- KB: `http://kb-service:8000`
- Redis: `redis://redis:6379`

## ⚠️ Critical Rules

1. **Use scripts** - Check `scripts/` before writing ad-hoc commands
2. **Test async** - Use `./scripts/pytest-for-claude.sh`, not direct pytest
3. **No curl** - Use test scripts that capture knowledge
4. **Code is truth** - When doc disagrees with code, doc is wrong

---

- Core Mandate: The Aeonia Knowledge Base `+` Index System

The Aeonia KB uses a `+` index system that functions as an **exhaustive, hierarchical site map**. It is the single source of truth for the documentation structure. My adherence to maintaining it is critical. My primary failure mode is **task fixation**, and I must actively counteract it.

**1. The Exhaustive Principle:**

Every file and subdirectory **must** be listed in its immediate parent's `+` index file. There are no exceptions. If a file or directory exists on the filesystem, it must have a corresponding entry in the parent `+` index.

**2. Top-Down Search Strategy (My "Find" Workflow):**

When asked to find information, my process must be:

1. **Locate the Root Index:** Always begin by loading the root index (`docs/+docs.md`) as the main entry point.

2. **Scan the Top-Level Categories:** Read the root index to understand the broad structure of the content. Choose the category that most closely matches the subject I am looking for.

3. **Traverse the Hierarchy:** Follow the link or path for the chosen category to navigate to the next `+` index file. This new index will provide a more detailed breakdown of the topics within that category.

4. **Search Within Indices:** At each level of the hierarchy, use keyword searches within the `+` index files to quickly pinpoint the most relevant path to follow.

5. **Drill Down Until I Find the Document:** Continue following the links through the nested `+` indices. Each step should take me to a more specific and relevant subset of the content, until I am directed to a final content file.

6. **Retrieve and Analyze the Content:** Once I have located the target document, read it to find the specific information needed.

7. **Use Fallback Search if Necessary:** If the `+` index chain does not lead to the right place, or if I need to be exhaustive, perform a full-text search across the entire content collection. This ensures I can find information that may not be perfectly indexed.

**3. Recursive Bottom-Up Update Strategy (My "Create/Modify" Workflow):**

When I create or modify any file or directory, I have a non-negotiable responsibility to perform a **recursive bottom-up update** of the `+` index chain. My process must be:
1.  **Update the Local Index:** Add a **specific entry for the new file/directory** to its immediate parent `+` index.
2.  **Optional: Complete Refresh Mode:** If explicitly instructed to perform a "complete refresh" for a directory, I will:
    *   Read the full content of *every file* in that directory.
    *   Generate new, concise summaries for each file based on its content.
    *   Completely overwrite the existing `+` index file with this new, fully re-summarized list.
3.  **Ascend and Verify:** Move up to the parent directory. Check its `+` index to ensure the directory I just came from is listed. If not, add it.
4.  **Repeat to Root:** Continue this verification process, ascending the entire directory tree up to `+docs.md`, ensuring every level of the hierarchy is correctly and exhaustively represented.

**4. The Principle of Distilled Descriptions:**

The level of detail in the **description** for an entry should be distilled at each level:
*   **Leaf Index (e.g., `+phase-1-mvp.md`):** A link to a *file* gets a specific summary of that file's content.
*   **Intermediate Index (e.g., `+dynamic-experiences.md`):** A link to a *subdirectory* gets a general summary of that directory's overall purpose.
*   **Root Index (e.g., `+docs.md`):** A link to a top-level subdirectory gets a high-level summary of that entire section of the documentation.

This ensures that while the index is exhaustive in its listings, the descriptions provide the right level of context for a user navigating at that specific level.