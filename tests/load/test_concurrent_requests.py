"""
Load tests for concurrent request handling.

These tests verify system behavior under concurrent load and should be run
separately from integration tests due to:
- Rate limit consumption
- Non-deterministic timing
- External API dependencies
"""
import pytest
import asyncio
import httpx
import os
from typing import List
import logging

logger = logging.getLogger(__name__)

# Mark all tests in this file as load tests
pytestmark = pytest.mark.load


class TestConcurrentRequests:
    """Test system behavior under concurrent request load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_same_user(self, gateway_url, auth_url, shared_test_user):
        """Test handling concurrent requests from the same user.
        
        This is a LOAD TEST that verifies the system can handle burst traffic
        from a single user. Should not be run as part of regular CI/CD.
        """
        # Login to get auth token
        async with httpx.AsyncClient(timeout=30.0) as client:
            login_response = await client.post(
                f"{auth_url}/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert login_response.status_code == 200
            auth_data = login_response.json()
            
            headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
            
            # Send concurrent requests
            tasks = []
            num_requests = int(os.getenv("LOAD_TEST_CONCURRENT_REQUESTS", "3"))
            
            for i in range(num_requests):
                task = client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": f"Concurrent request {i}"}
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            success_count = 0
            rate_limit_count = 0
            error_count = 0
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    error_count += 1
                    logger.error(f"Request {i} failed with exception: {response}")
                elif response.status_code == 200:
                    success_count += 1
                    logger.info(f"Request {i} succeeded")
                elif response.status_code == 429:
                    rate_limit_count += 1
                    logger.warning(f"Request {i} rate limited")
                else:
                    error_count += 1
                    logger.error(f"Request {i} failed: {response.status_code}")
            
            # Load test success criteria: system should handle load gracefully
            # Either succeed or rate limit, but not error
            assert error_count == 0, f"{error_count} requests resulted in errors"
            logger.info(f"Results: {success_count} success, {rate_limit_count} rate limited")
    
    @pytest.mark.asyncio
    async def test_concurrent_different_users(self, gateway_url, test_user_factory):
        """Test handling concurrent requests from different users.
        
        This verifies the system can handle multiple users simultaneously.
        """
        num_users = int(os.getenv("LOAD_TEST_CONCURRENT_USERS", "3"))
        
        # Create multiple test users
        users = []
        for i in range(num_users):
            user = test_user_factory.create_verified_test_user(
                email=f"load-test-user-{i}@test.local"
            )
            users.append(user)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Login all users and prepare requests
                tasks = []
                for i, user in enumerate(users):
                    # Create a coroutine for each user's request flow
                    async def user_request(user_data, index):
                        # Login
                        login_resp = await client.post(
                            f"{gateway_url}/api/v1/auth/login",
                            json={
                                "email": user_data["email"],
                                "password": user_data["password"]
                            }
                        )
                        if login_resp.status_code != 200:
                            return ("login_failed", index, login_resp.status_code)
                        
                        token = login_resp.json()["access_token"]
                        
                        # Make chat request
                        chat_resp = await client.post(
                            f"{gateway_url}/api/v1/chat",
                            headers={"Authorization": f"Bearer {token}"},
                            json={"message": f"User {index} message"}
                        )
                        
                        return ("success" if chat_resp.status_code == 200 else "failed", 
                                index, chat_resp.status_code)
                    
                    tasks.append(user_request(user, i))
                
                # Execute all user requests concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze results
                success_count = sum(1 for r in results if not isinstance(r, Exception) and r[0] == "success")
                
                logger.info(f"Concurrent users test: {success_count}/{num_users} succeeded")
                
                # In load testing, we expect most requests to succeed
                # Allow for some failures due to rate limiting
                assert success_count >= num_users * 0.6, \
                    f"Only {success_count}/{num_users} users succeeded"
                    
        finally:
            # Cleanup test users
            for user in users:
                test_user_factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio 
    async def test_burst_traffic_pattern(self, gateway_url, headers):
        """Test system behavior under burst traffic patterns.
        
        Simulates realistic burst patterns rather than perfectly concurrent requests.
        """
        burst_size = int(os.getenv("LOAD_TEST_BURST_SIZE", "5"))
        burst_delay = float(os.getenv("LOAD_TEST_BURST_DELAY", "0.1"))
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            results = []
            
            # Send burst with small delays
            for i in range(burst_size):
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": f"Burst request {i}"}
                )
                results.append({
                    "index": i,
                    "status": response.status_code,
                    "success": response.status_code == 200
                })
                
                # Small delay between requests in burst
                if i < burst_size - 1:
                    await asyncio.sleep(burst_delay)
            
            # Analyze burst handling
            success_rate = sum(1 for r in results if r["success"]) / len(results)
            logger.info(f"Burst test success rate: {success_rate:.2%}")
            
            # System should handle burst traffic gracefully
            assert success_rate >= 0.8, f"Burst success rate too low: {success_rate:.2%}"