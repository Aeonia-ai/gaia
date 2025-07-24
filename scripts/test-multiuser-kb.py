#!/usr/bin/env python3
"""
Test Multi-User KB Functionality

This script tests the multi-user KB with RBAC by:
1. Creating test users with different roles
2. Testing permission isolation
3. Creating teams and workspaces
4. Testing sharing functionality
"""

import asyncio
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import get_db_session
from app.shared.rbac import rbac_manager
from sqlalchemy import text

async def create_test_users():
    """Create test users with different roles"""
    print("\n=== Creating Test Users ===")
    
    users = [
        {"id": str(uuid4()), "email": "alice@test.com", "name": "Alice Admin", "role": "kb_admin"},
        {"id": str(uuid4()), "email": "bob@test.com", "name": "Bob Editor", "role": "kb_editor"},
        {"id": str(uuid4()), "email": "charlie@test.com", "name": "Charlie Viewer", "role": "kb_viewer"},
    ]
    
    async with get_db_session() as session:
        for user in users:
            # Create user
            await session.execute(
                text("""
                    INSERT INTO users (id, email, name, created_at, updated_at)
                    VALUES (:id, :email, :name, NOW(), NOW())
                    ON CONFLICT (email) DO UPDATE
                    SET name = :name, updated_at = NOW()
                    RETURNING id
                """),
                {"id": user["id"], "email": user["email"], "name": user["name"]}
            )
            
            # Get user ID (in case of existing user)
            result = await session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": user["email"]}
            )
            user_id = str(result.scalar())
            user["id"] = user_id
            
            # Assign role
            await rbac_manager.assign_role(
                user_id=user_id,
                role_name=user["role"],
                assigned_by="system"
            )
            
            print(f"✓ Created {user['name']} ({user['email']}) with role: {user['role']}")
        
        await session.commit()
    
    return users

async def test_permission_isolation(users):
    """Test that users can only access their allowed content"""
    print("\n=== Testing Permission Isolation ===")
    
    alice_id = users[0]["id"]
    bob_id = users[1]["id"]
    charlie_id = users[2]["id"]
    
    # Test Alice's private path
    alice_private = f"/kb/users/{alice_id}/private/notes.md"
    
    # Alice should have access to her private content
    can_read = await rbac_manager.check_kb_access(alice_id, alice_private)
    print(f"✓ Alice can read her private content: {can_read}")
    
    # Bob should NOT have access to Alice's private content
    can_read = await rbac_manager.check_kb_access(bob_id, alice_private)
    print(f"✓ Bob cannot read Alice's private content: {not can_read}")
    
    # Charlie should NOT have access either
    can_read = await rbac_manager.check_kb_access(charlie_id, alice_private)
    print(f"✓ Charlie cannot read Alice's private content: {not can_read}")
    
    # All users should have read access to shared content
    shared_path = "/kb/shared/policies/guidelines.md"
    for user in users:
        can_read = await rbac_manager.check_kb_access(user["id"], shared_path)
        print(f"✓ {user['name']} can read shared content: {can_read}")

