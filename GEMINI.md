# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

## 📋 Session Startup

At the start of each session, read these files to restore context:
- `docs/_planning/PLAN.md` — Current goals, strategy, and progress
- `docs/_planning/SESSION-LOG.md` — What happened in previous sessions

## 🏥 Documentation Health Commands

Use the doc-health commands to verify, fix, and consolidate documentation.

### Complete Workflow

```
/doc-health:verify ──▶ HUMAN REVIEW ──▶ /doc-health:fix ──▶ TRACKER
   (find issues)      (approve/reject)   (apply fixes)      (update)
```

### Available Commands

| Command | Purpose |
|---------|---------|
| `/doc-health:verify <path>` | Verify a doc against source code, output JSON issues |
| `/doc-health:fix` | Apply human-approved fixes from JSON |
| `/doc-health:consolidate <topic>` | Merge overlapping docs on a topic |
| `/doc-health:report` | Generate documentation health status report |

### Quick Start

```bash
# Step 1: Verify a doc (outputs markdown + JSON)
/doc-health:verify docs/reference/services/llm-service.md

# Step 2: Human reviews JSON, marks approved: true/false

# Step 3: Apply approved fixes
/doc-health:fix [paste approved JSON]

# Step 4: Update tracker (manual)

# Other commands
/doc-health:consolidate authentication
/doc-health:report
```

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

```bash
# Start services
docker compose up

# Run tests
./scripts/pytest-for-claude.sh tests/ -v

# Check service health
./scripts/test.sh --local health
```

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
