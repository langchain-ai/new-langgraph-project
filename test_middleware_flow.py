"""
Test middleware flow to debug gcs_root_path propagation issue.

This test file helps understand how state flows through middleware layers.
"""

import asyncio
from typing import Any
from contextlib import contextmanager
from langchain_core.runnables.config import var_child_runnable_config


@contextmanager
def mock_config(config: dict):
    """Context manager to set LangGraph config context variable."""
    token = var_child_runnable_config.set(config)
    try:
        yield
    finally:
        var_child_runnable_config.reset(token)


def test_config_to_state_middleware():
    """Test ConfigToStateMiddleware in isolation."""
    print("=" * 70)
    print("TEST 1: ConfigToStateMiddleware in isolation")
    print("=" * 70)

    from src.agent.middleware.config_to_state import ConfigToStateMiddleware

    middleware = ConfigToStateMiddleware()

    # Mock state and runtime
    state = {"messages": []}

    class MockRuntime:
        pass

    runtime = MockRuntime()

    # Mock config with gcs_root_path
    test_config = {
        "configurable": {
            "gcs_root_path": "/company-123/workspace-456/"
        }
    }

    print(f"\nInput state: {state}")
    print(f"Config: {test_config}")

    # Test with mocked config
    with mock_config(test_config):
        try:
            result = middleware.before_agent(state, runtime)
            print(f"✓ before_agent returned: {result}")
        except Exception as e:
            print(f"✗ before_agent failed: {e}")
            return False

    # Test async version
    with mock_config(test_config):
        try:
            result = asyncio.run(middleware.abefore_agent(state, runtime))
            print(f"✓ abefore_agent returned: {result}")
        except Exception as e:
            print(f"✗ abefore_agent failed: {e}")
            return False

    # Test without gcs_root_path
    print("\n--- Testing without gcs_root_path ---")
    empty_config = {"configurable": {}}

    with mock_config(empty_config):
        try:
            result = middleware.before_agent(state, runtime)
            print(f"✗ Should have raised ValueError, got: {result}")
            return False
        except ValueError as e:
            print(f"✓ Correctly raised ValueError: {e}")

    return True


def test_gcs_runtime_middleware():
    """Test GCSRuntimeMiddleware in isolation."""
    print("\n" + "=" * 70)
    print("TEST 2: GCSRuntimeMiddleware in isolation")
    print("=" * 70)

    from src.agent.sub_agents.gcs_filesystem.middleware import GCSRuntimeMiddleware

    middleware = GCSRuntimeMiddleware()

    # Mock state WITH gcs_root_path
    state_with_path = {
        "messages": [],
        "gcs_root_path": "/company-123/workspace-456/"
    }

    # Mock state WITHOUT gcs_root_path
    state_without_path = {
        "messages": []
    }

    class MockRuntime:
        pass

    runtime = MockRuntime()

    print(f"\nInput state (with path): {state_with_path}")

    # Test sync version WITH path
    try:
        result = middleware.before_agent(state_with_path, runtime)
        print(f"✓ before_agent (with path) returned: {result}")
    except Exception as e:
        print(f"✗ before_agent (with path) failed: {e}")
        return False

    # Test async version WITH path
    try:
        result = asyncio.run(middleware.abefore_agent(state_with_path, runtime))
        print(f"✓ abefore_agent (with path) returned: {result}")
    except Exception as e:
        print(f"✗ abefore_agent (with path) failed: {e}")
        return False

    # Test WITHOUT path
    print(f"\nInput state (without path): {state_without_path}")

    try:
        result = middleware.before_agent(state_without_path, runtime)
        print(f"✗ Should have raised ValueError, got: {result}")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

    return True


def test_subagent_middleware_state_propagation():
    """Test how SubAgentMiddleware creates sub-agent state."""
    print("\n" + "=" * 70)
    print("TEST 3: SubAgentMiddleware state creation")
    print("=" * 70)

    # Simulate what deepagents SubAgentMiddleware does
    _EXCLUDED_STATE_KEYS = ("messages", "todos")

    # Main agent state (after ConfigToStateMiddleware)
    main_agent_state = {
        "messages": ["message1", "message2"],
        "todos": ["todo1"],
        "gcs_root_path": "/company-123/workspace-456/",
        "other_key": "other_value"
    }

    print(f"\nMain agent state: {main_agent_state}")

    # Simulate SubAgentMiddleware creating sub-agent state
    # From deepagents/middleware/subagents.py:332
    subagent_state = {
        k: v for k, v in main_agent_state.items()
        if k not in _EXCLUDED_STATE_KEYS
    }
    subagent_state["messages"] = ["<new HumanMessage with task description>"]

    print(f"Sub-agent state (after SubAgentMiddleware): {subagent_state}")

    # Verify gcs_root_path is present
    if "gcs_root_path" in subagent_state:
        print(f"✓ gcs_root_path present in sub-agent state: {subagent_state['gcs_root_path']}")
        return True
    else:
        print(f"✗ gcs_root_path MISSING from sub-agent state!")
        return False


