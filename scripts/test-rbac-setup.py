#!/usr/bin/env python3
"""
Test RBAC Setup - Direct database operations
"""

import asyncio
import sys
import os
from uuid import uuid4, UUID
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import get_db_session

async def setup_users_and_roles():
    """Set up users and roles directly in database"""
    
    async with get_db_session() as conn:
        # Create users
        users = [
            ("jason@aeonia.ai", "Jason Asbahr", "e3a5ca05-d65c-416c-8b9b-5b3eaca8559b"),
            ("jasonasbahr+alice@gmail.com", "Alice Test User", str(uuid4())),
            ("jasonasbahr+bob@gmail.com", "Bob Test User", str(uuid4())),
            ("system@gaia.local", "System", str(uuid4()))
        ]
        
        user_ids = {}
        for email, name, user_id in users:
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", email
            )
            
            if existing:
                user_id = str(existing['id'])
                print(f"✓ User exists: {name} -> {user_id}")
            else:
                await conn.execute(
                    """
                    INSERT INTO users (id, email, name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    UUID(user_id), email, name, datetime.now(), datetime.now()
                )
                print(f"✓ Created user: {name} -> {user_id}")
            
            user_ids[email] = user_id
        
        # Assign roles directly
        role_assignments = [
            ("jason@aeonia.ai", "super_admin"),
            ("jasonasbahr+alice@gmail.com", "kb_editor"),
            ("jasonasbahr+bob@gmail.com", "kb_viewer")
        ]
        
        for email, role_name in role_assignments:
            # Get role ID
            role = await conn.fetchrow(
                "SELECT id FROM roles WHERE name = $1", role_name
            )
            
            if role:
                role_id = role['id']
                user_id = UUID(user_ids[email])
                system_id = UUID(user_ids["system@gaia.local"])
                
                # Insert user role
                await conn.execute(
                    """
                    INSERT INTO user_roles 
                    (user_id, role_id, context_type, context_id, assigned_by, assigned_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, role_id, context_type, context_id) 
                    DO UPDATE SET 
                        assigned_by = $5,
                        assigned_at = $6
                    """,
                    user_id, role_id, "global", "global", system_id, datetime.now()
                )
                print(f"✓ Assigned {role_name} to {email}")
        
        # Create Aeonia team
        team_id = uuid4()
        await conn.execute(
            """
            INSERT INTO teams (id, name, display_name, description, created_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO UPDATE SET
                display_name = $3,
                description = $4
            """,
            team_id, "aeonia", "Aeonia Team", "Main development team", 
            UUID(user_ids["jason@aeonia.ai"])
        )
        print(f"✓ Created team: aeonia -> {team_id}")
        
        # Add team members
        await conn.execute(
            """
            INSERT INTO team_members (team_id, user_id, role, invited_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (team_id, user_id) DO UPDATE SET role = $3
            """,
            team_id, UUID(user_ids["jason@aeonia.ai"]), "owner", 
            UUID(user_ids["system@gaia.local"])
        )
        
        await conn.execute(
            """
            INSERT INTO team_members (team_id, user_id, role, invited_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (team_id, user_id) DO UPDATE SET role = $3
            """,
            team_id, UUID(user_ids["jasonasbahr+alice@gmail.com"]), "member",
            UUID(user_ids["system@gaia.local"])
        )
        print("✓ Added team members")
        
        # Test permissions
        print("\n=== Testing Permissions ===")
        
        for email, role in role_assignments:
            result = await conn.fetchval(
                "SELECT check_user_permission($1::uuid, $2, $3, $4)",
                user_ids[email], "kb", "/kb/", "read"
            )
            print(f"{email} can read KB: {result}")
        
        print("\n✅ Setup complete!")
        print("User IDs:")
        for email, user_id in user_ids.items():
            if email != "system@gaia.local":
                print(f"  {email}: {user_id}")

if __name__ == "__main__":
    asyncio.run(setup_users_and_roles())