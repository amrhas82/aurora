"""TDD Tests for SpawnTask and SpawnResult models."""

from aurora_spawner.models import SpawnResult, SpawnTask


class TestSpawnTask:
    """Tests for SpawnTask dataclass."""

    def test_spawn_task_defaults(self):
        """Test SpawnTask has correct defaults (agent=None, timeout=300)."""
        task = SpawnTask(prompt="test prompt")
        assert task.prompt == "test prompt"
        assert task.agent is None
        assert task.timeout == 300

    def test_spawn_task_custom_values(self):
        """Test SpawnTask accepts custom prompt, agent, timeout."""
        task = SpawnTask(prompt="custom prompt", agent="code-developer", timeout=600)
        assert task.prompt == "custom prompt"
        assert task.agent == "code-developer"
        assert task.timeout == 600

    def test_spawn_task_to_dict(self):
        """Test SpawnTask.to_dict() returns expected structure."""
        task = SpawnTask(prompt="test prompt", agent="test-agent", timeout=450)
        result = task.to_dict()
        assert isinstance(result, dict)
        assert result["prompt"] == "test prompt"
        assert result["agent"] == "test-agent"
        assert result["timeout"] == 450


class TestSpawnResult:
    """Tests for SpawnResult dataclass."""

    def test_spawn_result_success(self):
        """Test SpawnResult with success=True, output, no error."""
        result = SpawnResult(
            success=True, output="task completed successfully", error=None, exit_code=0
        )
        assert result.success is True
        assert result.output == "task completed successfully"
        assert result.error is None
        assert result.exit_code == 0

    def test_spawn_result_failure(self):
        """Test SpawnResult with success=False, error message, exit_code."""
        result = SpawnResult(
            success=False, output="", error="Command failed with error", exit_code=1
        )
        assert result.success is False
        assert result.output == ""
        assert result.error == "Command failed with error"
        assert result.exit_code == 1

    def test_spawn_result_to_dict(self):
        """Test SpawnResult.to_dict() returns expected structure."""
        result = SpawnResult(success=True, output="test output", error=None, exit_code=0)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["output"] == "test output"
        assert result_dict["error"] is None
        assert result_dict["exit_code"] == 0

    def test_spawn_result_with_fallback_metadata(self):
        """Test SpawnResult with fallback tracking fields."""
        result = SpawnResult(
            success=True,
            output="fallback output",
            error=None,
            exit_code=0,
            fallback=True,
            original_agent="failing-agent",
            retry_count=2,
        )
        assert result.fallback is True
        assert result.original_agent == "failing-agent"
        assert result.retry_count == 2

    def test_spawn_result_fallback_metadata_in_to_dict(self):
        """Test SpawnResult.to_dict() includes fallback metadata fields."""
        result = SpawnResult(
            success=True,
            output="output",
            error=None,
            exit_code=0,
            fallback=True,
            original_agent="test-agent",
            retry_count=2,
        )
        result_dict = result.to_dict()
        assert result_dict["fallback"] is True
        assert result_dict["original_agent"] == "test-agent"
        assert result_dict["retry_count"] == 2

    def test_spawn_result_defaults_no_fallback(self):
        """Test SpawnResult defaults: fallback=False, original_agent=None, retry_count=0."""
        result = SpawnResult(success=True, output="output", error=None, exit_code=0)
        assert result.fallback is False
        assert result.original_agent is None
        assert result.retry_count == 0
