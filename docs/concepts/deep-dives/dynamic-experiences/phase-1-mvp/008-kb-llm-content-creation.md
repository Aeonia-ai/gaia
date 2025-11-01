# LLM-Powered KB Content Creation

> **Status**: DEMO DEVELOPMENT (4-Day Sprint)
> **Version**: 0.1
> **Purpose**: Enable game designers to create KB content through natural conversation
> **Created**: 2025-10-24
> **Target Demo**: 2025-10-28
> **Related**:
> - [Game Command Developer Guide](../../api/game-command-developer-guide.md) - Runtime game system
> - [KB Architecture Guide](./kb-architecture-guide.md) - KB infrastructure
> - [KB Git Sync Learnings](./kb-git-sync-learnings.md) - Git integration patterns

## Executive Summary

**Vision:** Game designers create AR waypoints, text adventure rooms, and game items through natural conversation with an LLM, rather than filling out forms or editing YAML files directly.

**Demo Value Proposition:**
"Create AR game content through natural conversation - no forms, no code, just chat"

**Key Innovation:** The LLM becomes a conversational form builder that:
- Guides designers through required fields incrementally
- Validates data as you go
- Generates properly formatted markdown + YAML
- Commits changes to Git with meaningful commit messages
- Enforces role-based access (only designers can create content)

## Architecture Overview

### How It Works

```
Designer (Web Chat):
"Create a new waypoint called Secret Garden at 37.905, -122.548"

     ↓

Chat Service:
- LLM detects admin command via KB_ADMIN_TOOLS
- Calls create_kb_waypoint tool
- Gathers missing data through conversation

     ↓

KB Service:
- Validates waypoint data
- Generates markdown file with YAML frontmatter
- Writes to /kb/experiences/{experience}/waypoints/
- Git commit + push

     ↓

Result:
✅ New waypoint file created
✅ Committed to Git with message "Add Secret Garden waypoint"
✅ Auto-syncs to production within 15 minutes
```

### Key Components

**1. KB Admin Tools** (`app/services/chat/kb_admin_tools.py`)
```python
KB_ADMIN_TOOLS = [
    {
        "name": "create_kb_waypoint",
        "description": "Create new AR waypoint through conversation",
        "parameters": {
            "waypoint_data": {
                "name": str,
                "location": {"lat": float, "lng": float},
                "waypoint_type": str,
                "media": {...}
            }
        }
    },
    {
        "name": "create_kb_room",
        "description": "Create text adventure room"
    },
    {
        "name": "create_kb_item",
        "description": "Create game item"
    },
    {
        "name": "list_kb_templates",
        "description": "List available content templates"
    }
]
```

**2. KB Write Endpoints** (`app/services/kb/admin_endpoints.py`)
```python
@router.post("/admin/waypoints")
async def create_waypoint(
    experience: str,
    waypoint: WaypointCreate,
    user: AuthUser = Depends(require_designer)
):
    # 1. Generate markdown with YAML
    content = generate_waypoint_markdown(waypoint)

    # 2. Write to KB filesystem
    path = f"/experiences/{experience}/waypoints/{waypoint.id}.md"
    await kb_storage.write_file(path, content)

    # 3. Git commit
    await kb_git.commit(
        message=f"Add waypoint: {waypoint.name}",
        author=user.email
    )

    # 4. Push to remote
    await kb_git.push()

    return {"success": True, "path": path, "commit": commit_hash}
```

**3. Conversational Flow Handler** (`app/services/chat/kb_creation_flow.py`)
```python
class KBCreationFlow:
    """Multi-turn conversation for KB content creation"""

    async def handle_create_waypoint(self, conversation_id, initial_data):
        # Store partial data in conversation metadata
        session = await get_creation_session(conversation_id)

        if not session:
            # Start new creation flow
            session = {
                "type": "waypoint",
                "data": initial_data,
                "missing_fields": ["lat", "lng", "waypoint_type"],
                "state": "gathering"
            }

        # Incrementally gather missing fields
        if session["missing_fields"]:
            return ask_for_next_field(session["missing_fields"][0])

        # All data gathered - show preview
        if session["state"] == "gathering":
            return show_preview_and_confirm(session["data"])

        # Confirmed - create in KB
        if session["state"] == "confirming":
            result = await create_waypoint_in_kb(session["data"])
            return format_success_message(result)
```

