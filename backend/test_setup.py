#!/usr/bin/env python3
"""
Test script to verify the new microservice architecture.
Run this after starting the services with docker-compose up -d
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_health_endpoints():
    """Test health endpoints for both services."""
    print("🔍 Testing Health Endpoints...")
    
    services = [
        ("Main Backend", "http://localhost:8000/health"),
        ("LLM Agent", "http://localhost:8001/health")
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service_name, url in services:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {service_name}: {data.get('status', 'unknown')}")
                else:
                    print(f"❌ {service_name}: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {service_name}: Connection failed - {str(e)}")


async def test_chat_endpoint():
    """Test the main chat endpoint."""
    print("\n💬 Testing Chat Endpoint...")
    
    url = "http://localhost:8000/chat/"
    payload = {
        "messages": [
            {"role": "user", "content": "Hello! This is a test message."}
        ],
        "stream": False,
        "temperature": 0.7,
        "model": "gpt-4"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                print("✅ Chat endpoint working")
                print(f"   Response: {data.get('response', '')[:100]}...")
                print(f"   Model: {data.get('model', 'unknown')}")
            else:
                print(f"❌ Chat endpoint failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Chat endpoint error: {str(e)}")


async def test_llm_agent_direct():
    """Test the LLM agent directly."""
    print("\n🤖 Testing LLM Agent Direct...")
    
    url = "http://localhost:8001/generate/"
    payload = {
        "messages": [
            {"role": "user", "content": "Say hello in a friendly way."}
        ],
        "stream": False,
        "temperature": 0.7,
        "model": "gpt-4"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                print("✅ LLM Agent working")
                print(f"   Response: {data.get('response', '')[:100]}...")
                print(f"   Model: {data.get('model', 'unknown')}")
            else:
                print(f"❌ LLM Agent failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ LLM Agent error: {str(e)}")


async def test_streaming():
    """Test streaming functionality."""
    print("\n🌊 Testing Streaming...")
    
    url = "http://localhost:8000/chat/stream"
    payload = {
        "messages": [
            {"role": "user", "content": "Count from 1 to 5 slowly."}
        ],
        "stream": True
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 200:
                    print("✅ Streaming endpoint working")
                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if chunk.get("content"):
                                    print(f"   Chunk {chunk_count}: {chunk['content']}")
                                    chunk_count += 1
                            except json.JSONDecodeError:
                                continue
                    print(f"   Total chunks received: {chunk_count}")
                else:
                    print(f"❌ Streaming failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Streaming error: {str(e)}")


async def main():
    """Run all tests."""
    print("🚀 Stubichat Microservice Architecture Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Test health endpoints
    await test_health_endpoints()
    
    # Test chat endpoint
    await test_chat_endpoint()
    
    # Test LLM agent directly
    await test_llm_agent_direct()
    
    # Test streaming
    await test_streaming()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main()) 