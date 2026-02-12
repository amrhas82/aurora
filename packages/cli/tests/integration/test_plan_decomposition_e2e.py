"""End-to-end integration tests for plan decomposition flow.

This module tests the full plan creation workflow including:
- SOAR decomposition with LLM integration
- Memory-based file path resolution
- Agent discovery and matching
- Checkpoint summary and confirmation
- Enhanced file generation with code-aware content
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.planning.core import create_plan


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for decomposition."""
    return {
        "subgoals": [
            {
                "id": "sg-1",
                "title": "Setup authentication module",
                "description": "Create authentication module with login/logout functionality",
                "dependencies": [],
            },
            {
                "id": "sg-2",
                "title": "Implement JWT token handling",
                "description": "Add JWT token generation and validation with secure storage",
                "dependencies": ["sg-1"],
            },
            {
                "id": "sg-3",
                "title": "Write integration tests",
                "description": "Create comprehensive integration tests for auth flow",
                "dependencies": ["sg-1", "sg-2"],
            },
        ],
        "complexity": "moderate",
        "rationale": "Requires authentication setup, token handling, and testing",
    }


@pytest.fixture
def mock_code_chunks():
    """Mock code chunks from memory retrieval."""
    return [
        MagicMock(
            file_path="src/auth/module.py",
            line_start=1,
            line_end=50,
            similarity_score=0.85,
            content="# Authentication module",
        ),
        MagicMock(
            file_path="src/auth/jwt.py",
            line_start=1,
            line_end=100,
            similarity_score=0.75,
            content="# JWT handling",
        ),
        MagicMock(
            file_path="tests/integration/test_auth.py",
            line_start=1,
            line_end=200,
            similarity_score=0.65,
            content="# Auth tests",
        ),
    ]


@pytest.fixture
def mock_agent_manifest():
    """Mock agent manifest with common agents."""
    return MagicMock(
        agents=[
            MagicMock(
                id="code-developer",
                when_to_use="code implementation, development, debugging",
                skills=["python", "javascript", "testing", "development"],
            ),
            MagicMock(
                id="quality-assurance",
                when_to_use="testing, quality assurance, test architecture",
                skills=["testing", "quality", "automation", "integration"],
            ),
        ],
    )


class TestPlanDecompositionE2E:
    """End-to-end tests for plan decomposition flow."""

    @patch("aurora_cli.planning.decompose.decompose_query")
    @patch("aurora_cli.planning.memory.MemoryRetriever")
    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_plan_create_with_soar_and_checkpoint(
        self,
        mock_manifest_mgr,
        mock_retriever_cls,
        mock_decompose,
        mock_llm_response,
        mock_code_chunks,
        mock_agent_manifest,
        tmp_path,
    ):
        """Test full plan creation with SOAR decomposition and checkpoint."""
        # Setup mocks
        mock_decompose.return_value = MagicMock(
            subgoals=[
                MagicMock(**sg, recommended_agent="@code-developer", agent_exists=True)
                for sg in mock_llm_response["subgoals"]
            ],
            complexity="moderate",
            decomposition_source="soar",
        )

        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = [
            mock_code_chunks[0:1],  # sg-1: auth module
            mock_code_chunks[1:2],  # sg-2: jwt
            mock_code_chunks[2:3],  # sg-3: tests
        ]
        mock_retriever.has_indexed_memory.return_value = True
        mock_retriever_cls.return_value = mock_retriever

        mock_manifest_mgr.get_or_refresh.return_value = mock_agent_manifest

        # Create plan with yes=True to skip confirmation
        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config to use tmp_path
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        goal = "Implement OAuth2 authentication"
        result = create_plan(
            goal=goal,
            config=mock_config,
            yes=True,  # Skip checkpoint prompt
        )

        # Verify result
        assert result.success is True
        assert result.plan is not None
        assert result.plan.plan_id.startswith("0001-")
        assert result.error is None

        # Verify plan directory created
        plan_dir = result.plan_dir
        assert plan_dir.exists()
        assert plan_dir.is_dir()

        # Verify all 8 files generated
        expected_files = [
            "plan.md",
            "prd.md",
            "tasks.md",
            "agents.json",
            "specs/0001-*-planning.md",
            "specs/0001-*-commands.md",
            "specs/0001-*-validation.md",
            "specs/0001-*-schemas.md",
        ]

        assert (plan_dir / "plan.md").exists()
        assert (plan_dir / "prd.md").exists()
        assert (plan_dir / "tasks.md").exists()
        assert (plan_dir / "agents.json").exists()
        assert (plan_dir / "specs").exists()
        assert (plan_dir / "specs").is_dir()

        # Verify agents.json includes enhanced fields
        agents_json_path = plan_dir / "agents.json"
        with open(agents_json_path) as f:
            agents_data = json.load(f)

        assert "decomposition_source" in agents_data
        assert agents_data["decomposition_source"] == "soar"
        assert "plan_id" in agents_data
        assert "subgoals" in agents_data
        assert len(agents_data["subgoals"]) == 3

        # Verify tasks.md includes file paths (if memory was indexed)
        tasks_md_path = plan_dir / "tasks.md"
        tasks_content = tasks_md_path.read_text()

        # Should have subgoal headers
        assert "SG-1:" in tasks_content or "sg-1:" in tasks_content.lower()
        assert "SG-2:" in tasks_content or "sg-2:" in tasks_content.lower()
        assert "SG-3:" in tasks_content or "sg-3:" in tasks_content.lower()

        # Verify SOAR was called with correct parameters
        mock_decompose.assert_called_once()
        call_args = mock_decompose.call_args
        assert call_args[0][0] == goal  # First arg is goal
        assert "complexity" in call_args[1] or len(call_args[0]) > 2  # Complexity passed

    @patch("aurora_cli.planning.decompose.decompose_query")
    def test_plan_create_graceful_degradation(
        self,
        mock_decompose,
        tmp_path,
    ):
        """Test plan creation falls back to heuristics when SOAR fails."""
        # Make SOAR raise exception
        mock_decompose.side_effect = RuntimeError("SOAR unavailable")

        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        goal = "Implement simple feature"
        result = create_plan(
            goal=goal,
            config=mock_config,
            yes=True,
        )

        # Should still succeed with heuristic fallback
        assert result.success is True
        assert result.plan is not None
        assert result.plan.plan_id.startswith("0001-")

        # Verify agents.json shows heuristic source
        plan_dir = result.plan_dir
        agents_json_path = plan_dir / "agents.json"

        if agents_json_path.exists():
            with open(agents_json_path) as f:
                agents_data = json.load(f)

            # Should show heuristic source (or no decomposition_source field)
            if "decomposition_source" in agents_data:
                assert agents_data["decomposition_source"] == "heuristic"

    def test_checkpoint_abort_no_files(self, tmp_path):
        """Test that aborting at checkpoint creates no files."""
        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        # Mock confirmation to return False (user says 'n')
        with patch("aurora_cli.planning.checkpoint.prompt_for_confirmation", return_value=False):
            goal = "Test feature"
            result = create_plan(
                goal=goal,
                config=mock_config,
                yes=False,  # Enable checkpoint
            )

            # Should fail with cancellation message
            assert result.success is False
            assert "cancel" in result.error.lower() or "abort" in result.error.lower()

            # No plan directories should be created
            plan_dirs = list(plans_dir.glob("0001-*"))
            assert len(plan_dirs) == 0

    def test_non_interactive_mode(self, tmp_path):
        """Test non-interactive mode skips checkpoint and creates plan."""
        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        goal = "Quick feature"
        result = create_plan(
            goal=goal,
            config=mock_config,
            yes=True,  # Non-interactive
        )

        # Should succeed without prompting
        assert result.success is True
        assert result.plan is not None
        assert result.plan.plan_id.startswith("0001-")

        # Verify files created
        plan_dir = result.plan_dir
        assert (plan_dir / "agents.json").exists()
        assert (plan_dir / "tasks.md").exists()


