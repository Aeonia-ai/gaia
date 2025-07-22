#!/usr/bin/env python3
"""
Migrate API keys from PostgreSQL to Supabase.
This script copies all existing API keys to the centralized Supabase storage.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIKeyMigrator:
    """Migrates API keys from PostgreSQL to Supabase."""
    
    def __init__(self):
        """Initialize database connections."""
        # PostgreSQL connection
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not set")
        
        self.pg_engine = create_engine(database_url)
        
        # Supabase connection
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)
        logger.info("Initialized database connections")
    
    def get_postgres_api_keys(self) -> List[Dict[str, Any]]:
        """Fetch all API keys from PostgreSQL."""
        query = """
        SELECT 
            ak.id,
            ak.user_id,
            ak.key_hash,
            ak.name,
            ak.permissions,
            ak.is_active,
            ak.expires_at,
            ak.last_used_at,
            ak.created_at,
            ak.updated_at,
            u.email as user_email
        FROM api_keys ak
        JOIN users u ON ak.user_id = u.id
        ORDER BY ak.created_at DESC
        """
        
        with self.pg_engine.connect() as conn:
            result = conn.execute(text(query))
            keys = []
            for row in result:
                keys.append({
                    'id': str(row.id),
                    'user_id': str(row.user_id),
                    'key_hash': row.key_hash,
                    'name': row.name,
                    'permissions': row.permissions or {},
                    'is_active': row.is_active,
                    'expires_at': row.expires_at.isoformat() if row.expires_at else None,
                    'last_used_at': row.last_used_at.isoformat() if row.last_used_at else None,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                    'user_email': row.user_email
                })
            
            logger.info(f"Found {len(keys)} API keys in PostgreSQL")
            return keys
    
    def ensure_supabase_user(self, email: str, postgres_user_id: str) -> str:
        """Ensure user exists in Supabase and return their ID."""
        try:
            # Check if user exists
            response = self.supabase.auth.admin.list_users()
            
            for user in response:
                if user.email == email:
                    logger.info(f"User {email} already exists in Supabase")
                    return user.id
            
            # Create user if not exists (with random password, they can reset it)
            import secrets
            temp_password = secrets.token_urlsafe(16)
            
            response = self.supabase.auth.admin.create_user({
                'email': email,
                'password': temp_password,
                'email_confirm': True,  # Auto-confirm for migration
                'user_metadata': {
                    'postgres_user_id': postgres_user_id,
                    'migrated_at': datetime.utcnow().isoformat()
                }
            })
            
            logger.info(f"Created user {email} in Supabase")
            return response.user.id
            
        except Exception as e:
            logger.error(f"Error ensuring user {email}: {str(e)}")
            raise
    
    def migrate_api_key(self, key_data: Dict[str, Any]) -> bool:
        """Migrate a single API key to Supabase."""
        try:
            # Ensure user exists in Supabase
            supabase_user_id = self.ensure_supabase_user(
                key_data['user_email'],
                key_data['user_id']
            )
            
            # Prepare data for Supabase
            api_key_data = {
                'user_id': supabase_user_id,
                'key_hash': key_data['key_hash'],
                'name': key_data['name'] or f"Migrated key for {key_data['user_email']}",
                'permissions': key_data['permissions'],
                'is_active': key_data['is_active'],
                'expires_at': key_data['expires_at'],
                'last_used_at': key_data['last_used_at'],
                'created_at': key_data['created_at'],
                'updated_at': key_data['updated_at']
            }
            
            # Insert into Supabase (upsert to handle duplicates)
            response = self.supabase.table('api_keys').upsert(
                api_key_data,
                on_conflict='key_hash'
            ).execute()
            
            if response.data:
                logger.info(f"Migrated API key '{key_data['name']}' for {key_data['user_email']}")
                return True
            else:
                logger.error(f"Failed to migrate API key for {key_data['user_email']}")
                return False
                
        except Exception as e:
            logger.error(f"Error migrating API key for {key_data['user_email']}: {str(e)}")
            return False
    
    def run_migration(self, dry_run: bool = False):
        """Run the migration process."""
        logger.info(f"Starting API key migration (dry_run={dry_run})")
        
        # Get all PostgreSQL API keys
        postgres_keys = self.get_postgres_api_keys()
        
        if not postgres_keys:
            logger.info("No API keys found to migrate")
            return
        
        # Summary
        logger.info(f"\nMigration Summary:")
        logger.info(f"- Total API keys to migrate: {len(postgres_keys)}")
        logger.info(f"- Unique users: {len(set(k['user_email'] for k in postgres_keys))}")
        
        if dry_run:
            logger.info("\nDRY RUN - No changes will be made")
            for key in postgres_keys:
                logger.info(f"Would migrate: {key['name']} for {key['user_email']}")
            return
        
        # Confirm migration
        print(f"\nAbout to migrate {len(postgres_keys)} API keys to Supabase.")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Migration cancelled")
            return
        
        # Migrate each key
        success_count = 0
        for key in postgres_keys:
            if self.migrate_api_key(key):
                success_count += 1
        
        logger.info(f"\nMigration complete: {success_count}/{len(postgres_keys)} keys migrated successfully")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate API keys to Supabase')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    args = parser.parse_args()
    
    try:
        migrator = APIKeyMigrator()
        migrator.run_migration(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()