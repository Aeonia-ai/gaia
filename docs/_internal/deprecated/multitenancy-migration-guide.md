# Multi-Tenancy Migration Guide

## Overview
This guide outlines how to migrate from cluster-per-game to a multi-tenant architecture when business needs require it (cost optimization, unified management, shared resources).

## When to Consider Multi-Tenancy

### Business Triggers
- **Cost Pressure**: Running 50+ small games becomes expensive
- **Operational Overhead**: Managing dozens of clusters is complex
- **Resource Efficiency**: Many games have low usage but need availability
- **Feature Sharing**: Games want to share players, assets, or economies

### Technical Indicators
- Average game has < 100 concurrent players
- Similar game mechanics across multiple titles
- Shared player base across games
- Need for cross-game features

## Migration Strategy

### Phase 1: Database Multi-Tenancy (Month 1)

#### 1.1 Add Tenant Column
```sql
-- Add tenant_id to all tables
ALTER TABLE users ADD COLUMN tenant_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE conversations ADD COLUMN tenant_id UUID NOT NULL;
ALTER TABLE chat_messages ADD COLUMN tenant_id UUID NOT NULL;
ALTER TABLE personas ADD COLUMN tenant_id UUID NOT NULL;

-- Create tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    game_id VARCHAR(100) UNIQUE NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_conversations_tenant_id ON conversations(tenant_id);
-- ... for all tables
```

#### 1.2 Update Models
```python
# app/models/database.py
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    game_id = Column(String(100), unique=True, nullable=False)
    config = Column(JSONB, default={})
    created_at = Column(DateTime, default=func.current_timestamp())

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    # ... existing fields
```

### Phase 2: Authentication Enhancement (Month 1-2)

#### 2.1 Tenant-Aware Authentication
```python
# app/shared/security.py
class AuthenticationResult:
    def __init__(self, auth_type: str, user_id: Optional[str] = None, 
                 tenant_id: Optional[str] = None, **kwargs):
        self.auth_type = auth_type
        self.user_id = user_id
        self.tenant_id = tenant_id  # NEW
        # ... existing fields

async def get_current_auth_with_tenant(
    request: Request,
    auth: AuthenticationResult = Depends(get_current_auth)
) -> Dict[str, Any]:
    """Extract tenant from subdomain or header"""
    
    # Option 1: Subdomain-based (zombie.gaia.com)
    host = request.headers.get("host", "")
    if "." in host:
        tenant_subdomain = host.split(".")[0]
        tenant = await get_tenant_by_subdomain(tenant_subdomain)
    
    # Option 2: Header-based
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        tenant = await get_tenant_by_id(tenant_id)
    
    # Option 3: Path-based (/api/v1/tenants/{tenant_id}/chat)
    # ... 
    
    auth.tenant_id = tenant.id if tenant else None
    return auth
```

### Phase 3: Redis Key Namespacing (Month 2)

#### 3.1 Update Cache Keys
```python
# app/shared/redis_client.py
class CacheManager:
    @staticmethod
    def cache_key(tenant_id: str, *parts: str) -> str:
        """Generate tenant-scoped cache key"""
        return f"tenant:{tenant_id}:" + ":".join(str(part) for part in parts)
    
    @staticmethod
    def chat_history_key(tenant_id: str, user_id: str) -> str:
        return CacheManager.cache_key(tenant_id, "chat", "history", user_id)
```

### Phase 4: Service Isolation (Month 2-3)

#### 4.1 Query Filtering
```python
# app/services/chat/db_operations.py
async def get_user_conversations(user_id: str, tenant_id: str, db: Session):
    """Get conversations filtered by tenant"""
    return db.query(Conversation).filter(
        Conversation.user_id == user_id,
        Conversation.tenant_id == tenant_id  # NEW
    ).order_by(Conversation.created_at.desc()).all()
```

#### 4.2 Middleware for Tenant Context
```python
# app/middleware/tenant.py
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Set tenant context for the request
        tenant_id = extract_tenant_from_request(request)
        request.state.tenant_id = tenant_id
        
        # Add tenant filter to all DB queries
        with tenant_context(tenant_id):
            response = await call_next(request)
        
        return response
```

### Phase 5: MCP Tool Isolation (Month 3)

#### 5.1 Tenant-Specific MCP Configuration
```python
# app/services/chat/mcp_config.py
class TenantMCPConfig:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.config = self.load_tenant_config()
    
    def get_allowed_tools(self) -> List[str]:
        """Get MCP tools allowed for this tenant"""
        return self.config.get("mcp_tools", [])
    
    def get_personas(self) -> List[Dict]:
        """Get AI personas for this tenant"""
        return self.config.get("personas", [])
```

