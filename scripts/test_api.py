#!/usr/bin/env python3
"""
API Test Tool for Gaia Platform

Usage:
    python scripts/test_api.py chat "Hello, what is 2+2?"
    python scripts/test_api.py stream "Tell me a joke"
    python scripts/test_api.py status
    python scripts/test_api.py models
"""

import sys
import json
import requests
import argparse
from typing import Optional, Dict, Any

# Configuration
BASE_URL = "http://localhost:8666"
API_KEY = "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"

class GaiaAPITester:
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        
    def _make_request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None, stream: bool = False) -> requests.Response:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{path}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, stream=stream)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error: Could not connect to {url}")
            print("   Make sure the Gateway service is running on port 8666")
            sys.exit(1)
            
    def test_health(self):
        """Test health endpoint"""
        print("🏥 Testing health endpoint...")
        response = self._make_request("GET", "/health")
        self._print_response(response)
        
    def test_chat(self, message: str, activity: str = "generic", model: Optional[str] = None):
        """Test non-streaming chat endpoint"""
        print(f"💬 Testing chat endpoint with message: '{message}'")
        data = {
            "message": message,
            "activity": activity,
            "stream": False
        }
        if model:
            data["model"] = model
            
        response = self._make_request("POST", "/api/v0.2/chat", data)
        self._print_response(response)
        
    def test_stream(self, message: str, activity: str = "generic", model: Optional[str] = None):
        """Test streaming chat endpoint"""
        print(f"📡 Testing streaming chat endpoint with message: '{message}'")
        data = {
            "message": message, 
            "activity": activity
        }
        if model:
            data["model"] = model
            
        response = self._make_request("POST", "/api/v0.2/chat/stream", data, stream=True)
        
        if response.status_code == 200:
            print("✅ Streaming response:")
            print("-" * 50)
            try:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                print("\n🏁 Stream completed")
                            else:
                                try:
                                    event_data = json.loads(data_str)
                                    self._print_stream_event(event_data)
                                except json.JSONDecodeError:
                                    print(f"⚠️  Raw: {decoded_line}")
            except KeyboardInterrupt:
                print("\n⏹️  Stream interrupted")
        else:
            self._print_response(response)
            
    def test_stream_status(self):
        """Test streaming status endpoint"""
        print("📊 Testing streaming status...")
        response = self._make_request("GET", "/api/v0.2/chat/stream/status")
        self._print_response(response)
        
    def test_stream_models(self):
        """Test streaming models endpoint"""
        print("🤖 Testing streaming models...")
        response = self._make_request("GET", "/api/v0.2/chat/stream/models")
        self._print_response(response)
        
    def test_vr_recommendation(self):
        """Test VR model recommendation"""
        print("🥽 Testing VR model recommendation...")
        response = self._make_request("GET", "/api/v0.2/chat/stream/models/vr-recommendation")
        self._print_response(response)
        
    def test_model_performance(self):
        """Test model performance comparison"""
        print("📈 Testing model performance comparison...")
        response = self._make_request("GET", "/api/v0.2/chat/stream/models/performance")
        self._print_response(response)
        
    def test_cache_status(self):
        """Test cache status"""
        print("💾 Testing cache status...")
        response = self._make_request("GET", "/api/v0.2/chat/stream/cache/status")
        self._print_response(response)
        
    def clear_history(self):
        """Clear chat history"""
        print("🗑️  Clearing chat history...")
        response = self._make_request("DELETE", "/api/v0.2/chat/stream/history")
        self._print_response(response)
        
    def _print_response(self, response: requests.Response):
        """Pretty print API response"""
        if response.status_code == 200:
            print(f"✅ Status: {response.status_code}")
            try:
                data = response.json()
                print(json.dumps(data, indent=2))
            except:
                print(response.text)
        else:
            print(f"❌ Status: {response.status_code}")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
                
    def _print_stream_event(self, event_data: Dict[str, Any]):
        """Pretty print streaming event"""
        event_type = event_data.get("type", "unknown")
        
        if event_type == "start":
            print(f"🚀 Stream started at {event_data.get('timestamp', 'unknown')}")
        elif event_type == "ready":
            print(f"✅ Ready - Persona: {event_data.get('persona', 'unknown')}, Fetch time: {event_data.get('fetch_time_ms', 0)}ms")
        elif event_type == "content":
            content = event_data.get("content", "")
            print(content, end="", flush=True)
        elif event_type == "complete":
            print(f"\n✅ Response complete - Length: {event_data.get('response_length', 0)} chars")
        elif event_type == "error":
            print(f"\n❌ Error: {event_data.get('error', 'unknown')}")
        elif event_type == "model_selection":
            print(f"🤖 Model: {event_data.get('model')} from {event_data.get('provider')}")
            print(f"   Reason: {event_data.get('reasoning')}")
        else:
            print(f"📦 {event_type}: {json.dumps(event_data)}")

def main():
    parser = argparse.ArgumentParser(description="Test Gaia Platform API endpoints")
    parser.add_argument("command", choices=[
        "health", "chat", "stream", "status", "models", 
        "vr", "performance", "cache", "clear"
    ], help="Command to run")
    parser.add_argument("message", nargs="?", help="Message for chat/stream commands")
    parser.add_argument("--model", help="Specific model to use")
    parser.add_argument("--activity", default="generic", help="Activity context")
    parser.add_argument("--url", default=BASE_URL, help="API base URL")
    parser.add_argument("--key", default=API_KEY, help="API key")
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = GaiaAPITester(args.url, args.key)
    
    # Execute command
    if args.command == "health":
        tester.test_health()
    elif args.command == "chat":
        if not args.message:
            print("❌ Message required for chat command")
            sys.exit(1)
        tester.test_chat(args.message, args.activity, args.model)
    elif args.command == "stream":
        if not args.message:
            print("❌ Message required for stream command")
            sys.exit(1)
        tester.test_stream(args.message, args.activity, args.model)
    elif args.command == "status":
        tester.test_stream_status()
    elif args.command == "models":
        tester.test_stream_models()
    elif args.command == "vr":
        tester.test_vr_recommendation()
    elif args.command == "performance":
        tester.test_model_performance()
    elif args.command == "cache":
        tester.test_cache_status()
    elif args.command == "clear":
        tester.clear_history()

if __name__ == "__main__":
    main()