"""
Conversation Cleanup Fixtures

Provides automatic cleanup of test conversations to prevent database pollution.
"""

import asyncio
import logging
from typing import List, Optional
import pytest_asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logger = logging.getLogger(__name__)

class ConversationCleanupManager:
    """Manages cleanup of test conversations"""

    def __init__(self):
        self.created_conversations: List[str] = []
        self.test_patterns = [
            "test message",
            "investigating creation",
            "duplicate investigation",
            "conversation reload test",
            "test conversation for deletion",
            "hello, this is my first message",
            "this is a message after page reload",
            "and this is my second message"
        ]

    def track_conversation(self, conversation_id: str):
        """Track a conversation for cleanup"""
        if conversation_id not in self.created_conversations:
            self.created_conversations.append(conversation_id)
            logger.info(f"Tracking conversation for cleanup: {conversation_id}")

    def cleanup_all_test_conversations(self) -> int:
        """Clean up all test conversations based on patterns"""
        try:
            # Get database connection details from environment
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'llm_platform')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'postgres')

            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                cursor_factory=RealDictCursor
            )

            with conn.cursor() as cursor:
                # Build WHERE clause for test conversations
                where_conditions = []
                params = []

                for pattern in self.test_patterns:
                    where_conditions.append("title ILIKE %s")
                    params.append(f"%{pattern}%")

                # Also clean up empty conversations
                where_conditions.append("title = %s")
                params.append("")

                where_clause = " OR ".join(where_conditions)

                # First, count what we're about to delete
                count_query = f"SELECT COUNT(*) as count FROM conversations WHERE {where_clause}"
                cursor.execute(count_query, params)
                count_result = cursor.fetchone()
                conversations_to_delete = count_result['count'] if count_result else 0

                if conversations_to_delete > 0:
                    # Delete the conversations
                    delete_query = f"DELETE FROM conversations WHERE {where_clause}"
                    cursor.execute(delete_query, params)
                    conn.commit()

                    logger.info(f"Cleaned up {conversations_to_delete} test conversations")
                else:
                    logger.info("No test conversations found to clean up")

            conn.close()
            return conversations_to_delete

        except Exception as e:
            logger.error(f"Error cleaning up test conversations: {e}")
            return 0

    def cleanup_specific_conversations(self, conversation_ids: List[str]) -> int:
        """Clean up specific conversations by ID"""
        if not conversation_ids:
            return 0

        try:
            # Get database connection details from environment
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'llm_platform')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'postgres')

            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                cursor_factory=RealDictCursor
            )

            with conn.cursor() as cursor:
                # Delete conversations by ID
                placeholders = ','.join(['%s'] * len(conversation_ids))
                delete_query = f"DELETE FROM conversations WHERE id IN ({placeholders})"
                cursor.execute(delete_query, conversation_ids)
                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Cleaned up {deleted_count} specific conversations")

            conn.close()
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up specific conversations: {e}")
            return 0

# Global cleanup manager instance
_cleanup_manager = ConversationCleanupManager()

@pytest_asyncio.fixture(scope="function")
async def conversation_cleanup():
    """Fixture that provides conversation cleanup after each test"""
    # Yield the cleanup manager for the test to use
    yield _cleanup_manager

    # Cleanup after the test
    logger.info("Running conversation cleanup after test...")
    cleaned_count = _cleanup_manager.cleanup_all_test_conversations()

    # Clear tracked conversations for next test
    _cleanup_manager.created_conversations.clear()

    if cleaned_count > 0:
        logger.info(f"✅ Cleaned up {cleaned_count} test conversations")

@pytest_asyncio.fixture(scope="session")
async def conversation_cleanup_session():
    """Fixture that provides conversation cleanup after entire test session"""
    yield

    # Final cleanup after all tests
    logger.info("Running final conversation cleanup after test session...")
    cleaned_count = _cleanup_manager.cleanup_all_test_conversations()

    if cleaned_count > 0:
        logger.info(f"✅ Final cleanup: removed {cleaned_count} test conversations")

def cleanup_test_conversations():
    """Standalone function to clean up test conversations"""
    return _cleanup_manager.cleanup_all_test_conversations()

def track_conversation_for_cleanup(conversation_id: str):
    """Track a conversation for cleanup (for use in diagnostic scripts)"""
    _cleanup_manager.track_conversation(conversation_id)