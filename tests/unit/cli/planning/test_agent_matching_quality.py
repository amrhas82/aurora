"""Unit tests for agent matching quality and decomposition accuracy.

Tests validate:
1. Agent matching quality across different query types
2. Decomposition accuracy for various goal complexity levels
3. Gap detection when ideal agents differ from available agents
4. One-shot example effectiveness for few-shot prompting
5. Keyword extraction quality and stop word filtering
"""

from unittest.mock import Mock, patch

import pytest

from aurora_cli.planning.agents import AgentMatcher, AgentRecommender
from aurora_cli.planning.decompose import PlanDecomposer
from aurora_cli.planning.models import Complexity, Subgoal

# =============================================================================
# Agent Matching Quality Tests
# =============================================================================


class TestAgentMatchingQuality:
    """Test suite for agent matching quality across query types."""

    def _create_mock_manifest_with_agents(self, agents: list[dict]) -> Mock:
        """Create a mock manifest with specified agents.

        Args:
            agents: List of dicts with id, goal, when_to_use, capabilities

        Returns:
            Mock manifest object

        """
        mock_manifest = Mock()
        mock_agents = []

        for agent_data in agents:
            mock_agent = Mock()
            mock_agent.id = agent_data["id"]
            mock_agent.goal = agent_data.get("goal", "")
            mock_agent.when_to_use = agent_data.get("when_to_use", "")
            mock_agent.capabilities = agent_data.get("capabilities", [])
            mock_agents.append(mock_agent)

        mock_manifest.agents = mock_agents
        mock_manifest.get_agent = Mock(
            side_effect=lambda aid: next((a for a in mock_agents if a.id == aid), None),
        )
        return mock_manifest

    # -------------------------------------------------------------------------
    # Testing/QA Query Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "title,description,expected_agent",
        [
            (
                "Write unit tests for authentication",
                "Create comprehensive unit tests for the OAuth2 authentication module",
                "@quality-assurance",
            ),
            (
                "Add integration tests",
                "Write integration tests for the payment processing pipeline",
                "@quality-assurance",
            ),
            (
                "Test coverage and quality",
                "Generate test coverage report and review quality assurance testing",
                "@quality-assurance",
            ),
            (
                "Quality assurance review",
                "Review code quality and testing strategy for the API layer",
                "@quality-assurance",
            ),
        ],
    )
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_testing_queries_match_qa_agent(
        self,
        mock_manager_class,
        title,
        description,
        expected_agent,
    ):
        """Test that testing-related queries match quality-assurance."""
        manifest = self._create_mock_manifest_with_agents(
            [
                {
                    "id": "quality-assurance",
                    "goal": "Quality assurance and testing specialist",
                    "when_to_use": "testing, quality assurance, test architecture, unit tests, integration tests",
                    "capabilities": ["testing", "quality", "pytest", "coverage", "integration"],
                },
                {
                    "id": "code-developer",
                    "goal": "Full-stack development",
                    "when_to_use": "coding, implementation, features",
                    "capabilities": ["python", "javascript", "api"],
                },
            ],
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender(score_threshold=0.3)
        subgoal = Subgoal(
            id="sg-1",
            title=title,
            description=description,
            assigned_agent="@code-developer",
        )

        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        assert agent_id == expected_agent, f"Expected {expected_agent} for '{title}'"
        assert score >= 0.3, f"Score {score} too low for testing query"

    # -------------------------------------------------------------------------
    # Development/Implementation Query Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "title,description,expected_agent",
        [
            (
                "Implement backend API",
                "Add backend API implementation with python development coding",
                "@code-developer",
            ),
            (
                "Debug and fix application bugs",
                "Debug application issues and fix bugs in the codebase using debugging tools",
                "@code-developer",
            ),
            (
                "Refactor backend code",
                "Refactor backend code implementation for better coding patterns",
                "@code-developer",
            ),
            (
                "Develop frontend features",
                "Implement frontend javascript development for new features",
                "@code-developer",
            ),
        ],
    )
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_development_queries_match_dev_agent(
        self,
        mock_manager_class,
        title,
        description,
        expected_agent,
    ):
        """Test that development queries match code-developer."""
        manifest = self._create_mock_manifest_with_agents(
            [
                {
                    "id": "code-developer",
                    "goal": "Full-stack development specialist",
                    "when_to_use": "implementing features, coding, development, api, debugging, refactoring, backend, frontend",
                    "capabilities": [
                        "python",
                        "javascript",
                        "backend",
                        "frontend",
                        "debugging",
                        "coding",
                        "implementation",
                    ],
                },
                {
                    "id": "quality-assurance",
                    "goal": "Testing specialist",
                    "when_to_use": "testing, qa",
                    "capabilities": ["testing"],
                },
            ],
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender(score_threshold=0.2)
        subgoal = Subgoal(
            id="sg-1",
            title=title,
            description=description,
            assigned_agent="@quality-assurance",
        )

        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        assert agent_id == expected_agent, f"Expected {expected_agent} for '{title}'"
        assert score >= 0.2

    # -------------------------------------------------------------------------
    # Architecture/Design Query Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "title,description,expected_agent",
        [
            (
                "Design API architecture",
                "Design RESTful API architecture with proper resource modeling",
                "@system-architect",
            ),
            (
                "Plan microservices migration",
                "Create architecture plan for migrating from monolith to microservices",
                "@system-architect",
            ),
            (
                "System design review",
                "Review and document system architecture for the payment platform",
                "@system-architect",
            ),
            (
                "Architecture infrastructure planning",
                "Design system architecture and infrastructure planning for cloud deployment",
                "@system-architect",
            ),
        ],
    )
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_architecture_queries_match_architect_agent(
        self,
        mock_manager_class,
        title,
        description,
        expected_agent,
    ):
        """Test that architecture queries match system-architect."""
        manifest = self._create_mock_manifest_with_agents(
            [
                {
                    "id": "system-architect",
                    "goal": "System design and architecture specialist",
                    "when_to_use": "architecture, system design, API design, infrastructure planning",
                    "capabilities": ["design", "architecture", "api", "microservices", "database"],
                },
                {
                    "id": "code-developer",
                    "goal": "Development",
                    "when_to_use": "coding",
                    "capabilities": ["python"],
                },
            ],
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender(score_threshold=0.3)
        subgoal = Subgoal(
            id="sg-1",
            title=title,
            description=description,
            assigned_agent="@code-developer",
        )

        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        assert agent_id == expected_agent, f"Expected {expected_agent} for '{title}'"
        assert score >= 0.3

    # -------------------------------------------------------------------------
    # Product/Business Query Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "title,description,expected_agent",
        [
            (
                "Create PRD for feature",
                "Write product requirements document for the dashboard feature",
                "@feature-planner",
            ),
            (
                "Feature prioritization",
                "Analyze and prioritize features for the upcoming release",
                "@feature-planner",
            ),
            (
                "Market research analysis",
                "Research competitive landscape and market trends for pricing",
                "@market-researcher",
            ),
            (
                "Write user stories",
                "Create detailed user stories with acceptance criteria",
                "@backlog-manager",
            ),
        ],
    )
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_product_queries_match_product_agents(
        self,
        mock_manager_class,
        title,
        description,
        expected_agent,
    ):
        """Test that product queries match appropriate product agents."""
        manifest = self._create_mock_manifest_with_agents(
            [
                {
                    "id": "feature-planner",
                    "goal": "Product strategy and requirements",
                    "when_to_use": "PRD creation, product strategy, feature prioritization, roadmap planning",
                    "capabilities": [
                        "product",
                        "requirements",
                        "prd",
                        "prioritization",
                        "strategy",
                    ],
                },
                {
                    "id": "backlog-manager",
                    "goal": "Backlog and story management",
                    "when_to_use": "user stories, backlog management, acceptance criteria, sprint planning",
                    "capabilities": ["stories", "backlog", "acceptance", "criteria", "sprint"],
                },
                {
                    "id": "market-researcher",
                    "goal": "Business analysis and research",
                    "when_to_use": "market research, competitive analysis, business requirements",
                    "capabilities": ["research", "market", "analysis", "competitive", "business"],
                },
                {
                    "id": "code-developer",
                    "goal": "Development",
                    "when_to_use": "coding",
                    "capabilities": ["python"],
                },
            ],
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender(score_threshold=0.2)
        subgoal = Subgoal(
            id="sg-1",
            title=title,
            description=description,
            assigned_agent="@code-developer",
        )

        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        assert agent_id == expected_agent, f"Expected {expected_agent} for '{title}'"

    # -------------------------------------------------------------------------
    # UI/UX Query Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "title,description,expected_agent",
        [
            (
                "Design dashboard wireframes",
                "Create wireframes and mockups for the analytics dashboard",
                "@ui-designer",
            ),
            (
                "Improve user experience",
                "Optimize user flow and interaction patterns for onboarding",
                "@ui-designer",
            ),
            (
                "UI UX design review",
                "Review UI components and UX design for user experience optimization",
                "@ui-designer",
            ),
        ],
    )
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_ux_queries_match_ux_agent(
        self,
        mock_manager_class,
        title,
        description,
        expected_agent,
    ):
        """Test that UX queries match ui-designer."""
        manifest = self._create_mock_manifest_with_agents(
            [
                {
                    "id": "ui-designer",
                    "goal": "UI/UX design specialist",
                    "when_to_use": "UI/UX design, wireframes, prototypes, user experience optimization",
                    "capabilities": ["design", "wireframes", "ux", "accessibility", "ui", "user"],
                },
                {
                    "id": "code-developer",
                    "goal": "Development",
                    "when_to_use": "coding",
                    "capabilities": ["python"],
                },
            ],
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender(score_threshold=0.3)
        subgoal = Subgoal(
            id="sg-1",
            title=title,
            description=description,
            assigned_agent="@code-developer",
        )

        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        assert agent_id == expected_agent, f"Expected {expected_agent} for '{title}'"


# =============================================================================
# Gap Detection Tests
# =============================================================================


class TestAgentGapDetection:
    """Test agent gap detection when ideal differs from assigned."""

    def test_gap_detected_when_ideal_differs_from_assigned(self):
        """Test that gap is detected when ideal_agent != assigned_agent."""
        subgoal = {
            "id": "sg-1",
            "ideal_agent": "@creative-writer",
            "ideal_agent_desc": "Specialist in creative writing and storytelling",
            "assigned_agent": "@market-researcher",
            "description": "Write creative marketing copy",
        }

        matcher = AgentMatcher()
        result = matcher.match_subgoal(subgoal)

        assert result.is_gap is True
        assert result.gap_info is not None
        assert result.gap_info.ideal_agent == "@creative-writer"
        assert result.gap_info.assigned_agent == "@market-researcher"

    def test_no_gap_when_ideal_equals_assigned(self):
        """Test that no gap when ideal_agent == assigned_agent."""
        subgoal = {
            "id": "sg-1",
            "ideal_agent": "@code-developer",
            "ideal_agent_desc": "Development specialist",
            "assigned_agent": "@code-developer",
            "description": "Implement feature",
        }

        matcher = AgentMatcher()
        result = matcher.match_subgoal(subgoal)

        assert result.is_gap is False
        assert result.gap_info is None

    def test_detect_gaps_returns_all_gaps(self):
        """Test detect_gaps returns all subgoals with gaps."""
        subgoals = [
            {
                "id": "sg-1",
                "ideal_agent": "@creative-writer",
                "ideal_agent_desc": "Creative writing",
                "assigned_agent": "@market-researcher",
            },
            {
                "id": "sg-2",
                "ideal_agent": "@code-developer",
                "ideal_agent_desc": "Development",
                "assigned_agent": "@code-developer",
            },
            {
                "id": "sg-3",
                "ideal_agent": "@data-scientist",
                "ideal_agent_desc": "Data analysis",
                "assigned_agent": "@master",
            },
        ]

        matcher = AgentMatcher()
        gaps = matcher.detect_gaps(subgoals)

        assert len(gaps) == 2
        gap_ids = {g.subgoal_id for g in gaps}
        assert "sg-1" in gap_ids
        assert "sg-3" in gap_ids
        assert "sg-2" not in gap_ids

    def test_spawn_prompt_generated_for_gap(self):
        """Test spawn prompt is generated when for_spawn=True."""
        subgoal = {
            "id": "sg-1",
            "ideal_agent": "@creative-writer",
            "ideal_agent_desc": "Creative writing specialist",
            "assigned_agent": "@market-researcher",
            "description": "Write compelling marketing narrative",
        }

        matcher = AgentMatcher()
        result = matcher.match_subgoal(subgoal, for_spawn=True)

        assert result.is_gap is True
        assert result.spawn_prompt is not None
        assert "@creative-writer" in result.spawn_prompt
        assert "Creative writing specialist" in result.spawn_prompt

    def test_spawn_prompt_not_generated_without_gap(self):
        """Test spawn prompt not generated when no gap."""
        subgoal = {
            "id": "sg-1",
            "ideal_agent": "@code-developer",
            "ideal_agent_desc": "Development",
            "assigned_agent": "@code-developer",
            "description": "Implement feature",
        }

        matcher = AgentMatcher()
        result = matcher.match_subgoal(subgoal, for_spawn=True)

        assert result.is_gap is False
        assert result.spawn_prompt is None


# =============================================================================
# Keyword Extraction Quality Tests
# =============================================================================


class TestKeywordExtractionQuality:
    """Test keyword extraction quality for agent matching."""

    def test_stop_words_filtered(self):
        """Test that common stop words are filtered from keywords."""
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="The implementation of the authentication for the system",
            description="Add the OAuth2 authentication to the application",
            assigned_agent="@dev",
        )

        keywords = recommender._extract_keywords(subgoal)

        stop_words = ["the", "of", "for", "to", "a", "an", "is", "are"]
        for stop_word in stop_words:
            assert stop_word not in keywords, f"Stop word '{stop_word}' not filtered"

    def test_keywords_lowercased(self):
        """Test that all keywords are lowercased."""
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Implement OAuth2 AUTHENTICATION",
            description="Add JWT Tokens for USER sessions",
            assigned_agent="@dev",
        )

        keywords = recommender._extract_keywords(subgoal)

        assert all(k.islower() for k in keywords), "Not all keywords lowercase"
        assert "oauth2" in keywords or "oauth" in keywords
        assert "authentication" in keywords

    def test_short_words_filtered(self):
        """Test that words <= 2 chars are filtered."""
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Fix UI bug in DB API",
            description="A fix is needed for DB",
            assigned_agent="@dev",
        )

        keywords = recommender._extract_keywords(subgoal)

        # Short words should be filtered
        assert "ui" not in keywords
        assert "db" not in keywords
        assert "is" not in keywords
        # Longer words should remain
        assert "fix" in keywords
        assert "bug" in keywords

    def test_domain_keywords_extracted(self):
        """Test that domain-specific keywords are extracted."""
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Write pytest unit tests",
            description="Create comprehensive unit tests with pytest fixtures and mocks",
            assigned_agent="@dev",
        )

        keywords = recommender._extract_keywords(subgoal)

        assert "pytest" in keywords
        assert "tests" in keywords or "test" in keywords
        assert "unit" in keywords
        assert "fixtures" in keywords
        assert "mocks" in keywords


