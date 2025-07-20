#!/usr/bin/env python3
"""
Real User Setup Script (Fixed Version)

Creates the actual user accounts we need:
1. jason@aeonia.ai (main account, owner of existing KB content)
2. jasonasbahr+alice@gmail.com (test user - KB editor)
3. jasonasbahr+bob@gmail.com (test user - KB viewer)

Also handles migrating existing KB content to jason@aeonia.ai's namespace.
"""

import asyncio
import sys
import os
from uuid import uuid4, UUID
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import get_db_session
from app.shared.rbac_fixed import rbac_manager

async def setup_default_roles():
    """Ensure default system roles exist"""
    print("=== Setting Up System Roles ===")
    
    default_roles = [
        {
            "name": "super_admin",
            "display_name": "Super Administrator",
            "description": "Full system access",
            "role_type": "system"
        },
        {
            "name": "admin", 
            "display_name": "Administrator",
            "description": "Administrative access",
            "role_type": "system"
        },
        {
            "name": "kb_admin",
            "display_name": "KB Administrator", 
            "description": "Full KB management access",
            "role_type": "system"
        },
        {
            "name": "kb_editor",
            "display_name": "KB Editor",
            "description": "Can create and edit KB content",
            "role_type": "system"
        },
        {
            "name": "kb_viewer",
            "display_name": "KB Viewer",
            "description": "Read-only KB access",
            "role_type": "system"
        },
        {
            "name": "guest",
            "display_name": "Guest",
            "description": "Limited guest access",
            "role_type": "system"
        }
    ]
    
    async with get_db_session() as conn:
        for role in default_roles:
            await conn.execute(
                """
                INSERT INTO roles (name, display_name, description, role_type)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name) DO UPDATE SET
                    display_name = $2,
                    description = $3,
                    updated_at = CURRENT_TIMESTAMP
                """,
                role["name"], role["display_name"], role["description"], role["role_type"]
            )
            print(f"✓ Role: {role['name']}")

async def create_user_account(email: str, name: str) -> str:
    """Create a new user account"""
    user_id = str(uuid4())
    
    async with get_db_session() as conn:
        # Check if user already exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )
        
        if existing:
            user_id = str(existing['id'])
            print(f"✓ User already exists: {name} ({email}) -> ID: {user_id}")
        else:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                UUID(user_id), email, name, datetime.now(), datetime.now()
            )
            print(f"✓ Created user: {name} ({email}) -> ID: {user_id}")
    
    return user_id

async def create_real_users():
    """Create the specific users we need"""
    print("\n=== Creating Real User Accounts ===")
    
    users = [
        {
            "email": "jason@aeonia.ai",
            "name": "Jason Asbahr", 
            "role": "super_admin",
            "description": "Main account, owner of existing KB content"
        },
        {
            "email": "jasonasbahr+alice@gmail.com",
            "name": "Alice Test User",
            "role": "kb_editor",
            "description": "Test user with editor permissions"
        },
        {
            "email": "jasonasbahr+bob@gmail.com",
            "name": "Bob Test User",
            "role": "kb_viewer", 
            "description": "Test user with viewer permissions"
        }
    ]
    
    created_users = {}
    
    # Create a system user first (for role assignments)
    system_user_id = await create_user_account("system@gaia.local", "System")
    
    for user_data in users:
        # Create user account
        user_id = await create_user_account(user_data["email"], user_data["name"])
        
        # Assign role using the fixed rbac_manager
        success = await rbac_manager.assign_role(
            user_id=user_id,
            role_name=user_data["role"],
            assigned_by=system_user_id,  # Use system user as assigner
            context_type="global",
            context_id="global"  # Important: provide context_id for global roles
        )
        
        if success:
            print(f"  ✓ Assigned role '{user_data['role']}' to {user_data['name']}")
        else:
            print(f"  ❌ Failed to assign role to {user_data['name']}")
        
        created_users[user_data["email"]] = {
            "user_id": user_id,
            "name": user_data["name"],
            "role": user_data["role"],
            "description": user_data["description"]
        }
    
    return created_users

async def migrate_existing_kb_content(jason_user_id: str):
    """
    Plan for migrating existing KB content to jason@aeonia.ai's namespace.
    
    Note: This would need to be implemented based on the current KB storage mode.
    For now, we'll just document what needs to happen.
    """
    print(f"\n=== KB Content Migration Plan ===")
    print(f"Target user: jason@aeonia.ai (ID: {jason_user_id})")
    
    # Define the migration strategy
    migration_plan = {
        "current_location": "/kb/",
        "target_location": f"/kb/users/{jason_user_id}/",
        "strategy": "Move existing content to user namespace",
        "backup_needed": True,
        "steps": [
            "1. Create backup of current /kb/ content",
            "2. Create jason's user namespace directory",
            f"3. Move content from /kb/ to /kb/users/{jason_user_id}/",
            "4. Update any internal references",
            "5. Verify content accessibility",
            "6. Update sharing permissions if needed"
        ]
    }
    
    print(f"Current KB location: {migration_plan['current_location']}")
    print(f"Target location: {migration_plan['target_location']}")
    print(f"\nMigration steps:")
    for step in migration_plan['steps']:
        print(f"  {step}")
    
    print(f"\n⚠️  Manual migration required:")
    print(f"   The existing KB content in /kb/ should be moved to:")
    print(f"   {migration_plan['target_location']}")
    print(f"   This preserves jason@aeonia.ai's ownership of current content.")
    
    return migration_plan

