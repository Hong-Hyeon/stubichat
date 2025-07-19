#!/usr/bin/env python3
"""
Comprehensive test script for proper MCP integration using fastapi-mcp:
- Main Backend (FastAPI + LangGraph)
- LLM Agent (OpenAI-based)
- MCP Server (FastAPI-MCP with proper tools)
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List


class MCPIntegrationTester:
    """Test proper MCP integration with fastapi-mcp."""
    
    def __init__(self):
        self.base_urls = {
            "main_backend": "http://localhost:8000",
            "llm_agent": "http://localhost:8001", 
            "mcp_server": "http://localhost:8002"
        }
        self.results = []
    
    async def test_health_endpoints(self) -> None:
        """Test health endpoints for all services."""
        print("\n🔍 Testing Health Endpoints...")
        
        for service_name, base_url in self.base_urls.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{base_url}/health") as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"✅ {service_name}: {data.get('status', 'unknown')}")
                            self.results.append({
                                "test": f"health_{service_name}",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print(f"❌ {service_name}: HTTP {response.status}")
                            self.results.append({
                                "test": f"health_{service_name}",
                                "status": "FAIL",
                                "details": f"HTTP {response.status}"
                            })
            except Exception as e:
                print(f"❌ {service_name}: {str(e)}")
                self.results.append({
                    "test": f"health_{service_name}",
                    "status": "FAIL",
                    "details": str(e)
                })
    
    async def test_mcp_server_tools_list(self) -> None:
        """Test the MCP server tools list endpoint."""
        print("\n🔍 Testing MCP Server Tools List...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_urls['mcp_server']}/tools/list") as response:
                    if response.status == 200:
                        data = await response.json()
                        tools = data.get("tools", [])
                        if len(tools) > 0:
                            print(f"✅ MCP Server Tools List: Found {len(tools)} tools")
                            for tool in tools:
                                print(f"   - {tool.get('name')}: {tool.get('description')}")
                            self.results.append({
                                "test": "mcp_server_tools_list",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print("❌ MCP Server Tools List: No tools found")
                            self.results.append({
                                "test": "mcp_server_tools_list",
                                "status": "FAIL",
                                "details": "No tools found"
                            })
                    else:
                        print(f"❌ MCP Server Tools List: HTTP {response.status}")
                        self.results.append({
                            "test": "mcp_server_tools_list",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ MCP Server Tools List: {str(e)}")
            self.results.append({
                "test": "mcp_server_tools_list",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_mcp_server_echo_tool(self) -> None:
        """Test the MCP server echo tool directly."""
        print("\n🔍 Testing MCP Server Echo Tool (Direct)...")
        
        try:
            async with aiohttp.ClientSession() as session:
                test_message = "Hello from MCP test!"
                test_request = {
                    "message": test_message,
                    "prefix": "MCP Echo: "
                }
                
                async with session.post(
                    f"{self.base_urls['mcp_server']}/tools/echo",
                    json=test_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        expected_result = f"MCP Echo: {test_message}"
                        if data.get("result") == expected_result:
                            print(f"✅ MCP Server Echo Tool: {data['result']}")
                            self.results.append({
                                "test": "mcp_server_echo_tool",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print("❌ MCP Server Echo Tool: Unexpected result")
                            self.results.append({
                                "test": "mcp_server_echo_tool",
                                "status": "FAIL",
                                "details": f"Expected: {expected_result}, Got: {data.get('result')}"
                            })
                    else:
                        print(f"❌ MCP Server Echo Tool: HTTP {response.status}")
                        self.results.append({
                            "test": "mcp_server_echo_tool",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ MCP Server Echo Tool: {str(e)}")
            self.results.append({
                "test": "mcp_server_echo_tool",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_main_backend_mcp_tools_list(self) -> None:
        """Test the main backend's MCP tools list endpoint."""
        print("\n🔍 Testing Main Backend MCP Tools List...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_urls['main_backend']}/mcp/tools/list") as response:
                    if response.status == 200:
                        data = await response.json()
                        tools = data.get("tools", [])
                        if len(tools) > 0:
                            print(f"✅ Main Backend MCP Tools List: Found {len(tools)} tools")
                            for tool in tools:
                                print(f"   - {tool.get('name')}: {tool.get('description')}")
                            self.results.append({
                                "test": "main_backend_mcp_tools_list",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print("❌ Main Backend MCP Tools List: No tools found")
                            self.results.append({
                                "test": "main_backend_mcp_tools_list",
                                "status": "FAIL",
                                "details": "No tools found"
                            })
                    else:
                        print(f"❌ Main Backend MCP Tools List: HTTP {response.status}")
                        self.results.append({
                            "test": "main_backend_mcp_tools_list",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ Main Backend MCP Tools List: {str(e)}")
            self.results.append({
                "test": "main_backend_mcp_tools_list",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_main_backend_mcp_tool_call(self) -> None:
        """Test the main backend's MCP tool call endpoint."""
        print("\n🔍 Testing Main Backend MCP Tool Call...")
        
        try:
            async with aiohttp.ClientSession() as session:
                test_request = {
                    "request": {
                        "tool_name": "echo",
                        "input_data": {
                            "message": "Hello from main backend!",
                            "prefix": "Main Backend Echo: "
                        }
                    }
                }
                
                async with session.post(
                    f"{self.base_urls['main_backend']}/mcp/tools/call",
                    json=test_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success") and "result" in data.get("result", {}):
                            print(f"✅ Main Backend MCP Tool Call: {data['result']['result']}")
                            self.results.append({
                                "test": "main_backend_mcp_tool_call",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print("❌ Main Backend MCP Tool Call: Unexpected response format")
                            self.results.append({
                                "test": "main_backend_mcp_tool_call",
                                "status": "FAIL",
                                "details": "Unexpected response format"
                            })
                    else:
                        print(f"❌ Main Backend MCP Tool Call: HTTP {response.status}")
                        self.results.append({
                            "test": "main_backend_mcp_tool_call",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ Main Backend MCP Tool Call: {str(e)}")
            self.results.append({
                "test": "main_backend_mcp_tool_call",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_main_backend_mcp_health(self) -> None:
        """Test the main backend's MCP health check endpoint."""
        print("\n🔍 Testing Main Backend MCP Health Check...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_urls['main_backend']}/mcp/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            print("✅ Main Backend MCP Health Check: MCP server is healthy")
                            self.results.append({
                                "test": "main_backend_mcp_health",
                                "status": "PASS",
                                "details": data
                            })
                        else:
                            print(f"❌ Main Backend MCP Health Check: MCP server status is {data.get('status')}")
                            self.results.append({
                                "test": "main_backend_mcp_health",
                                "status": "FAIL",
                                "details": data
                            })
                    else:
                        print(f"❌ Main Backend MCP Health Check: HTTP {response.status}")
                        self.results.append({
                            "test": "main_backend_mcp_health",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ Main Backend MCP Health Check: {str(e)}")
            self.results.append({
                "test": "main_backend_mcp_health",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_llm_agent_generate(self) -> None:
        """Test LLM agent text generation."""
        print("\n🔍 Testing LLM Agent Generate...")
        
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.post(
                    f"{self.base_urls['llm_agent']}/generate/",
                    json=test_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "response" in data:
                            print("✅ LLM Agent Generate: Response received")
                            self.results.append({
                                "test": "llm_agent_generate",
                                "status": "PASS",
                                "details": {"response_length": len(data["response"])}
                            })
                        else:
                            print("❌ LLM Agent Generate: No response field")
                            self.results.append({
                                "test": "llm_agent_generate",
                                "status": "FAIL",
                                "details": "No response field in data"
                            })
                    else:
                        print(f"❌ LLM Agent Generate: HTTP {response.status}")
                        self.results.append({
                            "test": "llm_agent_generate",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ LLM Agent Generate: {str(e)}")
            self.results.append({
                "test": "llm_agent_generate",
                "status": "FAIL",
                "details": str(e)
            })
    
    async def test_main_backend_chat(self) -> None:
        """Test main backend chat endpoint."""
        print("\n🔍 Testing Main Backend Chat...")
        
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.post(
                    f"{self.base_urls['main_backend']}/chat",
                    json=test_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "response" in data:
                            print("✅ Main Backend Chat: Response received")
                            self.results.append({
                                "test": "main_backend_chat",
                                "status": "PASS",
                                "details": {"response_length": len(data["response"])}
                            })
                        else:
                            print("❌ Main Backend Chat: No response field")
                            self.results.append({
                                "test": "main_backend_chat",
                                "status": "FAIL",
                                "details": "No response field in data"
                            })
                    else:
                        print(f"❌ Main Backend Chat: HTTP {response.status}")
                        self.results.append({
                            "test": "main_backend_chat",
                            "status": "FAIL",
                            "details": f"HTTP {response.status}"
                        })
        except Exception as e:
            print(f"❌ Main Backend Chat: {str(e)}")
            self.results.append({
                "test": "main_backend_chat",
                "status": "FAIL",
                "details": str(e)
            })
    
    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 MCP INTEGRATION TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASS"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "="*60)
        
        if failed_tests == 0:
            print("🎉 All tests passed! MCP integration is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the service logs.")
    
    async def run_all_tests(self) -> None:
        """Run all tests."""
        print("🚀 Starting MCP Integration Tests...")
        print(f"Testing services at: {self.base_urls}")
        
        # Wait a bit for services to be ready
        print("⏳ Waiting for services to be ready...")
        await asyncio.sleep(5)
        
        # Run all tests
        await self.test_health_endpoints()
        await self.test_mcp_server_tools_list()
        await self.test_mcp_server_echo_tool()
        await self.test_main_backend_mcp_tools_list()
        await self.test_main_backend_mcp_tool_call()
        await self.test_main_backend_mcp_health()
        await self.test_llm_agent_generate()
        await self.test_main_backend_chat()
        
        # Print summary
        self.print_summary()


async def main():
    """Main test function."""
    tester = MCPIntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 