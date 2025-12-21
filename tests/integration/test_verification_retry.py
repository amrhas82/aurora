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
from aurora_reasoning.llm_client import LLMClient
from aurora_soar import AgentInfo, AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator


class MockCostTracker(CostTracker):
    """Mock cost tracker that allows all queries."""

    def __init__(self):
        """Initialize mock cost tracker with unlimited budget."""
        super().__init__(monthly_limit_usd=999999.0)

    def can_proceed(self) -> tuple[bool, str]:
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
        self.feedback_received = []

    @property
    def default_model(self) -> str:
        """Get default model identifier."""
        return "mock-model"

    def generate_json(self, prompt: str, system: str = "", schema: dict | None = None, **kwargs) -> dict:
        """Generate JSON response (not used in these tests)."""
        response = self.generate(prompt, system, **kwargs)
        import json
        return json.loads(response)

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Generate text response based on retry scenario."""
        self.call_count += 1

        # Track if feedback is in the prompt (retry attempt)
        if "Previous attempt feedback:" in prompt or "previous decomposition" in prompt.lower():
            # Extract feedback section for verification
            if "Previous attempt feedback:" in prompt:
                feedback_start = prompt.index("Previous attempt feedback:")
                self.feedback_received.append(prompt[feedback_start:feedback_start + 200])

        # Decomposition request
        if "decompose" in prompt.lower() or "subgoals" in prompt.lower():
            if self.retry_scenario == "fail_then_pass":
                if self.call_count == 1:
                    # First attempt: incomplete decomposition
                    return """
{
  "subgoals": [
    {
      "id": "sg1",
      "description": "Read the auth module",
      "suggested_agent": "code-reader"
    }
  ],
  "execution_order": ["sg1"]
}
"""
                else:
                    # Second attempt: complete decomposition
                    return """
{
  "subgoals": [
    {
      "id": "sg1",
      "description": "Read the auth module code",
      "suggested_agent": "code-reader"
    },
    {
      "id": "sg2",
      "description": "Analyze authentication flow and identify vulnerabilities",
      "suggested_agent": "security-analyzer"
    },
    {
      "id": "sg3",
      "description": "Generate security assessment report",
      "suggested_agent": "report-generator"
    }
  ],
  "execution_order": ["sg1", "sg2", "sg3"]
}
"""
            elif self.retry_scenario == "fail_twice":
                # Both attempts: incomplete decomposition
                return """
{
  "subgoals": [
    {
      "id": "sg1",
      "description": "Read the auth module",
      "suggested_agent": "code-reader"
    }
  ],
  "execution_order": ["sg1"]
}
"""
            else:  # pass_first
                # First attempt: complete decomposition
                return """
{
  "subgoals": [
    {
      "id": "sg1",
      "description": "Read the auth module code",
      "suggested_agent": "code-reader"
    },
    {
      "id": "sg2",
      "description": "Analyze authentication flow and identify vulnerabilities",
      "suggested_agent": "security-analyzer"
    },
    {
      "id": "sg3",
      "description": "Generate security assessment report",
      "suggested_agent": "report-generator"
    }
  ],
  "execution_order": ["sg1", "sg2", "sg3"]
}
"""

        # Verification request
        if "verify" in prompt.lower() or "score" in prompt.lower():
            if self.retry_scenario == "fail_then_pass":
                if self.call_count <= 2:
                    # First decomposition gets low score
                    return """
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
"""
                else:
                    # Second decomposition passes
                    return """
{
  "completeness": 0.9,
  "consistency": 0.9,
  "groundedness": 0.9,
  "routability": 0.9,
  "overall_score": 0.9,
  "verdict": "PASS",
  "issues": []
}
"""
            elif self.retry_scenario == "fail_twice":
                # Both verifications fail
                return """
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
"""
            else:  # pass_first
                # First verification passes
                return """
{
  "completeness": 0.9,
  "consistency": 0.9,
  "groundedness": 0.9,
  "routability": 0.9,
  "overall_score": 0.9,
  "verdict": "PASS",
  "issues": []
}
"""

        # Feedback generation request
        if "feedback" in prompt.lower() and "improve" in prompt.lower():
            return """
The decomposition is incomplete. To improve:

1. Add a subgoal for analyzing the authentication flow in detail
2. Include a subgoal for identifying specific vulnerabilities (SQL injection, XSS, etc.)
3. Ensure the security assessment covers both code-level and architectural issues
4. Add a subgoal for generating a comprehensive report with recommendations

These additions will make the decomposition complete and actionable.
"""

        return "mock response"

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
        assert llm_client.call_count >= 4, "Should have multiple LLM calls (decompose + verify, then retry)"

        # Verify feedback was generated and used
        assert len(llm_client.feedback_received) > 0, "Should have received retry feedback"

        # Verify final verification passed
        phase_results = result["metadata"]["phase_results"]
        verify_result = phase_results[3]  # Phase 4 is verify (0-indexed)
        assert verify_result["final_verdict"] == "PASS", "Final verification should pass"
        assert verify_result["retry_count"] >= 1, "Should have at least one retry"

        # Verify decomposition improved
        decompose_result = phase_results[2]  # Phase 3 is decompose
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
        phase_results = result["metadata"]["phase_results"]
        verify_result = phase_results[3]  # Phase 4 is verify
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
        phase_results = result["metadata"]["phase_results"]
        verify_result = phase_results[3]  # Phase 4 is verify
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

        # Verify feedback was provided to retry attempt
        feedback = llm_client.feedback_received
        assert len(feedback) > 0, "Should have received feedback"

        # Verify feedback contains actionable content
        feedback_text = feedback[0]
        assert "improve" in feedback_text.lower() or "add" in feedback_text.lower(), \
            "Feedback should contain improvement suggestions"
