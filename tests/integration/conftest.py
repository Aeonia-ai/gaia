"""
Pytest configuration for integration tests.
"""
import pytest
import sys
import os

# Add project root to path so we can import test fixtures
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared test user fixture
from fixtures.shared_test_user import shared_test_user, test_user_credentials

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", 
        "sequential: mark test to run sequentially (not in parallel)"
    )
    config.addinivalue_line(
        "markers",
        "llm_intensive: mark test that makes heavy LLM API calls"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle sequential tests."""
    # Check if we're running with xdist (parallel execution)
    if hasattr(config, 'workerinput'):
        # We're in a worker process
        worker_id = config.workerinput['workerid']
        
        # Only run sequential tests on the first worker
        if worker_id != 'gw0':
            skip_sequential = pytest.mark.skip(reason="Sequential test - only runs on gw0")
            for item in items:
                if 'sequential' in item.keywords:
                    item.add_marker(skip_sequential)