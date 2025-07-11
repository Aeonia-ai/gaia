-- Persona management database tables
-- Run this script to create the necessary tables for persona functionality

-- Create personas table
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

-- Create user persona preferences table
CREATE TABLE IF NOT EXISTS user_persona_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_personas_name ON personas(name);
CREATE INDEX IF NOT EXISTS idx_personas_active ON personas(is_active);
CREATE INDEX IF NOT EXISTS idx_personas_created_by ON personas(created_by);
CREATE INDEX IF NOT EXISTS idx_user_persona_preferences_persona_id ON user_persona_preferences(persona_id);

-- Insert default "Mu" persona if it doesn't exist
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

-- Verify tables were created
SELECT 'personas table created' as status, count(*) as persona_count FROM personas;
SELECT 'user_persona_preferences table created' as status, count(*) as preference_count FROM user_persona_preferences;