#!/usr/bin/env python3
"""
KB Storage Performance Test

Compares performance between Git, Database, and Hybrid storage modes.
Tests various operations including:
- Document creation
- Document reading
- Search operations
- Bulk operations
- Concurrent operations
"""

import asyncio
import time
import statistics
import json
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.kb.kb_storage_manager import KBStorageManager, StorageMode
from app.services.kb.kb_database_storage import kb_db_storage
from app.services.kb.kb_hybrid_storage import kb_hybrid_storage
from app.shared.config import settings

class KBPerformanceTest:
    """Performance test suite for KB storage backends"""
    
    def __init__(self):
        self.test_documents = self._generate_test_documents()
        self.results = {}
    
    def _generate_test_documents(self, count: int = 50) -> list:
        """Generate test documents for benchmarking"""
        documents = []
        
        for i in range(count):
            documents.append({
                "path": f"test/perf/document_{i:03d}.md",
                "content": f"""# Test Document {i}

This is a test document for performance benchmarking.

## Content

{"Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10}

## Keywords

#test #performance #document-{i} #benchmark

## Links

[[test/perf/document_{(i+1) % count:03d}]]
[[test/perf/document_{(i-1) % count:03d}]]

## Timestamp

Created at: {time.time()}
Document ID: {i}
""",
                "metadata": {
                    "title": f"Test Document {i}",
                    "tags": ["test", "performance", f"document-{i}"],
                    "created_by": "performance_test",
                    "document_id": i
                }
            })
        
        return documents
    
    async def test_storage_mode(self, storage_mode: StorageMode) -> dict:
        """Test a specific storage mode"""
        print(f"\n🧪 Testing {storage_mode.value.upper()} storage mode...")
        
        # Set environment variable for the test
        os.environ['KB_STORAGE_MODE'] = storage_mode.value
        
        # Create new storage manager with the mode
        storage = KBStorageManager()
        await storage.initialize()
        
        results = {
            "storage_mode": storage_mode.value,
            "tests": {}
        }
        
        try:
            # Test 1: Document Creation
            print(f"  📝 Testing document creation...")
            create_times = await self._test_document_creation(storage)
            results["tests"]["create"] = {
                "mean_ms": statistics.mean(create_times),
                "median_ms": statistics.median(create_times),
                "min_ms": min(create_times),
                "max_ms": max(create_times),
                "operations": len(create_times)
            }
            
            # Test 2: Document Reading
            print(f"  📖 Testing document reading...")
            read_times = await self._test_document_reading(storage)
            results["tests"]["read"] = {
                "mean_ms": statistics.mean(read_times),
                "median_ms": statistics.median(read_times),
                "min_ms": min(read_times),
                "max_ms": max(read_times),
                "operations": len(read_times)
            }
            
            # Test 3: Search Operations
            print(f"  🔍 Testing search operations...")
            search_times = await self._test_search_operations(storage)
            results["tests"]["search"] = {
                "mean_ms": statistics.mean(search_times),
                "median_ms": statistics.median(search_times),
                "min_ms": min(search_times),
                "max_ms": max(search_times),
                "operations": len(search_times)
            }
            
            # Test 4: Bulk Operations
            print(f"  📦 Testing bulk operations...")
            bulk_time = await self._test_bulk_operations(storage)
            results["tests"]["bulk"] = {
                "total_time_ms": bulk_time,
                "operations": 10  # 10 bulk operations
            }
            
            # Test 5: Concurrent Operations
            print(f"  🔄 Testing concurrent operations...")
            concurrent_time = await self._test_concurrent_operations(storage)
            results["tests"]["concurrent"] = {
                "total_time_ms": concurrent_time,
                "operations": 20  # 20 concurrent operations
            }
            
            # Cleanup test documents
            await self._cleanup_test_documents(storage)
            
        except Exception as e:
            print(f"  ❌ Error testing {storage_mode.value}: {e}")
            results["error"] = str(e)
        
        finally:
            if hasattr(storage, 'shutdown'):
                await storage.shutdown()
        
        return results
    
    async def _test_document_creation(self, storage: KBStorageManager) -> list:
        """Test document creation performance"""
        times = []
        
        for doc in self.test_documents[:20]:  # Test with 20 documents
            start_time = time.perf_counter()
            
            result = await storage.save_document(
                path=doc["path"],
                content=doc["content"],
                metadata=doc["metadata"],
                user_id="perf_test"
            )
            
            end_time = time.perf_counter()
            
            if result.get("success"):
                times.append((end_time - start_time) * 1000)  # Convert to ms
            else:
                print(f"    ⚠️ Failed to create {doc['path']}: {result.get('message', 'Unknown error')}")
        
        return times
    
    async def _test_document_reading(self, storage: KBStorageManager) -> list:
        """Test document reading performance"""
        times = []
        
        # Read the first 20 test documents
        for doc in self.test_documents[:20]:
            start_time = time.perf_counter()
            
            result = await storage.get_document(doc["path"])
            
            end_time = time.perf_counter()
            
            if result:
                times.append((end_time - start_time) * 1000)  # Convert to ms
            else:
                print(f"    ⚠️ Failed to read {doc['path']}")
        
        return times
    
    async def _test_search_operations(self, storage: KBStorageManager) -> list:
        """Test search performance"""
        times = []
        
        search_queries = [
            "test document",
            "performance",
            "Lorem ipsum",
            "#test",
            "#performance", 
            "document_001",
            "benchmark",
            "created at",
            "dolor sit amet",
            "consectetur"
        ]
        
        for query in search_queries:
            start_time = time.perf_counter()
            
            result = await storage.search_documents(
                query=query,
                limit=10
            )
            
            end_time = time.perf_counter()
            
            if result.get("success"):
                times.append((end_time - start_time) * 1000)  # Convert to ms
            else:
                print(f"    ⚠️ Search failed for '{query}': {result.get('message', 'Unknown error')}")
        
        return times
    
    async def _test_bulk_operations(self, storage: KBStorageManager) -> float:
        """Test bulk operations performance"""
        start_time = time.perf_counter()
        
        # Create multiple documents in sequence
        for doc in self.test_documents[20:30]:  # Use documents 20-29
            await storage.save_document(
                path=doc["path"],
                content=doc["content"],
                metadata=doc["metadata"],
                user_id="bulk_test"
            )
        
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000  # Convert to ms
    
    async def _test_concurrent_operations(self, storage: KBStorageManager) -> float:
        """Test concurrent operations performance"""
        start_time = time.perf_counter()
        
        # Create tasks for concurrent operations
        tasks = []
        for doc in self.test_documents[30:50]:  # Use documents 30-49
            task = storage.save_document(
                path=doc["path"],
                content=doc["content"],
                metadata=doc["metadata"],
                user_id="concurrent_test"
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        
        # Check for failures
        failures = [r for r in results if isinstance(r, Exception) or not getattr(r, 'get', lambda x: True)('success')]
        if failures:
            print(f"    ⚠️ {len(failures)} concurrent operations failed")
        
        return (end_time - start_time) * 1000  # Convert to ms
    
    async def _cleanup_test_documents(self, storage: KBStorageManager):
        """Clean up test documents"""
        print(f"  🧹 Cleaning up test documents...")
        
        for doc in self.test_documents:
            try:
                await storage.delete_document(
                    path=doc["path"],
                    user_id="cleanup_test"
                )
            except Exception as e:
                # Ignore cleanup errors
                pass
    
    async def run_all_tests(self) -> dict:
        """Run performance tests for all storage modes"""
        print("🚀 Starting KB Storage Performance Tests")
        print("=" * 50)
        
        all_results = {
            "test_config": {
                "document_count": len(self.test_documents),
                "test_timestamp": time.time(),
                "kb_path": settings.KB_PATH
            },
            "results": {}
        }
        
        # Test each storage mode
        for mode in StorageMode:
            try:
                results = await self.test_storage_mode(mode)
                all_results["results"][mode.value] = results
            except Exception as e:
                print(f"❌ Failed to test {mode.value}: {e}")
                all_results["results"][mode.value] = {
                    "storage_mode": mode.value,
                    "error": str(e)
                }
        
        return all_results
    
    def print_results_summary(self, results: dict):
        """Print a summary of test results"""
        print("\n📊 Performance Test Results Summary")
        print("=" * 50)
        
        for mode, result in results["results"].items():
            if "error" in result:
                print(f"\n❌ {mode.upper()}: {result['error']}")
                continue
                
            print(f"\n✅ {mode.upper()} Storage:")
            tests = result.get("tests", {})
            
            for test_name, test_data in tests.items():
                if test_name in ["create", "read", "search"]:
                    print(f"  {test_name.title()}: {test_data['mean_ms']:.2f}ms avg, {test_data['median_ms']:.2f}ms median")
                elif test_name == "bulk":
                    print(f"  Bulk: {test_data['total_time_ms']:.2f}ms total ({test_data['operations']} ops)")
                elif test_name == "concurrent":
                    print(f"  Concurrent: {test_data['total_time_ms']:.2f}ms total ({test_data['operations']} ops)")
        
        # Performance comparison
        print(f"\n🏆 Performance Comparison:")
        create_times = {}
        read_times = {}
        search_times = {}
        
        for mode, result in results["results"].items():
            if "tests" in result:
                tests = result["tests"]
                if "create" in tests:
                    create_times[mode] = tests["create"]["mean_ms"]
                if "read" in tests:
                    read_times[mode] = tests["read"]["mean_ms"]
                if "search" in tests:
                    search_times[mode] = tests["search"]["mean_ms"]
        
        if create_times:
            fastest_create = min(create_times, key=create_times.get)
            print(f"  Fastest Create: {fastest_create} ({create_times[fastest_create]:.2f}ms)")
        
        if read_times:
            fastest_read = min(read_times, key=read_times.get)
            print(f"  Fastest Read: {fastest_read} ({read_times[fastest_read]:.2f}ms)")
        
        if search_times:
            fastest_search = min(search_times, key=search_times.get)
            print(f"  Fastest Search: {fastest_search} ({search_times[fastest_search]:.2f}ms)")

async def main():
    """Main test runner"""
    test = KBPerformanceTest()
    
    try:
        results = await test.run_all_tests()
        
        # Print summary
        test.print_results_summary(results)
        
        # Save detailed results to file
        results_file = project_root / "kb_performance_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())