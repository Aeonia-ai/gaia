-- RBAC Database Functions
-- These functions support the RBAC system for permission checking

-- Function to check if a user has a specific permission
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id UUID,
    p_resource_type VARCHAR,
    p_resource_path VARCHAR,
    p_action VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Check if user has super_admin role (global access)
    IF EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = p_user_id 
        AND r.name = 'super_admin'
        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check role-based permissions
    IF EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = p_user_id
        AND p.resource_type = p_resource_type
        AND p.action = p_action
        AND (p.resource_path IS NULL OR p_resource_path LIKE p.resource_path || '%')
        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check direct resource permissions
    IF EXISTS (
        SELECT 1 FROM resource_permissions
        WHERE resource_type = p_resource_type
        AND resource_id = p_resource_path
        AND principal_type = 'user'
        AND principal_id = p_user_id::TEXT
        AND p_action = ANY(permissions)
        AND (expires_at IS NULL OR expires_at > NOW())
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check team-based permissions
    IF EXISTS (
        SELECT 1 FROM resource_permissions rp
        JOIN team_members tm ON rp.principal_id = tm.team_id::TEXT
        WHERE rp.resource_type = p_resource_type
        AND rp.resource_id = p_resource_path
        AND rp.principal_type = 'team'
        AND tm.user_id = p_user_id
        AND p_action = ANY(rp.permissions)
        AND (rp.expires_at IS NULL OR rp.expires_at > NOW())
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check workspace-based permissions
    IF EXISTS (
        SELECT 1 FROM resource_permissions rp
        JOIN workspace_members wm ON rp.principal_id = wm.workspace_id::TEXT
        WHERE rp.resource_type = p_resource_type
        AND rp.resource_id = p_resource_path
        AND rp.principal_type = 'workspace'
        AND wm.user_id = p_user_id
        AND p_action = ANY(rp.permissions)
        AND (rp.expires_at IS NULL OR rp.expires_at > NOW())
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Special case for KB: users always have full access to their own namespace
    IF p_resource_type = 'kb' AND p_resource_path LIKE '/kb/users/' || p_user_id || '/%' THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to get all permissions for a user
CREATE OR REPLACE FUNCTION get_user_permissions(
    p_user_id UUID
) RETURNS TABLE (
    resource_type VARCHAR,
    resource_path VARCHAR,
    action VARCHAR,
    source VARCHAR  -- 'role', 'direct', 'team', 'workspace'
) AS $$
BEGIN
    -- Get permissions from roles
    RETURN QUERY
    SELECT DISTINCT
        p.resource_type,
        COALESCE(p.resource_path, '/*') as resource_path,
        p.action,
        'role'::VARCHAR as source
    FROM user_roles ur
    JOIN role_permissions rp ON ur.role_id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = p_user_id
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW());
    
    -- Get direct permissions
    RETURN QUERY
    SELECT DISTINCT
        rp.resource_type,
        rp.resource_id as resource_path,
        unnest(rp.permissions) as action,
        'direct'::VARCHAR as source
    FROM resource_permissions rp
    WHERE rp.principal_type = 'user'
    AND rp.principal_id = p_user_id::TEXT
    AND (rp.expires_at IS NULL OR rp.expires_at > NOW());
    
    -- Get team-based permissions
    RETURN QUERY
    SELECT DISTINCT
        rp.resource_type,
        rp.resource_id as resource_path,
        unnest(rp.permissions) as action,
        'team'::VARCHAR as source
    FROM resource_permissions rp
    JOIN team_members tm ON rp.principal_id = tm.team_id::TEXT
    WHERE rp.principal_type = 'team'
    AND tm.user_id = p_user_id
    AND (rp.expires_at IS NULL OR rp.expires_at > NOW());
    
    -- Get workspace-based permissions
    RETURN QUERY
    SELECT DISTINCT
        rp.resource_type,
        rp.resource_id as resource_path,
        unnest(rp.permissions) as action,
        'workspace'::VARCHAR as source
    FROM resource_permissions rp
    JOIN workspace_members wm ON rp.principal_id = wm.workspace_id::TEXT
    WHERE rp.principal_type = 'workspace'
    AND wm.user_id = p_user_id
    AND (rp.expires_at IS NULL OR rp.expires_at > NOW());
    
    -- Add implicit KB permissions for user's own namespace
    RETURN QUERY
    SELECT
        'kb'::VARCHAR as resource_type,
        '/kb/users/' || p_user_id || '/*' as resource_path,
        unnest(ARRAY['read', 'write', 'delete', 'share', 'admin']) as action,
        'owner'::VARCHAR as source;
END;
$$ LANGUAGE plpgsql;

-- Function to get accessible KB paths for a user
CREATE OR REPLACE FUNCTION get_user_kb_paths(
    p_user_id UUID
) RETURNS TABLE (
    kb_path VARCHAR,
    access_type VARCHAR  -- 'owner', 'team', 'workspace', 'shared', 'public'
) AS $$
BEGIN
    -- User's own namespace
    RETURN QUERY
    SELECT 
        '/kb/users/' || p_user_id as kb_path,
        'owner'::VARCHAR as access_type;
    
    -- Shared namespace (all authenticated users can read)
    RETURN QUERY
    SELECT 
        '/kb/shared' as kb_path,
        'shared'::VARCHAR as access_type;
    
    -- Public namespace (all users can read)
    RETURN QUERY
    SELECT 
        '/kb/public' as kb_path,
        'public'::VARCHAR as access_type;
    
    -- Team namespaces
    RETURN QUERY
    SELECT DISTINCT
        '/kb/teams/' || tm.team_id as kb_path,
        'team'::VARCHAR as access_type
    FROM team_members tm
    WHERE tm.user_id = p_user_id;
    
    -- Workspace namespaces
    RETURN QUERY
    SELECT DISTINCT
        '/kb/workspaces/' || wm.workspace_id as kb_path,
        'workspace'::VARCHAR as access_type
    FROM workspace_members wm
    WHERE wm.user_id = p_user_id;
    
    -- Explicitly shared resources
    RETURN QUERY
    SELECT DISTINCT
        rp.resource_id as kb_path,
        'shared'::VARCHAR as access_type
    FROM resource_permissions rp
    WHERE rp.resource_type = 'kb'
    AND rp.principal_type = 'user'
    AND rp.principal_id = p_user_id::TEXT
    AND (rp.expires_at IS NULL OR rp.expires_at > NOW());
END;
$$ LANGUAGE plpgsql;

-- Helper function to check team membership with role
CREATE OR REPLACE FUNCTION get_user_team_role(
    p_user_id UUID,
    p_team_id UUID
) RETURNS VARCHAR AS $$
DECLARE
    team_role VARCHAR;
BEGIN
    SELECT role INTO team_role
    FROM team_members
    WHERE user_id = p_user_id
    AND team_id = p_team_id;
    
    RETURN team_role;
END;
$$ LANGUAGE plpgsql;

-- Function to get team hierarchy (for nested teams)
CREATE OR REPLACE FUNCTION get_team_hierarchy(
    p_team_id UUID
) RETURNS TABLE (
    team_id UUID,
    level INTEGER
) AS $$
WITH RECURSIVE team_tree AS (
    -- Base case: the team itself
    SELECT 
        id as team_id,
        0 as level
    FROM teams
    WHERE id = p_team_id
    
    UNION ALL
    
    -- Recursive case: parent teams
    SELECT 
        t.parent_team_id as team_id,
        tt.level + 1 as level
    FROM teams t
    JOIN team_tree tt ON t.id = tt.team_id
    WHERE t.parent_team_id IS NOT NULL
)
SELECT * FROM team_tree;
$$ LANGUAGE sql;

-- Function to clean up expired permissions
CREATE OR REPLACE FUNCTION cleanup_expired_permissions() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    temp_count INTEGER;
BEGIN
    -- Clean up expired user roles
    DELETE FROM user_roles
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean up expired resource permissions
    DELETE FROM resource_permissions
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Clean up expired workspaces
    UPDATE workspaces
    SET status = 'expired'
    WHERE expires_at IS NOT NULL 
    AND expires_at < NOW()
    AND status = 'active';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_roles_user_expires ON user_roles(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_resource_permissions_lookup ON resource_permissions(resource_type, resource_id, principal_type, principal_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_permissions_lookup ON permissions(resource_type, action);

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION check_user_permission TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_user_permissions TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_user_kb_paths TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_user_team_role TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_team_hierarchy TO PUBLIC;
GRANT EXECUTE ON FUNCTION cleanup_expired_permissions TO PUBLIC;