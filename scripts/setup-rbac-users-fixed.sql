-- Setup RBAC Users and Roles (Fixed)
-- This script creates the real users and assigns them roles

-- Create system user first
INSERT INTO users (id, email, name, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000000', 'system@gaia.local', 'System', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Create real users
INSERT INTO users (id, email, name, created_at, updated_at)
VALUES 
    ('e3a5ca05-d65c-416c-8b9b-5b3eaca8559b', 'jason@aeonia.ai', 'Jason Asbahr', NOW(), NOW()),
    (gen_random_uuid(), 'jasonasbahr+alice@gmail.com', 'Alice Test User', NOW(), NOW()),
    (gen_random_uuid(), 'jasonasbahr+bob@gmail.com', 'Bob Test User', NOW(), NOW())
ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = NOW();

-- Get user IDs and set up roles
DO $$
DECLARE
    jason_id UUID;
    alice_id UUID;
    bob_id UUID;
    system_id UUID;
    super_admin_role_id UUID;
    kb_editor_role_id UUID;
    kb_viewer_role_id UUID;
    team_id UUID;
BEGIN
    -- Get user IDs
    SELECT id INTO jason_id FROM users WHERE email = 'jason@aeonia.ai';
    SELECT id INTO alice_id FROM users WHERE email = 'jasonasbahr+alice@gmail.com';
    SELECT id INTO bob_id FROM users WHERE email = 'jasonasbahr+bob@gmail.com';
    SELECT id INTO system_id FROM users WHERE email = 'system@gaia.local';
    
    -- Get role IDs
    SELECT id INTO super_admin_role_id FROM roles WHERE name = 'super_admin';
    SELECT id INTO kb_editor_role_id FROM roles WHERE name = 'kb_editor';
    SELECT id INTO kb_viewer_role_id FROM roles WHERE name = 'kb_viewer';
    
    -- Assign roles
    INSERT INTO user_roles (user_id, role_id, context_type, context_id, assigned_by, assigned_at)
    VALUES 
        (jason_id, super_admin_role_id, 'global', 'global', system_id, NOW()),
        (alice_id, kb_editor_role_id, 'global', 'global', system_id, NOW()),
        (bob_id, kb_viewer_role_id, 'global', 'global', system_id, NOW())
    ON CONFLICT (user_id, role_id, context_type, context_id) DO UPDATE SET
        assigned_by = EXCLUDED.assigned_by,
        assigned_at = NOW();
    
    -- Create Aeonia team
    INSERT INTO teams (name, display_name, description, created_by)
    VALUES ('aeonia', 'Aeonia Team', 'Main Aeonia development team', jason_id)
    ON CONFLICT (name) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO team_id;
    
    -- Get actual team ID if it already exists
    IF team_id IS NULL THEN
        SELECT id INTO team_id FROM teams WHERE name = 'aeonia';
    END IF;
    
    -- Add team members
    INSERT INTO team_members (team_id, user_id, team_role, invited_by, joined_at)
    VALUES 
        (team_id, jason_id, 'owner', system_id, NOW()),
        (team_id, alice_id, 'member', system_id, NOW())
    ON CONFLICT (team_id, user_id) DO UPDATE SET
        team_role = EXCLUDED.team_role;
    
    RAISE NOTICE 'Users created and roles assigned:';
    RAISE NOTICE '  Jason (super_admin): %', jason_id;
    RAISE NOTICE '  Alice (kb_editor): %', alice_id;
    RAISE NOTICE '  Bob (kb_viewer): %', bob_id;
    RAISE NOTICE '  Team aeonia: %', team_id;
END $$;

-- Test permissions
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

-- Show user namespaces
SELECT 
    u.email,
    '/kb/users/' || u.id || '/' as user_namespace
FROM users u
WHERE u.email IN ('jason@aeonia.ai', 'jasonasbahr+alice@gmail.com', 'jasonasbahr+bob@gmail.com')
ORDER BY u.email;