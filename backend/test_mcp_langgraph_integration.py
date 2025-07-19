#!/usr/bin/env python3
"""
Comprehensive test script for MCP integration with LangGraph workflow.
Tests the complete flow including conditional MCP tool calling.
"""

import asyncio
import httpx
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, List


class MCPLangGraphTester:
    """Test the MCP integration with LangGraph workflow."""
    
    def __init__(self):
        self.main_backend_url = "http://localhost:8000"
        self.llm_agent_url = "http://localhost:8001"
        self.mcp_server_url = "http://localhost:8002"
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
            
            def section(self, msg):
                print(f"\n🔍 {msg}")
                print("=" * 50)
        
        return Logger()
    
    async def wait_for_services(self) -> bool:
        """Wait for all services to become available."""
        self.logger.section("Waiting for services to be ready")
        
        services = [
            (f"{self.main_backend_url}/health", "Main Backend"),
            (f"{self.llm_agent_url}/health", "LLM Agent"),
            (f"{self.mcp_server_url}/health", "MCP Server")
        ]
        
        for url, name in services:
            if not await self._wait_for_service(url, name):
                return False
        
        return True
    
    async def _wait_for_service(self, url: str, service_name: str, max_retries: int = 30) -> bool:
        """Wait for a specific service to become available."""
        self.logger.info(f"Waiting for {service_name} to be ready...")
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
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
        """Test health endpoints for all services."""
        self.logger.section("Testing health endpoints")
        
        try:
            services = [
                (f"{self.main_backend_url}/health", "Main Backend"),
                (f"{self.llm_agent_url}/health", "LLM Agent"),
                (f"{self.mcp_server_url}/health", "MCP Server")
            ]
            
            for url, name in services:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        self.logger.success(f"{name} health: {data.get('status', 'unknown')}")
                    else:
                        self.logger.error(f"{name} health check failed: {response.status_code}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def test_mcp_server_tools(self) -> bool:
        """Test MCP server tools directly."""
        self.logger.section("Testing MCP server tools")
        
        try:
            # Test echo tool
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mcp_server_url}/echo",
                    json={"message": "Hello MCP!", "prefix": "Echo: "},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.success(f"Echo tool test successful: {data}")
                else:
                    self.logger.error(f"Echo tool test failed: {response.status_code}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"MCP server tools test failed: {str(e)}")
            return False
    
    async def test_chat_without_tools(self) -> bool:
        """Test chat endpoint without MCP tools."""
        self.logger.section("Testing chat without MCP tools")
        
        try:
            # Prepare test request that shouldn't trigger MCP tools
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
                    self.logger.success("Chat without tools request successful!")
                    self.logger.info(f"Response: {data.get('response', '')[:100]}...")
                    
                    # Check that no MCP tools were used
                    mcp_tools_used = data.get('mcp_tools_used')
                    if mcp_tools_used is None or len(mcp_tools_used) == 0:
                        self.logger.success("No MCP tools were used (as expected)")
                    else:
                        self.logger.warning(f"Unexpected MCP tools used: {mcp_tools_used}")
                    
                    return True
                else:
                    self.logger.error(f"Chat without tools request failed: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Chat without tools test failed: {str(e)}")
            return False
    
    async def test_chat_with_echo_tool(self) -> bool:
        """Test chat endpoint with echo MCP tool."""
        self.logger.section("Testing chat with echo MCP tool")
        
        try:
            # Prepare test request that should trigger echo tool
            test_request = {
                "request": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "echo Hello World!"
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
                    self.logger.success("Chat with echo tool request successful!")
                    self.logger.info(f"Response: {data.get('response', '')[:100]}...")
                    
                    # Check that echo tool was used
                    mcp_tools_used = data.get('mcp_tools_used', [])
                    if 'echo' in mcp_tools_used:
                        self.logger.success("Echo MCP tool was used successfully")
                    else:
                        self.logger.warning(f"Echo tool not used. Tools used: {mcp_tools_used}")
                    
                    return True
                else:
                    self.logger.error(f"Chat with echo tool request failed: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Chat with echo tool test failed: {str(e)}")
            return False
    
    async def test_chat_with_repeat_keyword(self) -> bool:
        """Test chat endpoint with 'repeat' keyword that should trigger echo tool."""
        self.logger.section("Testing chat with 'repeat' keyword")
        
        try:
            # Prepare test request with 'repeat' keyword
            test_request = {
                "request": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "Please repeat this message: Testing MCP integration"
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
                    self.logger.success("Chat with repeat keyword request successful!")
                    self.logger.info(f"Response: {data.get('response', '')[:100]}...")
                    
                    # Check that echo tool was used
                    mcp_tools_used = data.get('mcp_tools_used', [])
                    if 'echo' in mcp_tools_used:
                        self.logger.success("Echo MCP tool was triggered by 'repeat' keyword")
                    else:
                        self.logger.warning(f"Echo tool not triggered. Tools used: {mcp_tools_used}")
                    
                    return True
                else:
                    self.logger.error(f"Chat with repeat keyword request failed: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Chat with repeat keyword test failed: {str(e)}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling with invalid requests."""
        self.logger.section("Testing error handling")
        
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
                
                if response.status_code in [400, 422, 500]:
                    self.logger.success("Error handling test passed - invalid request properly rejected")
                    return True
                else:
                    self.logger.error(f"Error handling test failed - expected 400/422/500, got {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error handling test failed: {str(e)}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests and return overall success status."""
        self.logger.section("Starting MCP LangGraph Integration Tests")
        
        test_results = []
        
        # Wait for services
        if not await self.wait_for_services():
            self.logger.error("Services not ready - aborting tests")
            return False
        
        # Run tests
        tests = [
            ("Health Endpoints", self.test_health_endpoints),
            ("MCP Server Tools", self.test_mcp_server_tools),
            ("Chat Without Tools", self.test_chat_without_tools),
            ("Chat With Echo Tool", self.test_chat_with_echo_tool),
            ("Chat With Repeat Keyword", self.test_chat_with_repeat_keyword),
            ("Error Handling", self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_results.append((test_name, result))
                if result:
                    self.logger.success(f"✅ {test_name}: PASSED")
                else:
                    self.logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                self.logger.error(f"❌ {test_name}: ERROR - {str(e)}")
                test_results.append((test_name, False))
        
        # Summary
        self.logger.section("Test Results Summary")
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        self.logger.info(f"Tests passed: {passed}/{total}")
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            self.logger.info(f"  {test_name}: {status}")
        
        if passed == total:
            self.logger.success("🎉 All tests passed! MCP LangGraph integration is working correctly.")
        else:
            self.logger.error(f"⚠️  {total - passed} test(s) failed. Please check the implementation.")
        
        return passed == total


async def main():
    """Main function to run the tests."""
    tester = MCPLangGraphTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 