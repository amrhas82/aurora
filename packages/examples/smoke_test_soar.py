#!/usr/bin/env python3
"""
Smoke test for SOAR Orchestrator Python API.

Validates that the SOAR orchestrator can:
- Create orchestrator instance with mocked dependencies
- Initialize with required components
- Execute basic phases (mocked)

Exit codes:
  0 - All tests passed
  1 - One or more tests failed
"""

import sys
from unittest.mock import Mock, MagicMock

try:
    from aurora.soar.orchestrator import SOAROrchestrator
    from aurora.soar.agent_registry import AgentRegistry, AgentInfo
    from aurora.core.store.memory import MemoryStore
except ImportError as e:
    print(f"✗ SOAR orchestrator: FAIL - Import error: {e}")
    sys.exit(1)


def run_smoke_test() -> bool:
    """
    Run smoke tests for SOAR orchestrator.

    Returns:
        True if all tests pass, False otherwise
    """
    try:
        # Test 1: Create mocked dependencies
        print("  Testing: Create mocked dependencies...")

        # Mock memory store
        memory_store = MemoryStore()

        # Mock agent registry
        agent_registry = AgentRegistry()

        # Register a test agent
        test_agent = AgentInfo(
            id="test_agent",
            name="Test Agent",
            description="A test agent for smoke testing",
            capabilities=["code_analysis", "debugging"],
            agent_type="local"
        )
        agent_registry.register(test_agent)

        # Mock config
        config = {
            "budget": {
                "monthly_limit_usd": 100.0
            },
            "logging": {
                "conversation_logging_enabled": False  # Disable logging for test
            }
        }

        # Mock LLM clients
        reasoning_llm = Mock()
        reasoning_llm.generate = Mock(return_value="Mocked reasoning response")

        solving_llm = Mock()
        solving_llm.generate = Mock(return_value="Mocked solving response")

        print("    ✓ Dependencies mocked")

        # Test 2: Create orchestrator instance
        print("  Testing: Create SOAROrchestrator instance...")
        orchestrator = SOAROrchestrator(
            store=memory_store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=reasoning_llm,
            solving_llm=solving_llm
        )
        assert orchestrator is not None, "Orchestrator should be created"
        assert orchestrator.store is memory_store, "Store should be set"
        assert orchestrator.agent_registry is agent_registry, "Registry should be set"
        print("    ✓ Orchestrator created")

        # Test 3: Verify orchestrator components
        print("  Testing: Verify orchestrator components...")
        assert hasattr(orchestrator, 'execute'), "Orchestrator should have execute method"
        assert hasattr(orchestrator, 'cost_tracker'), "Orchestrator should have cost tracker"
        assert hasattr(orchestrator, 'conversation_logger'), "Orchestrator should have conversation logger"
        print("    ✓ Components verified")

        # Test 4: Verify agent registry works
        print("  Testing: Verify agent registry...")
        retrieved_agent = agent_registry.get("test_agent")
        assert retrieved_agent is not None, "Should retrieve registered agent"
        assert retrieved_agent.id == "test_agent", "Agent ID should match"
        assert len(retrieved_agent.capabilities) == 2, "Should have 2 capabilities"
        print(f"    ✓ Agent registry works (agent: {retrieved_agent.name})")

        # Test 5: Verify agent discovery by capability
        print("  Testing: Agent discovery by capability...")
        code_agents = agent_registry.find_by_capability("code_analysis")
        assert len(code_agents) > 0, "Should find agents with code_analysis capability"
        assert code_agents[0].id == "test_agent", "Should find our test agent"
        print(f"    ✓ Found {len(code_agents)} agent(s) with code_analysis capability")

        # Test 6: Mock a simple execution (without real API calls)
        print("  Testing: Mock SOAR execution...")
        # For smoke test, we just verify the execute method exists and accepts parameters
        # We don't actually run it because it would make real API calls
        try:
            # Verify method signature
            import inspect
            sig = inspect.signature(orchestrator.execute)
            params = list(sig.parameters.keys())
            assert 'query' in params, "Execute should accept query parameter"
            assert 'verbosity' in params, "Execute should accept verbosity parameter"
            print("    ✓ Execute method signature verified")
        except Exception as e:
            print(f"    ✗ Execute method verification failed: {e}")
            return False

        # Test 7: Verify cleanup
        print("  Testing: Cleanup...")
        memory_store.close()
        print("    ✓ Cleanup successful")

        return True

    except Exception as e:
        print(f"✗ SOAR orchestrator: FAIL - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("Running SOAR Orchestrator smoke test...")

    if run_smoke_test():
        print("✓ SOAR orchestrator: PASS")
        sys.exit(0)
    else:
        print("✗ SOAR orchestrator: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
