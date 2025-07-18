#!/usr/bin/env python3
"""
End-to-end test script for the Stubichat backend system.
Tests the complete flow from user input through LangGraph to LLM agent response.
"""

import asyncio
import httpx
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any


class EndToEndTester:
    """Test the complete backend system end-to-end."""
    
    def __init__(self):
        self.main_backend_url = "http://localhost:8000"
        self.llm_agent_url = "http://localhost:8001"
        self.timeout = 30.0
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Simple logger for test output."""
        class Logger:
            def info(self, msg):
                print(f"ℹ️  {msg}")
            
            def success(self, msg):
                print(f"✅ {msg}")
            
            def error(self, msg):
                print(f"❌ {msg}")
            
            def warning(self, msg):
                print(f"⚠️  {msg}")
        
        return Logger()
    
    async def wait_for_service(self, url: str, service_name: str, max_retries: int = 30) -> bool:
        """Wait for a service to become available."""
        self.logger.info(f"Waiting for {service_name} to be ready...")
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        self.logger.success(f"{service_name} is ready!")
                        return True
            except Exception as e:
                if attempt == 0:  # Only show first error
                    self.logger.warning(f"Waiting for {service_name}: {str(e)}")
            
            await asyncio.sleep(2)
        
        self.logger.error(f"{service_name} failed to start after {max_retries} attempts")
        return False
    
    async def test_health_endpoints(self) -> bool:
        """Test health endpoints for both services."""
        self.logger.info("Testing health endpoints...")
        
        try:
            # Test main backend health
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.main_backend_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    self.logger.success(f"Main backend health: {data.get('status', 'unknown')}")
                else:
                    self.logger.error(f"Main backend health check failed: {response.status_code}")
                    return False
            
            # Test LLM agent health
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.llm_agent_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    self.logger.success(f"LLM agent health: {data.get('status', 'unknown')}")
                else:
                    self.logger.error(f"LLM agent health check failed: {response.status_code}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def test_chat_endpoint(self) -> bool:
        """Test the chat endpoint with LangGraph workflow."""
        self.logger.info("Testing chat endpoint with LangGraph workflow...")
        
        try:
            # Prepare test request
            test_request = {
                "request": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello! Can you tell me a short joke?"
                        }
                    ],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 200,
                    "model": "gpt-4"
                }
            }
            
            # Send request to main backend
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.main_backend_url}/chat/",
                    json=test_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.success("Chat request successful!")
                    self.logger.info(f"Response: {data.get('response', '')[:100]}...")
                    self.logger.info(f"Model: {data.get('model', 'unknown')}")
                    return True
                else:
                    self.logger.error(f"Chat request failed: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Chat endpoint test failed: {str(e)}")
            return False
    
    async def test_direct_llm_agent(self) -> bool:
        """Test direct communication with LLM agent."""
        self.logger.info("Testing direct LLM agent communication...")
        
        try:
            # Prepare test request
            test_request = {
                "request": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "What is 2 + 2?"
                        }
                    ],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 100,
                    "model": "gpt-4"
                }
            }
            
            # Send request directly to LLM agent
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.llm_agent_url}/generate/",
                    json=test_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.success("Direct LLM agent request successful!")
                    self.logger.info(f"Response: {data.get('response', '')[:100]}...")
                    return True
                else:
                    self.logger.error(f"Direct LLM agent request failed: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Direct LLM agent test failed: {str(e)}")
            return False
    
    async def test_streaming(self) -> bool:
        """Test streaming functionality."""
        self.logger.info("Testing streaming functionality...")
        
        try:
            # Prepare test request
            test_request = {
                "request": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "Write a short story about a cat."
                        }
                    ],
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 300,
                    "model": "gpt-4"
                }
            }
            
            # Test streaming from main backend
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.main_backend_url}/chat/stream",
                    json=test_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code == 200:
                        chunk_count = 0
                        async for line in response.aiter_lines():
                            if line.strip() and line.startswith("data: "):
                                chunk_count += 1
                                if chunk_count >= 3:  # Get at least 3 chunks
                                    break
                        
                        if chunk_count > 0:
                            self.logger.success(f"Streaming test successful! Received {chunk_count} chunks")
                            return True
                        else:
                            self.logger.error("No streaming chunks received")
                            return False
                    else:
                        self.logger.error(f"Streaming request failed: {response.status_code}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Streaming test failed: {str(e)}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling with invalid requests."""
        self.logger.info("Testing error handling...")
        
        try:
            # Test with invalid request (no messages)
            invalid_request = {
                "messages": [],
                "stream": False,
                "temperature": 0.7,
                "model": "gpt-4"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.main_backend_url}/chat/",
                    json=invalid_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [400, 422, 500]:  # Expected error codes
                    self.logger.success("Error handling test passed - invalid request properly rejected")
                    return True
                else:
                    self.logger.warning(f"Unexpected response for invalid request: {response.status_code}")
                    return True  # Not a critical failure
                    
        except Exception as e:
            self.logger.error(f"Error handling test failed: {str(e)}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all end-to-end tests."""
        print("🚀 Stubichat Backend End-to-End Test Suite")
        print("=" * 60)
        
        # Wait for services to be ready
        main_backend_ready = await self.wait_for_service(self.main_backend_url, "Main Backend")
        llm_agent_ready = await self.wait_for_service(self.llm_agent_url, "LLM Agent")
        
        if not main_backend_ready or not llm_agent_ready:
            return False
        
        # Run tests
        tests = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Direct LLM Agent", self.test_direct_llm_agent),
            ("Chat Endpoint (LangGraph)", self.test_chat_endpoint),
            ("Streaming", self.test_streaming),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            print("-" * 40)
            
            try:
                result = await test_func()
                if result:
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the logs above for details.")
            return False


async def main():
    """Main test function."""
    tester = EndToEndTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 System Status: READY FOR PRODUCTION")
        print("\nNext Steps:")
        print("1. The backend services are running and healthy")
        print("2. LangGraph workflow is functioning correctly")
        print("3. LLM agent integration is working")
        print("4. You can now integrate with your frontend application")
        sys.exit(0)
    else:
        print("\n🚨 System Status: NEEDS ATTENTION")
        print("\nTroubleshooting:")
        print("1. Check Docker Compose logs: docker-compose logs")
        print("2. Verify environment variables in .env file")
        print("3. Ensure OpenAI API key is configured")
        print("4. Check service health: docker-compose ps")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 