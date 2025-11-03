"""Test script to verify custom events emission from EventTrackingMiddleware.

This script tests the agent locally to ensure custom events are emitted
when tools/sub-agents execute.

Usage:
    python test_custom_events.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.agent.main import agent


async def test_custom_events():
    """Test that custom events are emitted during tool execution."""
    print("=" * 80)
    print("🧪 Testing Custom Events Emission")
    print("=" * 80)

    # Test configuration with workspace isolation
    config = {
        "configurable": {
            "company_slug": "test-company",
            "workspace_slug": "test-workspace",
            "thread_id": "test-thread-custom-events",
        }
    }

    # Test input that will trigger sub-agent execution
    test_input = {
        "messages": [
            {
                "role": "user",
                "content": "List all files in the workspace"
            }
        ]
    }

    print("\n📨 Input Message:")
    print(f"   {test_input['messages'][0]['content']}")
    print("\n🔍 Looking for custom events in stream...\n")

    custom_events_found = []

    try:
        # Stream with custom mode enabled
        async for chunk in agent.astream(
            test_input,
            config=config,
            stream_mode=["messages", "updates", "custom"]  # Include custom mode
        ):
            stream_mode = chunk[0] if isinstance(chunk, tuple) else "unknown"
            data = chunk[1] if isinstance(chunk, tuple) else chunk

            # Print all events for debugging
            if stream_mode == "custom":
                print(f"✅ CUSTOM EVENT RECEIVED!")
                print(f"   Event: {data.get('event', 'unknown')}")
                print(f"   Entity Type: {data.get('entity_type', 'N/A')}")
                print(f"   Tool Name: {data.get('tool_name', 'N/A')}")
                print(f"   Status: {data.get('status', 'N/A')}")
                if data.get('task_description'):
                    print(f"   Task: {data.get('task_description')[:80]}...")
                print()
                custom_events_found.append(data)

            elif stream_mode == "messages":
                # Show AI messages
                if hasattr(data, 'content') and data.content:
                    print(f"💬 Message: {data.content[:100]}...")

            elif stream_mode == "updates":
                # Show state updates
                if isinstance(data, dict) and 'messages' in data:
                    last_msg = data['messages'][-1] if data['messages'] else None
                    if last_msg and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        print(f"🔧 Tool Call Detected: {last_msg.tool_calls[0].get('name', 'unknown')}")

    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Analysis
    print("\n" + "=" * 80)
    print("📊 Test Results")
    print("=" * 80)

    if not custom_events_found:
        print("❌ FAILED: No custom events received!")
        print("\nPossible issues:")
        print("  1. EventTrackingMiddleware not in middleware stack")
        print("  2. stream_mode doesn't include 'custom'")
        print("  3. No tools/sub-agents were executed")
        print("  4. runtime.stream_writer not available")
        return False

    print(f"✅ SUCCESS: {len(custom_events_found)} custom events received!\n")

    # Analyze event types
    event_types = {}
    for event in custom_events_found:
        event_type = event.get('event', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1

    print("Event breakdown:")
    for event_type, count in event_types.items():
        print(f"  - {event_type}: {count}")

    # Check for expected events
    has_starting = any(e.get('event') == 'tool_execution_starting' for e in custom_events_found)
    has_completed = any(e.get('event') == 'tool_execution_completed' for e in custom_events_found)

    print("\nExpected events:")
    print(f"  {'✅' if has_starting else '❌'} tool_execution_starting")
    print(f"  {'✅' if has_completed else '❌'} tool_execution_completed")

    # Show sample event
    if custom_events_found:
        print("\n📝 Sample Event (first):")
        print(json.dumps(custom_events_found[0], indent=2))

    return has_starting and has_completed


async def test_error_event():
    """Test that error events are emitted when tool fails."""
    print("\n" + "=" * 80)
    print("🧪 Testing Error Events")
    print("=" * 80)

    config = {
        "configurable": {
            "company_slug": "test-company",
            "workspace_slug": "test-workspace",
            "thread_id": "test-thread-error-events",
        }
    }

    # Test input that will likely cause an error (nonexistent file)
    test_input = {
        "messages": [
            {
                "role": "user",
                "content": "Read the file /nonexistent/file/path.txt"
            }
        ]
    }

    print("\n📨 Input Message:")
    print(f"   {test_input['messages'][0]['content']}")
    print("\n🔍 Looking for error events...\n")

    error_events = []

    try:
        async for chunk in agent.astream(
            test_input,
            config=config,
            stream_mode=["custom"]
        ):
            stream_mode = chunk[0] if isinstance(chunk, tuple) else "unknown"
            data = chunk[1] if isinstance(chunk, tuple) else chunk

            if stream_mode == "custom" and data.get('event') == 'tool_execution_error':
                print(f"✅ ERROR EVENT RECEIVED!")
                print(f"   Tool: {data.get('tool_name')}")
                print(f"   Error: {data.get('error_message', 'N/A')[:80]}...")
                print()
                error_events.append(data)

    except Exception as e:
        # Expected to have errors in the agent execution
        print(f"⚠️  Agent error (expected): {type(e).__name__}")

    print("\n" + "=" * 80)
    print("📊 Error Event Results")
    print("=" * 80)

    if error_events:
        print(f"✅ SUCCESS: {len(error_events)} error events received!")
        print("\n📝 Sample Error Event:")
        print(json.dumps(error_events[0], indent=2))
        return True
    else:
        print("❌ No error events received (might be expected if no errors occurred)")
        return False


async def main():
    """Run all tests."""
    print("\n🚀 Starting Custom Events Test Suite\n")

    # Check environment
    if not os.getenv("GCS_BUCKET_NAME"):
        print("❌ Error: GCS_BUCKET_NAME not set in environment")
        print("   Set it in .env file")
        return

    if not os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON"):
        print("❌ Error: GOOGLE_CLOUD_CREDENTIALS_JSON not set")
        print("   Set it in .env file")
        return

    print("✅ Environment configured\n")

    # Run tests
    test1_passed = await test_custom_events()

    # Uncomment to test error events
    # test2_passed = await test_error_event()

    print("\n" + "=" * 80)
    print("🏁 Test Suite Complete")
    print("=" * 80)

    if test1_passed:
        print("✅ All tests passed!")
        print("\nNext steps:")
        print("  1. Verify events have correct structure")
        print("  2. Test with backend SSE proxy")
        print("  3. Test frontend event processing")
    else:
        print("❌ Some tests failed. Check output above.")
        print("\nDebugging tips:")
        print("  1. Check middleware stack in src/agent/main.py")
        print("  2. Verify EventTrackingMiddleware is before SubAgentMiddleware")
        print("  3. Check that stream_mode includes 'custom'")
        print("  4. Run with langgraph dev and check logs")


if __name__ == "__main__":
    asyncio.run(main())
