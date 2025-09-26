#!/usr/bin/env python3
"""
Integration test script for the Chat Agent PoC system.
Tests the complete flow: AI Agent -> MCP Server -> svc-builder
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


async def test_service_health(service_name: str, url: str) -> bool:
    """Test if a service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                print(f"✅ {service_name} is healthy")
                return True
            else:
                print(f"❌ {service_name} health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ {service_name} is not accessible: {e}")
        return False


async def test_svc_builder():
    """Test svc-builder functionality."""
    print("\n📁 Testing svc-builder...")

    base_url = "http://localhost:8000/api/v1"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Test list workflows
            response = await client.get(f"{base_url}/workflows")
            if response.status_code == 200:
                workflows = response.json()
                print(f"✅ svc-builder has {workflows['total_count']} workflows")
            else:
                print(f"❌ Failed to list workflows: {response.status_code}")
                return False

            # Test get specific workflow
            if workflows['total_count'] > 0:
                first_workflow = workflows['workflows'][0]
                spec_id = first_workflow['spec_id']

                response = await client.get(f"{base_url}/workflows/{spec_id}")
                if response.status_code == 200:
                    workflow_data = response.json()
                    print(f"✅ Retrieved workflow '{spec_id}': {workflow_data['workflow_spec']['name']}")
                else:
                    print(f"❌ Failed to get workflow {spec_id}: {response.status_code}")
                    return False

            return True

    except Exception as e:
        print(f"❌ svc-builder test failed: {e}")
        return False


async def test_ai_agent():
    """Test AI Agent functionality."""
    print("\n🤖 Testing AI Agent...")

    base_url = "http://localhost:8001/api/v1"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Test basic chat
            chat_request = {
                "message": "Hello! Can you help me with workflows?"
            }

            response = await client.post(f"{base_url}/chat", json=chat_request)
            if response.status_code == 200:
                chat_data = response.json()
                print(f"✅ AI Agent responded: {chat_data['response'][:100]}...")
                conversation_id = chat_data['conversation_id']
            else:
                print(f"❌ AI Agent chat failed: {response.status_code}")
                return False

            # Test chat with workflow_id
            chat_with_workflow = {
                "message": "What is the wf_incidentes workflow about?",
                "workflow_id": "wf_incidentes",
                "conversation_id": conversation_id
            }

            response = await client.post(f"{base_url}/chat", json=chat_with_workflow)
            if response.status_code == 200:
                chat_data = response.json()
                print(f"✅ AI Agent with workflow: {chat_data['response'][:100]}...")
                print(f"✅ Tools used: {chat_data.get('mcp_tools_used', [])}")
            else:
                print(f"❌ AI Agent workflow chat failed: {response.status_code}")
                return False

            return True

    except Exception as e:
        print(f"❌ AI Agent test failed: {e}")
        return False


async def test_workflow_conversation():
    """Test a complete workflow conversation."""
    print("\n💬 Testing Complete Workflow Conversation...")

    base_url = "http://localhost:8001/api/v1"

    conversation_tests = [
        {
            "message": "What workflows are available?",
            "description": "List available workflows"
        },
        {
            "message": "Tell me about the incident management workflow",
            "workflow_id": "wf_incidentes",
            "description": "Describe specific workflow"
        },
        {
            "message": "What states does this workflow have?",
            "workflow_id": "wf_incidentes",
            "description": "Get workflow states"
        },
        {
            "message": "What can I do from the reportado state?",
            "workflow_id": "wf_incidentes",
            "description": "Get available actions"
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            conversation_id = None

            for test in conversation_tests:
                print(f"🗣️  Testing: {test['description']}")

                request_data = {
                    "message": test["message"]
                }

                if "workflow_id" in test:
                    request_data["workflow_id"] = test["workflow_id"]

                if conversation_id:
                    request_data["conversation_id"] = conversation_id

                response = await client.post(f"{base_url}/chat", json=request_data)

                if response.status_code == 200:
                    chat_data = response.json()
                    conversation_id = chat_data['conversation_id']
                    print(f"✅ Response: {chat_data['response'][:150]}...")
                    if chat_data.get('mcp_tools_used'):
                        print(f"   🔧 MCP Tools: {chat_data['mcp_tools_used']}")
                else:
                    print(f"❌ Failed: {response.status_code}")
                    return False

                # Brief pause between requests
                await asyncio.sleep(1)

            print("✅ Complete conversation flow successful!")
            return True

    except Exception as e:
        print(f"❌ Conversation test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 Starting Chat Agent PoC Integration Tests")
    print("=" * 50)

    # Test service health
    print("\n🏥 Health Checks...")
    services = [
        ("svc-builder", "http://localhost:8000/api/v1/health"),
        ("MCP Server", "http://localhost:8002/health"),  # Note: May not exist yet
        ("AI Agent", "http://localhost:8001/api/v1/health")
    ]

    healthy_services = 0
    for service_name, health_url in services:
        if await test_service_health(service_name, health_url):
            healthy_services += 1

    print(f"\n📊 Services Status: {healthy_services}/{len(services)} healthy")

    if healthy_services < 2:  # At least svc-builder and AI Agent
        print("❌ Not enough services running for integration tests")
        return False

    # Run component tests
    tests = [
        ("svc-builder", test_svc_builder),
        ("AI Agent", test_ai_agent),
        ("Complete Conversation", test_workflow_conversation)
    ]

    passed_tests = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} tests...")
        try:
            if await test_func():
                passed_tests += 1
                print(f"✅ {test_name} tests passed")
            else:
                print(f"❌ {test_name} tests failed")
        except Exception as e:
            print(f"❌ {test_name} tests crashed: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed_tests}/{len(tests)} test suites passed")

    if passed_tests == len(tests):
        print("🎉 All integration tests passed! PoC is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)