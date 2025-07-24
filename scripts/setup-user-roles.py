#!/usr/bin/env python3
"""
User Role Setup Script

This script demonstrates how to:
1. Create user accounts
2. Assign roles to users 
3. Set up teams and workspaces
4. Test user permissions

Usage: python scripts/setup-user-roles.py
"""

import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import get_db_session
from app.shared.rbac_fixed import rbac_manager

async def create_user_account(email: str, name: str) -> str:
    """Create a new user account"""
    user_id = str(uuid4())
    
    async with get_db_session() as session:
        await session.execute(
            """
            INSERT INTO users (id, email, name, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email) DO UPDATE SET
                name = $3,
                updated_at = $5
            RETURNING id
            """,
            user_id, email, name, datetime.now(), datetime.now()
        )
        
        # Get the actual user ID (in case of conflict)
        result = await session.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )
        actual_user_id = str(result['id'])
    
    print(f"✓ Created/Updated user: {name} ({email}) -> ID: {actual_user_id}")
    return actual_user_id

async def setup_default_roles():
    """Ensure default system roles exist"""
    print("\n=== Setting Up Default Roles ===")
    
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
        }
    ]
    
    async with get_db_session() as session:
        for role in default_roles:
            await session.execute(
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

async def create_demo_users():
    """Create demonstration users with different roles"""
    print("\n=== Creating Demo Users ===")
    
    users = [
        {
            "email": "alice@gaia.dev",
            "name": "Alice Admin", 
            "role": "kb_admin"
        },
        {
            "email": "bob@gaia.dev",
            "name": "Bob Editor",
            "role": "kb_editor" 
        },
        {
            "email": "charlie@gaia.dev",
            "name": "Charlie Viewer",
            "role": "kb_viewer"
        }
    ]
    
    created_users = {}
    
    for user_data in users:
        # Create user account
        user_id = await create_user_account(user_data["email"], user_data["name"])
        
        # Assign role
        success = await rbac_manager.assign_role(
            user_id=user_id,
            role_name=user_data["role"],
            assigned_by="system",
            context_type="global"
        )
        
        if success:
            print(f"  ✓ Assigned role '{user_data['role']}' to {user_data['name']}")
        else:
            print(f"  ❌ Failed to assign role to {user_data['name']}")
        
        created_users[user_data["name"]] = {
            "user_id": user_id,
            "email": user_data["email"],
            "role": user_data["role"]
        }
    
    return created_users

async def create_demo_team(users):
    """Create a demo team with members"""
    print("\n=== Creating Demo Team ===")
    
    team_id = str(uuid4())
    team_name = "engineering"
    
    async with get_db_session() as session:
        # Create team
        await session.execute(
            """
            INSERT INTO teams (id, name, display_name, description, created_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO UPDATE SET
                display_name = $3,
                description = $4
            RETURNING id
            """,
            team_id, team_name, "Engineering Team", "Core engineering team",
            users["Alice Admin"]["user_id"]
        )
        
        # Get actual team ID
        result = await session.fetchrow(
            "SELECT id FROM teams WHERE name = $1", team_name
        )
        actual_team_id = str(result['id'])
    
    print(f"✓ Created team: {team_name} -> ID: {actual_team_id}")
    
    # Add team members
    alice_id = users["Alice Admin"]["user_id"] 
    bob_id = users["Bob Editor"]["user_id"]
    
    await rbac_manager.add_team_member(actual_team_id, alice_id, "admin", "system")
    await rbac_manager.add_team_member(actual_team_id, bob_id, "member", "system")
    
    print(f"  ✓ Added Alice as team admin")
    print(f"  ✓ Added Bob as team member")
    
    return actual_team_id

async def create_demo_workspace(users):
    """Create a demo workspace"""
    print("\n=== Creating Demo Workspace ===")
    
    workspace_id = str(uuid4())
    
    async with get_db_session() as session:
        # Create workspace
        await session.execute(
            """
            INSERT INTO workspaces (id, name, display_name, description, created_by)
            VALUES ($1, $2, $3, $4, $5)
            """,
            workspace_id, "q1-2025-planning", "Q1 2025 Planning", 
            "Q1 2025 planning workspace", users["Alice Admin"]["user_id"]
        )
    
    print(f"✓ Created workspace: Q1 2025 Planning -> ID: {workspace_id}")
    
    # Add all users to workspace
    for user_name, user_data in users.items():
        await rbac_manager.add_workspace_member(
            workspace_id, user_data["user_id"], "system"
        )
        print(f"  ✓ Added {user_name} to workspace")
    
    return workspace_id

async def test_user_permissions(users):
    """Test that user permissions work correctly"""
    print("\n=== Testing User Permissions ===")
    
    alice_id = users["Alice Admin"]["user_id"]
    bob_id = users["Bob Editor"]["user_id"] 
    charlie_id = users["Charlie Viewer"]["user_id"]
    
    # Test different KB paths
    test_cases = [
        {
            "user": "Alice (admin)",
            "user_id": alice_id,
            "path": "/kb/",
            "action": "read",
            "expected": True
        },
        {
            "user": "Alice (admin)", 
            "user_id": alice_id,
            "path": "/kb/",
            "action": "write",
            "expected": True
        },
        {
            "user": "Bob (editor)",
            "user_id": bob_id,
            "path": f"/kb/users/{bob_id}/private/",
            "action": "read", 
            "expected": True
        },
        {
            "user": "Bob (editor)",
            "user_id": bob_id,
            "path": f"/kb/users/{alice_id}/private/",
            "action": "read",
            "expected": False  # Can't read Alice's private content
        },
        {
            "user": "Charlie (viewer)",
            "user_id": charlie_id,
            "path": "/kb/shared/",
            "action": "read",
            "expected": True
        },
        {
            "user": "Charlie (viewer)",
            "user_id": charlie_id, 
            "path": "/kb/shared/",
            "action": "write",
            "expected": False  # Viewers can't write
        }
    ]
    
    for test in test_cases:
        try:
            result = await rbac_manager.check_kb_access(
                user_id=test["user_id"],
                path=test["path"],
                action=test["action"]
            )
            
            status = "✓" if result == test["expected"] else "❌"
            print(f"  {status} {test['user']} {test['action']} access to {test['path']}: {result}")
            
        except Exception as e:
            print(f"  ❌ Error testing {test['user']}: {e}")

async def show_user_summary(users):
    """Show summary of created users and their access"""
    print("\n=== User Summary ===")
    
    for user_name, user_data in users.items():
        user_id = user_data["user_id"]
        
        print(f"\n**{user_name}** ({user_data['email']})")
        print(f"  User ID: {user_id}")
        print(f"  Role: {user_data['role']}")
        
        # Show accessible paths
        print("  Accessible KB paths:")
        
        kb_paths = [
            f"/kb/users/{user_id}/",  # User's private space
            "/kb/shared/",             # Shared content
            "/kb/public/",             # Public content
        ]
        
        for path in kb_paths:
            try:
                can_read = await rbac_manager.check_kb_access(user_id, path, "read")
                can_write = await rbac_manager.check_kb_access(user_id, path, "write")
                
                permissions = []
                if can_read: permissions.append("read")
                if can_write: permissions.append("write")
                
                if permissions:
                    print(f"    - {path}: {', '.join(permissions)}")
            except Exception as e:
                print(f"    - {path}: error ({e})")

async def main():
    """Run the user setup demonstration"""
    print("🚀 Setting up Multi-User KB with RBAC Demo")
    print("=" * 50)
    
    try:
        # Step 1: Set up default roles
        await setup_default_roles()
        
        # Step 2: Create demo users
        users = await create_demo_users()
        
        # Step 3: Create team and workspace
        team_id = await create_demo_team(users)
        workspace_id = await create_demo_workspace(users)
        
        # Step 4: Test permissions
        await test_user_permissions(users)
        
        # Step 5: Show summary
        await show_user_summary(users)
        
        print(f"\n✅ Demo setup complete!")
        print(f"Team ID: {team_id}")
        print(f"Workspace ID: {workspace_id}")
        
        print(f"\n🔗 Next steps:")
        print(f"1. Test KB operations with different user contexts")
        print(f"2. Try sharing documents between users")
        print(f"3. Test team/workspace collaboration")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())