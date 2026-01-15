"""Fault injection tests for bad decompositions.

Tests how the verification system handles intentionally bad decompositions:
- Incomplete subgoals that don't cover the full query
- Missing dependencies causing execution order issues
- Circular dependencies
- Verify phase catches issues and triggers retry loop
- Max retries exhaustion handling
"""

from unittest.mock import MagicMock, patch

import pytest

from aurora_reasoning.decompose import DecompositionResult
from aurora_reasoning.verify import VerificationOption, VerificationResult, VerificationVerdict
from aurora_soar.phases.verify import verify_decomposition


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client.

    Note: generate_json return value is NOT set here to allow tests to configure it.
    Tests that need a specific return value should set it themselves.
    """
    client = MagicMock()
    return client


@patch("aurora_reasoning.verify.verify_decomposition")
class TestIncompleteSubgoals:
    """Test verification catches incomplete subgoals."""

    @pytest.fixture
    def incomplete_decomposition(self):
        """Create decomposition with incomplete subgoals."""
        return DecompositionResult(
            goal="Complete task A, B, and C",
            subgoals=[
                {
                    "description": "Do task A",
                    "suggested_agent": "agent-1",
                    "is_critical": True,
                    "depends_on": [],
                },
                # Missing task B and C - incomplete coverage
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["tool-1"],
        )

    def test_incomplete_subgoals_caught(
        self, mock_reasoning_verify, mock_llm_client, incomplete_decomposition
    ):
        """Test that incomplete subgoals are caught by verification."""
        # Verification should detect incompleteness and return low completeness score
        low_completeness_verification = VerificationResult(
            completeness=0.3,  # Low completeness score
            consistency=0.8,
            groundedness=0.7,
            routability=0.8,
            overall_score=0.46,  # Below 0.5 threshold
            verdict=VerificationVerdict.FAIL,
            issues=["Decomposition only addresses task A but query requires A, B, and C"],
            suggestions=["Add subgoals for task B and task C"],
            option_used=VerificationOption.SELF,
        )

        mock_reasoning_verify.return_value = low_completeness_verification

        result = verify_decomposition(
            decomposition=incomplete_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Complete task A, B, and C",
        )

        # Should fail due to incompleteness
        assert result.final_verdict == "FAIL"
        assert result.verification.completeness < 0.5
        assert any("task" in issue.lower() for issue in result.verification.issues)

    @patch("aurora_soar.phases.decompose.decompose_query")
    @patch("aurora_reasoning.llm_client.LLMClient.generate")
    def test_incomplete_triggers_retry(
        self,
        mock_llm_generate,
        mock_phase_decompose,
        mock_reasoning_verify,
        mock_llm_client,
        incomplete_decomposition,
    ):
        """Test that incomplete subgoals trigger retry loop."""
        from aurora_reasoning.llm_client import LLMResponse
        from aurora_soar.phases.decompose import DecomposePhaseResult

        # First attempt: RETRY verdict
        retry_verification = VerificationResult(
            completeness=0.5,  # Borderline score triggers retry
            consistency=0.7,
            groundedness=0.6,
            routability=0.7,
            overall_score=0.58,  # Between 0.5 and 0.7
            verdict=VerificationVerdict.RETRY,
            issues=["Missing subgoals for task B and C"],
            suggestions=["Add comprehensive subgoals for all tasks"],
            option_used=VerificationOption.SELF,
        )

        # Second attempt: PASS after correction
        pass_verification = VerificationResult(
            completeness=0.9,
            consistency=0.8,
            groundedness=0.8,
            routability=0.9,
            overall_score=0.86,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        mock_reasoning_verify.side_effect = [retry_verification, pass_verification]

        # Mock LLM generate for retry feedback
        mock_llm_generate.return_value = LLMResponse(
            content="Add missing subgoals for tasks B and C",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        # Create corrected decomposition for retry
        corrected_decomposition = DecompositionResult(
            goal="Complete task A, B, and C",
            subgoals=[
                {
                    "description": "Do task A",
                    "suggested_agent": "agent-1",
                    "is_critical": True,
                    "depends_on": [],
                },
                {
                    "description": "Do task B",
                    "suggested_agent": "agent-2",
                    "is_critical": True,
                    "depends_on": [0],
                },
                {
                    "description": "Do task C",
                    "suggested_agent": "agent-3",
                    "is_critical": True,
                    "depends_on": [1],
                },
            ],
            execution_order=[
                {"phase": 1, "parallelizable": [0], "sequential": []},
                {"phase": 2, "parallelizable": [1], "sequential": []},
                {"phase": 3, "parallelizable": [2], "sequential": []},
            ],
            expected_tools=["tool-1", "tool-2", "tool-3"],
        )

        mock_phase_decompose.return_value = DecomposePhaseResult(
            decomposition=corrected_decomposition,
            cached=False,
            query_hash="corrected",
            timing_ms=200,
        )

        # Configure mock_llm_client.generate_json to return proper decomposition dict
        # (This is needed in case the phase_decompose mock doesn't intercept all calls)
        mock_llm_client.generate_json.return_value = corrected_decomposition.to_dict()

        result = verify_decomposition(
            decomposition=incomplete_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Complete task A, B, and C",
            max_retries=2,
        )

        # Should pass after retry
        assert result.final_verdict == "PASS"
        assert result.retry_count == 1
        assert len(result.all_attempts) == 2

        # Verify reasoning_verify was called twice
        assert mock_reasoning_verify.call_count == 2


@patch("aurora_reasoning.verify.verify_decomposition")
@patch("aurora_soar.phases.decompose.decompose_query")
class TestMissingDependencies:
    """Test verification catches missing dependencies."""

    @pytest.fixture
    def missing_dependency_decomposition(self):
        """Create decomposition with missing/incorrect dependencies."""
        return DecompositionResult(
            goal="Read file, process data, write results",
            subgoals=[
                {
                    "description": "Process the data",
                    "suggested_agent": "processor",
                    "is_critical": True,
                    "depends_on": [],  # Should depend on read_file but doesn't
                },
                {
                    "description": "Read file",
                    "suggested_agent": "reader",
                    "is_critical": True,
                    "depends_on": [],
                },
                {
                    "description": "Write results",
                    "suggested_agent": "writer",
                    "is_critical": True,
                    "depends_on": [],  # Should depend on process_data but doesn't
                },
            ],
            execution_order=[
                {
                    "phase": 1,
                    "parallelizable": [0, 1, 2],  # All parallel - incorrect!
                    "sequential": [],
                }
            ],
            expected_tools=["file-reader", "processor", "file-writer"],
        )

    def test_missing_dependencies_caught(
        self,
        mock_phase_decompose,
        mock_reasoning_verify,
        mock_llm_client,
        missing_dependency_decomposition,
    ):
        """Test that missing dependencies are caught by verification."""
        # Verification should detect consistency issues
        low_consistency_verification = VerificationResult(
            completeness=0.9,
            consistency=0.2,  # Low consistency due to missing dependencies
            groundedness=0.7,
            routability=0.6,
            overall_score=0.62,  # 0.4*0.9 + 0.2*0.2 + 0.2*0.7 + 0.2*0.6
            verdict=VerificationVerdict.RETRY,
            issues=[
                "Subgoal 0 (Process data) requires data but doesn't depend on subgoal 1 (Read file)",
                "Subgoal 2 (Write results) should depend on subgoal 0 (Process data)",
            ],
            suggestions=[
                "Add dependency from subgoal 0 to subgoal 1",
                "Add dependency from subgoal 2 to subgoal 0",
            ],
            option_used=VerificationOption.SELF,
        )

        mock_reasoning_verify.return_value = low_consistency_verification

        result = verify_decomposition(
            decomposition=missing_dependency_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Read file, process data, write results",
            max_retries=0,  # Don't retry - we want to see the RETRY verdict become FAIL
        )

        # Should detect consistency issues
        # Note: When RETRY verdict is returned on first attempt without actually retrying,
        # the final_verdict becomes FAIL (see verify.py line 164)
        assert result.final_verdict == "FAIL"
        assert result.verification.consistency < 0.5
        assert result.verification.verdict == VerificationVerdict.RETRY
        assert any("depend" in issue.lower() for issue in result.verification.issues)


@patch("aurora_reasoning.verify.verify_decomposition")
@patch("aurora_soar.phases.decompose.decompose_query")
class TestCircularDependencies:
    """Test verification catches circular dependencies."""

    @pytest.fixture
    def circular_dependency_decomposition(self):
        """Create decomposition with circular dependencies."""
        return DecompositionResult(
            goal="Execute tasks with circular dependencies",
            subgoals=[
                {
                    "description": "Task A depends on Task B",
                    "suggested_agent": "agent-a",
                    "is_critical": True,
                    "depends_on": [1],  # Depends on Task B
                },
                {
                    "description": "Task B depends on Task C",
                    "suggested_agent": "agent-b",
                    "is_critical": True,
                    "depends_on": [2],  # Depends on Task C
                },
                {
                    "description": "Task C depends on Task A",
                    "suggested_agent": "agent-c",
                    "is_critical": True,
                    "depends_on": [0],  # Depends on Task A - creates cycle!
                },
            ],
            execution_order=[
                {
                    "phase": 1,
                    "parallelizable": [],
                    "sequential": [0, 1, 2],  # Invalid - circular dependency
                }
            ],
            expected_tools=["tool-a", "tool-b", "tool-c"],
        )

    def test_circular_dependencies_caught(
        self,
        mock_phase_decompose,
        mock_reasoning_verify,
        mock_llm_client,
        circular_dependency_decomposition,
    ):
        """Test that circular dependencies are caught by verification."""
        # Verification should detect routability issues
        low_routability_verification = VerificationResult(
            completeness=0.8,
            consistency=0.5,
            groundedness=0.7,
            routability=0.1,  # Very low routability due to circular deps
            overall_score=0.52,  # 0.4*0.8 + 0.2*0.5 + 0.2*0.7 + 0.2*0.1
            verdict=VerificationVerdict.RETRY,
            issues=[
                "Circular dependency detected: Task A → Task B → Task C → Task A",
                "Execution order cannot be determined due to dependency cycle",
            ],
            suggestions=[
                "Break the circular dependency by removing one of the dependencies",
                "Restructure tasks to have a clear execution order",
            ],
            option_used=VerificationOption.ADVERSARIAL,
        )

        mock_reasoning_verify.return_value = low_routability_verification

        result = verify_decomposition(
            decomposition=circular_dependency_decomposition,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            query="Execute tasks with circular dependencies",
            max_retries=0,  # Don't retry - we want to see the RETRY verdict become FAIL
        )

        # Should detect routability issues
        # Note: When RETRY verdict is returned on first attempt without actually retrying,
        # the final_verdict becomes FAIL (see verify.py line 164)
        assert result.final_verdict == "FAIL"
        assert result.verification.routability < 0.5
        assert result.verification.verdict == VerificationVerdict.RETRY
        assert any(
            "circular" in issue.lower() or "cycle" in issue.lower()
            for issue in result.verification.issues
        )


@patch("aurora_reasoning.verify.verify_decomposition")
class TestRetryLoopExhaustion:
    """Test max retries exhaustion handling."""

    @pytest.fixture
    def persistently_bad_decomposition(self):
        """Create decomposition that never passes verification."""
        return DecompositionResult(
            goal="Impossible task",
            subgoals=[
                {
                    "description": "Do something impossible",
                    "suggested_agent": "impossible-agent",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["impossible-tool"],
        )

    @patch("aurora_reasoning.llm_client.LLMClient.generate")
    def test_max_retries_exhaustion(
        self,
        mock_llm_generate,
        mock_reasoning_verify,
        mock_llm_client,
        persistently_bad_decomposition,
    ):
        """Test that max retries are enforced and result in FAIL."""
        from aurora_reasoning.llm_client import LLMResponse

        # Always return RETRY verdict (never passes)
        persistent_retry_verification = VerificationResult(
            completeness=0.5,
            consistency=0.6,
            groundedness=0.5,
            routability=0.6,
            overall_score=0.54,  # Between 0.5 and 0.7 - RETRY
            verdict=VerificationVerdict.RETRY,
            issues=["Fundamental issue that can't be fixed"],
            suggestions=["Try a different approach"],
            option_used=VerificationOption.SELF,
        )

        mock_reasoning_verify.return_value = persistent_retry_verification

        # Mock LLM generate for retry feedback
        mock_llm_generate.return_value = LLMResponse(
            content="Try fixing this issue",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        # Configure mock_llm_client.generate_json to return proper decomposition
        # (This is the llm_client instance passed to functions, not the class patch)
        mock_llm_client.generate_json.return_value = persistently_bad_decomposition.to_dict()

        # Note: Not mocking phase_decompose - let it run with mocked generate_json

        result = verify_decomposition(
            decomposition=persistently_bad_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Impossible task",
            max_retries=3,
        )

        # Should fail after max retries exhausted
        assert result.final_verdict == "FAIL"
        assert result.retry_count == 3
        assert len(result.all_attempts) == 4  # Initial + 3 retries

        # Verify retry was attempted max_retries times
        assert mock_reasoning_verify.call_count == 4
        # Note: Not checking phase_decompose call_count since we're not mocking it

    def test_fail_verdict_no_retry(
        self,
        mock_reasoning_verify,
        mock_llm_client,
        persistently_bad_decomposition,
    ):
        """Test that FAIL verdict does not trigger retry loop."""
        # Return immediate FAIL verdict
        fail_verification = VerificationResult(
            completeness=0.2,
            consistency=0.3,
            groundedness=0.2,
            routability=0.3,
            overall_score=0.24,  # Below 0.5 threshold
            verdict=VerificationVerdict.FAIL,
            issues=["Fundamental design flaw - cannot be fixed with retry"],
            suggestions=["Completely redesign the approach"],
            option_used=VerificationOption.ADVERSARIAL,
        )

        mock_reasoning_verify.return_value = fail_verification

        result = verify_decomposition(
            decomposition=persistently_bad_decomposition,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            query="Impossible task",
            max_retries=3,
        )

        # Should fail immediately without retry
        assert result.final_verdict == "FAIL"
        assert result.retry_count == 0
        assert len(result.all_attempts) == 1

        # Verify no retry was attempted
        assert mock_reasoning_verify.call_count == 1


@patch("aurora_reasoning.verify.verify_decomposition")
class TestMultipleBadQualityDimensions:
    """Test decompositions with multiple quality issues."""

    @pytest.fixture
    def multi_issue_decomposition(self):
        """Create decomposition with multiple quality issues."""
        return DecompositionResult(
            goal="Complex task with multiple issues",
            subgoals=[
                {
                    "description": "Vague task description",  # Poor groundedness
                    "suggested_agent": "nonexistent-agent",  # Poor routability
                    "is_critical": True,
                    "depends_on": [1],  # Depends on missing subgoal - poor consistency
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["unknown-tool"],
        )

    def test_multiple_quality_issues(
        self, mock_reasoning_verify, mock_llm_client, multi_issue_decomposition
    ):
        """Test that multiple quality issues are all caught."""
        # All dimensions score low
        multi_issue_verification = VerificationResult(
            completeness=0.4,  # Incomplete
            consistency=0.3,  # Invalid dependencies
            groundedness=0.2,  # Vague descriptions
            routability=0.3,  # Invalid agent
            overall_score=0.3,  # 0.4*0.4 + 0.2*0.3 + 0.2*0.2 + 0.2*0.3
            verdict=VerificationVerdict.FAIL,
            issues=[
                "Vague task descriptions lack concrete actions",
                "References nonexistent agent 'nonexistent-agent'",
                "Dependency on non-existent subgoal index 1",
                "Incomplete decomposition for complex task",
            ],
            suggestions=[
                "Provide concrete, actionable descriptions",
                "Use valid agent names from registry",
                "Fix dependency references",
                "Add missing subgoals",
            ],
            option_used=VerificationOption.ADVERSARIAL,
        )

        mock_reasoning_verify.return_value = multi_issue_verification

        result = verify_decomposition(
            decomposition=multi_issue_decomposition,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            query="Complex task with multiple issues",
        )

        # Should fail with multiple issues identified
        assert result.final_verdict == "FAIL"
        assert len(result.verification.issues) >= 3
        assert result.verification.overall_score < 0.5
