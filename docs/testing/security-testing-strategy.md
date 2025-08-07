# 🔒 Security Testing Strategy

📍 **Location:** [Home](../../README.md) → [Current](../README.md) → [Development](README.md) → Security Testing

## 🎯 Overview

Comprehensive security testing strategy for Gaia Platform, focusing on OWASP Top 10 vulnerabilities and multi-tenant security concerns.

## 🚨 Priority: CRITICAL

**Why Critical?**
- Handling sensitive user authentication data
- Multi-tenant KB with RBAC permissions
- API keys and JWT tokens in production
- External Git repository integrations

## 🛡️ Security Test Categories

### 1. SQL Injection Prevention 💉

#### Test Coverage
```python
# tests/security/test_sql_injection.py
import pytest
from app.shared.database import get_db
from app.services.kb.models import Document

class TestSQLInjection:
    """Test SQL injection prevention across all endpoints"""
    
    @pytest.mark.parametrize("malicious_input", [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM api_keys --",
        "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
        "' OR 1=1 LIMIT 1 OFFSET 1 --"
    ])
    async def test_kb_search_sql_injection(self, client, malicious_input):
        """Test KB search endpoint against SQL injection"""
        response = await client.post("/api/v0.2/kb/search", json={
            "query": malicious_input,
            "max_results": 10
        })
        
        # Should not return unauthorized data or cause errors
        assert response.status_code in [200, 400]  # 400 for invalid input is OK
        if response.status_code == 200:
            data = response.json()
            # Verify no sensitive data leaked
            assert "api_keys" not in str(data).lower()
            assert "password" not in str(data).lower()
    
    async def test_user_registration_sql_injection(self, client):
        """Test user registration against SQL injection"""
        malicious_emails = [
            "test'; DROP TABLE users; --@example.com",
            "test' OR '1'='1'@example.com"
        ]
        
        for email in malicious_emails:
            response = await client.post("/auth/register", json={
                "email": email,
                "password": "SecurePass123!"
            })
            
            # Should handle malicious input gracefully
            assert response.status_code in [400, 422]  # Validation error expected
```

#### ORM-Specific Testing
```python
async def test_orm_parameterization(self, db_session):
    """Verify ORM uses parameterized queries"""
    # Test direct ORM usage doesn't allow injection
    malicious_query = "'; DROP TABLE documents; --"
    
    # This should be safe due to SQLAlchemy parameterization
    result = db_session.query(Document).filter(
        Document.title.contains(malicious_query)
    ).all()
    
    # Verify table still exists and query was parameterized
    assert db_session.query(Document).count() >= 0  # Table not dropped
```

### 2. Cross-Site Scripting (XSS) Prevention 🎭

#### Test Coverage
```python
# tests/security/test_xss_prevention.py
class TestXSSPrevention:
    """Test XSS prevention in web UI and API responses"""
    
    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "';alert('XSS');//"
    ])
    async def test_kb_document_xss_prevention(self, client, xss_payload):
        """Test stored XSS prevention in KB documents"""
        # Create document with XSS payload
        response = await client.post("/api/v0.2/kb/write", json={
            "file_path": "test-xss.md",
            "content": f"# Test Document\n\n{xss_payload}"
        })
        assert response.status_code == 200
        
        # Read document back
        response = await client.post("/api/v0.2/kb/read", json={
            "file_path": "test-xss.md"
        })
        assert response.status_code == 200
        
        content = response.json()["content"]
        # Verify XSS payload is sanitized or escaped
        assert "<script>" not in content or "&lt;script&gt;" in content
    
    async def test_chat_message_xss_prevention(self, client):
        """Test XSS prevention in chat messages"""
        xss_message = "<script>fetch('/api/v0.2/users').then(r=>r.json()).then(console.log)</script>"
        
        response = await client.post("/api/v0.2/chat", json={
            "messages": [{"role": "user", "content": xss_message}]
        })
        
        # Verify response doesn't contain unescaped script tags
        response_text = response.text
        assert "<script>" not in response_text or "&lt;script&gt;" in response_text
```

