# ADR-008: User Deletion Cascade Cleanup

## Status
Proposed - **CRITICAL ISSUE**

## Context
During integration testing, we discovered a **critical data cleanup bug**: a single test user had accumulated **1697 orphaned conversations** in the database. This indicates that when users are deleted from Supabase, their associated conversations are not being cleaned up from our PostgreSQL database.

### Discovery
- **Test**: `test_conversation_list` failed with ReadTimeout due to large dataset
- **Log Evidence**: "Found 1697 conversations" for a single user
- **Root Cause**: Test fixtures only delete Supabase users, not associated data

### Current User Deletion Flow
```python
# tests/fixtures/test_auth.py:85
def cleanup_test_user(self, user_id: str):
    """Delete a specific test user."""
    self.client.auth.admin.delete_user(user_id)  # ← Only Supabase deletion
    # ❌ No conversation cleanup!
```

### Impact Assessment
- **Storage Bloat**: 1697 orphaned conversations = significant database growth
- **Performance Degradation**: Large datasets cause ReadTimeout errors
- **Data Privacy**: User data persists after account deletion (GDPR violation)
- **Test Environment**: Accumulated test data affecting test reliability

## Decision
Implement **cascade deletion** for user accounts that automatically cleans up all associated data when a user is deleted.

## Implementation Plan

### 1. Database Schema Changes (Priority: High)
Add foreign key constraints with CASCADE DELETE:

```sql
-- Migration: Add cascade deletion for conversations
ALTER TABLE conversations 
ADD CONSTRAINT fk_conversations_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Migration: Add cascade deletion for messages  
ALTER TABLE messages
ADD CONSTRAINT fk_messages_conversation_id
FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;

-- Migration: Add cascade deletion for user preferences
ALTER TABLE user_personas
ADD CONSTRAINT fk_user_personas_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 2. Service-Level Cleanup (Priority: High)
Implement comprehensive cleanup in user deletion logic:

```python
# New: app/shared/user_cleanup.py
class UserCleanupService:
    def __init__(self, db_pool, supabase_client):
        self.db = db_pool
        self.supabase = supabase_client
    
    async def delete_user_completely(self, user_id: str) -> bool:
        """Delete user and ALL associated data"""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # 1. Delete conversations (CASCADE deletes messages)
                await conn.execute(
                    "DELETE FROM conversations WHERE user_id = $1", 
                    user_id
                )
                
                # 2. Delete user preferences
                await conn.execute(
                    "DELETE FROM user_personas WHERE user_id = $1",
                    user_id
                )
                
                # 3. Delete user record
                await conn.execute(
                    "DELETE FROM users WHERE id = $1",
                    user_id
                )
                
                # 4. Delete from Supabase
                self.supabase.auth.admin.delete_user(user_id)
                
        return True
```

### 3. Test Fixture Updates (Priority: High)
Update test fixtures to use comprehensive cleanup:

```python
# tests/fixtures/test_auth.py
def cleanup_test_user(self, user_id: str):
    """Delete a test user and ALL associated data"""
    try:
        # Use comprehensive cleanup service
        cleanup_service = UserCleanupService(db_pool, self.client)
        await cleanup_service.delete_user_completely(user_id)
        
        if user_id in self.created_users:
            self.created_users.remove(user_id)
        logger.info(f"Completely deleted test user and data: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete test user {user_id}: {e}")
```

### 4. Production User Deletion Endpoint (Priority: Medium)
Add admin endpoint for proper user deletion:

```python
# app/services/auth/routes.py
@app.delete("/admin/users/{user_id}")
async def delete_user_admin(user_id: str, current_user: User = Depends(get_admin_user)):
    """Admin endpoint to completely delete a user"""
    cleanup_service = UserCleanupService(db_pool, supabase_client)
    success = await cleanup_service.delete_user_completely(user_id)
    
    if success:
        return {"message": "User and all data deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="User deletion failed")
```

### 5. Data Migration for Existing Orphans (Priority: Medium)
Clean up existing orphaned data:

```sql
-- Migration: Clean up existing orphaned conversations
DELETE FROM conversations 
WHERE user_id NOT IN (
    SELECT id FROM users
);

-- Migration: Clean up existing orphaned user preferences
DELETE FROM user_personas
WHERE user_id NOT IN (
    SELECT id FROM users  
);
```

## Validation Plan

### 1. Database Integrity Tests
```python
async def test_cascade_deletion():
    # Create user with conversations and preferences
    user_id = create_test_user()
    create_test_conversations(user_id, count=5)
    create_test_preferences(user_id)
    
    # Delete user
    await cleanup_service.delete_user_completely(user_id)
    
    # Verify all data is gone
    assert count_conversations(user_id) == 0
    assert count_preferences(user_id) == 0
    assert user_exists(user_id) == False
```

### 2. Performance Tests
```python
async def test_large_user_deletion_performance():
    # Create user with 1000+ conversations
    user_id = create_test_user()
    create_test_conversations(user_id, count=1000)
    
    # Measure deletion time
    start_time = time.time()
    await cleanup_service.delete_user_completely(user_id)
    duration = time.time() - start_time
    
    # Should complete within reasonable time
    assert duration < 30  # seconds
```

### 3. Integration Test Fixes
- Fix `test_conversation_list` timeout by ensuring proper cleanup
- Add verification that test users start with 0 conversations
- Monitor test database size over time

## Consequences

### Positive
- **Data Privacy Compliance**: Proper user data deletion (GDPR compliant)
- **Database Performance**: No more orphaned data causing slowdowns
- **Test Reliability**: Clean test environment, no accumulated data
- **Storage Efficiency**: Significant database size reduction

### Negative
- **Implementation Complexity**: Need careful transaction management
- **Migration Risk**: Existing orphaned data cleanup could be large operation
- **Deletion Speed**: Cascade deletions may be slower than simple user deletion

### Risks
- **Data Loss**: Incorrect implementation could delete wrong data
- **Transaction Failures**: Partial deletions could leave system in inconsistent state
- **Performance Impact**: Large cascade deletions could temporarily slow database

## Timeline
- **Week 1**: Database schema changes and migrations
- **Week 2**: Service implementation and test fixture updates  
- **Week 3**: Production endpoints and comprehensive testing
- **Week 4**: Deploy and monitor, clean up existing orphaned data

## Monitoring
- Track database size before/after implementation
- Monitor user deletion endpoint performance
- Alert on any orphaned data detection
- Test environment database size monitoring

## Related Issues
- Integration test timeout in `test_conversation_list`
- Test environment data accumulation
- Potential production data privacy compliance issues

---
*Created: 2025-08-11*  
*Author: Integration Test Analysis*  
*Status: Proposed - Requires immediate implementation*  
*Priority: CRITICAL - Data privacy and system performance impact*