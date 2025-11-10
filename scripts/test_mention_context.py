#!/usr/bin/env python3
"""Integration test for mention context system.

Tests the @[filename] mention system by sending requests with
mention_context to the agent and verifying the responses.

Usage:
    python scripts/test_mention_context.py

Requirements:
    - langgraph server running (langgraph dev)
    - Environment variables set (GOOGLE_CLOUD_CREDENTIALS_JSON, etc.)
"""

import asyncio
import os
import sys

from langgraph_sdk import get_client


async def test_single_file_mention():
    """Test agent with single file mention."""
    print("\n" + "=" * 60)
    print("TEST 1: Single File Mention")
    print("=" * 60)

    client = get_client(url="http://localhost:8123")

    try:
        # Create thread
        thread = await client.threads.create()
        print(f"✓ Created thread: {thread['thread_id']}")

        # Send request with mention context
        print("\nSending message with @[test_file.txt] mention...")
        response = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "What's in @[test_file.txt]?",
                    }
                ]
            },
            config={
                "configurable": {
                    "company_slug": "test-company",
                    "workspace_slug": "test-workspace",
                    "mention_context": {
                        "files": [
                            {
                                "path": "test_file.txt",
                                "content": "This is a test file.\nLine 2.\nLine 3.",
                            }
                        ],
                        "folders": [],
                    },
                }
            },
        )

        print(f"✓ Received response")
        print(f"Response: {response}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_folder_mention():
    """Test agent with folder mention."""
    print("\n" + "=" * 60)
    print("TEST 2: Folder Mention")
    print("=" * 60)

    client = get_client(url="http://localhost:8123")

    try:
        # Create thread
        thread = await client.threads.create()
        print(f"✓ Created thread: {thread['thread_id']}")

        # Send request with folder mention
        print("\nSending message with @[reports/] mention...")
        response = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "List files in @[reports/]",
                    }
                ]
            },
            config={
                "configurable": {
                    "company_slug": "test-company",
                    "workspace_slug": "test-workspace",
                    "mention_context": {
                        "files": [],
                        "folders": [
                            {
                                "path": "reports/",
                                "files": ["report1.pdf", "report2.pdf", "summary.txt"],
                            }
                        ],
                    },
                }
            },
        )

        print(f"✓ Received response")
        print(f"Response: {response}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_multiple_files():
    """Test agent with multiple file mentions."""
    print("\n" + "=" * 60)
    print("TEST 3: Multiple File Mentions")
    print("=" * 60)

    client = get_client(url="http://localhost:8123")

    try:
        # Create thread
        thread = await client.threads.create()
        print(f"✓ Created thread: {thread['thread_id']}")

        # Send request with multiple files
        print("\nSending message with @[file1.txt] and @[file2.txt] mentions...")
        response = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "Compare @[file1.txt] and @[file2.txt]",
                    }
                ]
            },
            config={
                "configurable": {
                    "company_slug": "test-company",
                    "workspace_slug": "test-workspace",
                    "mention_context": {
                        "files": [
                            {
                                "path": "file1.txt",
                                "content": "Revenue Q1: $100,000",
                            },
                            {
                                "path": "file2.txt",
                                "content": "Revenue Q2: $150,000",
                            },
                        ],
                        "folders": [],
                    },
                }
            },
        )

        print(f"✓ Received response")
        print(f"Response: {response}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_no_mention_context():
    """Test backward compatibility (no mention context)."""
    print("\n" + "=" * 60)
    print("TEST 4: No Mention Context (Backward Compatibility)")
    print("=" * 60)

    client = get_client(url="http://localhost:8123")

    try:
        # Create thread
        thread = await client.threads.create()
        print(f"✓ Created thread: {thread['thread_id']}")

        # Send request WITHOUT mention context
        print("\nSending normal message without mention context...")
        response = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "List all files in workspace",
                    }
                ]
            },
            config={
                "configurable": {
                    "company_slug": "test-company",
                    "workspace_slug": "test-workspace",
                    # No mention_context
                }
            },
        )

        print(f"✓ Received response")
        print(f"Response: {response}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_empty_mention_context():
    """Test with empty mention context."""
    print("\n" + "=" * 60)
    print("TEST 5: Empty Mention Context")
    print("=" * 60)

    client = get_client(url="http://localhost:8123")

    try:
        # Create thread
        thread = await client.threads.create()
        print(f"✓ Created thread: {thread['thread_id']}")

        # Send request with empty mention context
        print("\nSending message with empty mention context...")
        response = await client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "What files do I have?",
                    }
                ]
            },
            config={
                "configurable": {
                    "company_slug": "test-company",
                    "workspace_slug": "test-workspace",
                    "mention_context": {
                        "files": [],
                        "folders": [],
                    },
                }
            },
        )

        print(f"✓ Received response")
        print(f"Response: {response}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MENTION CONTEXT INTEGRATION TESTS")
    print("=" * 60)
    print("\nEnsure langgraph server is running: langgraph dev")
    print("Press Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTests cancelled.")
        sys.exit(0)

    results = []

    # Run tests
    results.append(("Single File Mention", await test_single_file_mention()))
    results.append(("Folder Mention", await test_folder_mention()))
    results.append(("Multiple Files", await test_multiple_files()))
    results.append(("No Mention Context", await test_no_mention_context()))
    results.append(("Empty Mention Context", await test_empty_mention_context()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