#### Web UI XSS Testing
```python
# tests/ui/test_xss_web_ui.py (Playwright)
async def test_chat_interface_xss_prevention(page):
    """Test XSS prevention in chat interface"""
    await page.goto("/chat")
    
    # Input XSS payload
    xss_payload = "<img src=x onerror=alert('XSS')>"
    await page.fill('[data-testid="chat-input"]', xss_payload)
    await page.click('[data-testid="send-button"]')
    
    # Verify no alert dialog appears (XSS blocked)
    await page.wait_for_timeout(1000)  # Wait for potential XSS execution
    
    # Check that message is displayed but sanitized
    message_content = await page.locator('[data-testid="chat-message"]').text_content()
    assert "alert" not in message_content or "&lt;img" in message_content
```

### 3. Authorization Boundary Testing 🚪

#### RBAC Permission Testing
```python
# tests/security/test_auth_boundaries.py
class TestAuthorizationBoundaries:
    """Test RBAC and permission boundary enforcement"""
    
    async def test_kb_access_isolation(self, client):
        """Test users can only access their own KB data"""
        # Create two users with separate KB data
        user1_token = await create_test_user("user1@example.com")
        user2_token = await create_test_user("user2@example.com")
        
        # User 1 creates a document
        await client.post("/api/v0.2/kb/write", 
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"file_path": "user1-secret.md", "content": "User 1 secret data"}
        )
        
        # User 2 tries to access User 1's document
        response = await client.post("/api/v0.2/kb/read",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={"file_path": "user1-secret.md"}
        )
        
        # Should be forbidden
        assert response.status_code == 403
    
    async def test_api_key_scope_enforcement(self, client):
        """Test API key scope limitations"""
        # Create API key with limited scope
        limited_key = await create_api_key(scopes=["kb:read"])
        
        # Should allow read operations
        response = await client.post("/api/v0.2/kb/search",
            headers={"X-API-Key": limited_key},
            json={"query": "test"}
        )
        assert response.status_code == 200
        
        # Should deny write operations
        response = await client.post("/api/v0.2/kb/write",
            headers={"X-API-Key": limited_key},
            json={"file_path": "test.md", "content": "test"}
        )
        assert response.status_code == 403
```

#### Privilege Escalation Testing
```python
async def test_privilege_escalation_prevention(self, client):
    """Test prevention of privilege escalation attacks"""
    regular_user_token = await create_test_user("regular@example.com", role="user")
    
    # Try to access admin endpoints
    admin_endpoints = [
        "/api/v0.2/admin/users",
        "/api/v0.2/admin/api-keys",
        "/api/v0.2/admin/system-config"
    ]
    
    for endpoint in admin_endpoints:
        response = await client.get(endpoint,
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        assert response.status_code in [403, 404]  # Forbidden or not found
```

### 4. Rate Limiting & DDoS Protection 🚦

#### Rate Limiting Tests
```python
# tests/security/test_rate_limiting.py
class TestRateLimiting:
    """Test rate limiting and DDoS protection"""
    
    async def test_api_rate_limiting(self, client):
        """Test API endpoint rate limiting"""
        # Make rapid requests to exceed rate limit
        responses = []
        for i in range(100):  # Exceed typical rate limit
            response = await client.post("/api/v0.2/kb/search", json={
                "query": f"test query {i}"
            })
            responses.append(response.status_code)
        
        # Should see 429 (Too Many Requests) responses
        assert 429 in responses
        
        # Count how many requests succeeded vs were rate limited
        success_count = responses.count(200)
        rate_limited_count = responses.count(429)
        
        # Verify rate limiting is working
        assert rate_limited_count > 0
        assert success_count < 100  # Not all requests should succeed
    
    async def test_per_user_rate_limiting(self, client):
        """Test per-user rate limiting isolation"""
        user1_token = await create_test_user("user1@example.com")
        user2_token = await create_test_user("user2@example.com")
        
        # User 1 exhausts their rate limit
        for i in range(50):
            await client.post("/api/v0.2/kb/search",
                headers={"Authorization": f"Bearer {user1_token}"},
                json={"query": f"test {i}"}
            )
        
        # User 2 should still be able to make requests
        response = await client.post("/api/v0.2/kb/search",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={"query": "user2 test"}
        )
        assert response.status_code == 200
```

### 5. Input Validation & Sanitization 🧹

