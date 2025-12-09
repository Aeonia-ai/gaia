# Role-Based Access Control (RBAC) System Guide

## Overview

The Gaia Platform implements a flexible, extensible RBAC system that starts with Knowledge Base (KB) permissions but scales to control access across the entire platform. **While the core RBAC logic is implemented in code, its full activation and deployment are conditional on specific environment configurations.** This guide covers the architecture, implementation, and usage of the RBAC system.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Implementation](#implementation)
5. [Usage Examples](#usage-examples)
6. [API Reference](#api-reference)
7. [Migration Guide](#migration-guide)
8. [Best Practices](#best-practices)

## Core Concepts

### Resources
Resources are the entities that can have permissions:
- **KB**: Knowledge Base documents and directories
- **API**: API endpoints and services
- **Chat**: Conversations and chat features
- **Asset**: Generated assets and media
- **Admin**: Administrative functions

### Actions
Standard actions that can be performed on resources:
- `read`: View/access the resource
- `write`: Modify the resource
- `delete`: Remove the resource
- `share`: Share with others
- `admin`: Full administrative control
- `create`: Create new resources
- `access`: Generic access permission

### Roles
Roles are collections of permissions that can be assigned to users:
- **System Roles**: Pre-defined platform roles (`admin`, `user`, etc.)
- **Custom Roles**: User-defined roles for specific needs
- **Team Roles**: Roles within team contexts
- **Workspace Roles**: Project-specific roles

### Contexts
Permissions can be scoped to different contexts:
- **Global**: Platform-wide permissions
- **Team**: Permissions within a team
- **Workspace**: Project-specific permissions
- **Resource**: Permissions on specific resources

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RBAC Manager                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Permission Checking Engine             │    │
│  │  - Direct user permissions                       │    │
│  │  - Role-based permissions                        │    │
│  │  - Team/workspace context                        │    │
│  │  - Resource-specific rules                       │    │
│  └─────────────────────────────────────────────────┘    │
│                          ↓                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Redis Cache Layer                   │    │
│  │  - Permission results (5min TTL)                 │    │
│  │  - User permission sets                          │    │
│  │  - Team/workspace memberships                    │    │
│  └─────────────────────────────────────────────────┘    │
│                          ↓                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │            PostgreSQL Database                   │    │
│  │  - Roles, permissions, assignments               │    │
│  │  - Teams, workspaces, memberships                │    │
│  │  - Audit logs                                    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables

```sql
-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    role_type VARCHAR(50), -- 'system', 'custom', 'team', 'workspace'
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY,
    resource_type VARCHAR(100), -- 'kb', 'api', 'chat', etc.
    resource_path VARCHAR(500), -- '/kb/users/*', '/api/v1/chat/*'
    action VARCHAR(50),         -- 'read', 'write', 'delete', etc.
    description TEXT
);

-- User-Role assignments
CREATE TABLE user_roles (
    user_id UUID,
    role_id UUID,
    context_type VARCHAR(50),  -- 'global', 'team', 'workspace'
    context_id VARCHAR(500),   -- team_id, workspace_id, etc.
    expires_at TIMESTAMP       -- For temporary access
);
```

### Default Roles

The system includes pre-defined roles:

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `super_admin` | Full system access | All permissions |
| `admin` | Administrative access | Most permissions except system |
| `developer` | Developer access | API, KB read/write, chat, assets |
| `user` | Standard user | Personal KB, shared read, basic API |
| `kb_admin` | KB Administrator | Full KB management |
| `kb_editor` | KB Editor | Create/edit KB content |
| `viewer` | Read-only access | Read permissions only |

## Implementation

### Python RBAC Manager

The core RBAC logic is implemented across several modules within `app/shared/`. Specifically, `app/shared/rbac_simple.py` is currently integrated with the KB storage for performance and simplicity. More comprehensive versions like `app/shared/rbac.py` and `app/shared/rbac_fixed.py` exist for broader platform use or future enhancements.

The activation of multi-user RBAC features, particularly for the Knowledge Base, is controlled by environment variables. For instance, setting `KB_MULTI_USER_ENABLED=true` will enable RBAC-aware storage and routing in the KB service.

```python
# Example conceptual usage (actual import may vary based on configuration)
from app.shared.rbac_simple import rbac_manager, ResourceType, Action # Or from app.shared.rbac

# Check permission
has_access = await rbac_manager.check_permission(
    user_id="user_123",
    resource_type=ResourceType.KB,
    resource_path="/kb/teams/engineering/docs",
    action=Action.WRITE
)

# Assign role
await rbac_manager.assign_role(
    user_id="user_123",
    role_name="kb_editor",
    assigned_by="admin_user",
    context_type=ContextType.TEAM,
    context_id="engineering"
)

# Get user permissions
permissions = await rbac_manager.get_user_permissions("user_123")
```

### FastAPI Integration

FastAPI endpoints can leverage the RBAC manager for automatic permission checking. The specific `rbac` module imported will depend on the active configuration.

```python
from app.shared.rbac_simple import require_permission, ResourceType, Action # Or from app.shared.rbac

# Automatic permission checking
@app.get("/kb/{path:path}")
async def read_kb(
    path: str,
    auth: dict = Depends(get_current_auth),
    _: None = Depends(require_permission(ResourceType.KB, Action.READ))
):
    # User has permission to read KB
    return await get_kb_content(path)

# Convenience decorators
@app.post("/kb/{path:path}")
async def write_kb(
    path: str,
    content: str,
    auth: dict = Depends(get_current_auth),
    _: None = Depends(require_kb_write)
):
    # User has write permission
    return await save_kb_content(path, content)
```

## Current Deployment Status

**The RBAC system is fully implemented in code but is not enabled by default in the current production environment.** Its activation, particularly for multi-user Knowledge Base features, is controlled by environment variables (e.g., `KB_MULTI_USER_ENABLED=true`). This aligns with the phased migration strategy outlined in the [KB Architecture Guide](../kb/developer/kb-architecture-guide.md), where multi-user features are progressively rolled out.

## Usage Examples

### 1. Creating Custom Roles

```python
# Create a machine learning researcher role
await create_custom_role(
    name="ml_researcher",
    display_name="Machine Learning Researcher",
    permissions=[
        {"resource_type": "kb", "resource_path": "/kb/ml/*", "action": "read"},
        {"resource_type": "kb", "resource_path": "/kb/ml/*", "action": "write"},
        {"resource_type": "api", "resource_path": "/api/v1/ml/*", "action": "access"},
        {"resource_type": "asset", "resource_path": "/assets/models/*", "action": "create"}
    ]
)
```

### 2. Team-Based Access

```python
# Add user to team
await rbac_manager.add_team_member(
    team_id="engineering",
    user_id="user_123",
    team_role="member",
    invited_by="team_lead"
)

# Team members automatically get access to team KB
# /kb/teams/engineering/* -> read, write (based on team role)
```

### 3. Temporary Access

```python
# Grant temporary access for incident response
await rbac_manager.assign_role(
    user_id="oncall_engineer",
    role_name="incident_responder",
    assigned_by="security_team",
    expires_at=datetime.now() + timedelta(hours=4)
)
```

### 4. Resource Sharing

```python
# Share a KB document
await rbac_manager.share_resource(
    resource_type=ResourceType.KB,
    resource_id="/kb/docs/architecture.md",
    shared_by="doc_owner",
    principal_type="team",
    principal_id="frontend_team",
    permissions=[Action.READ, Action.WRITE],
    expires_at=datetime.now() + timedelta(days=30)
)
```

## API Reference

### Permission Checking

```python
async def check_permission(
    user_id: str,
    resource_type: ResourceType,
    resource_path: str,
    action: Action,
    context: Optional[Dict[str, str]] = None
) -> bool
```

### Role Management

```python
async def assign_role(
    user_id: str,
    role_name: str,
    assigned_by: str,
    context_type: ContextType = ContextType.GLOBAL,
    context_id: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> bool

async def revoke_role(
    user_id: str,
    role_name: str,
    revoked_by: str,
    context_id: Optional[str] = None
) -> bool
```

### Team/Workspace Management

```python
async def add_team_member(
    team_id: str,
    user_id: str,
    team_role: TeamRole,
    invited_by: str
) -> bool

async def add_workspace_member(
    workspace_id: str,
    user_id: str,
    invited_by: str
) -> bool
```

## Migration Guide

### Adding RBAC to Existing System

1. **Apply Database Migration**
   ```bash
   docker compose exec db psql -U postgres -d llm_platform < migrations/004_create_rbac_tables.sql
   ```

2. **Assign Initial Roles**
   ```python
   # Script to assign roles to existing users
   async def migrate_users_to_rbac():
       users = await get_all_users()
       for user in users:
           if user.is_admin:
               await rbac_manager.assign_role(user.id, "admin", "system")
           else:
               await rbac_manager.assign_role(user.id, "user", "system")
   ```

3. **Update API Endpoints**
   ```python
   # Before
   @app.get("/api/endpoint")
   async def endpoint(auth: dict = Depends(get_current_auth)):
       if not auth.get("is_admin"):
           raise HTTPException(403)
   
   # After
   @app.get("/api/endpoint")
   async def endpoint(
       auth: dict = Depends(get_current_auth),
       _: None = Depends(require_permission(ResourceType.API, Action.ACCESS))
   ):
       # Permission already checked
   ```

## Best Practices

### 1. Role Design
- Start with minimal permissions and add as needed
- Use descriptive role names: `financial_report_viewer` not `frv`
- Document what each custom role is for
- Regular audit of role assignments

### 2. Permission Patterns
- Use wildcards carefully: `/kb/public/*` vs `/kb/*`
- Prefer role-based over direct user permissions
- Set expiration for temporary access
- Use context-specific roles when possible

### 3. Performance
- Redis caching reduces database queries
- Batch permission checks when possible
- Use `get_accessible_paths()` for efficient filtering
- Monitor cache hit rates

### 4. Security
- Audit all permission changes
- Regular review of super_admin assignments
- Use principle of least privilege
- Enable MFA for high-privilege roles

### 5. Multi-User KB
- Users own `/kb/users/{user_id}/*` by default
- Teams use `/kb/teams/{team_id}/*`
- Workspaces use `/kb/workspaces/{workspace_id}/*`
- Shared content in `/kb/shared/*`

## Advanced Features

### Dynamic Roles

```python
# Context-aware permissions
if user.is_on_call:
    grant_temporary_role("incident_responder")

# Attribute-based access
if user.department == "finance" and user.seniority >= 5:
    grant_role("budget_approver")
```

### Role Inheritance

```python
# Create role hierarchy
junior_dev -> developer -> senior_dev -> tech_lead
# Each inherits permissions from previous
```

### Policy-Based Permissions

```python
role_policy = {
    "effect": "allow",
    "actions": ["read", "write"],
    "resources": ["kb:/kb/data/*"],
    "conditions": {
        "ip_range": "10.0.0.0/8",
        "time_range": "business_hours",
        "mfa_required": True
    }
}
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Check user has required role
   - Verify role has permission
   - Check for context mismatches
   - Look for expired assignments

2. **Cache Inconsistency**
   - Clear Redis cache: `redis-cli FLUSHDB`
   - Check cache TTL settings
   - Verify cache invalidation

3. **Performance Issues**
   - Monitor permission check times
   - Increase cache TTL if appropriate
   - Add database indexes if needed

### Debug Commands

```bash
# Check user permissions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8666/api/v1/auth/permissions

# View user roles
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8666/api/v1/auth/roles

# Test specific permission
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -d '{"resource": "/kb/test", "action": "read"}' \
  http://localhost:8666/api/v1/auth/check-permission
```

## Future Enhancements

1. **GUI Role Management**: Web interface for role/permission management
2. **Permission Templates**: Pre-built permission sets for common use cases
3. **Delegation**: Allow users to delegate their permissions temporarily
4. **Approval Workflows**: Require approval for sensitive permission grants
5. **Integration**: SAML/OIDC group mapping to roles

The RBAC system provides fine-grained access control that scales from simple KB permissions to complex platform-wide authorization rules, all while maintaining performance through intelligent caching and efficient database queries.