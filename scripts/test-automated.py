#!/usr/bin/env python3
"""
Automated test runner for Gaia Platform.
Replaces manual test.sh script functionality with pytest-based automation.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_pytest(test_pattern: str, verbose: bool = True, environment: str = "local") -> int:
    """Run pytest with the specified test pattern."""
    cmd = ["docker", "compose", "run", "--rm", "test", "python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Always exclude host_only tests when running in container
    cmd.extend(["-m", "not host_only"])
    
    # Handle test pattern - split if it contains multiple arguments
    if test_pattern:
        if test_pattern.startswith("-k "):
            # Handle -k patterns - need to split properly
            cmd.append("tests/")
            parts = test_pattern.split(" ", 1)  # Split only on first space
            cmd.append(parts[0])  # "-k"
            cmd.append(parts[1])  # The pattern
        else:
            # Handle file/class patterns - split on spaces
            patterns = test_pattern.split()
            cmd.extend(patterns)
    
    # Set environment variables for tests
    env = os.environ.copy()
    env["TEST_ENVIRONMENT"] = environment
    
    print(f"🚀 Running: {' '.join(cmd[4:])}")  # Show the pytest command
    print("")
    
    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Automated Gaia Platform Test Runner")
    parser.add_argument("test_type", nargs="?", default="all", 
                       help="Type of test to run (all, health, chat, kb, providers, comprehensive)")
    parser.add_argument("--environment", default="local", choices=["local", "dev", "staging", "prod"],
                       help="Environment to test against")
    parser.add_argument("--quiet", "-q", action="store_true", help="Run tests in quiet mode")
    
    args = parser.parse_args()
    
    # Map test types to pytest patterns (use -k for multiple patterns)
    test_patterns = {
        "all": "tests/",
        "health": "-k test_gateway_health or test_core_system_health",
        "chat": "tests/test_working_endpoints.py tests/test_api_endpoints_comprehensive.py::TestComprehensiveAPIEndpoints::test_chat_endpoints_functional",
        "chat-basic": "-k test_v02_chat_completion or test_v1_chat_completion",
        "chat-all": "tests/test_v02_chat_api.py tests/test_working_endpoints.py::TestWorkingEndpoints",
        "kb": "tests/test_kb_endpoints.py",
        "kb-health": "tests/test_kb_endpoints.py::TestKBHealthAndStatus",
        "providers": "tests/test_provider_model_endpoints.py",
        "models": "tests/test_provider_model_endpoints.py::TestModelEndpoints",
        "comprehensive": "tests/test_comprehensive_suite.py",
        "auth": "-k TestAuthenticationMethods or TestAPIAuthentication",
        "compatibility": "-k TestAPICompatibility",
        "integration": "tests/integration/",
        "performance": "tests/test_comprehensive_suite.py::TestComprehensiveSuite::test_system_performance_basics",
        "core": "tests/test_working_endpoints.py tests/test_api_endpoints_comprehensive.py",
        "endpoints": "tests/integration/test_working_endpoints.py tests/integration/test_api_endpoints_comprehensive.py tests/integration/test_v02_chat_api.py",
        "status": "-k test_v1_chat_status or test_core_system_health",
        "v03": "tests/test_v03_api.py",
        "v03-chat": "tests/test_v03_api.py::TestV03ChatAPI",
        "v03-auth": "tests/test_v03_api.py::TestV03Authentication"
    }
    
    # Print environment info
    print(f"🌍 Testing Environment: {args.environment}")
    print(f"🔗 Test Type: {args.test_type}")
    print(f"🐳 Running tests in Docker environment")
    print("")
    
    # Get test pattern
    test_pattern = test_patterns.get(args.test_type)
    if not test_pattern and args.test_type != "help":
        print(f"❌ Unknown test type: {args.test_type}")
        print("\nAvailable test types:")
        for test_type in sorted(test_patterns.keys()):
            print(f"  - {test_type}")
        return 1
    
    if args.test_type == "help":
        print("Available test types:")
        print("\n🏥 Health & Status:")
        print("  health       - Core system health checks")
        print("  status       - Service status and chat status")
        print("  kb-health    - Knowledge Base health and repository status")
        
        print("\n💬 Chat & Communication:")
        print("  chat         - All chat functionality tests")
        print("  chat-basic   - Basic v0.2 and v1 chat tests")
        print("  chat-all     - Comprehensive chat endpoint tests")
        
        print("\n🧠 Knowledge Base:")
        print("  kb           - All Knowledge Base tests")
        print("  kb-health    - KB health and repository tests")
        
        print("\n🔧 Providers & Models:")
        print("  providers    - Provider endpoint tests")
        print("  models       - Model endpoint tests")
        
        print("\n🔐 Security & Auth:")
        print("  auth         - Authentication and security tests")
        
        print("\n🔄 Integration & Performance:")
        print("  comprehensive - Full system integration tests")
        print("  integration   - End-to-end integration tests")
        print("  performance   - Basic performance tests")
        print("  compatibility - API compatibility tests")
        
        print("\n📊 Test Suites:")
        print("  all          - Run all automated tests")
        print("  core         - Core working endpoints tests")
        print("  endpoints    - All endpoint tests")
        
        print("\n🆕 API Versions:")
        print("  v03          - New v0.3 clean API tests")
        print("  v03-chat     - v0.3 chat functionality tests")
        print("  v03-auth     - v0.3 authentication tests")
        
        print(f"\n💡 Examples:")
        print(f"  {sys.argv[0]} health")
        print(f"  {sys.argv[0]} chat-basic")
        print(f"  {sys.argv[0]} comprehensive")
        print(f"  {sys.argv[0]} all")
        return 0
    
    # Run the tests
    verbose = not args.quiet
    return run_pytest(test_pattern, verbose, args.environment)


if __name__ == "__main__":
    sys.exit(main())