def test_middleware_return_value_merge():
    """Test how middleware return values merge with state."""
    print("\n" + "=" * 70)
    print("TEST 4: Middleware return value merging")
    print("=" * 70)

    # Simulate what happens when middleware returns a dict
    initial_state = {
        "messages": [],
        "existing_key": "existing_value"
    }

    print(f"\nInitial state: {initial_state}")

    # Middleware returns this
    middleware_return = {
        "gcs_root_path": "/company-123/workspace-456/"
    }

    print(f"Middleware returns: {middleware_return}")

    # In LangGraph, middleware return values are merged into state
    updated_state = {**initial_state, **middleware_return}

    print(f"Updated state (after merge): {updated_state}")

    if "gcs_root_path" in updated_state:
        print(f"✓ gcs_root_path merged into state: {updated_state['gcs_root_path']}")
        return True
    else:
        print(f"✗ gcs_root_path NOT merged into state!")
        return False


def test_full_flow_simulation():
    """Simulate the complete flow from main agent to sub-agent."""
    print("\n" + "=" * 70)
    print("TEST 5: Full flow simulation")
    print("=" * 70)

    from src.agent.middleware.config_to_state import ConfigToStateMiddleware
    from src.agent.sub_agents.gcs_filesystem.middleware import GCSRuntimeMiddleware

    # Step 1: Config comes from frontend
    request_config = {
        "configurable": {
            "gcs_root_path": "/company-123/workspace-456/"
        }
    }

    print(f"\n[Step 1] Request config: {request_config}")

    # Step 2: Main agent starts with empty state
    main_agent_state = {
        "messages": []
    }

    print(f"[Step 2] Main agent initial state: {main_agent_state}")

    # Step 3: ConfigToStateMiddleware.before_agent() is called
    config_middleware = ConfigToStateMiddleware()

    class MockRuntime:
        pass

    runtime = MockRuntime()

    with mock_config(request_config):
        try:
            config_update = config_middleware.before_agent(main_agent_state, runtime)
            print(f"[Step 3] ConfigToStateMiddleware returned: {config_update}")

            # LangGraph merges this into state
            main_agent_state = {**main_agent_state, **config_update}
            print(f"[Step 3] Main agent state after merge: {main_agent_state}")
        except Exception as e:
            print(f"[Step 3] ✗ ConfigToStateMiddleware failed: {e}")
            return False

    # Step 4: SubAgentMiddleware creates sub-agent state
    _EXCLUDED_STATE_KEYS = ("messages", "todos")
    subagent_state = {
        k: v for k, v in main_agent_state.items()
        if k not in _EXCLUDED_STATE_KEYS
    }
    subagent_state["messages"] = ["<task description>"]

    print(f"[Step 4] Sub-agent state created: {subagent_state}")

    # Step 5: GCSRuntimeMiddleware.abefore_agent() is called
    gcs_middleware = GCSRuntimeMiddleware()

    try:
        gcs_update = asyncio.run(gcs_middleware.abefore_agent(subagent_state, runtime))
        print(f"[Step 5] GCSRuntimeMiddleware returned: {gcs_update}")
        print(f"✓ Full flow successful!")
        return True
    except Exception as e:
        print(f"[Step 5] ✗ GCSRuntimeMiddleware failed: {e}")
        print(f"         Sub-agent state keys: {list(subagent_state.keys())}")
        print(f"         'gcs_root_path' present: {'gcs_root_path' in subagent_state}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MIDDLEWARE FLOW DEBUG TESTS")
    print("=" * 70)

    results = []

    results.append(("ConfigToStateMiddleware", test_config_to_state_middleware()))
    results.append(("GCSRuntimeMiddleware", test_gcs_runtime_middleware()))
    results.append(("SubAgentMiddleware state propagation", test_subagent_middleware_state_propagation()))
    results.append(("Middleware return value merge", test_middleware_return_value_merge()))
    results.append(("Full flow simulation", test_full_flow_simulation()))

    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ All tests passed! Middleware flow is correct in isolation.")
        print("   Issue must be in the actual agent execution environment.")
    else:
        print("\n❌ Some tests failed! Issue is in the middleware implementation.")
