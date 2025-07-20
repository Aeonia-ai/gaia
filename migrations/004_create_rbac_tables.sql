-- RBAC (Role-Based Access Control) Tables for Gaia Platform
-- Supports both KB-specific and platform-wide permissions

BEGIN;

-- ========================================================================
-- CORE RBAC TABLES
-- ========================================================================

-- Roles table (platform-wide roles)
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    role_type VARCHAR(50) NOT NULL CHECK (role_type IN ('system', 'custom', 'team', 'workspace')),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table (granular permissions)
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(100) NOT NULL, -- 'kb', 'api', 'chat', 'asset', 'admin'
    resource_path VARCHAR(500),          -- '/kb/users/*', '/api/v1/chat/*', etc.
    action VARCHAR(50) NOT NULL,         -- 'read', 'write', 'delete', 'share', 'admin'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role assignments
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    context_type VARCHAR(50),            -- 'global', 'team', 'workspace', 'resource'
    context_id VARCHAR(500),             -- team_id, workspace_id, or resource path
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,                -- For temporary access
    PRIMARY KEY (user_id, role_id, context_type, context_id)
);

-- Direct user permissions (overrides/exceptions)
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    granted BOOLEAN DEFAULT true,        -- Can also revoke specific permissions
    context_type VARCHAR(50),
    context_id VARCHAR(500),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, permission_id, context_type, context_id)
);

-- ========================================================================
-- TEAM AND WORKSPACE SUPPORT
-- ========================================================================

-- Teams table (organizational units)
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_team_id UUID REFERENCES teams(id),  -- For hierarchical teams
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team membership
CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_role VARCHAR(50) DEFAULT 'member', -- 'owner', 'admin', 'member', 'viewer'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by UUID REFERENCES users(id),
    PRIMARY KEY (team_id, user_id)
);

-- Workspaces table (project collaboration spaces)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    workspace_type VARCHAR(50) DEFAULT 'project', -- 'project', 'incident', 'research'
    status VARCHAR(50) DEFAULT 'active',          -- 'active', 'archived', 'completed'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    archived_at TIMESTAMP,
    expires_at TIMESTAMP                          -- For time-bound workspaces
);

-- Workspace membership
CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by UUID REFERENCES users(id),
    PRIMARY KEY (workspace_id, user_id)
);

-- ========================================================================
-- RESOURCE ACCESS CONTROL (For KB and other resources)
-- ========================================================================

-- Shared resources table (for tracking shared documents, assets, etc.)
CREATE TABLE IF NOT EXISTS shared_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(100) NOT NULL,    -- 'kb_document', 'chat_conversation', 'asset'
    resource_id VARCHAR(500) NOT NULL,      -- Document path, conversation ID, etc.
    shared_by UUID REFERENCES users(id) NOT NULL,
    share_name VARCHAR(255),                -- Optional name for the share
    share_message TEXT,                     -- Optional message from sharer
    share_type VARCHAR(50) DEFAULT 'direct', -- 'direct', 'link', 'public'
    permissions TEXT[] NOT NULL,            -- ['read', 'write', 'delete', 'share']
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,        -- Track usage
    metadata JSONB DEFAULT '{}',           -- Additional share metadata
    is_active BOOLEAN DEFAULT true
);

-- Generic resource permissions (extends kb_permissions concept)
CREATE TABLE IF NOT EXISTS resource_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(100) NOT NULL,    -- 'kb_document', 'chat_conversation', 'asset'
    resource_id VARCHAR(500) NOT NULL,      -- Document path, conversation ID, etc.
    principal_type VARCHAR(50) NOT NULL,    -- 'user', 'team', 'workspace', 'role'
    principal_id VARCHAR(500) NOT NULL,     -- User ID, team ID, etc.
    permissions TEXT[] NOT NULL,            -- ['read', 'write', 'delete', 'share']
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',            -- Additional permission data
    UNIQUE(resource_type, resource_id, principal_type, principal_id)
);