async def create_demo_team(users):
    """Create a demo team with the real users"""
    print(f"\n=== Creating Demo Team ===")
    
    team_id = str(uuid4())
    team_name = "aeonia"
    
    jason_id = users["jason@aeonia.ai"]["user_id"]
    alice_id = users["jasonasbahr+alice@gmail.com"]["user_id"]
    
    async with get_db_session() as conn:
        # Create team
        await conn.execute(
            """
            INSERT INTO teams (id, name, display_name, description, created_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO UPDATE SET
                display_name = $3,
                description = $4
            RETURNING id
            """,
            UUID(team_id), team_name, "Aeonia Team", "Main Aeonia development team", UUID(jason_id)
        )
        
        # Get actual team ID
        result = await conn.fetchrow(
            "SELECT id FROM teams WHERE name = $1", team_name
        )
        actual_team_id = str(result['id'])
    
    print(f"✓ Created team: {team_name} -> ID: {actual_team_id}")
    
    # Get system user for assignments
    system_result = await get_db_session().fetchrow(
        "SELECT id FROM users WHERE email = $1", "system@gaia.local"
    )
    system_user_id = str(system_result['id'])
    
    # Add team members
    await rbac_manager.add_team_member(actual_team_id, jason_id, "admin", system_user_id)
    await rbac_manager.add_team_member(actual_team_id, alice_id, "member", system_user_id)
    
    print(f"  ✓ Added Jason as team admin")
    print(f"  ✓ Added Alice as team member")
    print(f"  ℹ️ Bob (viewer) not added to team - will test external access")
    
    return actual_team_id

async def test_user_permissions(users):
    """Test permissions for the real users"""
    print(f"\n=== Testing User Permissions ===")
    
    jason_id = users["jason@aeonia.ai"]["user_id"]
    alice_id = users["jasonasbahr+alice@gmail.com"]["user_id"] 
    bob_id = users["jasonasbahr+bob@gmail.com"]["user_id"]
    
    test_cases = [
        {
            "user": "Jason (super_admin)",
            "user_id": jason_id,
            "path": "/kb/",
            "action": "read",
            "expected": True
        },
        {
            "user": "Jason (super_admin)", 
            "user_id": jason_id,
            "path": "/kb/",
            "action": "write",
            "expected": True
        },
        {
            "user": "Alice (kb_editor)",
            "user_id": alice_id,
            "path": f"/kb/users/{alice_id}/",
            "action": "write",
            "expected": True
        },
        {
            "user": "Alice (kb_editor)",
            "user_id": alice_id,
            "path": f"/kb/users/{jason_id}/",
            "action": "read",
            "expected": False  # Can't read Jason's private content
        },
        {
            "user": "Bob (kb_viewer)",
            "user_id": bob_id,
            "path": "/kb/shared/",
            "action": "read",
            "expected": True
        },
        {
            "user": "Bob (kb_viewer)",
            "user_id": bob_id, 
            "path": "/kb/shared/",
            "action": "write",
            "expected": False  # Viewers can't write
        },
        {
            "user": "Bob (kb_viewer)",
            "user_id": bob_id,
            "path": f"/kb/users/{bob_id}/",
            "action": "read",
            "expected": True  # Can read own space
        }
    ]
    
    for test in test_cases:
        try:
            from app.shared.rbac_fixed import Action
            action_enum = Action(test["action"])
            
            result = await rbac_manager.check_kb_access(
                user_id=test["user_id"],
                kb_path=test["path"],
                action=action_enum
            )
            
            status = "✓" if result == test["expected"] else "❌"
            print(f"  {status} {test['user']} {test['action']} access to {test['path']}: {result}")
            
        except Exception as e:
            print(f"  ❌ Error testing {test['user']}: {e}")

async def show_user_summary(users):
    """Show summary of created users and next steps"""
    print(f"\n=== User Account Summary ===")
    
    for email, user_data in users.items():
        print(f"\n**{user_data['name']}** ({email})")
        print(f"  User ID: {user_data['user_id']}")
        print(f"  Role: {user_data['role']}")
        print(f"  Description: {user_data['description']}")
        
        # Show user's KB namespace
        user_namespace = f"/kb/users/{user_data['user_id']}/"
        print(f"  KB Namespace: {user_namespace}")
    
    print(f"\n=== Next Steps ===")
    print(f"1. **Migrate existing KB content:**")
    print(f"   Move current /kb/ content to /kb/users/{users['jason@aeonia.ai']['user_id']}/")
    print(f"   This preserves Jason's ownership of existing content")
    
    print(f"\n2. **Test multi-user functionality:**")
    print(f"   - Login as different users via web interface")
    print(f"   - Create content in user namespaces") 
    print(f"   - Test sharing between users")
    print(f"   - Verify permission isolation")
    
    print(f"\n3. **Web interface integration:**")
    print(f"   - Update login to pass user_id to KB operations")
    print(f"   - Add namespace switching in UI")
    print(f"   - Add sharing controls")
    
    print(f"\n4. **API key association:**")
    print(f"   - Create user-specific API keys")
    print(f"   - Test programmatic access with user context")

async def main():
    """Set up real user accounts for multi-user KB"""
    print("🚀 Setting up Real Multi-User KB Accounts")
    print("=" * 50)
    
    try:
        # Step 1: Set up system roles
        await setup_default_roles()
        
        # Step 2: Create real user accounts
        users = await create_real_users()
        
        # Step 3: Plan KB content migration
        jason_id = users["jason@aeonia.ai"]["user_id"]
        migration_plan = await migrate_existing_kb_content(jason_id)
        
        # Step 4: Create team structure
        team_id = await create_demo_team(users)
        
        # Step 5: Test permissions
        await test_user_permissions(users)
        
        # Step 6: Show summary and next steps
        await show_user_summary(users)
        
        print(f"\n✅ Real user setup complete!")
        print(f"🔑 User IDs for reference:")
        for email, data in users.items():
            print(f"   {email}: {data['user_id']}")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())