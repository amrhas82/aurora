"""Unit tests for prompt templates."""

from aurora_reasoning.prompts.assess import AssessPromptTemplate
from aurora_reasoning.prompts.decompose import DecomposePromptTemplate
from aurora_reasoning.prompts.examples import Complexity, ExamplesLoader, get_loader
from aurora_reasoning.prompts.retry_feedback import RetryFeedbackPromptTemplate
from aurora_reasoning.prompts.verify_adversarial import VerifyAdversarialPromptTemplate
from aurora_reasoning.prompts.verify_agent_output import VerifyAgentOutputPromptTemplate
from aurora_reasoning.prompts.verify_self import VerifySelfPromptTemplate
from aurora_reasoning.prompts.verify_synthesis import VerifySynthesisPromptTemplate


class TestAssessPromptTemplate:
    """Test complexity assessment prompt template."""

    def test_system_prompt_contains_key_instructions(self):
        """Test system prompt has required instructions."""
        template = AssessPromptTemplate()
        system = template.build_system_prompt()

        assert "SIMPLE" in system
        assert "MEDIUM" in system
        assert "COMPLEX" in system
        assert "CRITICAL" in system
        assert "JSON" in system

    def test_user_prompt_with_query(self):
        """Test user prompt includes query."""
        template = AssessPromptTemplate()
        user = template.build_user_prompt(query="What is this function?")

        assert "What is this function?" in user

    def test_user_prompt_with_keyword_result(self):
        """Test user prompt includes keyword classification."""
        template = AssessPromptTemplate()
        keyword_result = {
            "complexity": "MEDIUM",
            "score": 0.5,
            "confidence": 0.6,
        }
        user = template.build_user_prompt(query="Test query", keyword_result=keyword_result)

        assert "MEDIUM" in user
        assert "0.50" in user or "0.5" in user
        assert "uncertain" in user.lower()

    def test_build_full_prompt(self):
        """Test building complete prompt."""
        template = AssessPromptTemplate()
        prompt = template.build_prompt(query="Test query")

        assert "system" in prompt
        assert "user" in prompt
        assert len(prompt["system"]) > 0
        assert len(prompt["user"]) > 0


class TestDecomposePromptTemplate:
    """Test query decomposition prompt template."""

    def test_user_prompt_with_query(self):
        """Test user prompt includes query."""
        template = DecomposePromptTemplate()
        user = template.build_user_prompt(query="Add a feature")

        assert "Add a feature" in user

    def test_user_prompt_with_context_summary(self):
        """Test user prompt includes context."""
        template = DecomposePromptTemplate()
        user = template.build_user_prompt(query="Test query", context_summary="Context info here")

        assert "Context info here" in user

    def test_user_prompt_with_retry_feedback(self):
        """Test user prompt includes retry feedback."""
        template = DecomposePromptTemplate()
        user = template.build_user_prompt(
            query="Test query",
            retry_feedback="Try again with more detail",
        )

        assert "Try again with more detail" in user
        assert "previous" in user.lower()


class TestVerifySelfPromptTemplate:
    """Test self-verification prompt template."""

    def test_system_prompt_contains_scoring_dimensions(self):
        """Test system prompt has all scoring dimensions."""
        template = VerifySelfPromptTemplate()
        system = template.build_system_prompt()

        assert "COMPLETENESS" in system
        assert "CONSISTENCY" in system
        assert "GROUNDEDNESS" in system
        assert "ROUTABILITY" in system
        assert "PASS" in system
        assert "RETRY" in system
        assert "FAIL" in system

    def test_user_prompt_includes_decomposition(self):
        """Test user prompt includes decomposition."""
        template = VerifySelfPromptTemplate()
        decomposition = {"goal": "Test goal", "subgoals": [{"description": "Step 1"}]}
        user = template.build_user_prompt(query="Test query", decomposition=decomposition)

        assert "Test goal" in user
        assert "Step 1" in user


