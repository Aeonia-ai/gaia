# RBAC Role Examples for Gaia Platform



This document showcases the flexibility of role definitions in our RBAC system.

## Core Concept: Infinitely Flexible Roles

The RBAC system allows you to define **any role** with **any combination of permissions**. Here are examples of creative role definitions for different use cases.

## 1. Industry-Specific Roles

### Healthcare/Medical
```python
roles = [
    {
        "name": "clinical_researcher",
        "permissions": [
            "kb:/kb/clinical/studies/* -> read, write",
            "kb:/kb/patient/anonymized/* -> read",
            "api:/api/v1/analysis/medical/* -> access",
            "asset:/assets/medical/images/* -> read"
        ]
    },
    {
        "name": "compliance_officer",
        "permissions": [
            "kb:/kb/compliance/* -> admin",
            "admin:audit_logs -> read",
            "kb:/kb/*/audit/* -> read"
        ]
    }
]
```

### Finance/Trading
```python
roles = [
    {
        "name": "quant_analyst",
        "permissions": [
            "kb:/kb/strategies/quantitative/* -> read, write",
            "api:/api/v1/backtest/* -> access",
            "asset:/assets/market_data/* -> read",
            "chat:trading_models -> create"
        ]
    },
    {
        "name": "risk_manager",
        "permissions": [
            "kb:/kb/risk/* -> admin",
            "api:/api/v1/risk/reports/* -> access",
            "kb:/kb/trades/* -> read"  # Read-only access to trades
        ]
    }
]
```

### Gaming/Entertainment
```python
roles = [
    {
        "name": "game_designer",
        "permissions": [
            "kb:/kb/game/design/* -> write",
            "kb:/kb/game/narrative/* -> write",
            "asset:/assets/concepts/* -> create",
            "chat:creative_ai -> access"
        ]
    },
    {
        "name": "community_manager",
        "permissions": [
            "kb:/kb/community/* -> admin",
            "api:/api/v1/social/* -> access",
            "chat:community_support -> create"
        ]
    }
]
```

## 2. Time-Based/Temporary Roles

```python
# Contractor with expiring access
await rbac_manager.assign_role(
    user_id="contractor_123",
    role_name="temp_developer",
    expires_at=datetime.now() + timedelta(days=90),
    permissions=[
        "kb:/kb/projects/current/* -> read, write",
        "api:/api/v1/dev/* -> access"
    ]
)

# Incident responder with emergency access
await rbac_manager.assign_role(
    user_id="oncall_engineer",
    role_name="incident_responder",
    expires_at=datetime.now() + timedelta(hours=4),
    permissions=[
        "kb:/kb/* -> read",  # Read everything during incident
        "admin:system_logs -> read",
        "api:/api/v1/debug/* -> access"
    ]
)
```

## 3. Hierarchical/Inherited Roles

```python
# Base role
base_employee = {
    "name": "employee",
    "permissions": [
        "kb:/kb/shared/policies/* -> read",
        "kb:/kb/shared/handbook/* -> read",
        "api:/api/v1/profile/* -> access"
    ]
}

# Inherited role with additional permissions
senior_employee = {
    "name": "senior_employee",
    "inherits_from": ["employee"],
    "additional_permissions": [
        "kb:/kb/mentorship/* -> write",
        "kb:/kb/junior/reviews/* -> write"
    ]
}

# Department head with team permissions
dept_head = {
    "name": "department_head",
    "inherits_from": ["senior_employee"],
    "additional_permissions": [
        "kb:/kb/teams/{team_id}/* -> admin",
        "admin:team_management -> access",
        "kb:/kb/budgets/{team_id}/* -> write"
    ]
}
```

## 4. Feature-Based Roles

```python
# AI/ML Features
roles["ai_beta_tester"] = {
    "permissions": [
        "api:/api/v1/ai/beta/* -> access",
        "kb:/kb/ai/feedback/* -> write",
        "chat:experimental_models -> access"
    ]
}

# Advanced Analytics
roles["analytics_power_user"] = {
    "permissions": [
        "api:/api/v1/analytics/advanced/* -> access",
        "kb:/kb/analytics/custom_queries/* -> write",
        "asset:/assets/dashboards/* -> create"
    ]
}
```

## 5. Cross-Functional Roles

```python
# Product Manager - crosses engineering, design, and business
roles["product_manager"] = {
    "permissions": [
        # Engineering visibility
        "kb:/kb/engineering/roadmap/* -> read",
        "kb:/kb/engineering/specs/* -> write",
        
        # Design collaboration
        "kb:/kb/design/mockups/* -> read, write",
        "asset:/assets/prototypes/* -> create",
        
        # Business metrics
        "kb:/kb/business/metrics/* -> read",
        "api:/api/v1/analytics/product/* -> access",
        
        # Customer insights
        "kb:/kb/customer/feedback/* -> read",
        "kb:/kb/customer/interviews/* -> write"
    ]
}
```

## 6. Dynamic Context-Based Roles