**4. RBAC - Designer Role**
```python
class UserRole(str, Enum):
    PLAYER = "player"
    DESIGNER = "designer"  # NEW - Can create KB content
    GAMEMASTER = "gamemaster"
    ADMIN = "admin"

@require_role("designer")
async def create_kb_content(...):
    # Only designers and admins can execute
    ...
```

## 4-Day Implementation Plan

### Day 1: Foundation + Basic Write (8 hours)

**Goal:** Enable LLM to write single waypoint to KB

**Morning: KB Write Infrastructure (4h)**
- [ ] Add write permissions to KB service
- [ ] Create `POST /admin/kb/write` endpoint
- [ ] Implement file write + validation
- [ ] Add basic Git commit (no push yet)
- [ ] Create `create_kb_waypoint` tool (single-turn)

**Afternoon: Test & Validate (4h)**
- [ ] Test tool via chat interface
- [ ] Verify file created in KB filesystem
- [ ] Verify Git commit created
- [ ] Add template/schema endpoint
- [ ] LLM can query "what fields does waypoint need?"

**Demo-able by EOD:** Single-turn waypoint creation
```
Designer: "Create waypoint test_point at 37.9, -122.5 type gps"
AI: "✅ Created waypoint test_point"
```

---

### Day 2: Conversational Flow (8 hours)

**Goal:** LLM guides designer through multi-turn data collection

**Morning: Multi-Turn Conversation (5h)**
- [ ] Conversation state management
- [ ] Store partial waypoint data in conversation metadata
- [ ] Track "what fields still needed"
- [ ] Resume from where left off
- [ ] Incremental data gathering

**Afternoon: Validation & Preview (3h)**
- [ ] Field validation (GPS range, file existence)
- [ ] Duplicate ID checking
- [ ] Preview before commit
- [ ] "Does this look correct? (yes/edit/cancel)"

**Demo-able by EOD:** Full conversational creation
```
Designer: "Create new waypoint"
AI: "What's the name?"
Designer: "Secret Garden"
AI: "Where is it located?"
Designer: "37.905, -122.548"
AI: "What type?" ...
```

---

### Day 3: Git Integration + RBAC (8 hours)

**Goal:** Changes go to Git, only designers can create

**Morning: Production Git Workflow (4h)**
- [ ] Git push implementation
- [ ] Show commit hash in response
- [ ] Handle merge conflicts gracefully
- [ ] KB auto-sync trigger (force reload or wait 15min)
- [ ] "Changes will be live in X minutes" message

**Afternoon: Designer Role (4h)**
- [ ] Add "designer" role to auth system
- [ ] Update user model
- [ ] Add role checking middleware
- [ ] Block non-designers from KB admin tools
- [ ] Test: player can't create, designer can

**Demo-able by EOD:** Secure, Git-backed content creation
```
[Show GitHub commit]
[Show content appears in KB service after sync]
[Try as player - blocked]
[Try as designer - works]
```

---

### Day 4: Polish + Additional Content (8 hours)

**Goal:** Multi-content support + demo-ready

**Morning: Multi-Content Support (4h)**
- [ ] Add `create_kb_room` tool (text adventures)
- [ ] Add `create_kb_item` tool (game items)
- [ ] Add `list_kb_content` tool (search/browse)
- [ ] Different schemas for different content types

**Afternoon: Demo Prep (4h)**
- [ ] Error handling polish
- [ ] Friendly error messages
- [ ] Recovery from failures
- [ ] Rollback on Git errors
- [ ] Write detailed demo script
- [ ] Practice run (timing, rough edges)
- [ ] Pre-create test data as backup

**Demo-ready by EOD!**

---

## Demo Script (5 minutes)

### Act 1: Play the Game (1 min)
```
"Let me show you our AR game, Wylding Woods."

[Open chat UI]
Designer: "I want to play Wylding Woods"
AI: [Game starts]

Designer: "go north"
AI: [Narrative response with location description]

"This works great. But how do we ADD MORE content?"
```

