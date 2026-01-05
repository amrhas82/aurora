"""End-to-End Integration Test Framework.

This module provides the base framework for E2E integration tests of the
full SOAR pipeline. It includes:
- Mock LLM clients with configurable responses
- Mock agent implementations
- Test data generators
- Assertion helpers for verifying phase outputs
- Performance measurement utilities
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from aurora_core.budget import CostTracker
from aurora_core.config.loader import Config
from aurora_core.logging import ConversationLogger
from aurora_core.store.sqlite import SQLiteStore
from aurora_reasoning.llm_client import LLMClient
from aurora_soar.agent_registry import AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator


@dataclass
class MockLLMResponse:
    """Mock LLM response configuration."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str = "mock-model"


class MockLLMClient(LLMClient):
    """Mock LLM client for testing.

    Supports configurable responses based on prompt patterns.
    Tracks all calls for verification.
    """

    def __init__(self, default_model: str = "mock-model"):
        """Initialize mock LLM client.

        Args:
            default_model: Default model identifier
        """
        self._default_model = default_model
        self._responses: dict[str, list[MockLLMResponse]] = {}
        self._calls: list[dict[str, Any]] = []
        self._call_count: int = 0

    @property
    def default_model(self) -> str:
        """Get default model identifier."""
        return self._default_model

    def count_tokens(self, text: str) -> int:
        """Count tokens in text (mock implementation).

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        # Simple approximation: 1 token per 4 characters
        return len(text) // 4

    def configure_response(self, pattern: str, response: MockLLMResponse) -> None:
        """Configure a response for prompts matching a pattern.

        Args:
            pattern: Pattern to match in prompt (substring match)
            response: Response to return
        """
        if pattern not in self._responses:
            self._responses[pattern] = []
        self._responses[pattern].append(response)

    def configure_responses(self, pattern: str, responses: list[MockLLMResponse]) -> None:
        """Configure multiple responses for a pattern (returned in order).

        Args:
            pattern: Pattern to match in prompt
            responses: List of responses to return in sequence
        """
        self._responses[pattern] = responses.copy()

    def get_calls(self) -> list[dict[str, Any]]:
        """Get all LLM calls made.

        Returns:
            List of call records with prompt, model, response
        """
        return self._calls.copy()

    def get_call_count(self) -> int:
        """Get total number of LLM calls.

        Returns:
            Number of calls
        """
        return self._call_count

    def reset(self) -> None:
        """Reset call tracking and responses."""
        self._calls.clear()
        self._responses.clear()
        self._call_count = 0

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model: str | None = None,
        **kwargs,
    ):
        """Generate text response (mock).

        Args:
            prompt: Input prompt
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model: Model to use (optional)
            **kwargs: Additional arguments (ignored)

        Returns:
            LLMResponse object
        """
        from aurora_reasoning.llm_client import LLMResponse

        model = model or self._default_model
        self._call_count += 1

        # Find matching response (check both prompt and system)
        combined_text = f"{prompt} {system}".lower()
        for pattern, responses in self._responses.items():
            if pattern.lower() in combined_text and responses:
                response = responses.pop(0)
                self._calls.append(
                    {
                        "type": "generate",
                        "prompt": prompt,
                        "model": model,
                        "response": response.content,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                    }
                )
                return LLMResponse(
                    content=response.content,
                    model=model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    finish_reason="stop",
                )

        # No matching response - return default
        default_content = "Mock LLM response"
        self._calls.append(
            {
                "type": "generate",
                "prompt": prompt,
                "model": model,
                "response": default_content,
                "input_tokens": 100,
                "output_tokens": 50,
            }
        )
        return LLMResponse(
            content=default_content,
            model=model,
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        schema: dict | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate JSON response (mock).

        Args:
            prompt: Input prompt
            system: System prompt
            schema: JSON schema (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model: Model to use (optional)
            **kwargs: Additional arguments (ignored)

        Returns:
            Parsed JSON object
        """
        model = model or self._default_model
        self._call_count += 1

        # Find matching response (check both prompt and system)
        combined_text = f"{prompt} {system}".lower()
        for pattern, responses in self._responses.items():
            if pattern.lower() in combined_text and responses:
                response = responses.pop(0)
                self._calls.append(
                    {
                        "type": "generate_json",
                        "prompt": prompt,
                        "model": model,
                        "response": response.content,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                    }
                )
                return json.loads(response.content)

        # No matching response - return default
        default_response = {"mock": "json"}
        self._calls.append(
            {
                "type": "generate_json",
                "prompt": prompt,
                "model": model,
                "response": default_response,
                "input_tokens": 100,
                "output_tokens": 50,
            }
        )
        return default_response


