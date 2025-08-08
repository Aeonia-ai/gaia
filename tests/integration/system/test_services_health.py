#!/usr/bin/env python3
"""
Quick health check for all Gaia services
"""
import httpx
import asyncio
import json

async def check_services():
    """Check health of all services"""
    services = {
        "Gateway": "http://localhost:8666/health",
        "Auth": "http://localhost:8666/api/v1/auth/health",
        "Chat": "http://localhost:8666/api/v1/chat/health", 
        "KB": "http://localhost:8666/api/v1/kb/health",
        "Asset": "http://localhost:8666/api/v1/asset/health",
        "Web": "http://localhost:8080/health"
    }
    
    print("🏥 Checking Gaia Services Health\n")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    status = data.get("status", "ok")
                    print(f"✅ {name:10} - {status}")
                else:
                    print(f"⚠️  {name:10} - HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {name:10} - {type(e).__name__}: {str(e)}")
    
    # Test basic functionality
    print("\n🧪 Testing Basic Functionality\n")
    
    # Test gateway providers endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8666/api/v1/providers",
                headers={"X-API-Key": "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"}
            )
            if response.status_code == 200:
                providers = response.json()
                print(f"✅ Providers: {len(providers)} available")
            else:
                print(f"⚠️  Providers: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Providers: {e}")
    
    # Test chat endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8666/api/v1/chat",
                headers={
                    "X-API-Key": "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE",
                    "Content-Type": "application/json"
                },
                json={"message": "Hello", "stream": False}
            )
            if response.status_code == 200:
                print(f"✅ Chat: Working")
            else:
                print(f"⚠️  Chat: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Chat: {e}")

if __name__ == "__main__":
    asyncio.run(check_services())