#!/usr/bin/env python3
"""
Simple test script for chat + KB integration
"""

import urllib.request
import urllib.parse
import json

def test_kb_chat():
    """Test chat with KB integration"""
    
    url = "http://localhost:8666/api/v1/chat"
    headers = {
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY",
        "Content-Type": "application/json"
    }
    data = {
        "message": "search my knowledge base for gaia platform information"
    }
    
    print("🧪 Testing chat + KB integration...")
    print(f"📤 Request: {data['message']}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        print(f"📊 Status: {response.status_code}")
        print(f"🔗 Route type: {result.get('_metadata', {}).get('route_type', 'unknown')}")
        print(f"🛠️ Tools used: {result.get('_metadata', {}).get('tools_used', [])}")
        print(f"⏱️ Time: {result.get('_metadata', {}).get('total_time_ms', 0)}ms")
        
        choices = result.get('choices', [])
        print(f"📝 Choices: {len(choices)}")
        
        if choices:
            content = choices[0].get('message', {}).get('content', '')
            print(f"💬 Response length: {len(content)} characters")
            print(f"📄 Response preview: {content[:200]}...")
            return True
        else:
            print("❌ No response content generated")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

def test_kb_direct():
    """Test KB service directly"""
    
    url = "http://localhost:8666/api/v1/chat/kb-search"
    headers = {
        "X-API-Key": "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY",
        "Content-Type": "application/json"
    }
    data = {
        "message": "gaia platform"
    }
    
    print("\n🔍 Testing direct KB search...")
    print(f"📤 Query: {data['message']}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        print(f"📊 Status: {response.status_code}")
        response_text = result.get('response', '')
        print(f"📄 Response length: {len(response_text)} characters")
        
        if 'Found' in response_text:
            lines = response_text.split('\n')
            found_line = [line for line in lines if 'Found' in line][0]
            print(f"✅ {found_line}")
            return True
        else:
            print("❌ No search results found")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting KB integration tests...\n")
    
    # Test direct KB search first
    kb_works = test_kb_direct()
    
    # Test chat integration
    chat_works = test_kb_chat()
    
    print(f"\n📊 Results:")
    print(f"   KB Direct: {'✅ Working' if kb_works else '❌ Failed'}")
    print(f"   Chat Integration: {'✅ Working' if chat_works else '❌ Failed'}")
    
    if kb_works and not chat_works:
        print("\n🔧 KB tools work but chat integration has issues.")
        print("   The LLM service might be having trouble with the tool results format.")