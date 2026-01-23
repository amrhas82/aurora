"""Performance benchmarks for SOAR pipeline.

These benchmarks verify that SOAR operations meet the required
performance targets specified in the PRD:
- Simple query latency: < 2s
- Complex query latency: < 10s
- Verification phase: < 1s
"""

import time

import pytest

from aurora_core.budget import CostTracker
from aurora_core.chunks import CodeChunk
from aurora_core.config.loader import Config
from aurora_core.store.memory import MemoryStore
from aurora_reasoning.llm_client import LLMClient
from aurora_soar import AgentInfo, AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator

# Performance targets from PRD
SIMPLE_QUERY_TARGET_S = 2.0
COMPLEX_QUERY_TARGET_S = 10.0
VERIFICATION_TARGET_S = 1.0


class MockLLMClientFast(LLMClient):
    """Fast mock LLM client for performance testing."""

    @property
    def default_model(self) -> str:
        """Get default model."""
        return "mock-fast"

    def count_tokens(self, text: str) -> int:
        """Count tokens (minimal)."""
        return 1

    def generate(self, prompt: str, system: str = "", **kwargs):
        """Generate fast mock response."""
        from aurora_reasoning.llm_client import LLMResponse

        content = ""
        prompt_lower = prompt.lower()
        system_lower = system.lower()
        combined = prompt_lower + " " + system_lower

        # Debug: print first 200 chars to see what we're matching
        # if "verify" in combined or "validate" in combined:

        # Order matters - check more specific patterns first
        # Check synthesis verification BEFORE decomposition verification
        if ("verify" in combined or "validate" in combined) and (
            "coherence" in combined or "factuality" in combined or "synthesis" in combined
        ):
            # Verification of synthesis - has coherence and factuality
            content = (
                '{"coherence": 0.9, "completeness": 0.9, "factuality": 0.9, "overall_score": 0.9}'
            )
        elif ("verify" in combined or "validate" in combined) and (
            "verdict" in combined or "score" in combined
        ):
            # Verification of decomposition - has verdict and issues
            content = '{"completeness": 0.9, "consistency": 0.9, "groundedness": 0.9, "routability": 0.9, "overall_score": 0.9, "verdict": "PASS", "issues": []}'
        elif "decompose" in combined or "break down" in combined:
            content = '{"goal": "test goal", "subgoals": [{"id": "sg1", "description": "test", "suggested_agent": "test-agent", "is_critical": true, "depends_on": []}], "execution_order": [{"phase": "sg1", "sequential": true}], "expected_tools": []}'
        elif "complexity" in combined or "assess" in combined:
            content = '{"complexity": "SIMPLE", "confidence": 0.9, "reasoning": "test"}'
        else:
            # Default to synthesis response for all other cases
            # (synthesize prompts are generic so this is the catch-all)
            # Agent name must match what's in the decomposition/agent_outputs
            content = "ANSWER: Test answer based on test-agent output\n\nCONFIDENCE: 0.9"

        return LLMResponse(
            content=content,
            model="mock-fast",
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
        )

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        schema: dict | None = None,
        **kwargs,
    ) -> dict:
        """Generate JSON response."""
        import json

        response = self.generate(prompt, system, **kwargs)
        return json.loads(response.content)


class NoOpCostTracker(CostTracker):
    """Cost tracker that doesn't track anything (for performance testing)."""

    def __init__(self):
        """Initialize no-op tracker with isolated temp file."""
        import tempfile
        from pathlib import Path

        temp_dir = tempfile.mkdtemp()
        tracker_path = Path(temp_dir) / "perf_budget_tracker.json"
        super().__init__(monthly_limit_usd=999999.0, tracker_path=tracker_path)

    def check_budget(self, estimated_cost: float) -> tuple[bool, str]:
        """Always allow."""
        return True, "OK"

    def can_proceed(self) -> tuple[bool, str]:
        """Always allow."""
        return True, "OK"

    def track_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """No-op tracking."""
        return 0.0


