-- Add conversations table for organizing chat messages
-- Migration: 002_add_conversations_table.sql

BEGIN;

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    preview TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_is_active ON conversations(is_active);

-- Add updated_at trigger for conversations
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add foreign key constraint to existing chat_messages table for conversation_id
-- Note: The conversation_id column already exists, we just need to make it a proper foreign key
DO $$
BEGIN
    -- Check if foreign key constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_chat_messages_conversation_id' 
        AND table_name = 'chat_messages'
    ) THEN
        -- Add foreign key constraint
        ALTER TABLE chat_messages 
        ADD CONSTRAINT fk_chat_messages_conversation_id 
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
    END IF;
END$$;

-- Add index for conversation_id in chat_messages if it doesn't exist
-- (it should already exist from the original schema, but let's be safe)
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);

COMMIT;

-- Verification
SELECT 'Conversations table migration completed successfully' as status;
SELECT 'Conversations table:' as info, COUNT(*) as count FROM conversations;