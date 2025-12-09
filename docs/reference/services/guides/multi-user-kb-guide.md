# Multi-User Knowledge Base Guide



## Overview

The Gaia Platform's Knowledge Base (KB) system supports multi-user collaboration through user namespaces, teams, workspaces, and granular sharing controls. This guide covers the architecture, features, and implementation of the multi-user KB system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [User Namespaces](#user-namespaces)
3. [Teams vs Workspaces](#teams-vs-workspaces)
4. [Sharing Mechanisms](#sharing-mechanisms)
5. [Permission Model](#permission-model)
6. [Implementation Guide](#implementation-guide)
7. [API Reference](#api-reference)
8. [Best Practices](#best-practices)

## Architecture Overview

### Directory Structure

```
/kb/
├── users/                  # Personal user spaces
│   └── {user_id}/         # Individual user KB
│       ├── private/       # Never shared (default)
│       ├── workspace/     # Working documents
│       └── published/     # User's published content
│
├── teams/                  # Team collaboration spaces
│   └── {team_id}/
│       ├── standards/     # Team standards and guidelines
│       ├── onboarding/    # New member resources
│       ├── projects/      # Team projects
│       └── archive/       # Archived content
│
├── workspaces/            # Project-specific collaboration
│   └── {workspace_id}/
│       ├── members.json   # Workspace configuration
│       ├── planning/      # Project planning docs
│       ├── design/        # Design documents
│       └── deliverables/  # Project outputs
│
└── shared/                # Organization-wide content
    ├── templates/         # Reusable templates
    ├── policies/          # Company policies
    └── knowledge/         # Common knowledge base
```

### Storage Architecture

The KB system supports three storage modes:

1. **Git Mode**: File-based with version control
2. **Database Mode**: PostgreSQL for fast queries and collaboration
3. **Hybrid Mode** (Recommended): Database primary + Git backup

## User Namespaces

### Personal KB Space

Each user has a dedicated namespace at `/kb/users/{user_id}/`:

```python
# User always has full access to their space
/kb/users/alice/
├── private/          # Only Alice can access
├── workspace/        # Alice's working documents
└── published/        # Alice's shared content
```

### Default Permissions

- **Own Space**: Full read/write/delete access
- **Other Users**: No access unless explicitly shared
- **Shared Space**: Read-only access to `/kb/shared/*`

### Usage Example

```python
# Save to personal KB
await kb_storage.save_document(
    path="/kb/users/alice/notes/meeting-2024.md",
    content="# Meeting Notes\n\n...",
    user_id="alice"
)

# Search personal KB
results = await kb_storage.search_documents(
    query="project requirements",
    user_id="alice",
    contexts=["/kb/users/alice"]  # Search only personal space
)
```

## Teams vs Workspaces

### Teams - Organizational Units

Teams represent **permanent organizational structures** with stable membership:

#### Characteristics
- **Long-lived**: Exist as long as the organization unit exists
- **Hierarchical**: Can have sub-teams
- **Role-based**: Members have roles (owner, admin, member, viewer)
- **Knowledge Ownership**: Team collectively owns their KB

#### Example Structure
```
/kb/teams/engineering/
├── standards/
│   ├── code-review.md
│   ├── testing-guide.md
│   └── architecture-decisions/
├── onboarding/
│   ├── setup-guide.md
│   └── team-contacts.md
└── knowledge-base/
    ├── troubleshooting/
    └── best-practices/
```

#### Creating a Team
```python
result = await kb_storage.create_team(
    name="engineering",
    display_name="Engineering Team",
    description="Core engineering team",
    created_by="team_lead_id"
)
```

### Workspaces - Project Collaboration

Workspaces are **temporary collaboration spaces** for specific projects:

#### Characteristics
- **Time-bound**: Created for specific projects
- **Cross-functional**: Members from multiple teams
- **Flat permissions**: Usually equal access for all members
- **Goal-oriented**: Exists to achieve specific objectives

#### Example Structure
```
/kb/workspaces/q4-launch/
├── members.json
├── charter.md
├── planning/
│   ├── timeline.md
│   └── milestones.md
├── design/
├── engineering/
└── marketing/
```

#### Creating a Workspace
```python
result = await kb_storage.create_workspace(
    name="q4-launch",
    display_name="Q4 Product Launch",
    description="Cross-functional team for Q4 launch",
    created_by="project_manager_id",
    initial_members=["alice", "bob", "charlie"],
    workspace_type="project"
)
```

### Key Differences

| Aspect | Teams | Workspaces |
|--------|-------|------------|
| **Lifespan** | Permanent | Temporary |
| **Membership** | Stable, role-based | Dynamic, equal access |
| **Purpose** | Organizational knowledge | Project deliverables |
| **Structure** | Hierarchical | Flat |
| **Examples** | Engineering Team | Q4 Launch Project |

## Sharing Mechanisms

### Three-Tier Sharing Model

1. **Private (Default)**
   - Location: `/kb/users/{user_id}/private/`
   - Access: Owner only
   - Cannot be shared

2. **Selective Sharing**
   - Share with specific users, teams, or workspaces
   - Granular permissions (read, write, delete)
   - Time-limited sharing with expiration

3. **Published/Public**
   - Location: `/kb/shared/published/`
   - Access: All authenticated users
   - Read-only by default

### Sharing API

```python
# Share a document
result = await kb_storage.share_document(
    path="/kb/users/alice/docs/guide.md",
    shared_by="alice",
    recipients=["bob", "charlie"],      # Individual users
    teams=["engineering"],              # Teams
    workspaces=["q4-launch"],          # Workspaces
    permissions=["read", "write"],      # Permissions to grant
    expires_at="2024-12-31",           # Optional expiration
    message="Please review and provide feedback"
)

# Share with a team
await rbac_manager.share_resource(
    resource_type=ResourceType.KB,
    resource_id="/kb/users/alice/research/ml-paper.md",
    shared_by="alice",
    principal_type="team",
    principal_id="data-science",
    permissions=[Action.READ],
    expires_at=None  # Permanent share
)
```

### Cross-User Linking

Support for wiki-style links across user boundaries:

```markdown
# In a document
See [[user:bob/guides/setup]] for setup instructions.
The [[team:engineering/standards/code-review]] process applies.
Details in [[workspace:q4-launch/planning/timeline]].
Use the [[shared:templates/rfc]] template.
```

## Permission Model

### Permission Hierarchy

1. **Owner**: Full control (read, write, delete, share)
2. **Admin**: Can manage permissions and content
3. **Editor**: Can read and modify content
4. **Commenter**: Can read and add comments
5. **Viewer**: Read-only access

### Permission Checking

```python
# Check KB access
has_access = await rbac_manager.check_kb_access(
    user_id="alice",
    kb_path="/kb/teams/engineering/docs",
    action=Action.WRITE
)

# Get accessible paths
paths = await rbac_manager.get_accessible_kb_paths("alice")
# Returns: [
#   "/kb/users/alice",
#   "/kb/teams/engineering",
#   "/kb/workspaces/q4-launch",
#   "/kb/shared"
# ]
```

### Search with Permissions

```python
# Search respects access control
results = await kb_storage.search_documents(
    query="architecture patterns",
    user_id="alice",
    include_shared=True,    # Include shared content
    include_public=True     # Include public content
)
# Only returns documents Alice can read
```

## Implementation Guide

### 1. Enable Multi-User Mode

```bash
# In .env
KB_MULTI_USER_ENABLED=true
KB_USER_ISOLATION=strict
KB_DEFAULT_VISIBILITY=private
KB_SHARING_ENABLED=true
```

### 2. Apply Database Migrations

```bash
# RBAC tables
docker compose exec db psql -U postgres -d llm_platform < migrations/004_create_rbac_tables.sql

# KB tables (if using database/hybrid mode)
docker compose exec db psql -U postgres -d llm_platform < migrations/003_create_kb_tables.sql
```

### 3. Initialize User Spaces

```python
# One-time setup for existing users
async def setup_user_spaces():
    users = await get_all_users()
    for user in users:
        # Create user directory
        user_path = f"/kb/users/{user.id}"
        await kb_storage.create_directory(user_path)
        
        # Set default permissions
        await rbac_manager.assign_role(
            user.id, 
            "kb_user",
            "system",
            context_type=ContextType.RESOURCE,
            context_id=user_path
        )
```

### 4. Integrate with FastAPI

```python
from app.services.kb.kb_storage_with_rbac import router as kb_router

# Add KB routes with RBAC
app.include_router(kb_router, prefix="/api/v1")

# Example endpoint with automatic permission checking
@app.get("/api/v1/kb/{path:path}")
async def read_kb_document(
    path: str,
    auth: dict = Depends(get_current_auth),
    _: None = Depends(require_kb_read)
):
    user_id = auth["user_id"]
    doc = await kb_storage.get_document(path, user_id=user_id)
    if not doc:
        raise HTTPException(404, "Document not found or access denied")
    return doc
```

## API Reference

### Document Operations

```python
# Search with user context
POST /api/v1/kb/search
{
    "query": "machine learning",
    "contexts": ["/kb/teams/data-science"],
    "include_shared": true,
    "limit": 20
}

# Get document (with permission check)
GET /api/v1/kb/document/{path}

# Save document (requires write permission)
POST /api/v1/kb/document
{
    "path": "/kb/users/me/notes/idea.md",
    "content": "# My Idea\n\n..."
}

# Delete document (requires delete permission)
DELETE /api/v1/kb/document/{path}
```

### Sharing Operations

```python
# Share document
POST /api/v1/kb/share
{
    "path": "/kb/users/me/docs/guide.md",
    "recipients": ["user1", "user2"],
    "teams": ["engineering"],
    "permissions": ["read", "write"],
    "expires_at": "2024-12-31"
}

# Create workspace
POST /api/v1/kb/workspace
{
    "name": "new-feature",
    "display_name": "New Feature Development",
    "description": "Workspace for feature X",
    "initial_members": ["alice", "bob"]
}

# Create team
POST /api/v1/kb/team
{
    "name": "frontend",
    "display_name": "Frontend Team",
    "description": "Frontend development team"
}
```

## Best Practices

### 1. Namespace Organization

- **Personal**: Keep truly private content in `/private/`
- **Collaboration**: Use workspaces for temporary projects
- **Team Knowledge**: Document team processes and standards
- **Publishing**: Move mature content to `/shared/`

### 2. Permission Management

- Start with minimal permissions
- Use role-based assignments over direct permissions
- Set expiration for temporary access
- Regular audit of sharing

### 3. Search Optimization

- Use specific contexts to narrow search scope
- Default to user's namespace for performance
- Cache frequently accessed shared content

### 4. Collaboration Patterns

```python
# Team documentation workflow
1. Draft in personal space: /kb/users/alice/drafts/
2. Share with team for review
3. Move to team space when approved: /kb/teams/engineering/
4. Publish to shared when mature: /kb/shared/

# Project workflow
1. Create workspace for project
2. All members contribute to workspace
3. Archive valuable content to team spaces
4. Delete workspace when project completes
```

### 5. Security Considerations

- Validate all paths to prevent directory traversal
- Audit all sharing actions
- Implement quotas to prevent abuse
- Regular cleanup of expired permissions

## Migration from Single-User

### Phase 1: Enable Multi-User
```python
# Update configuration
KB_MULTI_USER_ENABLED=true

# Existing content moves to admin user
/kb/* -> /kb/users/admin/migrated/
```

### Phase 2: Create Structure
```python
# Set up organizational structure
await create_team("engineering", "Engineering Team")
await create_team("product", "Product Team")
await create_workspace("migration", "KB Migration Project")
```

### Phase 3: Redistribute Content
```python
# Move content to appropriate locations
/kb/users/admin/migrated/engineering/* -> /kb/teams/engineering/
/kb/users/admin/migrated/policies/* -> /kb/shared/policies/
```

## Advanced Features

### Real-Time Collaboration

```python
# Track active editors
async def track_active_editor(doc_path: str, user_id: str):
    await redis_client.setex(
        f"kb:editing:{doc_path}:{user_id}",
        30,  # 30 second heartbeat
        json.dumps({"user": user_id, "timestamp": datetime.now()})
    )

# Get active editors
async def get_active_editors(doc_path: str):
    pattern = f"kb:editing:{doc_path}:*"
    keys = await redis_client.keys(pattern)
    return [await redis_client.get(key) for key in keys]
```

### Conflict Resolution

```python
# Optimistic locking for concurrent edits
async def save_with_conflict_detection(
    path: str,
    content: str,
    user_id: str,
    expected_version: int
):
    current_version = await get_document_version(path)
    if current_version != expected_version:
        return {
            "success": False,
            "error": "version_conflict",
            "current_version": current_version
        }
    
    return await save_document(path, content, user_id)
```

### Analytics and Insights

```python
# Track popular content
async def track_document_access(path: str, user_id: str):
    await increment_access_count(path)
    await log_access_event(path, user_id)

# Get team insights
async def get_team_kb_stats(team_id: str):
    return {
        "total_documents": await count_team_documents(team_id),
        "active_contributors": await get_active_contributors(team_id),
        "popular_documents": await get_popular_documents(team_id),
        "recent_activity": await get_recent_activity(team_id)
    }
```

## Troubleshooting

### Common Issues

1. **"Access Denied" Errors**
   - Verify user has appropriate role/permissions
   - Check path is correctly formatted
   - Ensure user is member of team/workspace

2. **Search Not Finding Documents**
   - Check user has read access to documents
   - Verify search contexts are accessible
   - Ensure indexing is up to date

3. **Sharing Not Working**
   - Confirm user has share permission on source
   - Verify recipient IDs are valid
   - Check for permission conflicts

### Debug Tools

```bash
# Check user's accessible paths
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8666/api/v1/kb/accessible-paths

# View user's teams and workspaces
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8666/api/v1/kb/memberships

# Test specific permission
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -d '{"path": "/kb/teams/engineering/docs"}' \
  http://localhost:8666/api/v1/kb/check-access
```

## Future Enhancements

1. **Real-time Collaborative Editing**: Multiple users editing simultaneously
2. **Version Control Integration**: Git-like branching and merging
3. **AI-Powered Organization**: Automatic content categorization
4. **Advanced Analytics**: Usage patterns and content insights
5. **Mobile Optimization**: Native mobile KB experience

The multi-user KB system provides a flexible, secure foundation for collaborative knowledge management that scales from individual users to large organizations.