-- ========================================================================
-- AUDIT AND ACTIVITY TRACKING
-- ========================================================================

-- Permission audit log
CREATE TABLE IF NOT EXISTS permission_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,       -- 'permission_granted', 'role_assigned', etc.
    actor_id UUID REFERENCES users(id),
    target_user_id UUID REFERENCES users(id),
    target_type VARCHAR(50),                -- 'user', 'team', 'workspace'
    target_id VARCHAR(500),
    permission_details JSONB NOT NULL,
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- ========================================================================
-- DEFAULT ROLES AND PERMISSIONS
-- ========================================================================

-- Insert default system roles
INSERT INTO roles (name, display_name, description, role_type) VALUES
    ('super_admin', 'Super Administrator', 'Full system access', 'system'),
    ('admin', 'Administrator', 'Administrative access', 'system'),
    ('developer', 'Developer', 'Developer access to APIs and services', 'system'),
    ('analyst', 'Analyst', 'Read access to data and analytics', 'system'),
    ('user', 'User', 'Standard user access', 'system'),
    ('viewer', 'Viewer', 'Read-only access', 'system'),
    ('guest', 'Guest', 'Limited guest access', 'system');

-- Insert default KB-specific roles
INSERT INTO roles (name, display_name, description, role_type) VALUES
    ('kb_admin', 'KB Administrator', 'Full KB management access', 'system'),
    ('kb_editor', 'KB Editor', 'Can create and edit KB content', 'system'),
    ('kb_contributor', 'KB Contributor', 'Can contribute to assigned KB areas', 'system'),
    ('kb_viewer', 'KB Viewer', 'Read-only KB access', 'system');

-- Insert core permissions
INSERT INTO permissions (resource_type, resource_path, action, description) VALUES
    -- KB permissions
    ('kb', '/kb/*', 'read', 'Read any KB content'),
    ('kb', '/kb/*', 'write', 'Write any KB content'),
    ('kb', '/kb/*', 'delete', 'Delete any KB content'),
    ('kb', '/kb/*', 'share', 'Share KB content'),
    ('kb', '/kb/*', 'admin', 'Administer KB system'),
    ('kb', '/kb/users/{user_id}/*', 'read', 'Read own KB content'),
    ('kb', '/kb/users/{user_id}/*', 'write', 'Write own KB content'),
    ('kb', '/kb/shared/*', 'read', 'Read shared KB content'),
    
    -- API permissions
    ('api', '/api/v1/chat/*', 'access', 'Access chat API'),
    ('api', '/api/v1/assets/*', 'access', 'Access assets API'),
    ('api', '/api/v1/auth/*', 'access', 'Access auth API'),
    ('api', '/api/v1/admin/*', 'access', 'Access admin API'),
    
    -- Chat permissions
    ('chat', '*', 'create', 'Create chat conversations'),
    ('chat', '*', 'read', 'Read chat conversations'),
    ('chat', '*', 'delete', 'Delete chat conversations'),
    
    -- Asset permissions
    ('asset', '*', 'create', 'Create assets'),
    ('asset', '*', 'read', 'View assets'),
    ('asset', '*', 'delete', 'Delete assets'),
    
    -- Admin permissions
    ('admin', '*', 'users', 'Manage users'),
    ('admin', '*', 'roles', 'Manage roles'),
    ('admin', '*', 'permissions', 'Manage permissions'),
    ('admin', '*', 'system', 'System administration');

-- Map permissions to default roles
-- Super Admin gets everything
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'super_admin';

-- Admin gets most permissions except system
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'admin' 
  AND NOT (p.resource_type = 'admin' AND p.action = 'system');

-- Developer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'developer' 
  AND p.resource_type IN ('api', 'kb', 'chat', 'asset')
  AND p.action IN ('access', 'read', 'write', 'create');