### Act 2: Create Content via Chat (3 min)
```
"Watch this - I'll add a new waypoint through conversation."

[Switch to designer account]
Designer: "Create a new waypoint for Wylding Woods"

AI: "Great! What should we call it?"

Designer: "Secret Garden"

AI: "Where should it be located?"

Designer: "37.9055, -122.5483"

AI: "What type of waypoint is this?"

Designer: "Interactive - players can pick mystical flowers"

AI: "What should happen when players interact?"

Designer: "Play flower-chime.wav, show petal-fall visual effect,
         and display 'You gather mystical flowers that glow softly'"

AI: [Shows formatted preview]
    "📍 Waypoint: Secret Garden
     🗺️ Location: 37.9055, -122.5483
     🎮 Type: Interactive
     🎵 Audio: flower-chime.wav
     ✨ Visual FX: petal-fall
     💬 Text: 'You gather mystical flowers...'

     Does this look correct? (yes/edit/cancel)"

Designer: "yes"

AI: "✅ Created waypoint at /kb/experiences/wylding-woods/waypoints/secret_garden.md
     🔄 Committed to Git: 'Add Secret Garden waypoint'
     📝 Commit hash: abc1234

     The waypoint will be live within 15 minutes."

[Show actual commit on GitHub]
[Explain: "Git version control means we can track who added what, when, and roll back if needed"]
```

### Act 3: The Payoff (1 min)
```
"This is the power of LLM-driven game design:

✅ No forms to fill out
✅ No code to write
✅ Natural conversation
✅ Git version control
✅ Role-based security
✅ Works for waypoints, rooms, items, NPCs...

Designers focus on creativity. AI handles the structure."
```

---

## Risk Mitigation

### If Things Break

**Plan B (Day 3 slip):**
- Skip auto-push, demo manual Git commands
- Show commits in filesystem, skip KB reload
- "In production, this auto-syncs"

**Plan C (Day 4 slip):**
- Demo only waypoint creation (skip rooms/items)
- Use pre-scripted conversation (not live LLM)
- Show canned demo with pre-created content

**Emergency Fallback:**
- Have pre-created content ready
- "Here's what I created earlier using this system..."
- Show Git commit history as proof of concept

### Common Issues

**Git Conflicts:**
- Solution: Pull before push, auto-merge non-conflicting
- If conflict: Show error, ask designer to try again

**KB Sync Delay:**
- Solution: Show "pending" status
- Explain 15-minute sync window
- OR implement force-sync endpoint

**LLM Hallucination:**
- Solution: Validate ALL fields before commit
- Check file existence for media assets
- Reject invalid GPS coordinates

---

## Technical Details

### File Format Generation

**Input (from LLM conversation):**
```python
{
    "name": "Secret Garden",
    "id": "secret_garden",  # Auto-slugified
    "location": {"lat": 37.9055, "lng": -122.5483},
    "waypoint_type": "interactive",
    "media": {
        "audio": "flower-chime.wav",
        "visual_fx": "petal-fall",
        "display_text": "You gather mystical flowers that glow softly"
    }
}
```

**Output (generated markdown):**
```markdown
# Secret Garden

​```yaml
id: secret_garden
name: Secret Garden
location:
  lat: 37.9055
  lng: -122.5483
waypoint_type: interactive
media:
  audio: flower-chime.wav
  visual_fx: petal-fall
  interaction: tap
  display_text: You gather mystical flowers that glow softly
​```
```

### Git Workflow

```python
# 1. Write file
await kb_storage.write_file(
    path="/experiences/wylding-woods/waypoints/secret_garden.md",
    content=generated_markdown
)

# 2. Stage changes
await git.add("experiences/wylding-woods/waypoints/secret_garden.md")

# 3. Commit with attribution
await git.commit(
    message="Add Secret Garden waypoint",
    author=f"{designer.name} <{designer.email}>"
)

# 4. Push to remote
await git.push("origin", "main")

# 5. Trigger KB service reload (optional)
await kb_service.reload_content()
```

### Validation Rules

