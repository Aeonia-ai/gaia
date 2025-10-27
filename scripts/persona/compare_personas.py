#!/usr/bin/env python3
"""
Quick script to compare Mu and Louisa persona prompts
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def compare_personas():
    # Get database URL
    raw_db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_platform")
    db_url = raw_db_url.replace("postgres://", "postgresql://", 1) if raw_db_url.startswith("postgres://") else raw_db_url

    # Connect and query
    conn = await asyncpg.connect(db_url)

    try:
        rows = await conn.fetch("""
            SELECT name, system_prompt, personality_traits
            FROM personas
            WHERE name IN ('Mu', 'Louisa')
            ORDER BY name
        """)

        for row in rows:
            print(f"\n{'='*80}")
            print(f"PERSONA: {row['name']}")
            print(f"{'='*80}")
            print(f"\nSYSTEM PROMPT:")
            print(row['system_prompt'])
            print(f"\nPERSONALITY TRAITS:")
            print(row['personality_traits'])
            print()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(compare_personas())