# =============================================================================
# Decomposition Accuracy Tests
# =============================================================================


class TestDecompositionAccuracy:
    """Test decomposition accuracy for various goal types."""

    def test_heuristic_simple_creates_three_subgoals(self):
        """Test SIMPLE complexity creates 3 subgoals via heuristic."""
        decomposer = PlanDecomposer()
        subgoals = decomposer._fallback_to_heuristics("Add login feature", Complexity.SIMPLE)

        assert len(subgoals) == 3
        titles = [sg.title.lower() for sg in subgoals]

        # Should have plan, implement, test
        assert any("plan" in t or "design" in t for t in titles)
        assert any("implement" in t for t in titles)
        assert any("test" in t or "verify" in t for t in titles)

    def test_heuristic_complex_creates_four_subgoals(self):
        """Test COMPLEX complexity creates 4 subgoals with documentation."""
        decomposer = PlanDecomposer()
        subgoals = decomposer._fallback_to_heuristics(
            "Implement payment system",
            Complexity.COMPLEX,
        )

        assert len(subgoals) == 4
        titles = [sg.title.lower() for sg in subgoals]

        # Should include documentation step
        assert any("document" in t for t in titles)

    def test_heuristic_assigns_appropriate_agents(self):
        """Test heuristic assigns appropriate agents for each step."""
        decomposer = PlanDecomposer()
        subgoals = decomposer._fallback_to_heuristics("Add feature", Complexity.SIMPLE)

        # Planning step should use architect
        plan_step = next(sg for sg in subgoals if "plan" in sg.title.lower())
        assert plan_step.assigned_agent == "@system-architect"

        # Implementation step should use dev
        impl_step = next(sg for sg in subgoals if "implement" in sg.title.lower())
        assert impl_step.assigned_agent == "@code-developer"

        # Testing step should use QA
        test_step = next(sg for sg in subgoals if "test" in sg.title.lower())
        assert test_step.assigned_agent == "@quality-assurance"

    def test_subgoal_ids_follow_format(self):
        """Test that subgoal IDs follow sg-N format."""
        decomposer = PlanDecomposer()
        subgoals = decomposer._fallback_to_heuristics("Add feature", Complexity.COMPLEX)

        for i, sg in enumerate(subgoals, 1):
            assert sg.id == f"sg-{i}", f"Expected sg-{i}, got {sg.id}"

    @patch("aurora_cli.planning.decompose.decompose_query")
    @patch("aurora_cli.planning.decompose.LLMClient")
    @patch("aurora_cli.planning.decompose.SOAR_AVAILABLE", True)
    def test_soar_decomposition_converts_response(self, mock_llm_client, mock_decompose_query):
        """Test SOAR decomposition converts response to Subgoal objects."""
        mock_llm_client.return_value = Mock()

        # Mock SOAR response with new schema
        mock_decomposition = Mock()
        mock_decomposition.subgoals = [
            {
                "id": "sg-1",
                "description": "Analyze authentication requirements",
                "ideal_agent": "security-expert",
                "ideal_agent_desc": "Security specialist",
                "assigned_agent": "code-developer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "id": "sg-2",
                "description": "Implement OAuth2 authentication flow",
                "ideal_agent": "code-developer",
                "ideal_agent_desc": "Development specialist",
                "assigned_agent": "code-developer",
                "is_critical": True,
                "depends_on": [0],
            },
        ]
        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        decomposer = PlanDecomposer(enable_persistent_cache=False)

        with patch.object(decomposer.cache, "get", return_value=None):
            subgoals, source = decomposer.decompose("Implement authentication")

        assert source == "soar"
        assert len(subgoals) == 2

        # Check first subgoal
        assert subgoals[0].id == "sg-1"
        assert subgoals[0].ideal_agent == "@security-expert"
        assert subgoals[0].assigned_agent == "@code-developer"

        # Check second subgoal has dependency
        assert "sg-1" in subgoals[1].dependencies


