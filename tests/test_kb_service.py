"""
Knowledge Base Service Tests
Test the KB service functionality including content access, Git sync, and search
"""
import pytest
import requests
import json
import os
from tests.fixtures.test_auth import TestAuthManager

# Test configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")


class TestKBService:
    """Test Knowledge Base service functionality"""
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Authentication headers for API requests"""
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    def test_kb_health_through_gateway(self, headers):
        """Test that KB service is healthy through gateway"""
        response = requests.get(f"{GATEWAY_URL}/health", headers=headers)
        assert response.status_code == 200
        
        health_data = response.json()
        assert "services" in health_data
        assert "kb" in health_data["services"]
        
        kb_health = health_data["services"]["kb"]
        assert kb_health["status"] == "healthy"
        assert "response_time" in kb_health
        assert isinstance(kb_health["response_time"], (int, float))
    
    def test_kb_git_repository_status(self):
        """Test that KB has proper Git repository setup"""
        # Test through docker exec since KB service doesn't expose Git info via API
        import subprocess
        
        # Skip this test if we're running inside a container (no docker access)
        try:
            subprocess.run(["docker", "version"], capture_output=True, timeout=1)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("Test requires Docker access from host machine")
        
        try:
            # Check current branch
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1", 
                "bash", "-c", "cd /kb && git branch --show-current"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            branch = result.stdout.strip()
            assert branch == "main", f"Expected 'main' branch, got '{branch}'"
            
            # Check repo URL
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && git remote get-url origin"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            remote_url = result.stdout.strip()
            assert "Obsidian-Vault" in remote_url
            assert "Aeonia-ai" in remote_url
            
        except subprocess.TimeoutExpired:
            pytest.skip("Docker command timed out")
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Git command failed: {e}")
    
    def test_kb_content_availability(self):
        """Test that KB contains expected content"""
        import subprocess
        
        # Skip this test if we're running inside a container (no docker access)
        try:
            subprocess.run(["docker", "version"], capture_output=True, timeout=1)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("Test requires Docker access from host machine")
        
        try:
            # Count markdown files
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && find . -name '*.md' | wc -l"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            file_count = int(result.stdout.strip())
            assert file_count > 100, f"Expected >100 markdown files, got {file_count}"
            
            # Check for key directories
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && ls -la"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            directory_listing = result.stdout
            
            # Should have key directories from Aeonia KB
            expected_indicators = ["shared", "public", ".git"]
            for indicator in expected_indicators:
                assert indicator in directory_listing, f"Missing expected directory/file: {indicator}"
                
        except subprocess.TimeoutExpired:
            pytest.skip("Docker command timed out")
        except Exception as e:
            pytest.fail(f"Content check failed: {e}")
    
    def test_kb_recent_updates(self):
        """Test that KB has recent commits (fresh pull)"""
        import subprocess
        from datetime import datetime, timedelta
        
        # Skip this test if we're running inside a container (no docker access)
        try:
            subprocess.run(["docker", "version"], capture_output=True, timeout=1)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("Test requires Docker access from host machine")
        
        try:
            # Get latest commit date
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && git log -1 --format='%ci'"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            commit_date_str = result.stdout.strip()
            
            # Parse commit date (format: 2025-07-20 01:23:45 +0000)
            commit_date = datetime.fromisoformat(commit_date_str.replace(' +0000', '+00:00'))
            now = datetime.now(commit_date.tzinfo)
            
            # Should be relatively recent (within last 30 days for active repo)
            days_old = (now - commit_date).days
            assert days_old < 30, f"Latest commit is {days_old} days old - KB may be stale"
            
            # Get commit hash for verification
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && git rev-parse HEAD"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            commit_hash = result.stdout.strip()
            assert len(commit_hash) == 40, "Invalid Git commit hash"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Docker command timed out")
        except Exception as e:
            pytest.fail(f"Recent updates check failed: {e}")
    
    def test_kb_service_responsiveness(self, headers):
        """Test KB service response times are reasonable"""
        response = requests.get(f"{GATEWAY_URL}/health", headers=headers)
        assert response.status_code == 200
        
        health_data = response.json()
        kb_health = health_data["services"]["kb"]
        response_time = kb_health["response_time"]
        
        # KB should respond quickly (under 1 second for health checks)
        assert response_time < 1.0, f"KB response time too slow: {response_time}s"
        
        # For a local KB with 1000+ files, should be very fast
        assert response_time < 0.1, f"KB response time should be <100ms for local setup: {response_time}s"

    @pytest.mark.host_only
    def test_multiuser_kb_structure(self):
        """Test that KB has proper multi-user structure"""
        import subprocess
        
        # Skip this test if we're running inside a container (no docker access)
        try:
            subprocess.run(["docker", "version"], capture_output=True, timeout=1)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("Test requires Docker access from host machine")
        
        try:
            # Check for multi-user structure
            result = subprocess.run([
                "docker", "exec", "gaia-kb-service-1",
                "bash", "-c", "cd /kb && ls -la | grep -E '(shared|public|users)'"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            structure = result.stdout
            
            # Should have shared and public directories for multi-user setup
            assert "shared" in structure, "Missing 'shared' directory for multi-user KB"
            assert "public" in structure, "Missing 'public' directory for multi-user KB"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Docker command timed out")
        except Exception as e:
            pytest.fail(f"Multi-user structure check failed: {e}")


class TestKBIntegration:
    """Test KB integration with other services"""
    
    @pytest.fixture
    def headers(self):
        return {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }
    
    def test_all_services_healthy_with_kb(self, headers):
        """Test that all services including KB are healthy"""
        response = requests.get(f"{GATEWAY_URL}/health", headers=headers)
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        
        # All services should be healthy
        services = health_data["services"]
        for service_name, service_health in services.items():
            assert service_health["status"] == "healthy", f"{service_name} service is not healthy"
    
    def test_kb_service_isolation(self, headers):
        """Test that KB service is properly isolated but accessible"""
        # KB should be healthy
        response = requests.get(f"{GATEWAY_URL}/health", headers=headers)
        health_data = response.json()
        
        kb_health = health_data["services"]["kb"]
        assert kb_health["status"] == "healthy"
        
        # KB should have good performance characteristics
        response_time = kb_health["response_time"]
        assert response_time < 0.5, "KB service response time too slow for integration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])