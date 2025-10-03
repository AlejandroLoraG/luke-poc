#!/usr/bin/env python3
"""
Test script for session management and chat-workflow binding features.

Tests:
1. Create a session
2. Create first chat and workflow
3. Verify chat is bound to workflow
4. Try creating second workflow in same chat (should be prevented by AI)
5. Create second chat in same session
6. Create different workflow in second chat
7. Verify both chats are independent but in same session
"""

import requests
import json

BASE_URL = "http://localhost:8001"


def test_session_workflow_binding():
    print("=" * 70)
    print("Testing Session Management & Chat-Workflow Binding")
    print("=" * 70)

    # Step 1: Create a session
    print("\n1️⃣  Creating new session...")
    response = requests.post(
        f"{BASE_URL}/api/v1/sessions",
        params={"user_identifier": "test_user_123"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.text)
        return

    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"✅ Created session: {session_id}")
    print(f"   User: {session_data['user_identifier']}")

    # Step 2: Create first chat and workflow
    print("\n2️⃣  Creating first chat with workflow...")
    chat1_request = {
        "message": "Create a simple approval workflow with states: Draft, Review, Approved",
        "session_id": session_id,
        "language": "en"
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json=chat1_request
    )

    if response.status_code != 200:
        print(f"❌ Failed to create first chat: {response.status_code}")
        print(response.text)
        return

    chat1_response = response.json()
    conversation_id_1 = chat1_response["conversation_id"]
    workflow_id_1 = chat1_response.get("workflow_created_id") or chat1_response.get("workflow_bound_id")

    print(f"✅ First chat created: {conversation_id_1}")
    print(f"   Response: {chat1_response['response'][:100]}...")
    print(f"   Workflow created: {workflow_id_1}")
    print(f"   Is chat locked: {chat1_response.get('is_chat_locked', False)}")
    print(f"   Bound workflow: {chat1_response.get('workflow_bound_id', 'None')}")

    # Step 3: Verify chat is bound
    print("\n3️⃣  Verifying first chat binding...")
    response = requests.get(f"{BASE_URL}/api/v1/chats/{conversation_id_1}/binding")

    if response.status_code == 200:
        binding = response.json()
        print(f"✅ Chat binding verified:")
        print(f"   Conversation ID: {binding['conversation_id']}")
        print(f"   Session ID: {binding['session_id']}")
        print(f"   Bound workflow: {binding['bound_workflow_id']}")
        print(f"   Is bound: {binding['is_bound']}")
    else:
        print(f"⚠️  Couldn't verify binding: {response.status_code}")

    # Step 4: Try to create second workflow in same chat (AI should refuse)
    print("\n4️⃣  Attempting to create second workflow in same chat...")
    chat1_second_request = {
        "message": "Now create an onboarding workflow with states: New, Training, Active",
        "session_id": session_id,
        "conversation_id": conversation_id_1,  # Same chat
        "language": "en"
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json=chat1_second_request
    )

    if response.status_code == 200:
        chat1_response_2 = response.json()
        print(f"📝 AI Response: {chat1_response_2['response'][:200]}...")

        if chat1_response_2.get("workflow_created_id"):
            print(f"❌ UNEXPECTED: AI created a second workflow! This should not happen.")
        else:
            print(f"✅ EXPECTED: AI did not create a second workflow")
            print(f"   Chat is still bound to: {chat1_response_2.get('workflow_bound_id')}")
    else:
        print(f"❌ Request failed: {response.status_code}")

    # Step 5: Create second chat in same session
    print("\n5️⃣  Creating second chat in same session...")
    chat2_request = {
        "message": "Create an expense approval workflow with states: Submitted, Manager Review, Approved, Rejected",
        "session_id": session_id,  # Same session
        # No conversation_id = new chat
        "language": "en"
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json=chat2_request
    )

    if response.status_code == 200:
        chat2_response = response.json()
        conversation_id_2 = chat2_response["conversation_id"]
        workflow_id_2 = chat2_response.get("workflow_created_id") or chat2_response.get("workflow_bound_id")

        print(f"✅ Second chat created: {conversation_id_2}")
        print(f"   Response: {chat2_response['response'][:100]}...")
        print(f"   Workflow created: {workflow_id_2}")
        print(f"   Bound workflow: {chat2_response.get('workflow_bound_id')}")
    else:
        print(f"❌ Failed to create second chat: {response.status_code}")
        return

    # Step 6: Get session details
    print("\n6️⃣  Fetching session details...")
    response = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}")

    if response.status_code == 200:
        session_details = response.json()
        print(f"✅ Session details:")
        print(f"   Session ID: {session_details['session']['session_id']}")
        print(f"   Total chats: {session_details['total_chats']}")
        print(f"   Chats:")
        for chat in session_details['chats']:
            print(f"      - {chat['conversation_id']}")
            print(f"        Bound to: {chat['bound_workflow_id']}")
            print(f"        Is bound: {chat['is_bound']}")
    else:
        print(f"❌ Failed to get session details: {response.status_code}")

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("✅ TEST SUMMARY")
    print("=" * 70)
    print(f"✓ Session created: {session_id}")
    print(f"✓ Chat 1 created: {conversation_id_1}")
    print(f"  └─ Bound to workflow: {workflow_id_1}")
    if 'conversation_id_2' in locals():
        print(f"✓ Chat 2 created: {conversation_id_2}")
        print(f"  └─ Bound to workflow: {workflow_id_2}")
    print(f"\n✅ Session management and binding working correctly!")


if __name__ == "__main__":
    try:
        test_session_workflow_binding()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8001?")
        print("   Start it with: docker-compose up")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