```python
# Role that changes based on context
class ContextualRole:
    @staticmethod
    async def get_permissions(user_id: str, context: dict):
        """Generate permissions based on current context"""
        
        if context.get("is_on_call"):
            return [
                "admin:production_systems -> access",
                "kb:/kb/runbooks/* -> read",
                "api:/api/v1/emergency/* -> access"
            ]
        
        elif context.get("active_project"):
            project_id = context["active_project"]
            return [
                f"kb:/kb/projects/{project_id}/* -> write",
                f"workspace:{project_id} -> full_access"
            ]
        
        # Default permissions
        return ["kb:/kb/users/{user_id}/* -> admin"]
```

## 7. Composite Roles (Multiple Contexts)

```python
# User can have multiple roles in different contexts
user_role_assignments = [
    {
        "role": "developer",
        "context": "global"  # Platform-wide developer access
    },
    {
        "role": "team_lead",
        "context": "team:engineering"  # Lead of engineering team
    },
    {
        "role": "contributor",
        "context": "workspace:opensource_project"  # Contributor to specific project
    },
    {
        "role": "reviewer",
        "context": "kb:/kb/docs/api"  # Reviewer for API docs only
    }
]
```

## 8. AI Agent Roles

Since Gaia works with AI agents, you can create specific roles for them:

```python
roles["ai_researcher"] = {
    "permissions": [
        "kb:/kb/* -> read",  # Read all KB for context
        "kb:/kb/research/findings/* -> write",  # Write research results
        "api:/api/v1/llm/* -> access",  # Access LLM APIs
        "chat:research_threads -> create"  # Create research conversations
    ],
    "constraints": {
        "rate_limit": "100_requests_per_hour",
        "max_tokens_per_request": 4000
    }
}

roles["ai_code_reviewer"] = {
    "permissions": [
        "kb:/kb/code/* -> read",
        "kb:/kb/code/reviews/* -> write",
        "api:/api/v1/code_analysis/* -> access"
    ]
}
```

## Implementation Example

Here's how to create and assign these custom roles:

```python
from app.shared.rbac import rbac_manager, ResourceType, Action

# Create a custom role
async def create_custom_role(name: str, permissions: List[dict]):
    """Create a custom role with specific permissions"""
    
    async with get_db_session() as session:
        # Insert role
        role_result = await session.execute(
            text("""
                INSERT INTO roles (name, display_name, description, role_type)
                VALUES (:name, :display_name, :description, 'custom')
                RETURNING id
            """),
            {
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "description": f"Custom role: {name}"
            }
        )
        role_id = role_result.scalar()
        
        # Create and assign permissions
        for perm in permissions:
            # Parse permission string or dict
            # Insert into permissions table
            # Link to role via role_permissions
            pass
        
        await session.commit()
        
    return role_id

# Assign custom role to user
await rbac_manager.assign_role(
    user_id="user_123",
    role_name="ml_researcher",
    assigned_by="admin_user",
    context_type="workspace",
    context_id="ml_project_alpha"
)
```

## Best Practices for Custom Roles

1. **Naming Convention**
   - Use lowercase with underscores: `role_name_here`
   - Be descriptive: `financial_report_viewer` not `frv`
   - Include context if needed: `team_lead_engineering`

2. **Permission Granularity**
   - Start restrictive, add permissions as needed
   - Use wildcards carefully: `/kb/sensitive/*` vs `/kb/sensitive/public/*`
   - Consider read/write/admin separation

3. **Role Composition**
   - Build complex roles from simpler ones
   - Use inheritance where it makes sense
   - Document role relationships

4. **Temporal Considerations**
   - Set expiration for temporary access
   - Regular audit of role assignments
   - Automated cleanup of expired roles

5. **Context Awareness**
   - Roles can be global, team-specific, or resource-specific
   - Same user can have different roles in different contexts
   - Context helps prevent permission sprawl

## Advanced Patterns

### 1. Capability-Based Roles
Instead of resource-based permissions, define what users can do:

```python
roles["content_creator"] = {
    "capabilities": [
        "create_documents",
        "upload_images", 
        "publish_content",
        "moderate_comments"
    ]
}
```

### 2. Attribute-Based Roles
Roles that depend on user attributes:

```python
async def get_attribute_based_permissions(user):
    if user.department == "engineering" and user.seniority > 5:
        return ["kb:/kb/architecture/* -> write"]
    elif user.clearance_level >= "secret":
        return ["kb:/kb/classified/* -> read"]
```

### 3. Policy-Based Roles
Define roles using policy languages:

```python
role_policy = {
    "name": "data_scientist",
    "policy": {
        "effect": "allow",
        "actions": ["read", "write", "execute"],
        "resources": ["kb:/kb/data/*", "api:/api/v1/ml/*"],
        "conditions": {
            "ip_range": "10.0.0.0/8",
            "time_range": "business_hours",
            "mfa_required": True
        }
    }
}
```

## Conclusion

The RBAC system's flexibility means you can:
- Define any role for any use case
- Combine permissions in unlimited ways
- Apply roles in different contexts
- Create temporal, hierarchical, or dynamic roles
- Build complex authorization logic while keeping it manageable

The only limit is your imagination and your security requirements!