# =============================================================================
# One-Shot Example Quality Tests
# =============================================================================


class TestOneShotExampleQuality:
    """Test one-shot example quality for few-shot prompting."""

    def test_example_decompositions_have_required_fields(self):
        """Test example decompositions have all required fields."""
        import json
        from pathlib import Path

        examples_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "packages"
            / "reasoning"
            / "examples"
            / "example_decompositions.json"
        )

        if not examples_path.exists():
            pytest.skip("Examples file not found")

        with open(examples_path) as f:
            examples = json.load(f)

        assert len(examples) >= 4, "Should have at least 4 examples for all complexity levels"

        for example in examples:
            # Check required top-level fields
            assert "complexity" in example
            assert "query" in example
            assert "decomposition" in example

            decomp = example["decomposition"]
            assert "goal" in decomp
            assert "subgoals" in decomp
            assert "execution_order" in decomp
            assert "expected_tools" in decomp

            # Check subgoal structure - support both old and new schema
            for subgoal in decomp["subgoals"]:
                assert "description" in subgoal
                # Accept either old schema (suggested_agent) or new schema (ideal_agent + assigned_agent)
                has_old_schema = "suggested_agent" in subgoal
                has_new_schema = "ideal_agent" in subgoal and "assigned_agent" in subgoal
                assert has_old_schema or has_new_schema, (
                    f"Subgoal must have either suggested_agent (old) or "
                    f"ideal_agent+assigned_agent (new): {subgoal}"
                )
                assert "is_critical" in subgoal
                assert "depends_on" in subgoal

    def test_examples_cover_all_complexity_levels(self):
        """Test examples cover SIMPLE, MEDIUM, COMPLEX, CRITICAL."""
        import json
        from pathlib import Path

        examples_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "packages"
            / "reasoning"
            / "examples"
            / "example_decompositions.json"
        )

        if not examples_path.exists():
            pytest.skip("Examples file not found")

        with open(examples_path) as f:
            examples = json.load(f)

        complexities = {ex["complexity"] for ex in examples}

        assert "SIMPLE" in complexities
        assert "MEDIUM" in complexities
        assert "COMPLEX" in complexities
        assert "CRITICAL" in complexities

    def test_example_subgoal_counts_match_complexity(self):
        """Test that subgoal counts correlate with complexity."""
        import json
        from pathlib import Path

        examples_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "packages"
            / "reasoning"
            / "examples"
            / "example_decompositions.json"
        )

        if not examples_path.exists():
            pytest.skip("Examples file not found")

        with open(examples_path) as f:
            examples = json.load(f)

        for example in examples:
            complexity = example["complexity"]
            subgoal_count = len(example["decomposition"]["subgoals"])

            if complexity == "SIMPLE":
                assert subgoal_count <= 2, "SIMPLE should have <= 2 subgoals"
            elif complexity == "MEDIUM":
                assert 2 <= subgoal_count <= 5, "MEDIUM should have 2-5 subgoals"
            elif complexity == "COMPLEX":
                assert 5 <= subgoal_count <= 10, "COMPLEX should have 5-10 subgoals"
            elif complexity == "CRITICAL":
                assert subgoal_count >= 8, "CRITICAL should have >= 8 subgoals"