#### 5.2 Dynamic Tool Loading
```python
# app/services/chat/lightweight_chat.py
async def create_chat_agent(tenant_id: str, user_context: Dict):
    tenant_config = TenantMCPConfig(tenant_id)
    
    # Load only tenant-specific tools
    server_names = tenant_config.get_allowed_tools()
    
    # Use tenant-specific personas
    instruction = tenant_config.get_instruction()
    
    agent = Agent(
        name=f"gaia_chat_{tenant_id}",
        instruction=instruction,
        server_names=server_names
    )
    return agent
```

### Phase 6: Gradual Migration (Month 3-4)

#### 6.1 Hybrid Deployment
```yaml
# Run both architectures side-by-side
services:
  # Multi-tenant cluster
  gateway-mt:
    image: gaia-gateway:multitenant
    environment:
      MULTITENANCY_ENABLED: "true"
  
  # Legacy single-tenant (gradually sunset)
  gateway-zombie:
    image: gaia-gateway:v1
    environment:
      GAME_ID: "zombie-survival"
```

#### 6.2 Migration Script
```python
# scripts/migrate_to_multitenant.py
async def migrate_game_to_tenant(game_id: str, target_cluster: str):
    """Migrate a single game to multi-tenant cluster"""
    
    # 1. Create tenant record
    tenant = create_tenant(game_id)
    
    # 2. Export data from single-tenant DB
    data = export_game_data(game_id)
    
    # 3. Import with tenant_id
    import_to_multitenant(data, tenant.id)
    
    # 4. Update DNS/routing
    update_routing(game_id, target_cluster)
    
    # 5. Verify and switch traffic
    if verify_migration(game_id, tenant.id):
        switch_traffic(game_id, target_cluster)
```

## Architecture Patterns

### 1. Subdomain Routing
```nginx
# nginx.conf
server {
    server_name ~^(?<tenant>.+)\.gaia\.com$;
    
    location / {
        proxy_set_header X-Tenant-ID $tenant;
        proxy_pass http://gateway;
    }
}
```

### 2. Schema Isolation (PostgreSQL)
```sql
-- Create schema per tenant for stronger isolation
CREATE SCHEMA tenant_zombie;
CREATE SCHEMA tenant_fantasy;

-- Update search_path based on tenant
SET search_path TO tenant_zombie, public;
```

### 3. Resource Quotas
```python
# app/middleware/quotas.py
class TenantQuotaMiddleware:
    async def check_quota(self, tenant_id: str, resource: str):
        quota = await get_tenant_quota(tenant_id, resource)
        usage = await get_tenant_usage(tenant_id, resource)
        
        if usage >= quota:
            raise HTTPException(429, "Tenant quota exceeded")
```

## Rollback Strategy

### Maintaining Reversibility
1. **Keep cluster-per-game code**: Use feature flags
2. **Dual-write period**: Write to both systems
3. **Traffic splitting**: Gradually move games
4. **Quick rollback**: DNS switch back to dedicated cluster

### Feature Flags
```python
# app/shared/config.py
class Settings(BaseSettings):
    MULTITENANCY_ENABLED: bool = False
    TENANT_ISOLATION_LEVEL: str = "basic"  # basic, schema, database
    
    def get_db_filter(self, tenant_id: Optional[str]):
        if not self.MULTITENANCY_ENABLED:
            return {}
        return {"tenant_id": tenant_id}
```

## Cost-Benefit Analysis

### When Multi-Tenancy Saves Money
```
Break-even point = (Shared Cluster Cost) / (Per-Game Cluster Cost)

Example:
- Shared cluster: $5000/month (large, handles 100 games)
- Per-game cluster: $100/month
- Break-even: 50 games

If you have > 50 small games, multi-tenancy saves money
```

### Hidden Costs
1. **Development Complexity**: 3-6 months to implement
2. **Operational Risk**: One bug affects all games
3. **Performance Overhead**: ~10-20% from tenant filtering
4. **Limited Customization**: Harder to have game-specific features

## Recommended Path

### Start Simple
1. **0-10 games**: Keep cluster-per-game
2. **10-50 games**: Evaluate based on game sizes
3. **50+ games**: Consider multi-tenancy for small games
4. **Hybrid approach**: Big games get dedicated clusters, small games share

### Gradual Adoption
1. Start with database multi-tenancy only
2. Add Redis namespacing when needed
3. Implement full isolation if required
4. Keep ability to extract games back to dedicated clusters

## Conclusion

Multi-tenancy is a reversible optimization. Start with cluster-per-game for simplicity, migrate to multi-tenancy when economics demand it, but maintain the ability to give successful games their own clusters again.