class MockAgent:
    """Mock agent for testing agent execution."""

    def __init__(
        self,
        agent_id: str,
        capabilities: list[str],
        response: dict[str, Any] | None = None,
        execution_time: float = 0.1,
        should_fail: bool = False,
    ):
        """Initialize mock agent.

        Args:
            agent_id: Agent identifier
            capabilities: List of capabilities
            response: Response to return (optional)
            execution_time: Simulated execution time in seconds
            should_fail: Whether agent should fail
        """
        self.agent_id = agent_id
        self.capabilities = capabilities
        self._response = response or {
            "summary": f"Mock response from {agent_id}",
            "data": {},
            "confidence": 0.9,
        }
        self._execution_time = execution_time
        self._should_fail = should_fail
        self._calls: list[dict[str, Any]] = []

    async def execute(self, subgoal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute agent (mock).

        Args:
            subgoal: Subgoal to execute
            context: Execution context

        Returns:
            Agent response

        Raises:
            RuntimeError: If agent configured to fail
        """
        self._calls.append({"subgoal": subgoal, "context": context})

        # Simulate execution time
        await asyncio.sleep(self._execution_time)

        if self._should_fail:
            raise RuntimeError(f"Mock agent {self.agent_id} failed")

        return self._response.copy()

    def get_calls(self) -> list[dict[str, Any]]:
        """Get all agent execution calls.

        Returns:
            List of call records
        """
        return self._calls.copy()

    def reset(self) -> None:
        """Reset call tracking."""
        self._calls.clear()


class E2ETestFramework:
    """Base framework for E2E integration tests.

    Provides:
    - Orchestrator setup with mocks
    - Test data generation
    - Assertion helpers
    - Performance measurement
    """

    def __init__(self, temp_dir: str):
        """Initialize E2E test framework.

        Args:
            temp_dir: Temporary directory for test files
        """
        self.temp_dir = temp_dir

        # Initialize components
        self.config = self._create_test_config()
        self.store = self._create_test_store()
        self.agent_registry = AgentRegistry()
        self.mock_llm = MockLLMClient()
        # Use unique tracker file for tests to avoid persistence issues
        from pathlib import Path

        tracker_path = Path(temp_dir) / "test_budget_tracker.json"
        self.cost_tracker = CostTracker(
            monthly_limit_usd=1000.0, tracker_path=tracker_path
        )  # High limit for tests
        self.conversation_logger = ConversationLogger(enabled=False)

        # Track mock agents
        self._mock_agents: dict[str, MockAgent] = {}

    def _create_test_config(self) -> Config:
        """Create test configuration.

        Returns:
            Test configuration
        """
        config_data = {
            "budget": {"monthly_limit_usd": 100.0},
            "logging": {"conversation_logging_enabled": False},
            "soar": {
                "timeout_seconds": 60,
                "max_retries": 2,
            },
        }
        return Config(data=config_data)

    def _create_test_store(self) -> SQLiteStore:
        """Create test store in temp directory.

        Returns:
            Test store
        """
        import os

        db_path = os.path.join(self.temp_dir, "test_aurora.db")
        return SQLiteStore(db_path=db_path)

    def create_orchestrator(self) -> SOAROrchestrator:
        """Create orchestrator with test configuration.

        Returns:
            Test orchestrator
        """
        return SOAROrchestrator(
            store=self.store,
            agent_registry=self.agent_registry,
            config=self.config,
            reasoning_llm=self.mock_llm,
            solving_llm=self.mock_llm,
            cost_tracker=self.cost_tracker,
            conversation_logger=self.conversation_logger,
        )

    def register_mock_agent(self, agent: MockAgent) -> None:
        """Register a mock agent in the registry.

        Args:
            agent: Mock agent to register
        """
        from aurora_soar.agent_registry import AgentInfo

        self._mock_agents[agent.agent_id] = agent
        agent_info = AgentInfo(
            id=agent.agent_id,
            name=agent.agent_id.replace("-", " ").title(),
            description=f"Mock agent: {agent.agent_id}",
            capabilities=agent.capabilities,
            agent_type="local",
            config={},
        )
        self.agent_registry.register(agent_info)

    def configure_assessment_response(self, complexity: str, confidence: float = 0.9) -> None:
        """Configure mock response for complexity assessment.

        Args:
            complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            confidence: Assessment confidence
        """
        response = MockLLMResponse(
            content=json.dumps(
                {
                    "complexity": complexity,
                    "confidence": confidence,
                    "reasoning": f"Mock assessment: {complexity}",
                }
            ),
            input_tokens=200,
            output_tokens=50,
        )
        # Match on more specific patterns to avoid conflicts with synthesis verification
        # Use patterns that appear in assessment prompts but not in synthesis verification
        self.mock_llm.configure_response("query complexity analyzer", response)
        self.mock_llm.configure_response("classify user queries", response)

    def configure_decomposition_response(self, subgoals: list[dict[str, Any]]) -> None:
        """Configure mock response for query decomposition.

        Args:
            subgoals: List of subgoal dictionaries with proper Phase 2 format
        """
        # Convert subgoals to proper format if needed
        formatted_subgoals = []
        for i, sg in enumerate(subgoals):
            formatted_sg = {
                "description": sg.get("description", f"Subgoal {i + 1}"),
                "suggested_agent": sg.get("agent_type", sg.get("suggested_agent", "mock-agent")),
                "is_critical": sg.get("is_critical", True),
                "depends_on": sg.get("dependencies", sg.get("depends_on", [])),
            }
            formatted_subgoals.append(formatted_sg)

        # Create proper execution_order structure
        execution_order = [
            {"phase": 1, "parallelizable": list(range(len(subgoals))), "sequential": []}
        ]

        response = MockLLMResponse(
            content=json.dumps(
                {
                    "goal": "Mock goal",
                    "subgoals": formatted_subgoals,
                    "execution_order": execution_order,
                    "expected_tools": ["mock-tool"],
                }
            ),
            input_tokens=500,
            output_tokens=200,
        )
        # Match on multiple possible patterns in decomposition prompts
        self.mock_llm.configure_response("subgoal", response)
        self.mock_llm.configure_response("decompose", response)
        self.mock_llm.configure_response("break down", response)

    def configure_verification_response(
        self, verdict: str, score: float, feedback: str = ""
    ) -> None:
        """Configure mock response for verification.

        Args:
            verdict: Verification verdict (PASS, RETRY, FAIL)
            score: Verification score (0-1)
            feedback: Feedback message
        """
        response = MockLLMResponse(
            content=json.dumps(
                {
                    "completeness": score,
                    "consistency": score,
                    "groundedness": score,
                    "routability": score,
                    "overall_score": score,
                    "verdict": verdict,
                    "issues": [feedback] if feedback else [],
                    "suggestions": [],
                }
            ),
            input_tokens=400,
            output_tokens=150,
        )
        # Match on unique patterns for decomposition verification (not synthesis verification)
        self.mock_llm.configure_response("CONSISTENCY", response)
        self.mock_llm.configure_response("GROUNDEDNESS", response)
        self.mock_llm.configure_response("ROUTABILITY", response)

    def configure_synthesis_response(
        self, answer: str, confidence: float = 0.9, agent_name: str | None = None
    ) -> None:
        """Configure mock response for synthesis.

        Args:
            answer: Synthesized answer
            confidence: Synthesis confidence
            agent_name: Optional agent name to reference for traceability.
                       If not provided, uses first registered agent or "mock-agent".
        """
        # Auto-detect agent name from registered agents if not provided
        if agent_name is None:
            if self._mock_agents:
                # Use first registered agent
                agent_name = list(self._mock_agents.keys())[0]
            else:
                agent_name = "mock-agent"

        # Format response according to synthesis phase requirements
        # Include agent reference for traceability validation
        answer_with_citation = f"{answer} (Agent: {agent_name})"
        content = f"ANSWER: {answer_with_citation}\nCONFIDENCE: {confidence}"
        response = MockLLMResponse(content=content, input_tokens=600, output_tokens=300)
        # Multiple patterns for synthesis text generation (avoid patterns that appear in verification)
        self.mock_llm.configure_response("synthesizing information", response)
        self.mock_llm.configure_response("combine the agent outputs", response)

        # Also configure synthesis verification response (called after synthesis)
        verification_response = MockLLMResponse(
            content=json.dumps(
                {
                    "coherence": 0.9,
                    "completeness": 0.9,
                    "factuality": 0.9,
                    "overall_score": 0.9,
                }
            ),
            input_tokens=200,
            output_tokens=50,
        )
        # Match on verification-specific patterns (case-insensitive)
        self.mock_llm.configure_response("COHERENCE", verification_response)
        self.mock_llm.configure_response("COMPLETENESS", verification_response)
        self.mock_llm.configure_response("FACTUALITY", verification_response)
        self.mock_llm.configure_response("quality verifier", verification_response)

    def assert_phase_executed(self, response: dict[str, Any], phase_name: str) -> None:
        """Assert that a specific phase was executed.

        Args:
            response: Orchestrator response
            phase_name: Phase name to check (e.g., "phase1_assess")
        """
        assert "metadata" in response, "Response missing metadata"
        assert "phases" in response["metadata"], "Metadata missing phases"
        assert phase_name in response["metadata"]["phases"], f"Phase {phase_name} not executed"

    def assert_performance(self, response: dict[str, Any], max_duration_ms: float) -> None:
        """Assert that query completed within time limit.

        Args:
            response: Orchestrator response
            max_duration_ms: Maximum allowed duration in milliseconds
        """
        assert "metadata" in response, "Response missing metadata"
        duration = response["metadata"].get("total_duration_ms", 0)
        assert duration <= max_duration_ms, (
            f"Query took {duration}ms, expected <{max_duration_ms}ms"
        )

    def assert_cost_within_limit(self, response: dict[str, Any], max_cost_usd: float) -> None:
        """Assert that query cost is within limit.

        Args:
            response: Orchestrator response
            max_cost_usd: Maximum allowed cost in USD
        """
        assert "metadata" in response, "Response missing metadata"
        cost = response["metadata"].get("total_cost_usd", 0)
        assert cost <= max_cost_usd, f"Query cost ${cost}, expected <${max_cost_usd}"

    def measure_performance(self, func: callable) -> tuple[Any, float]:
        """Measure execution time of a function.

        Args:
            func: Function to measure

        Returns:
            Tuple of (result, duration_ms)
        """
        start_time = time.time()
        result = func()
        duration_ms = (time.time() - start_time) * 1000
        return result, duration_ms

    def cleanup(self) -> None:
        """Clean up test resources."""
        self.store.close()
        self.mock_llm.reset()
        for agent in self._mock_agents.values():
            agent.reset()


def create_mock_decomposition(num_subgoals: int = 3) -> dict[str, Any]:
    """Create a mock decomposition for testing.

    Args:
        num_subgoals: Number of subgoals to create

    Returns:
        Mock decomposition dictionary
    """
    subgoals = []
    for i in range(num_subgoals):
        subgoals.append(
            {
                "id": f"subgoal_{i + 1}",
                "description": f"Mock subgoal {i + 1}",
                "agent_type": f"mock-agent-{i % 2}",
                "inputs": {},
                "dependencies": [],
            }
        )

    return {
        "goal": "Mock goal",
        "subgoals": subgoals,
        "execution_order": list(range(num_subgoals)),
        "parallelizable": [list(range(num_subgoals))],
    }


def create_mock_agent_response(agent_id: str, confidence: float = 0.9) -> dict[str, Any]:
    """Create a mock agent response.

    Args:
        agent_id: Agent identifier
        confidence: Response confidence

    Returns:
        Mock agent response dictionary
    """
    return {
        "summary": f"Mock response from {agent_id}",
        "data": {"result": "mock data"},
        "confidence": confidence,
        "metadata": {
            "agent_id": agent_id,
            "duration_ms": 100,
            "model_used": "mock-model",
        },
    }
