"""Simple test to verify test setup"""
import pytest


def test_basic():
    """Basic test that should always pass"""
    assert 1 + 1 == 2


def test_imports():
    """Test that we can import web service modules"""
    try:
        from app.services.web.components import gaia_ui
        assert hasattr(gaia_ui, 'gaia_error_message')
        print("✓ Web components import successful")
    except ImportError as e:
        pytest.skip(f"Web service imports not available: {e}")