class TestVerifyAdversarialPromptTemplate:
    """Test adversarial verification prompt template."""

    def test_system_prompt_has_red_team_instructions(self):
        """Test system prompt emphasizes adversarial stance."""
        template = VerifyAdversarialPromptTemplate()
        system = template.build_system_prompt()

        assert "RED TEAM" in system or "adversarial" in system.lower()
        assert "flaws" in system.lower()
        assert "critical" in system.lower()

    def test_user_prompt_emphasizes_red_team_mode(self):
        """Test user prompt emphasizes red team mode."""
        template = VerifyAdversarialPromptTemplate()
        decomposition = {"goal": "Test"}
        user = template.build_user_prompt(query="Test query", decomposition=decomposition)

        assert "RED TEAM" in user or "critical" in user.lower()


class TestVerifyAgentOutputPromptTemplate:
    """Test agent output verification prompt template."""

    def test_system_prompt_contains_quality_criteria(self):
        """Test system prompt has quality criteria."""
        template = VerifyAgentOutputPromptTemplate()
        system = template.build_system_prompt()

        assert "COMPLETENESS" in system
        assert "CORRECTNESS" in system
        assert "quality" in system.lower()

    def test_user_prompt_includes_agent_output(self):
        """Test user prompt includes agent output."""
        template = VerifyAgentOutputPromptTemplate()
        agent_output = {"summary": "Completed task", "data": {"result": "success"}}
        user = template.build_user_prompt(subgoal="Do something", agent_output=agent_output)

        assert "Do something" in user
        assert "Completed task" in user


class TestVerifySynthesisPromptTemplate:
    """Test synthesis verification prompt template."""

    def test_system_prompt_contains_traceability_check(self):
        """Test system prompt checks traceability/factuality."""
        template = VerifySynthesisPromptTemplate()
        system = template.build_system_prompt()

        # Implementation uses "FACTUALITY" instead of "TRACEABILITY"
        assert "FACTUALITY" in system or "TRACEABILITY" in system
        assert "grounded" in system.lower()

    def test_user_prompt_includes_synthesis_and_sources(self):
        """Test user prompt includes synthesis and agent outputs."""
        template = VerifySynthesisPromptTemplate()
        user = template.build_user_prompt(
            query="Test query",
            synthesis_answer="This is the synthesized answer",
            agent_outputs=[{"agent_name": "test", "summary": "did work", "confidence": 0.9}],
        )

        assert "synthesized answer" in user.lower()
        assert "did work" in user


class TestRetryFeedbackPromptTemplate:
    """Test retry feedback generation prompt template."""

    def test_system_prompt_focuses_on_actionable_feedback(self):
        """Test system prompt emphasizes actionable feedback."""
        template = RetryFeedbackPromptTemplate()
        system = template.build_system_prompt()

        assert "actionable" in system.lower()
        assert "feedback" in system.lower()

    def test_user_prompt_includes_verification_result(self):
        """Test user prompt includes verification result."""
        template = RetryFeedbackPromptTemplate()
        verification = {
            "verdict": "RETRY",
            "issues": ["Problem 1", "Problem 2"],
            "suggestions": ["Fix 1"],
        }
        user = template.build_user_prompt(verification_result=verification, attempt_number=1)

        assert "Problem 1" in user
        assert "Problem 2" in user


class TestExamplesLoader:
    """Test few-shot examples loader."""

    def test_get_examples_by_complexity_simple(self):
        """Test loading 0 examples for SIMPLE complexity."""
        loader = ExamplesLoader()
        # Note: This will fail if example file doesn't exist, but that's expected
        try:
            examples = loader.get_examples_by_complexity(
                "example_decompositions.json",
                Complexity.SIMPLE,
            )
            assert len(examples) == 0
        except FileNotFoundError:
            # Expected if running tests without examples
            pass

    def test_get_loader_singleton(self):
        """Test global loader singleton."""
        loader1 = get_loader()
        loader2 = get_loader()
        assert loader1 is loader2


class TestPromptTemplateWithExamples:
    """Test prompt template with few-shot examples."""

    def test_build_prompt_with_examples(self):
        """Test building prompt with examples."""
        template = AssessPromptTemplate()
        examples = [
            {
                "query": "Example query",
                "complexity": "SIMPLE",
                "confidence": 0.9,
                "reasoning": "Direct question",
            },
        ]

        prompt = template.build_prompt(query="Test query", examples=examples)

        assert "Example" in prompt["user"]
        assert "Example query" in prompt["user"]
