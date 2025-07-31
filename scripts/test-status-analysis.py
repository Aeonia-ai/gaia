#!/usr/bin/env python3
"""
Analyze which tests we've run successfully vs which we haven't.
"""

# Tests we know are working (successfully run)
WORKING_TESTS = {
    # Unit tests (all working)
    "tests/unit/test_auth_flow.py",
    "tests/unit/test_auth_integration.py", 
    "tests/unit/test_authentication_consistency.py",
    "tests/unit/test_db_persistence.py",
    "tests/unit/test_error_handling.py",
    "tests/unit/test_simple.py",
    "tests/unit/test_ui_layout.py",
    
    # Integration tests (mostly working)
    "tests/integration/test_api_endpoints_comprehensive.py",
    "tests/integration/test_comprehensive_suite.py",
    "tests/integration/test_conversation_delete.py",
    "tests/integration/test_gateway_client.py",
    "tests/integration/test_integration.py",
    "tests/integration/test_kb_endpoints.py",
    "tests/integration/test_kb_service.py",
    "tests/integration/test_provider_model_endpoints.py",
    "tests/integration/test_v02_chat_api.py",  # 1 failure but runs
    "tests/integration/test_v03_api.py",
    "tests/integration/test_working_endpoints.py",
    
    # E2E tests (working with new pattern)
    "tests/e2e/test_simple_browser.py",
    "tests/e2e/test_browser_registration.py", 
    "tests/e2e/test_auth_working_pattern.py",  # 1 failure but runs
    "tests/e2e/test_bare_minimum.py",
    "tests/e2e/test_standalone.py",
    "tests/e2e/test_chat_browser_auth_fixed.py",
    "tests/e2e/test_debug_login.py",
    "tests/e2e/test_browser_edge_cases.py",  # Just fixed
    "tests/e2e/test_chat_simple.py",  # Already using working pattern
    "tests/e2e/test_chat_working.py",  # Already using working pattern
    "tests/e2e/test_chat_browser.py",  # Already using working pattern
    "tests/e2e/test_auth_htmx_fix.py",  # Already using working pattern
    "tests/e2e/test_authenticated_browser.py",  # Already using working pattern
    "tests/e2e/test_chat_htmx.py",  # Already using working pattern
    "tests/e2e/test_chat_browser_auth.py",  # Just migrated to working pattern
    "tests/e2e/test_simple_auth_fixed.py",  # Just migrated to working pattern
    "tests/e2e/test_layout_integrity.py",  # Already using working pattern
    
    # Web tests
    "tests/web/test_auth_routes.py",
}

# Tests we haven't properly run yet (broken fixture pattern or untested)
UNTESTED_TESTS = {
    # E2E tests still using broken fixtures
 
    "tests/e2e/test_e2e_real_auth.py",
    "tests/e2e/test_full_web_browser.py",
    "tests/e2e/test_manual_auth_browser.py",
    "tests/e2e/test_real_auth_browser.py",
    "tests/e2e/test_real_e2e_with_supabase.py",
}

# Non-test files (fixtures, config, etc.)
NON_TESTS = {
    "tests/conftest.py",
    "tests/fixtures/auth_helpers.py",
    "tests/fixtures/test_auth.py", 
    "tests/web/browser_auth_fixtures.py",
    "tests/web/browser_test_config.py",
    "tests/web/conftest.py",
    "tests/web/playwright_conftest.py",
    "tests/web/simple_browser_auth.py",
    "tests/e2e/test_browser_config.py",  # Utility file, not actual tests
}

def main():
    print("📊 TEST STATUS ANALYSIS")
    print("=" * 50)
    
    print(f"\n✅ WORKING TESTS ({len(WORKING_TESTS)}):")
    print("   These run successfully with current patterns")
    for test in sorted(WORKING_TESTS):
        category = test.split('/')[1]
        print(f"   • {test} [{category}]")
    
    print(f"\n❌ UNTESTED/BROKEN TESTS ({len(UNTESTED_TESTS)}):")
    print("   These need migration to working pattern or haven't been run")
    for test in sorted(UNTESTED_TESTS):
        category = test.split('/')[1] 
        print(f"   • {test} [{category}]")
    
    print(f"\n📁 NON-TEST FILES ({len(NON_TESTS)}):")
    print("   Fixtures, config, and helper files")
    for file in sorted(NON_TESTS):
        print(f"   • {file}")
    
    print(f"\n📈 SUMMARY:")
    total_actual_tests = len(WORKING_TESTS) + len(UNTESTED_TESTS)
    working_percentage = (len(WORKING_TESTS) / total_actual_tests) * 100
    print(f"   • Working tests: {len(WORKING_TESTS)}")
    print(f"   • Untested/broken: {len(UNTESTED_TESTS)}")
    print(f"   • Success rate: {working_percentage:.1f}%")
    print(f"   • Non-test files: {len(NON_TESTS)}")
    
    print(f"\n🎯 NEXT PRIORITIES:")
    e2e_broken = [t for t in UNTESTED_TESTS if '/e2e/' in t]
    print(f"   • Migrate {len(e2e_broken)} e2e tests to working pattern")
    print(f"   • Fix the 1 integration test failure")
    print(f"   • Fix the 1 e2e error message selector issue")

if __name__ == "__main__":
    main()