#### Malicious Payload Testing
```python
# tests/security/test_input_validation.py
class TestInputValidation:
    """Test input validation and sanitization"""
    
    @pytest.mark.parametrize("malicious_filename", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/dev/null",
        "CON.txt",  # Windows reserved name
        "file\x00.txt",  # Null byte injection
        "very" + "long" * 1000 + ".txt"  # Extremely long filename
    ])
    async def test_filename_validation(self, client, malicious_filename):
        """Test file path validation in KB operations"""
        response = await client.post("/api/v0.2/kb/write", json={
            "file_path": malicious_filename,
            "content": "test content"
        })
        
        # Should reject malicious filenames
        assert response.status_code in [400, 422]
    
    async def test_json_payload_validation(self, client):
        """Test JSON payload size and structure validation"""
        # Extremely large payload
        large_content = "A" * (10 * 1024 * 1024)  # 10MB
        response = await client.post("/api/v0.2/kb/write", json={
            "file_path": "large-file.txt",
            "content": large_content
        })
        
        # Should reject overly large payloads
        assert response.status_code in [413, 422]  # Payload too large
```

## 🔧 Security Testing Tools & Integration

### Static Security Analysis
```bash
# Integrate security scanning tools
pip install bandit safety
bandit -r app/  # Python security linter
safety check    # Vulnerability scanning
```

### Dynamic Security Testing
```python
# tests/security/conftest.py
@pytest.fixture
def security_headers_check():
    """Verify security headers are present"""
    def check_headers(response):
        security_headers = [
            'x-content-type-options',
            'x-frame-options', 
            'x-xss-protection',
            'strict-transport-security'
        ]
        
        for header in security_headers:
            assert header in response.headers.keys()
    
    return check_headers
```

### Penetration Testing Automation
```python
# tests/security/test_penetration.py
class TestPenetrationTesting:
    """Automated penetration testing scenarios"""
    
    async def test_authentication_bypass_attempts(self, client):
        """Test various authentication bypass techniques"""
        bypass_attempts = [
            {"Authorization": "Bearer invalid-token"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic YWRtaW46cGFzc3dvcmQ="},  # admin:password
            {"X-API-Key": ""},
            {"X-API-Key": "invalid-key"}
        ]
        
        for headers in bypass_attempts:
            response = await client.get("/api/v0.2/kb/list", headers=headers)
            assert response.status_code in [401, 403]  # Unauthorized/Forbidden
```

## 📊 Security Metrics & Monitoring

### Key Performance Indicators
- **0 Critical Vulnerabilities** - OWASP Top 10 compliance
- **100% Endpoint Coverage** - All API endpoints tested
- **<100ms Security Overhead** - Minimal performance impact
- **Daily Security Scans** - Automated vulnerability detection

### Reporting & Alerting
```python
# tests/security/test_reporting.py
def test_security_report_generation():
    """Generate security test reports"""
    report = {
        "timestamp": datetime.utcnow(),
        "vulnerabilities_found": 0,
        "tests_passed": 95,
        "tests_failed": 0,
        "coverage_percentage": 100.0
    }
    
    # Save report for monitoring
    with open("security-report.json", "w") as f:
        json.dump(report, f)
```

## 🚀 CI/CD Integration

### GitHub Actions Security Pipeline
```yaml
# .github/workflows/security-tests.yml
name: Security Testing
on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
        
      - name: Run security tests
        run: pytest tests/security/ -v --junitxml=security-results.xml
        
      - name: Upload security results
        uses: actions/upload-artifact@v3
        with:
          name: security-test-results
          path: security-results.xml
```

## 🔗 See Also

- **[Authentication Guide](../authentication/)** - Current auth implementation
- **[RBAC System Guide](../kb/rbac-system-guide.md)** - Role-based access control
- **[API Contracts](../../api/api-contracts.md)** - Endpoint security requirements
- **[Testing Improvement Plan](automated-testing-improvement-plan.md)** - Overall testing strategy

---

**Status**: 📋 **PLANNED** - Ready for implementation in Phase 1  
**Priority**: 🔥 **CRITICAL** - Security foundation for production readiness  
**Estimated Effort**: 1 week (Phase 1 of testing improvement plan)