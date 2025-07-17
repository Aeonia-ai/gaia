#!/usr/bin/env python3
"""Debug registration to see exact error"""

import requests

BASE_URL = "http://localhost:8080"

def debug_registration():
    """Debug registration response"""
    
    session = requests.Session()
    
    # Try to register with a test email
    response = session.post(
        f"{BASE_URL}/auth/register",
        data={
            "email": "test.debug@example.com",
            "password": "TestPassword123!"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\nResponse Text (first 1000 chars):")
    print("-" * 60)
    print(response.text[:1000])
    print("-" * 60)
    
    # Look for error messages
    if "error" in response.text or "Error" in response.text or "⚠️" in response.text:
        print("\nFound error indicators in response")
        
        # Try to extract error message
        import re
        error_patterns = [
            r'<div[^>]*>([^<]*error[^<]*)</div>',
            r'⚠️\s*([^<]+)',
            r'class="[^"]*error[^"]*"[^>]*>([^<]+)',
            r'alert[^>]*>([^<]+)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                print(f"\nExtracted errors:")
                for match in matches:
                    if match.strip():
                        print(f"  - {match.strip()}")

if __name__ == "__main__":
    debug_registration()