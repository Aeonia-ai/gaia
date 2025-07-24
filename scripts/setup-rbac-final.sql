-- Setup RBAC Users and Roles (Final)
-- This script creates the real users and assigns them roles

-- Add team members directly (team already exists)
DO $$
DECLARE
    jason_id UUID;
    alice_id UUID;
    bob_id UUID;
    system_id UUID;
    aeonia_team_id UUID;
BEGIN
    -- Get user IDs
    SELECT id INTO jason_id FROM users WHERE email = 'jason@aeonia.ai';
    SELECT id INTO alice_id FROM users WHERE email = 'jasonasbahr+alice@gmail.com';
    SELECT id INTO bob_id FROM users WHERE email = 'jasonasbahr+bob@gmail.com';
    SELECT id INTO system_id FROM users WHERE email = 'system@gaia.local';
    
    -- Get team ID
    SELECT id INTO aeonia_team_id FROM teams WHERE name = 'aeonia';
    
    -- Add team members
    INSERT INTO team_members (team_id, user_id, team_role, invited_by, joined_at)
    VALUES 
        (aeonia_team_id, jason_id, 'owner', system_id, NOW()),
        (aeonia_team_id, alice_id, 'member', system_id, NOW())
    ON CONFLICT (team_id, user_id) DO UPDATE SET
        team_role = EXCLUDED.team_role;
    
    RAISE NOTICE 'Team members added to Aeonia team: %', aeonia_team_id;
    
    -- Add KB permissions for kb_editor role
    INSERT INTO permissions (resource_type, resource_path, action, description)
    VALUES 
        ('kb', NULL, 'read', 'Read KB content'),
        ('kb', NULL, 'write', 'Write KB content'),
        ('kb', NULL, 'share', 'Share KB content')
    ON CONFLICT DO NOTHING;
    
    -- Grant permissions to kb_editor role
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id
    FROM roles r
    CROSS JOIN permissions p
    WHERE r.name = 'kb_editor'
    AND p.resource_type = 'kb'
    AND p.action IN ('read', 'write', 'share')
    ON CONFLICT DO NOTHING;
    
    -- Grant read permission to kb_viewer role
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id
    FROM roles r
    CROSS JOIN permissions p
    WHERE r.name = 'kb_viewer'
    AND p.resource_type = 'kb'
    AND p.action = 'read'
    ON CONFLICT DO NOTHING;
    
    RAISE NOTICE 'KB permissions configured';
END $$;

-- Test permissions again
SELECT 
    u.email,
    r.name as role,
    check_user_permission(u.id, 'kb', '/kb/', 'read') as can_read_kb,
    check_user_permission(u.id, 'kb', '/kb/', 'write') as can_write_kb,
    check_user_permission(u.id, 'kb', '/kb/users/' || u.id || '/', 'write') as can_write_own_kb
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.email IN ('jason@aeonia.ai', 'jasonasbahr+alice@gmail.com', 'jasonasbahr+bob@gmail.com')
ORDER BY u.email;

-- Show team membership
SELECT 
    t.name as team_name,
    u.email,
    tm.team_role
FROM teams t
JOIN team_members tm ON t.id = tm.team_id
JOIN users u ON tm.user_id = u.id
WHERE t.name = 'aeonia'
ORDER BY u.email;