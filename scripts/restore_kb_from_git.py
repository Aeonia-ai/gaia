#!/usr/bin/env python3
"""
KB Git Restore Script

Manually triggers the restore_from_git functionality to populate
the KB database from the Git repository files.

This solves the Unity integration issue where KB content exists in Git
but isn't indexed in the database layer that the chat service accesses.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to sys.path to import KB modules
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

async def restore_kb_from_git():
    """Restore KB database from Git repository"""
    try:
        print("🔄 Starting KB restore from Git...")

        # Import KB hybrid storage
        from services.kb.kb_hybrid_storage import kb_hybrid_storage

        # Initialize the storage backend
        await kb_hybrid_storage.initialize()
        print("✅ KB hybrid storage initialized")

        # Trigger restore from Git
        result = await kb_hybrid_storage.restore_from_git()

        if result["success"]:
            stats = result["stats"]
            print(f"✅ KB restore completed successfully!")
            print(f"📊 Import stats:")
            print(f"   - Imported: {stats['imported']} documents")
            print(f"   - Skipped: {stats['skipped']} documents")
            print(f"   - Errors: {stats['errors']} documents")

            if stats["imported"] > 0:
                print("\n🎉 KB database is now populated with Git content!")
                print("   Unity should now be able to access KB files via chat API.")
            else:
                print("\n⚠️  No documents were imported. Check the Git repository:")
                print("   - Ensure markdown files exist in /kb")
                print("   - Check file permissions and encoding")
        else:
            print(f"❌ KB restore failed: {result.get('message', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Error during KB restore: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(restore_kb_from_git())
    sys.exit(exit_code)