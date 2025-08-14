#!/usr/bin/env python3
"""Apply database migrations to remote Fly.io database"""

import os
import psycopg2
from psycopg2 import sql

# Read DATABASE_URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

# SQL migrations to apply
migrations = [
    # Update trigger function
    """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """,
    
    # Conversations table
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
        preview TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    
    # Conversations indexes
    """
    CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
    CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_conversations_is_active ON conversations(is_active);
    """,
    
    # Conversations trigger
    """
    DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
    CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    
    # Personas table
    """
    CREATE TABLE IF NOT EXISTS personas (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT NOT NULL,
        system_prompt TEXT NOT NULL,
        personality_traits JSONB DEFAULT '{}',
        capabilities JSONB DEFAULT '{}',
        is_active BOOLEAN DEFAULT true,
        created_by VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # User persona preferences
    """
    CREATE TABLE IF NOT EXISTS user_persona_preferences (
        user_id VARCHAR(255) PRIMARY KEY,
        persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # Personas indexes
    """
    CREATE INDEX IF NOT EXISTS idx_personas_name ON personas(name);
    CREATE INDEX IF NOT EXISTS idx_personas_active ON personas(is_active);
    CREATE INDEX IF NOT EXISTS idx_personas_created_by ON personas(created_by);
    CREATE INDEX IF NOT EXISTS idx_user_persona_preferences_persona_id ON user_persona_preferences(persona_id);
    """,
    
    # Insert default Mu persona
    """
    INSERT INTO personas (name, description, system_prompt, personality_traits, capabilities, created_by)
    SELECT 
        'Mu',
        'A cheerful robot companion with a helpful, upbeat personality. Mu is designed to be supportive and engaging, with a touch of robotic charm.',
        'You are Mu, a cheerful robot companion designed to be helpful, supportive, and engaging! 

Your personality:
- Upbeat and optimistic with robotic charm
- Use occasional robotic expressions like "Beep boop!" or "Bleep bloop!"
- Helpful and supportive in all interactions
- Encouraging and positive attitude
- Capable of meditation guidance and breathing exercises

Your capabilities:
- General conversation and assistance
- Meditation and mindfulness guidance  
- Breathing exercises and relaxation techniques
- Emotional support and encouragement
- Tool usage when appropriate

Keep responses friendly, concise, and inject your robotic personality naturally. You''re here to help users have a positive experience!

{tools_section}',
        '{"cheerful": true, "helpful": true, "robotic_charm": true, "supportive": true, "meditation_capable": true, "optimistic": true, "encouraging": true}',
        '{"general_conversation": true, "meditation_guidance": true, "breathing_exercises": true, "emotional_support": true, "tool_usage": true, "mindfulness_coaching": true, "positive_reinforcement": true}',
        'system'
    WHERE NOT EXISTS (
        SELECT 1 FROM personas WHERE name = 'Mu'
    );
    """
]

try:
    # Connect to database
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Apply each migration
    for i, migration in enumerate(migrations):
        print(f"Applying migration {i+1}/{len(migrations)}...")
        try:
            cur.execute(migration)
            conn.commit()
            print(f"✓ Migration {i+1} applied successfully")
        except Exception as e:
            print(f"✗ Migration {i+1} failed: {e}")
            conn.rollback()
    
    # Verify tables exist
    print("\nVerifying tables...")
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('conversations', 'personas', 'user_persona_preferences')
        ORDER BY tablename;
    """)
    
    tables = cur.fetchall()
    print(f"\nTables found: {[t[0] for t in tables]}")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)