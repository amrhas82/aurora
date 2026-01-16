#!/usr/bin/env python3
"""Quick test script for medium query cost tracking."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from aurora_cli.config import Config
from aurora_core.budget import CostTracker
from aurora_core.store.sqlite import SQLiteStore
from aurora_reasoning.llm_client import LLMResponse
from aurora_soar.agent_registry import AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator


def test_medium_query_cost():
    """Test cost tracking for a MEDIUM complexity query."""

    # Setup temp paths
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test_aurora.db"
        tracker_path = f"{tmpdir}/budget_tracker.json"

        # Create components
        store = SQLiteStore(db_path)
        agent_registry = AgentRegistry()
        config = Config({"budget": {"monthly_limit_usd": 50.0}})
        cost_tracker = CostTracker(monthly_limit_usd=50.0, tracker_path=Path(tracker_path))

        # Create mock LLMs
        reasoning_llm = Mock()
        solving_llm = Mock()
        reasoning_llm.default_model = "claude-sonnet-4-20250514"
        solving_llm.default_model = "claude-3-5-haiku-20241022"

        # Create orchestrator
        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=reasoning_llm,
            solving_llm=solving_llm,
            cost_tracker=cost_tracker,
        )

        # Mock responses for MEDIUM complexity
        # Phase 1: Assess - returns MEDIUM complexity
        reasoning_llm.generate_json.return_value = {
            "complexity": "MEDIUM",
            "confidence": 0.85,
            "reasoning": "Multi-step question requiring analysis",
        }

        # Phase 2: Decompose - for MEDIUM queries
        reasoning_llm.generate.return_value = LLMResponse(
            content='{"goal": "Test", "subgoals": [{"id": "1", "description": "Step 1"}], "execution_order": ["1"], "expected_tools": ["read"]}',
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            finish_reason="stop",
        )

        # Phase 3: Solve subgoals
        solving_llm.generate.return_value = LLMResponse(
            content="Answer to the query",
            model="claude-3-5-haiku-20241022",
            input_tokens=800,
            output_tokens=400,
            finish_reason="stop",
        )

        # Execute medium query
        query = "Explain how the SOAR pipeline works and what are the key phases?"

        try:
            _ = orchestrator.execute(query, verbosity="NORMAL")
            print("\n✓ Execution completed successfully")
        except Exception as e:
            print(f"\n⚠ Execution encountered error (partial costs may still be tracked): {e}")

        # Get cost tracking results
        status = cost_tracker.get_status()
        breakdown_by_model = cost_tracker.get_breakdown_by_model()
        breakdown_by_operation = cost_tracker.get_breakdown_by_operation()
        history = cost_tracker.get_history()

        # Display results
        print("\n" + "=" * 60)
        print("MEDIUM QUERY COST TRACKING RESULTS")
        print("=" * 60)
        print(f"\n📊 Total Cost: ${status['consumed_usd']:.6f}")
        print(f"📝 Total Entries: {status['total_entries']}")
        print(
            f"💰 Budget Remaining: ${status['remaining_usd']:.2f} / ${status.get('limit_usd', 50.0):.2f}"
        )
        print(f"📈 Budget Used: {status['percent_consumed']:.1f}%")

        print("\n🤖 Cost by Model:")
        for model, cost in breakdown_by_model.items():
            model_short = model.split("-")[1] if "-" in model else model
            print(f"   • {model_short}: ${cost:.6f}")

        print("\n⚙️  Cost by Operation:")
        for operation, cost in breakdown_by_operation.items():
            print(f"   • {operation}: ${cost:.6f}")

        # Token analysis
        total_input = sum(h["input_tokens"] for h in history)
        total_output = sum(h["output_tokens"] for h in history)
        print("\n🔢 Token Usage:")
        print(f"   • Input tokens: {total_input:,}")
        print(f"   • Output tokens: {total_output:,}")
        print(f"   • Total tokens: {total_input + total_output:,}")

        # Detailed history
        print("\n📜 Detailed Cost History:")
        for i, entry in enumerate(history, 1):
            model_short = entry["model"].split("-")[1] if "-" in entry["model"] else entry["model"]
            print(f"   {i}. {entry['operation']}")
            print(f"      Model: {model_short}")
            print(f"      Tokens: {entry['input_tokens']} in, {entry['output_tokens']} out")
            print(f"      Cost: ${entry['cost_usd']:.6f}")

        print("\n" + "=" * 60)

        # Cleanup
        store.close()


if __name__ == "__main__":
    test_medium_query_cost()