# =============================================================================
# Score Agent Tests (Direct Scoring)
# =============================================================================


class TestScoreAgentForSubgoal:
    """Test scoring a specific agent against a subgoal."""

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_score_agent_high_match(self, mock_manager_class):
        """Test high score when agent matches task well."""
        mock_manifest = Mock()
        mock_agent = Mock()
        mock_agent.id = "quality-assurance"
        mock_agent.goal = "Quality assurance and testing"
        mock_agent.when_to_use = "testing, quality, unit tests, integration tests"
        mock_agent.capabilities = ["testing", "pytest", "quality"]
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = Mock(return_value=mock_agent)

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Write unit tests",
            description="Create comprehensive unit tests for authentication",
            assigned_agent="@quality-assurance",
        )

        score = recommender.score_agent_for_subgoal("@quality-assurance", subgoal)

        # Should have good score with boost for semantic understanding
        assert score >= 0.5, f"Expected score >= 0.5, got {score}"

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_score_agent_low_match(self, mock_manager_class):
        """Test low score when agent doesn't match task."""
        mock_manifest = Mock()
        mock_agent = Mock()
        mock_agent.id = "code-developer"
        mock_agent.goal = "Development"
        mock_agent.when_to_use = "coding, backend, frontend"
        mock_agent.capabilities = ["python", "javascript"]
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = Mock(return_value=mock_agent)

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Design database schema",
            description="Create normalized database schema for users and orders",
            assigned_agent="@code-developer",
        )

        score = recommender.score_agent_for_subgoal("@code-developer", subgoal)

        # Score should be moderate (some overlap but not specialized)
        assert 0.2 <= score <= 0.7, f"Expected moderate score, got {score}"

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_score_unknown_agent(self, mock_manager_class):
        """Test low score for unknown agent."""
        mock_manifest = Mock()
        mock_manifest.agents = []
        mock_manifest.get_agent = Mock(return_value=None)

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Write tests",
            description="Create tests",
            assigned_agent="@unknown-agent",
        )

        score = recommender.score_agent_for_subgoal("@unknown-agent", subgoal)

        # Unknown agent should get low score
        assert score <= 0.4, f"Expected score <= 0.4 for unknown agent, got {score}"


