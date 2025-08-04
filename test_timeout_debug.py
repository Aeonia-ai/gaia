import httpx
import asyncio
import os

async def test_unified_endpoint():
    gateway_url = "http://localhost:8666"
    api_key = os.getenv("API_KEY", "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    print(f"Testing unified endpoint at {gateway_url}/api/v1/chat")
    print(f"Headers: {headers}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello, this is a test"}
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
    except httpx.TimeoutException as e:
        print(f"Timeout error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_unified_endpoint())