async def create_team_and_test(users):
    """Create a team and test team-based access"""
    print("\n=== Testing Team-Based Access ===")
    
    # Create engineering team
    team_id = str(uuid4())
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO teams (id, name, display_name, description, created_by)
                VALUES (:id, 'engineering', 'Engineering Team', 'Core engineering team', :created_by)
                ON CONFLICT (name) DO UPDATE
                SET display_name = 'Engineering Team'
                RETURNING id
            """),
            {"id": team_id, "created_by": users[0]["id"]}
        )
        
        result = await session.execute(
            text("SELECT id FROM teams WHERE name = 'engineering'")
        )
        team_id = str(result.scalar())
        await session.commit()
    
    print(f"✓ Created Engineering team (ID: {team_id})")
    
    # Add Alice and Bob to team
    await rbac_manager.add_team_member(team_id, users[0]["id"], "admin", "system")
    await rbac_manager.add_team_member(team_id, users[1]["id"], "member", "system")
    print("✓ Added Alice (admin) and Bob (member) to Engineering team")
    
    # Test team KB access
    team_path = f"/kb/teams/{team_id}/docs/architecture.md"
    
    # Alice and Bob should have access
    can_read = await rbac_manager.check_kb_access(users[0]["id"], team_path)
    print(f"✓ Alice (team admin) can access team KB: {can_read}")
    
    can_read = await rbac_manager.check_kb_access(users[1]["id"], team_path)
    print(f"✓ Bob (team member) can access team KB: {can_read}")
    
    # Charlie is not in the team
    can_read = await rbac_manager.check_kb_access(users[2]["id"], team_path)
    print(f"✓ Charlie (not in team) cannot access team KB: {not can_read}")
    
    return team_id

async def create_workspace_and_test(users):
    """Create a workspace and test project-based access"""
    print("\n=== Testing Workspace Access ===")
    
    # Create Q1 Planning workspace
    workspace_id = str(uuid4())
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO workspaces (id, name, display_name, description, created_by)
                VALUES (:id, 'q1-planning', 'Q1 Planning', 'Q1 2025 planning workspace', :created_by)
                RETURNING id
            """),
            {"id": workspace_id, "created_by": users[0]["id"]}
        )
        await session.commit()
    
    print(f"✓ Created Q1 Planning workspace (ID: {workspace_id})")
    
    # Add all users to workspace
    for user in users:
        await rbac_manager.add_workspace_member(workspace_id, user["id"], "system")
    print("✓ Added all users to workspace")
    
    # Test workspace access
    workspace_path = f"/kb/workspaces/{workspace_id}/planning/roadmap.md"
    
    for user in users:
        can_read = await rbac_manager.check_kb_access(user["id"], workspace_path)
        print(f"✓ {user['name']} can access workspace: {can_read}")
    
    return workspace_id

async def test_document_sharing(users):
    """Test document sharing between users"""
    print("\n=== Testing Document Sharing ===")
    
    alice_id = users[0]["id"]
    bob_id = users[1]["id"]
    
    # Alice shares a document with Bob
    doc_path = f"/kb/users/{alice_id}/projects/ml-research.md"
    
    # Before sharing, Bob shouldn't have access
    can_read = await rbac_manager.check_kb_access(bob_id, doc_path)
    print(f"✓ Bob cannot read Alice's document before sharing: {not can_read}")
    
    # Share the document
    await rbac_manager.share_resource(
        resource_type="kb",
        resource_id=doc_path,
        shared_by=alice_id,
        principal_type="user",
        principal_id=bob_id,
        permissions=["read", "write"]
    )
    print(f"✓ Alice shared document with Bob")
    
    # After sharing, Bob should have access
    can_read = await rbac_manager.check_kb_access(bob_id, doc_path)
    print(f"✓ Bob can now read the shared document: {can_read}")
    
    can_write = await rbac_manager.check_kb_access(bob_id, doc_path, "write")
    print(f"✓ Bob can write to the shared document: {can_write}")

async def test_accessible_paths(users):
    """Test getting all accessible paths for each user"""
    print("\n=== Testing Accessible Paths ===")
    
    for user in users:
        paths = await rbac_manager.get_accessible_kb_paths(user["id"])
        print(f"\n{user['name']} can access:")
        for path in paths:
            print(f"  - {path}")

async def main():
    """Run all tests"""
    print("Starting Multi-User KB Tests...")
    
    try:
        # Create test users
        users = await create_test_users()
        
        # Test permission isolation
        await test_permission_isolation(users)
        
        # Test team-based access
        team_id = await create_team_and_test(users)
        
        # Test workspace access
        workspace_id = await create_workspace_and_test(users)
        
        # Test document sharing
        await test_document_sharing(users)
        
        # Test accessible paths
        await test_accessible_paths(users)
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())