**Waypoint Validation:**
```python
def validate_waypoint(data: WaypointCreate) -> ValidationResult:
    errors = []

    # GPS coordinates
    if not (-90 <= data.location.lat <= 90):
        errors.append("Latitude must be between -90 and 90")
    if not (-180 <= data.location.lng <= 180):
        errors.append("Longitude must be between -180 and 180")

    # Unique ID
    if waypoint_exists(data.id):
        errors.append(f"Waypoint ID '{data.id}' already exists")

    # Media files exist
    if data.media.audio and not file_exists(data.media.audio):
        errors.append(f"Audio file '{data.media.audio}' not found")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

---

## Future Enhancements (Post-Demo)

### Phase 2: Additional Content Types
- [ ] NPCs (characters with dialogue trees)
- [ ] Quests (multi-step missions)
- [ ] Collectibles (items to find)
- [ ] Sound zones (ambient audio regions)

### Phase 3: Advanced Features
- [ ] Bulk import (CSV → waypoints)
- [ ] Template library (reusable patterns)
- [ ] Content preview (see on map before commit)
- [ ] Collaborative editing (multiple designers)
- [ ] Approval workflow (designer → lead approval)

### Phase 4: Visual Tools
- [ ] Map-based placement (drag-drop on map)
- [ ] Visual waypoint editor (alongside LLM)
- [ ] Asset upload via chat ("attach audio file")
- [ ] Screenshot annotation ("place waypoint here")

---

## Comparison to Traditional Approaches

### Traditional CMS/Form Approach
```
Designer logs into admin panel
→ Clicks "Add Waypoint"
→ Fills out 15-field form
→ Uploads media files separately
→ Clicks "Save Draft"
→ Clicks "Publish"
→ No version control
→ No attribution
```

### Obsidian/Git Approach (Current)
```
Designer opens Obsidian
→ Creates new .md file
→ Writes YAML frontmatter by hand
→ Commits to Git
→ Pushes to remote
→ KB service auto-syncs
→ Requires technical knowledge
```

### LLM-Powered Approach (This System)
```
Designer opens chat
→ "Create waypoint Secret Garden at 37.9, -122.5"
→ AI guides through remaining fields
→ AI shows preview
→ Designer confirms
→ AI writes file, commits to Git, syncs
→ Zero technical knowledge required
→ Natural conversation interface
```

---

## Success Metrics

### Demo Success Criteria
- [ ] Can create waypoint in <2 minutes via conversation
- [ ] Waypoint appears in Git with proper commit
- [ ] Waypoint loads in game within 15 minutes
- [ ] Non-designer blocked from creating content
- [ ] Designer can create without touching code/YAML

### Post-Demo Metrics
- Time to create content: Target <3 min per waypoint
- Designer satisfaction: >4/5 rating
- Error rate: <5% failed creations
- Git conflict rate: <1%
- Adoption: 80% of designers prefer LLM over Obsidian

---

## Related Documentation

- [Game Command Developer Guide](../../api/game-command-developer-guide.md) - Runtime game system
- [KB Architecture Guide](./kb-architecture-guide.md) - KB infrastructure
- [KB Git Sync Learnings](./kb-git-sync-learnings.md) - Git integration patterns
- [KB-Driven Command Processing Spec](../../api/kb-driven-command-processing-spec.md) - Game command spec
- [RBAC System Guide](../../rbac-system-guide.md) - Role-based access control

---

## Questions & Answers

**Q: Why not just use Obsidian?**
A: Obsidian works great for technical designers. This system enables non-technical content creators to contribute without learning Git, YAML, or markdown formatting.

**Q: What if the LLM generates invalid data?**
A: All data is validated before writing to KB. Invalid GPS coordinates, missing files, duplicate IDs are caught and the user is asked to correct.

**Q: How do we handle media assets (images, audio)?**
A: Phase 1: Designer references existing files by name. Phase 2+: Upload via chat attachment.

**Q: Can designers edit existing waypoints?**
A: Phase 1: Create only. Phase 2: "Edit waypoint Secret Garden" opens conversational editor.

**Q: What about bulk operations?**
A: Phase 3: "Create 10 waypoints along this path" with CSV import or map-based bulk placement.

**Q: How is this different from Claude Code's MCP KB tools?**
A: MCP tools are for Claude Code (local development). This system is for game designers in production web UI. Different use case, different users.
