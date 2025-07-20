-- Add resource_permissions table that RBAC code expects

CREATE TABLE IF NOT EXISTS resource_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(500) NOT NULL,
    principal_type VARCHAR(50) NOT NULL, -- 'user', 'team', 'workspace', 'role'
    principal_id UUID NOT NULL,
    permissions JSONB DEFAULT '["read"]'::jsonb,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(resource_type, resource_id, principal_type, principal_id)
);

-- Create indexes for performance
CREATE INDEX idx_resource_permissions_resource ON resource_permissions(resource_type, resource_id);
CREATE INDEX idx_resource_permissions_principal ON resource_permissions(principal_type, principal_id);
CREATE INDEX idx_resource_permissions_expires ON resource_permissions(expires_at) WHERE expires_at IS NOT NULL;

-- Grant Jason full KB permissions
INSERT INTO resource_permissions (resource_type, resource_id, principal_type, principal_id, permissions)
SELECT 
    'kb',
    '/kb',
    'user',
    u.id,
    '["read", "write", "delete", "admin"]'::jsonb
FROM users u
WHERE u.email = 'jason@aeonia.ai'
ON CONFLICT DO NOTHING;