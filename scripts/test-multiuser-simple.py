#!/usr/bin/env python3
"""
Simple Multi-User KB Test

Test if the multi-user KB mode is enabled and working.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_multiuser_setup():
    """Test if multi-user KB is properly configured"""
    print("=== Testing Multi-User KB Setup ===")
    
    # Test 1: Check if settings are loaded
    try:
        from app.shared.config import settings
        print(f"✓ Settings loaded")
        print(f"  KB_MULTI_USER_ENABLED: {settings.KB_MULTI_USER_ENABLED}")
        print(f"  KB_STORAGE_MODE: {settings.KB_STORAGE_MODE}")
        print(f"  KB_USER_ISOLATION: {settings.KB_USER_ISOLATION}")
        print(f"  KB_DEFAULT_VISIBILITY: {settings.KB_DEFAULT_VISIBILITY}")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False
    
    # Test 2: Check if RBAC manager is available
    try:
        from app.shared.rbac import rbac_manager
        print(f"✓ RBAC manager imported")
    except Exception as e:
        print(f"❌ Failed to import RBAC manager: {e}")
        return False
    
    # Test 3: Check if multi-user storage is available
    if settings.KB_MULTI_USER_ENABLED:
        try:
            from app.services.kb.kb_storage_with_rbac import KBStorageWithRBAC
            print(f"✓ Multi-user storage manager available")
        except Exception as e:
            print(f"❌ Failed to import multi-user storage: {e}")
            return False
    else:
        print("ℹ️ Multi-user mode is disabled")
    
    # Test 4: Check if database connection works
    try:
        from app.shared.database import get_db_session
        async with get_db_session() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"✓ Database connection works: {result}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Test 5: Check if KB service is configured correctly
    try:
        if settings.KB_MULTI_USER_ENABLED:
            from app.services.kb.kb_rbac_integration import kb_server_with_rbac
            print(f"✓ RBAC-enabled KB server available")
        else:
            from app.services.kb.kb_mcp_server import kb_server
            print(f"✓ Standard KB server available")
    except Exception as e:
        print(f"❌ KB server import failed: {e}")
        return False
    
    return True

async def test_database_tables():
    """Test if RBAC tables exist in database"""
    print("\n=== Testing Database Tables ===")
    
    try:
        from app.shared.database import get_db_session
        
        tables_to_check = [
            'roles',
            'permissions', 
            'role_permissions',
            'user_roles',
            'shared_resources',
            'teams',
            'team_members',
            'workspaces',
            'workspace_members'
        ]
        
        async with get_db_session() as conn:
            for table in tables_to_check:
                try:
                    result = await conn.fetchval(
                        f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                    )
                    if result:
                        print(f"✓ Table '{table}' exists")
                    else:
                        print(f"❌ Table '{table}' missing")
                except Exception as e:
                    print(f"❌ Error checking table '{table}': {e}")
                    
    except Exception as e:
        print(f"❌ Database table check failed: {e}")
        return False
    
    return True

async def main():
    """Run all tests"""
    print("Starting Multi-User KB Setup Tests...\n")
    
    try:
        # Test basic setup
        setup_ok = await test_multiuser_setup()
        
        # Test database tables
        tables_ok = await test_database_tables()
        
        if setup_ok and tables_ok:
            print("\n✅ All setup tests passed!")
            print("\nNext steps:")
            print("1. Create test users and roles")
            print("2. Test permission isolation")
            print("3. Test team and workspace functionality")
        else:
            print("\n❌ Some tests failed!")
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())