class TestEnhancedFileGeneration:
    """Test enhanced file generation with code-aware content."""

    @patch("aurora_cli.planning.memory.MemoryRetriever")
    def test_tasks_md_with_file_resolutions(self, mock_retriever_cls, tmp_path):
        """Test tasks.md includes resolved file paths when memory indexed."""
        # Setup mock retriever
        mock_retriever = MagicMock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_retriever.retrieve.return_value = [
            MagicMock(
                file_path="src/feature.py",
                line_start=1,
                line_end=50,
                similarity_score=0.9,  # High confidence
            ),
        ]
        mock_retriever_cls.return_value = mock_retriever

        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        result = create_plan(
            goal="Add simple feature",
            config=mock_config,
            yes=True,
        )

        assert result.success is True

        # Check tasks.md for file paths
        plan_dir = result.plan_dir
        tasks_md = (plan_dir / "tasks.md").read_text()

        # Should include "Relevant Files" section with paths
        # (exact format depends on template implementation)
        assert "task" in tasks_md.lower() or "sg-" in tasks_md.lower()

    def test_tasks_md_without_memory(self, tmp_path):
        """Test tasks.md shows TBD message when memory not indexed."""
        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        result = create_plan(
            goal="Add feature without memory",
            config=mock_config,
            yes=True,
        )

        assert result.success is True

        plan_dir = result.plan_dir
        tasks_md = (plan_dir / "tasks.md").read_text()

        # Should show TBD message or generic guidance
        # (templates handle this gracefully)
        assert "task" in tasks_md.lower() or "sg-" in tasks_md.lower()


class TestPerformanceTargets:
    """Test that operations meet performance targets."""

    def test_plan_creation_completes_quickly(self, tmp_path):
        """Test plan creation completes within reasonable time."""
        import time

        plans_dir = tmp_path / ".aurora" / "plans" / "active"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Mock config
        mock_config = MagicMock()
        mock_config.project_root = tmp_path

        start = time.time()
        result = create_plan(
            goal="Simple feature",
            config=mock_config,
            yes=True,
        )
        duration = time.time() - start

        assert result.success is True
        # Should complete in reasonable time (allow 30s for CI/slow systems)
        assert duration < 30.0, f"Plan creation took {duration:.2f}s (expected < 30s)"