-- Standard user role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'user' 
  AND (
    (p.resource_type = 'kb' AND p.resource_path LIKE '%{user_id}%') OR
    (p.resource_type = 'kb' AND p.resource_path = '/kb/shared/*' AND p.action = 'read') OR
    (p.resource_type = 'api' AND p.action = 'access') OR
    (p.resource_type = 'chat' AND p.action IN ('create', 'read')) OR
    (p.resource_type = 'asset' AND p.action IN ('create', 'read'))
  );

-- ========================================================================
-- INDEXES FOR PERFORMANCE
-- ========================================================================

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_context ON user_roles(context_type, context_id);
CREATE INDEX idx_team_members_user_id ON team_members(user_id);
CREATE INDEX idx_workspace_members_user_id ON workspace_members(user_id);
CREATE INDEX idx_resource_permissions_lookup ON resource_permissions(resource_type, resource_id, principal_type, principal_id);
CREATE INDEX idx_permission_audit_log_actor ON permission_audit_log(actor_id, event_timestamp DESC);
CREATE INDEX idx_permission_audit_log_target ON permission_audit_log(target_user_id, event_timestamp DESC);

-- ========================================================================
-- HELPER FUNCTIONS
-- ========================================================================

-- Function to check if user has permission
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id UUID,
    p_resource_type VARCHAR,
    p_resource_path VARCHAR,
    p_action VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Check direct user permissions
    SELECT EXISTS(
        SELECT 1 FROM user_permissions up
        JOIN permissions p ON up.permission_id = p.id
        WHERE up.user_id = p_user_id
          AND up.granted = true
          AND p.resource_type = p_resource_type
          AND (p.resource_path = p_resource_path OR p.resource_path LIKE '%*' AND p_resource_path SIMILAR TO REPLACE(p_resource_path, '*', '%'))
          AND p.action = p_action
          AND (up.expires_at IS NULL OR up.expires_at > NOW())
    ) INTO has_permission;
    
    IF has_permission THEN
        RETURN TRUE;
    END IF;
    
    -- Check role-based permissions
    SELECT EXISTS(
        SELECT 1 FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = p_user_id
          AND p.resource_type = p_resource_type
          AND (p.resource_path = p_resource_path OR p.resource_path LIKE '%*' AND p_resource_path SIMILAR TO REPLACE(p_resource_path, '*', '%'))
          AND p.action = p_action
          AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- Function to get all permissions for a user
CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id UUID)
RETURNS TABLE(
    resource_type VARCHAR,
    resource_path VARCHAR,
    action VARCHAR,
    source VARCHAR  -- 'role' or 'direct'
) AS $$
BEGIN
    -- Get role-based permissions
    RETURN QUERY
    SELECT DISTINCT
        p.resource_type,
        p.resource_path,
        p.action,
        'role'::VARCHAR as source
    FROM user_roles ur
    JOIN role_permissions rp ON ur.role_id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = p_user_id
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    
    UNION
    
    -- Get direct permissions
    SELECT DISTINCT
        p.resource_type,
        p.resource_path,
        p.action,
        'direct'::VARCHAR as source
    FROM user_permissions up
    JOIN permissions p ON up.permission_id = p.id
    WHERE up.user_id = p_user_id
      AND up.granted = true
      AND (up.expires_at IS NULL OR up.expires_at > NOW());
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- ========================================================================
-- MIGRATION NOTES
-- ========================================================================
-- This RBAC system is designed to:
-- 1. Start with KB permissions but extend to the entire platform
-- 2. Support teams and workspaces as first-class concepts
-- 3. Enable fine-grained permission control with wildcards
-- 4. Provide audit trails for compliance
-- 5. Support temporary/expiring permissions
-- 6. Allow both role-based and direct permission assignments
--
-- To apply: docker compose exec db psql -U postgres -d llm_platform < migrations/004_create_rbac_tables.sql