# =============================================================================
# Context Summary Building Tests
# =============================================================================


class TestContextSummaryBuilding:
    """Test context summary building for decomposition."""

    def test_empty_context_returns_default_message(self):
        """Test empty context returns appropriate message."""
        decomposer = PlanDecomposer()
        summary = decomposer._build_context_summary({})

        assert "No indexed context available" in summary

    def test_code_chunks_included_in_summary(self):
        """Test code chunks are included in summary."""
        decomposer = PlanDecomposer()
        context = {
            "code_chunks": [
                {"file_path": "src/auth.py", "name": "authenticate", "element_type": "function"},
                {"file_path": "src/users.py", "name": "User", "element_type": "class"},
            ],
            "reasoning_chunks": [],
        }

        summary = decomposer._build_context_summary(context)

        assert "Relevant Code" in summary
        assert "2 elements" in summary

    def test_reasoning_chunks_included_in_summary(self):
        """Test reasoning chunks are included in summary."""
        decomposer = PlanDecomposer()
        context = {
            "code_chunks": [],
            "reasoning_chunks": [
                {"pattern": "auth-pattern-1"},
                {"pattern": "auth-pattern-2"},
            ],
        }

        summary = decomposer._build_context_summary(context)

        assert "Previous Solutions" in summary
        assert "2 relevant patterns" in summary


