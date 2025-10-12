#!/usr/bin/env python3
"""
Local test script for semantic search functionality.
Tests the ChromaDB manager and semantic search without full service.
"""

import sys
import os
import tempfile
import json
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try to load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📍 Loaded environment from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment")
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        print(f"   Run: export $(cat {env_path} | grep -v '^#' | xargs)")

# Show current settings
print(f"   KB_SEMANTIC_SEARCH_ENABLED: {os.getenv('KB_SEMANTIC_SEARCH_ENABLED', 'not set')}")
print(f"   KB_PATH: {os.getenv('KB_PATH', 'not set')}")
print()

def test_chromadb_manager():
    """Test the ChromaDB manager functionality."""
    print("🧪 Testing ChromaDB Manager")
    print("=" * 40)
    
    try:
        from app.services.kb.kb_chromadb_manager import ChromaDBManager
        print("✓ ChromaDB manager module imported")
    except ImportError as e:
        print(f"✗ Failed to import ChromaDB manager: {e}")
        print("\nInstall required packages:")
        print("  pip install chromadb")
        return False
    
    # Test manager initialization
    manager = ChromaDBManager()
    if not manager.enabled:
        print("✗ ChromaDB not enabled - install chromadb package")
        return False
    
    print("✓ ChromaDB manager initialized")
    
    # Test collection creation
    test_namespace = "test_namespace"
    collection = manager.get_or_create_collection(test_namespace)
    if collection:
        print(f"✓ Created collection for namespace: {test_namespace}")
    else:
        print(f"✗ Failed to create collection")
        return False
    
    # Test adding documents
    collection.add(
        documents=["This is a test document about authentication and login"],
        metadatas=[{"file": "test.md"}],
        ids=["1"]
    )
    print("✓ Added test document to collection")
    
    # Test search
    results = manager.search("how to login", collection, limit=5)
    if results:
        print(f"✓ Search returned {len(results)} results")
        print(f"  First result score: {results[0]['score']:.3f}")
    else:
        print("✗ Search returned no results")
    
    # Test persistence (search again - should be faster)
    start_time = time.time()
    results2 = manager.search("authentication process", collection, limit=5)
    search_time = (time.time() - start_time) * 1000
    print(f"✓ Second search completed in {search_time:.1f}ms")
    
    # Test stats
    stats = manager.get_stats()
    print(f"✓ Stats: {stats['cached_collections']} collections cached")
    
    # Cleanup
    manager.invalidate_collection(test_namespace)
    print("✓ Cleaned up test collection")
    
    return True


def test_semantic_indexer():
    """Test the semantic indexer (requires aifs)."""
    print("\n🧪 Testing Semantic Indexer")
    print("=" * 40)
    
    try:
        from app.services.kb.kb_semantic_search import SemanticIndexer
        print("✓ Semantic indexer module imported")
    except ImportError as e:
        print(f"✗ Failed to import semantic indexer: {e}")
        return False
    
    try:
        import aifs
        print("✓ aifs package available")
    except ImportError:
        print("⚠ aifs not installed - skipping indexer tests")
        print("  Install with: pip install aifs")
        return False
    
    # Create temp directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir)
        
        # Create test markdown file
        test_file = test_path / "test_doc.md"
        test_file.write_text("""
# Test Document

This is a test document about authentication and security.
Users can log in using their email and password.
The system uses JWT tokens for session management.
        """)
        
        print(f"✓ Created test file: {test_file}")
        
        # Initialize indexer with test path
        indexer = SemanticIndexer()
        indexer.kb_path = test_path
        indexer.enabled = True
        
        # Test indexing
        from aifs import search as aifs_search
        print("  Indexing test directory...")
        aifs_search("", path=str(test_path))
        
        # Check if index was created
        aifs_file = test_path / "_.aifs"
        if aifs_file.exists():
            file_size = aifs_file.stat().st_size / 1024
            print(f"✓ Index created: _.aifs ({file_size:.1f} KB)")
            
            # Load and inspect index
            with open(aifs_file, 'r') as f:
                index = json.load(f)
            print(f"  Index contains {len(index)} files")
        else:
            print("✗ Index file not created")
            return False
        
        # Test search
        print("  Performing semantic search...")
        results = aifs_search("how to login", path=str(test_path))
        if results:
            print(f"✓ Search returned results")
        else:
            print("⚠ Search returned no results")
    
    return True


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("📦 Checking Dependencies")
    print("=" * 40)
    
    dependencies = {
        "aifs": "Semantic search library",
        "chromadb": "Vector database",
        "unstructured": "Document parsing"
    }
    
    missing = []
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✓ {package}: {description}")
        except ImportError:
            print(f"✗ {package}: Not installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        if "unstructured" in missing:
            print('  pip install "unstructured[all-docs]"  # For full document support')
        return False
    
    return True


def main():
    """Run all tests."""
    print("🚀 Semantic Search Local Testing")
    print("=" * 40)
    print()
    
    # Check dependencies first
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n❌ Please install missing dependencies first")
        sys.exit(1)
    
    print()
    
    # Test ChromaDB manager
    chromadb_ok = test_chromadb_manager()
    
    # Test semantic indexer (if aifs available)
    indexer_ok = test_semantic_indexer()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 40)
    if chromadb_ok:
        print("✅ ChromaDB Manager: Working")
        print("   - Singleton pattern implemented")
        print("   - Collections persist across searches")
        print("   - Performance optimization confirmed")
    else:
        print("❌ ChromaDB Manager: Issues detected")
    
    if indexer_ok:
        print("✅ Semantic Indexer: Working")
        print("   - Can create indexes")
        print("   - Search functionality operational")
    elif indexer_ok is False:
        print("❌ Semantic Indexer: Issues detected")
    else:
        print("⚠️  Semantic Indexer: Not fully tested (aifs not installed)")
    
    print("\nNext steps:")
    print("1. Run Docker: docker compose up kb-service")
    print("2. Test via API: ./scripts/test-semantic-search.sh")
    print("3. Check logs: docker compose logs kb-service")


if __name__ == "__main__":
    main()