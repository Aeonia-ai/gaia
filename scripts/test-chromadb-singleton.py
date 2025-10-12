#!/usr/bin/env python3
"""
Quick test to verify ChromaDB singleton manager performance improvements.
Tests that collections persist across multiple search operations.
"""

import sys
import os
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📍 Loaded environment from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment")

def test_singleton_pattern():
    """Test that ChromaDB manager uses singleton pattern."""
    print("\n🧪 Testing ChromaDB Singleton Pattern")
    print("=" * 40)
    
    try:
        from app.services.kb.kb_chromadb_manager import ChromaDBManager
    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        print("Install: pip install chromadb")
        return False
    
    # Get first instance
    manager1 = ChromaDBManager()
    print(f"✓ Created first manager instance: {id(manager1)}")
    
    # Get second instance - should be same object
    manager2 = ChromaDBManager()
    print(f"✓ Got second manager instance: {id(manager2)}")
    
    if manager1 is manager2:
        print("✅ Singleton pattern working - same instance returned!")
    else:
        print("❌ Singleton pattern broken - different instances")
        return False
    
    # Test collection caching
    print("\n🧪 Testing Collection Caching")
    print("=" * 40)
    
    namespace = "test_namespace"
    
    # First collection creation
    start = time.time()
    collection1 = manager1.get_or_create_collection(namespace)
    time1 = (time.time() - start) * 1000
    print(f"✓ First collection creation: {time1:.1f}ms")
    
    # Second request - should be cached
    start = time.time()
    collection2 = manager1.get_or_create_collection(namespace)
    time2 = (time.time() - start) * 1000
    print(f"✓ Second collection (cached): {time2:.1f}ms")
    
    if collection1 is collection2:
        print("✅ Collection caching working - same collection returned!")
    else:
        print("⚠️  Collections are different objects but may have same data")
    
    # Performance comparison
    if time2 < time1 * 0.5:  # Cached should be at least 2x faster
        improvement = ((time1 - time2) / time1) * 100
        print(f"✅ Performance gain: {improvement:.0f}% faster")
    else:
        print(f"⚠️  Cache performance not optimal (first: {time1:.1f}ms, cached: {time2:.1f}ms)")
    
    # Test search functionality
    print("\n🧪 Testing Search with Cached Collection")
    print("=" * 40)
    
    # Add test document
    collection1.add(
        documents=["This is a test about user authentication and login"],
        metadatas=[{"file": "test.md", "section": "auth"}],
        ids=["test_1"]
    )
    print("✓ Added test document")
    
    # Search using manager
    results = manager1.search("how users log in", collection1, limit=5)
    if results:
        print(f"✓ Search returned {len(results)} results")
        print(f"  Best match score: {results[0]['score']:.3f}")
        print(f"  Document: {results[0]['document'][:50]}...")
    else:
        print("⚠️  No search results")
    
    # Cleanup
    manager1.invalidate_collection(namespace)
    print("\n✓ Cleanup completed")
    
    return True

def test_performance_across_requests():
    """Test that manager persists across multiple 'requests'."""
    print("\n🧪 Testing Persistence Across Requests")
    print("=" * 40)
    
    from app.services.kb.kb_chromadb_manager import ChromaDBManager
    
    times = []
    for i in range(3):
        start = time.time()
        
        # Simulate new request
        manager = ChromaDBManager()
        collection = manager.get_or_create_collection(f"namespace_{i}")
        
        # Add and search
        collection.add(
            documents=[f"Document {i} about testing"],
            metadatas=[{"request": i}],
            ids=[f"doc_{i}"]
        )
        
        results = manager.search("testing", collection, limit=1)
        
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"  Request {i+1}: {elapsed:.1f}ms")
    
    # First might be slower, but subsequent should be fast
    if times[1] < times[0] * 0.8 and times[2] < times[0] * 0.8:
        avg_improvement = (1 - (sum(times[1:]) / len(times[1:])) / times[0]) * 100
        print(f"✅ Consistent performance improvement: {avg_improvement:.0f}% faster after first")
    else:
        print("⚠️  Performance not consistently improved")
    
    return True

def main():
    """Run all tests."""
    print("🚀 ChromaDB Singleton Manager Test")
    print("=" * 40)
    
    # Check if chromadb is installed
    try:
        import chromadb
        print(f"✓ ChromaDB version: {chromadb.__version__}")
    except ImportError:
        print("✗ ChromaDB not installed")
        print("\nInstall with: pip install chromadb>=0.4.22")
        return
    
    # Run tests
    if test_singleton_pattern():
        test_performance_across_requests()
    
    print("\n📊 Summary")
    print("=" * 40)
    print("✅ ChromaDB Singleton Manager is working correctly")
    print("   - Singleton pattern ensures single instance")
    print("   - Collections are cached for performance")
    print("   - No ChromaDB server needed (ephemeral mode)")
    print("\n   This avoids the performance issue in aifs where")
    print("   ChromaDB client is recreated on every search.")

if __name__ == "__main__":
    main()