# =============================================================================
# Match Quality Tests (3-tier system)
# =============================================================================


class TestMatchQualityTiers:
    """Test the 3-tier match quality system (excellent/acceptable/insufficient)."""

    def test_match_quality_in_prompt_template(self):
        """Test that match_quality is mentioned in decomposition prompt."""
        from aurora_reasoning.prompts.decompose import DecomposePromptTemplate

        template = DecomposePromptTemplate()
        system_prompt = template.build_system_prompt(available_agents=["@code-developer"])

        # Should mention match_quality in schema
        assert "match_quality" in system_prompt
        assert "excellent" in system_prompt
        assert "acceptable" in system_prompt
        assert "insufficient" in system_prompt

    def test_excellent_match_quality_criteria(self):
        """Test criteria for excellent match quality."""
        # Excellent: Agent's core specialty matches task exactly
        # e.g., @quality-assurance for "Write unit tests"

        from aurora_reasoning.prompts.decompose import DecomposePromptTemplate

        template = DecomposePromptTemplate()
        system_prompt = template.build_system_prompt(available_agents=["@quality-assurance"])

        # Excellent criteria should be documented
        assert "excellent" in system_prompt.lower()
        # Check for "specialt" prefix to match both "specialty" and "specialties"
        assert "specialt" in system_prompt.lower() or "core" in system_prompt.lower()

    def test_insufficient_match_quality_criteria(self):
        """Test criteria for insufficient match quality."""
        # Insufficient: No capable agent available
        # e.g., @master for "Write creative marketing copy"

        from aurora_reasoning.prompts.decompose import DecomposePromptTemplate

        template = DecomposePromptTemplate()
        system_prompt = template.build_system_prompt(available_agents=["@master"])

        # Insufficient criteria should be documented
        assert "insufficient" in system_prompt.lower()


# =============================================================================
# Agent ID Normalization Tests
# =============================================================================


class TestAgentIdNormalization:
    """Test agent ID normalization (@prefix handling)."""

    def test_normalize_adds_prefix(self):
        """Test that @ prefix is added when missing."""
        matcher = AgentMatcher()

        assert matcher._normalize_agent_id("code-developer") == "@code-developer"
        assert matcher._normalize_agent_id("quality-assurance") == "@quality-assurance"

    def test_normalize_preserves_prefix(self):
        """Test that existing @ prefix is preserved."""
        matcher = AgentMatcher()

        assert matcher._normalize_agent_id("@code-developer") == "@code-developer"
        assert matcher._normalize_agent_id("@master") == "@master"

    def test_normalize_empty_returns_unknown(self):
        """Test that empty string returns @unknown."""
        matcher = AgentMatcher()

        assert matcher._normalize_agent_id("") == "@unknown"
        assert matcher._normalize_agent_id(None) == "@unknown"