class TestSOARPerformance:
    """Performance benchmarks for SOAR pipeline."""

    @pytest.fixture
    def store(self):
        """Create memory store with test data."""
        store = MemoryStore()
        # Add a few chunks for retrieval
        for i in range(10):
            chunk = CodeChunk(
                chunk_id=f"perf_chunk_{i}",
                file_path="/test/perf.py",
                element_type="function",
                name=f"func_{i}",
                line_start=i * 10 + 1,
                line_end=i * 10 + 5,
                language="python",
                complexity_score=0.5,
            )
            store.save_chunk(chunk)
            store.update_activation(chunk.id, 0.8)
        return store

    @pytest.fixture
    def agent_registry(self):
        """Create agent registry."""
        registry = AgentRegistry()
        registry.register(
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Test agent for performance testing",
                capabilities=["test"],
                agent_type="local",
            ),
        )
        return registry

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            data={
                "budget": {"monthly_limit_usd": 999999.0},
                "logging": {"conversation_logging_enabled": False},
                "soar": {"timeout_seconds": 60, "max_retries": 2},
            },
        )

    @pytest.fixture
    def orchestrator(self, store, agent_registry, config):
        """Create orchestrator with fast mocks."""
        llm_client = MockLLMClientFast()
        cost_tracker = NoOpCostTracker()

        return SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=llm_client,
            solving_llm=llm_client,
            cost_tracker=cost_tracker,
        )

    def test_simple_query_latency(self, orchestrator):
        """Benchmark simple query end-to-end latency."""
        query = "What does the main function do?"

        start = time.perf_counter()
        result = orchestrator.execute(query=query, verbosity="JSON")
        end = time.perf_counter()

        elapsed_s = end - start
        print(f"\nSimple query latency: {elapsed_s:.3f}s")

        assert (
            elapsed_s < SIMPLE_QUERY_TARGET_S
        ), f"Simple query took {elapsed_s:.3f}s, target is {SIMPLE_QUERY_TARGET_S}s"

        # Verify result structure
        assert "answer" in result
        assert "metadata" in result

    def test_complex_query_latency(self, orchestrator):
        """Benchmark complex query end-to-end latency."""
        query = "Analyze the authentication flow and identify potential security vulnerabilities in the session management code"

        start = time.perf_counter()
        result = orchestrator.execute(query=query, verbosity="JSON")
        end = time.perf_counter()

        elapsed_s = end - start
        print(f"\nComplex query latency: {elapsed_s:.3f}s")

        assert (
            elapsed_s < COMPLEX_QUERY_TARGET_S
        ), f"Complex query took {elapsed_s:.3f}s, target is {COMPLEX_QUERY_TARGET_S}s"

        # Verify result structure
        assert "answer" in result
        assert "metadata" in result

    def test_verification_phase_timing(self, orchestrator):
        """Benchmark verification phase in isolation."""
        from aurora_reasoning import verify

        llm_client = MockLLMClientFast()
        decomposition = {
            "goal": "Test query for verification timing",
            "subgoals": [
                {"id": "sg1", "description": "Test 1", "suggested_agent": "test-agent"},
                {"id": "sg2", "description": "Test 2", "suggested_agent": "test-agent"},
            ],
            "execution_order": ["sg1", "sg2"],
            "expected_tools": [],
        }

        start = time.perf_counter()
        verify.verify_decomposition(
            llm_client=llm_client,
            query="Test query for verification timing",
            decomposition=decomposition,
            option=verify.VerificationOption.ADVERSARIAL,
        )
        end = time.perf_counter()

        elapsed_s = end - start
        print(f"\nVerification phase: {elapsed_s:.3f}s")

        assert (
            elapsed_s < VERIFICATION_TARGET_S
        ), f"Verification took {elapsed_s:.3f}s, target is {VERIFICATION_TARGET_S}s"

    def test_throughput_sequential(self, orchestrator):
        """Benchmark sequential query throughput."""
        queries = [
            "What does function A do?",
            "Explain function B",
            "Show me function C",
        ]

        start = time.perf_counter()
        for query in queries:
            orchestrator.execute(query=query, verbosity="QUIET")
        end = time.perf_counter()

        total_time = end - start
        queries_per_second = len(queries) / total_time
        print(
            f"\nSequential throughput: {queries_per_second:.2f} queries/second ({total_time:.3f}s total for {len(queries)} queries)",
        )

        # No strict assertion, just measuring and reporting
        assert queries_per_second > 0, "Should complete queries"

    @pytest.mark.benchmark
    def test_memory_usage_footprint(self, orchestrator):
        """Measure memory footprint during query execution."""
        import tracemalloc

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # Execute multiple queries
        for i in range(10):
            orchestrator.execute(
                query=f"Test query {i}",
                verbosity="QUIET",
            )

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Calculate memory delta
        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_kb = sum(stat.size_diff for stat in top_stats) / 1024

        print(f"\nMemory delta for 10 queries: {total_kb:.2f} KB")

        # No strict assertion, just measuring
        assert total_kb > 0, "Should use some memory"


class TestPhasePerformance:
    """Performance benchmarks for individual SOAR phases."""

    def test_assess_phase_timing(self):
        """Benchmark Phase 1 (Assess) timing."""
        from aurora_soar.phases import assess

        llm_client = MockLLMClientFast()

        start = time.perf_counter()
        assess.assess_complexity(
            query="Test query for complexity assessment",
            llm_client=llm_client,
        )
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        print(f"\nAssess phase: {elapsed_ms:.2f}ms")

        # Assess should be very fast (keyword-based with optional LLM)
        assert elapsed_ms < 500, f"Assess took {elapsed_ms:.2f}ms, should be < 500ms"

    def test_decompose_phase_timing(self):
        """Benchmark Phase 3 (Decompose) timing."""
        from aurora_reasoning import decompose

        llm_client = MockLLMClientFast()

        start = time.perf_counter()
        decompose.decompose_query(
            llm_client=llm_client,
            query="Test query for decomposition timing",
            complexity="COMPLEX",
            context_summary="Test context summary",
        )
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        print(f"\nDecompose phase: {elapsed_ms:.2f}ms")

        # Decompose is LLM-bound, should be reasonably fast with mock
        assert elapsed_ms < 1000, f"Decompose took {elapsed_ms:.2f}ms, should be < 1000ms"

    def test_synthesis_phase_timing(self):
        """Benchmark Phase 7 (Synthesize) timing."""
        from aurora_reasoning import synthesize

        llm_client = MockLLMClientFast()

        start = time.perf_counter()
        synthesize.synthesize_results(
            llm_client=llm_client,
            query="Test query",
            agent_outputs=[
                {
                    "subgoal_id": "sg1",
                    "description": "Test subgoal",
                    "agent_name": "test-agent",
                    "agent_output": "Test output",
                    "status": "completed",
                },
            ],
            decomposition={
                "goal": "Test query",
                "subgoals": [
                    {"id": "sg1", "description": "Test subgoal", "suggested_agent": "test-agent"},
                ],
                "execution_order": ["sg1"],
                "expected_tools": [],
            },
        )
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        print(f"\nSynthesize phase: {elapsed_ms:.2f}ms")

        # Synthesis is LLM-bound, should be reasonably fast with mock
        assert elapsed_ms < 1000, f"Synthesis took {elapsed_ms:.2f}ms, should be < 1000ms"
