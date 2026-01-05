"""
Integration tests for verification retry loop.

Tests that CRITICAL queries with low verification scores trigger
the retry loop and that feedback is properly generated and incorporated.
"""

import pytest
from aurora_core.budget import CostTracker
from aurora_core.chunks import CodeChunk
from aurora_core.config.loader import Config
from aurora_core.store.memory import MemoryStore
from aurora_reasoning.llm_client import LLMClient, LLMResponse
from aurora_soar.orchestrator import SOAROrchestrator

from aurora_soar import AgentInfo, AgentRegistry


class MockCostTracker(CostTracker):
    """Mock cost tracker that allows all queries."""

    def __init__(self):
        """Initialize mock cost tracker with unlimited budget."""
        # Use temp file to avoid loading persistent budget data
        import tempfile
        from pathlib import Path

        temp_dir = tempfile.mkdtemp()
        tracker_path = Path(temp_dir) / "mock_budget_tracker.json"
        super().__init__(monthly_limit_usd=999999.0, tracker_path=tracker_path)

    def check_budget(self, estimated_cost: float) -> tuple[bool, str]:
        """Always allow queries."""
        return True, "OK"

    def track_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Track cost but always return 0."""
        return 0.0


class MockLLMClientWithRetry(LLMClient):
    """Mock LLM client that simulates retry scenarios."""

    def __init__(self, retry_scenario: str):
        """Initialize with retry scenario.

        Args:
            retry_scenario: One of:
                - "fail_then_pass": First attempt gets low score, second attempt passes
                - "fail_twice": Both attempts get low scores
                - "pass_first": First attempt passes (no retry needed)
        """
        self.retry_scenario = retry_scenario
        self.call_count = 0
        self.verification_count = 0  # Track verification calls separately
        self.feedback_received = []  # Stores prompts that USE feedback (for detecting retry)
        self.feedback_generated = []  # Stores actual feedback TEXT generated

    @property
    def default_model(self) -> str:
        """Get default model identifier."""
        return "mock-model"

    def generate_json(
        self, prompt: str, system: str = "", schema: dict | None = None, **kwargs
    ) -> dict:
        """Generate JSON response (not used in these tests)."""
        response = self.generate(prompt, system, **kwargs)
        import json

        return json.loads(response.content)

    def _make_response(self, content: str) -> LLMResponse:
        """Helper to create LLMResponse."""
        return LLMResponse(
            content=content,
            model="mock-model",
            input_tokens=10,
            output_tokens=10,
            finish_reason="stop",
            metadata={},
        )

    def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """Generate text response based on retry scenario."""
        self.call_count += 1

        # Track if retry feedback is being used in decomposition (not generation)
        # The retry decomposition will have the feedback embedded in examples/context
        is_retry_with_feedback = (
            "decompose" in prompt.lower() or "subgoals" in prompt.lower()
        ) and ("feedback" in prompt.lower() or "attempt" in prompt.lower())
        if is_retry_with_feedback:
            # Store as evidence that retry feedback was used
            self.feedback_received.append(prompt[:500])

        # Check decomposition with retry feedback FIRST (most specific)
        # Then check verification (contains decomposition)
        # Then check regular decomposition (contains subgoals)

        combined = (prompt + " " + system).upper()
        # Verification: RED TEAM or contains verification keywords, but NOT feedback generation
        is_verification = (
            (
                "RED TEAM" in combined
                or ("VERIF" in combined and "DECOMPOSITION" in combined)
                or ("CONSISTENCY" in combined and "GROUNDEDNESS" in combined)
            )
            and "VERIFICATION RESULT (ATTEMPT" not in combined  # Exclude feedback generation
        )

        # Retry decomposition: has both decompose keywords AND retry indicators
        is_retry_decompose = (
            ("DECOMPOSE" in combined or "SUBGOALS" in combined)
            and ("FEEDBACK" in combined or "RETRY" in combined or "ATTEMPT" in combined)
            and not is_verification  # Not a verification prompt
        )

        if is_retry_decompose:
            # This is a retry decomposition with feedback - return decomposition based on scenario

            if self.retry_scenario == "fail_then_pass":
                # Second attempt: complete decomposition (Phase 2 format)
                return self._make_response("""
{
  "goal": "Review authentication module for security",
  "subgoals": [
    {
      "description": "Read the auth module code",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    },
    {
      "description": "Analyze authentication flow and identify vulnerabilities",
      "suggested_agent": "security-analyzer",
      "is_critical": true,
      "depends_on": [0]
    },
    {
      "description": "Generate security assessment report",
      "suggested_agent": "report-generator",
      "is_critical": true,
      "depends_on": [1]
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}, {"phase": 2, "parallelizable": [1], "sequential": []}, {"phase": 3, "parallelizable": [2], "sequential": []}],
  "expected_tools": ["file_reader", "security_analyzer", "report_generator"]
}
""")
            if self.retry_scenario == "fail_twice":
                # Still incomplete even after retry
                return self._make_response("""
{
  "goal": "Review authentication module",
  "subgoals": [
    {
      "description": "Read the auth module",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
  "expected_tools": ["file_reader"]
}
""")
            # pass_first - shouldn't reach here
            return self._make_response("mock response")

        if is_verification:
            self.verification_count += 1

            if self.retry_scenario == "fail_then_pass":
                if self.verification_count == 1:
                    # First decomposition gets low score
                    return self._make_response("""
{
  "completeness": 0.4,
  "consistency": 0.7,
  "groundedness": 0.8,
  "routability": 0.6,
  "overall_score": 0.6,
  "verdict": "RETRY",
  "issues": [
    "Decomposition is incomplete - missing security analysis steps",
    "No vulnerability identification subgoal",
    "Report generation not specified"
  ]
}
""")
                # Second decomposition passes
                return self._make_response("""
{
  "completeness": 0.9,
  "consistency": 0.9,
  "groundedness": 0.9,
  "routability": 0.9,
  "overall_score": 0.9,
  "verdict": "PASS",
  "issues": []
}
""")
            if self.retry_scenario == "fail_twice":
                # Both verifications fail
                return self._make_response("""
{
  "completeness": 0.4,
  "consistency": 0.7,
  "groundedness": 0.8,
  "routability": 0.6,
  "overall_score": 0.6,
  "verdict": "RETRY",
  "issues": [
    "Decomposition is incomplete - missing security analysis steps",
    "No vulnerability identification subgoal"
  ]
}
""")
            # pass_first
            # First verification passes
            return self._make_response("""
{
  "completeness": 0.9,
  "consistency": 0.9,
  "groundedness": 0.9,
  "routability": 0.9,
  "overall_score": 0.9,
  "verdict": "PASS",
  "issues": []
}
""")

        # Decomposition request
        if "decompose" in prompt.lower() or "subgoals" in prompt.lower():
            if self.retry_scenario == "fail_then_pass":
                if self.call_count == 1:
                    # First attempt: incomplete decomposition (Phase 2 format)
                    return self._make_response("""
{
  "goal": "Review authentication module",
  "subgoals": [
    {
      "description": "Read the auth module",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
  "expected_tools": ["file_reader"]
}
""")
                # Second attempt: complete decomposition (Phase 2 format)
                return self._make_response("""
{
  "goal": "Review authentication module for security",
  "subgoals": [
    {
      "description": "Read the auth module code",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    },
    {
      "description": "Analyze authentication flow and identify vulnerabilities",
      "suggested_agent": "security-analyzer",
      "is_critical": true,
      "depends_on": [0]
    },
    {
      "description": "Generate security assessment report",
      "suggested_agent": "report-generator",
      "is_critical": true,
      "depends_on": [1]
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}, {"phase": 2, "parallelizable": [1], "sequential": []}, {"phase": 3, "parallelizable": [2], "sequential": []}],
  "expected_tools": ["file_reader", "security_analyzer", "report_generator"]
}
""")
            if self.retry_scenario == "fail_twice":
                # Both attempts: incomplete decomposition (Phase 2 format)
                return self._make_response("""
{
  "goal": "Review authentication module",
  "subgoals": [
    {
      "description": "Read the auth module",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
  "expected_tools": ["file_reader"]
}
""")
            # pass_first
            # First attempt: complete decomposition (Phase 2 format)
            return self._make_response("""
{
  "goal": "Review authentication module for security",
  "subgoals": [
    {
      "description": "Read the auth module code",
      "suggested_agent": "code-reader",
      "is_critical": true,
      "depends_on": []
    },
    {
      "description": "Analyze authentication flow and identify vulnerabilities",
      "suggested_agent": "security-analyzer",
      "is_critical": true,
      "depends_on": [0]
    },
    {
      "description": "Generate security assessment report",
      "suggested_agent": "report-generator",
      "is_critical": true,
      "depends_on": [1]
    }
  ],
  "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}, {"phase": 2, "parallelizable": [1], "sequential": []}, {"phase": 3, "parallelizable": [2], "sequential": []}],
  "expected_tools": ["file_reader", "security_analyzer", "report_generator"]
}
""")

        # Feedback generation request (check for verification result in prompt)
        if "verification result" in prompt.lower() or (
            "feedback" in prompt.lower() and "improve" in prompt.lower()
        ):
            feedback_text = """
The decomposition is incomplete. To improve:

1. Add a subgoal for analyzing the authentication flow in detail
2. Include a subgoal for identifying specific vulnerabilities (SQL injection, XSS, etc.)
3. Ensure the security assessment covers both code-level and architectural issues
4. Add a subgoal for generating a comprehensive report with recommendations

These additions will make the decomposition complete and actionable.
"""
            self.feedback_generated.append(feedback_text)  # Store the actual feedback
            return self._make_response(feedback_text)

        return self._make_response("mock response")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        # Return very small token counts to avoid budget issues in tests
        return min(10, len(text) // 100)


class TestVerificationRetry:
    """Test verification retry loop functionality."""

    @pytest.fixture
    def store(self):
        """Create memory store."""
        store = MemoryStore()
        # Add some code chunks for retrieval
        chunk1 = CodeChunk(
            chunk_id="auth_py_AuthenticationManager_1_50",
            file_path="/app/auth.py",
            line_start=1,
            line_end=50,
            element_type="class",
            name="AuthenticationManager",
            signature="class AuthenticationManager",
            docstring="Handles user authentication",
            language="python",
            complexity_score=0.6,
            dependencies=[],
        )
        chunk2 = CodeChunk(
            chunk_id="auth_py_verify_token_51_100",
            file_path="/app/auth.py",
            line_start=51,
            line_end=100,
            element_type="function",
            name="verify_token",
            signature="def verify_token(token: str) -> bool",
            docstring="Verify JWT token",
            language="python",
            complexity_score=0.4,
            dependencies=["jwt"],
        )
        store.save_chunk(chunk1)
        store.save_chunk(chunk2)
        store.update_activation(chunk1.id, 0.8)
        store.update_activation(chunk2.id, 0.7)
        return store

    @pytest.fixture
    def agent_registry(self):
        """Create agent registry."""
        registry = AgentRegistry()
        registry.register(
            AgentInfo(
                id="code-reader",
                name="Code Reader",
                description="Reads and parses code files",
                capabilities=["read_code", "parse_syntax"],
                agent_type="local",
            )
        )
        registry.register(
            AgentInfo(
                id="security-analyzer",
                name="Security Analyzer",
                description="Analyzes code for security vulnerabilities",
                capabilities=["security_audit", "vulnerability_scan"],
                agent_type="local",
            )
        )
        registry.register(
            AgentInfo(
                id="report-generator",
                name="Report Generator",
                description="Generates formatted reports",
                capabilities=["generate_report", "format_output"],
                agent_type="local",
            )
        )
        return registry

    @pytest.fixture
    def config(self):
        """Create test config."""
        config_data = {
            "budget": {"monthly_limit_usd": 999999.0},  # Effectively unlimited budget for testing
            "logging": {"conversation_logging_enabled": False},
            "soar": {
                "timeout_seconds": 60,
                "max_retries": 2,
            },
        }
        return Config(data=config_data)

    def test_retry_loop_fail_then_pass(self, store, agent_registry, config):
        """Test retry loop when first attempt fails but second passes."""
        llm_client = MockLLMClientWithRetry(retry_scenario="fail_then_pass")
        cost_tracker = MockCostTracker()

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=llm_client,
            solving_llm=llm_client,
            cost_tracker=cost_tracker,
        )

        # Execute CRITICAL query
        result = orchestrator.execute(
            query="Review the authentication module for security vulnerabilities",
            verbosity="JSON",
        )

        # Verify retry occurred
        assert llm_client.call_count >= 4, (
            "Should have multiple LLM calls (decompose + verify, then retry)"
        )

        # Verify feedback was generated and used
        assert len(llm_client.feedback_received) > 0, "Should have received retry feedback"

        # Verify final verification passed
        phase_results = result["metadata"]["phases"]
        verify_result = phase_results["phase4_verify"]
        assert verify_result["final_verdict"] == "PASS", "Final verification should pass"
        assert verify_result["retry_count"] >= 1, "Should have at least one retry"

        # Verify decomposition improved
        decompose_result = phase_results["phase3_decompose"]
        subgoals = decompose_result["decomposition"]["subgoals"]
        assert len(subgoals) >= 3, "Final decomposition should have multiple subgoals"

    def test_retry_loop_max_retries_exhausted(self, store, agent_registry, config):
        """Test retry loop when max retries are exhausted."""
        llm_client = MockLLMClientWithRetry(retry_scenario="fail_twice")
        cost_tracker = MockCostTracker()

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=llm_client,
            solving_llm=llm_client,
            cost_tracker=cost_tracker,
        )

        # Execute CRITICAL query
        result = orchestrator.execute(
            query="Review the authentication module for security vulnerabilities",
            verbosity="JSON",
        )

        # Verify max retries reached
        phase_results = result["metadata"]["phases"]
        verify_result = phase_results["phase4_verify"]  # Phase 4 is verify
        assert verify_result["retry_count"] == 2, "Should have exhausted max retries (2)"
        assert verify_result["final_verdict"] == "FAIL", "Should FAIL after max retries"

        # Verify all attempts tracked
        assert len(verify_result["all_attempts"]) == 3, "Should track initial + 2 retry attempts"

        # Verify orchestrator continues despite FAIL verdict (best effort)
        assert "answer" in result, "Should still produce an answer (best effort)"

    def test_no_retry_when_first_attempt_passes(self, store, agent_registry, config):
        """Test that no retry occurs when first attempt passes."""
        llm_client = MockLLMClientWithRetry(retry_scenario="pass_first")
        cost_tracker = MockCostTracker()

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=llm_client,
            solving_llm=llm_client,
            cost_tracker=cost_tracker,
        )

        # Execute CRITICAL query
        result = orchestrator.execute(
            query="Review the authentication module for security vulnerabilities",
            verbosity="JSON",
        )

        # Debug: print result structure
        print(f"Result keys: {result.keys()}")
        if "metadata" in result:
            print(f"Metadata keys: {result['metadata'].keys()}")

        # Verify no retry occurred
        phase_results = result["metadata"]["phases"]
        verify_result = phase_results["phase4_verify"]  # Phase 4 is verify
        assert verify_result["retry_count"] == 0, "Should have no retries when first attempt passes"
        assert verify_result["final_verdict"] == "PASS", "Should pass on first attempt"

        # Verify only one verification attempt
        assert len(verify_result["all_attempts"]) == 1, "Should have only one attempt"

        # Verify no feedback was generated
        assert len(llm_client.feedback_received) == 0, "Should not generate feedback when passing"

    def test_retry_feedback_quality(self, store, agent_registry, config):
        """Test that retry feedback is specific and actionable."""
        llm_client = MockLLMClientWithRetry(retry_scenario="fail_then_pass")
        cost_tracker = MockCostTracker()

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=llm_client,
            solving_llm=llm_client,
            cost_tracker=cost_tracker,
        )

        # Execute CRITICAL query
        orchestrator.execute(
            query="Review the authentication module for security vulnerabilities",
            verbosity="JSON",
        )

        # Verify feedback was generated and provided to retry attempt
        assert len(llm_client.feedback_generated) > 0, "Should have generated feedback"
        assert len(llm_client.feedback_received) > 0, "Should have used feedback in retry"

        # Verify feedback contains actionable content
        feedback_text = llm_client.feedback_generated[0]
        assert "improve" in feedback_text.lower() or "add" in feedback_text.lower(), (
            "Feedback should contain improvement suggestions"
        )
