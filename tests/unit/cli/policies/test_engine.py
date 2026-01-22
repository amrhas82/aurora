"""Unit tests for PoliciesEngine."""

import tempfile
from pathlib import Path

import pytest

from aurora_cli.policies import Operation, OperationType, PoliciesEngine, PolicyAction


@pytest.fixture
def temp_policies_file():
    """Create a temporary policies file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
budget:
  monthly_limit_usd: 50.0
  warn_at_percent: 70
  hard_limit_action: reject

agent_recovery:
  timeout_seconds: 60
  max_retries: 1
  fallback_to_llm: false

destructive:
  file_delete:
    action: prompt
    max_files: 3
  git_force_push:
    action: deny
  git_push_main:
    action: prompt
  drop_table:
    action: deny
  truncate:
    action: prompt

safety:
  auto_branch: true
  branch_prefix: "test/"
  max_files_modified: 10
  max_lines_changed: 500
  protected_paths:
    - ".git/"
    - "*.key"

anomalies:
  scope_multiplier: 2
  unexpected_file_types:
    - "*.sql"
""",
        )
        path = Path(f.name)
    yield path
    path.unlink()


class TestPoliciesEngine:
    """Test PoliciesEngine functionality."""

    def test_load_default_policies(self):
        """Test loading default policies when no file exists."""
        # Use non-existent path
        engine = PoliciesEngine(Path("/tmp/nonexistent-policies.yaml"))

        # Should load defaults
        assert engine.config is not None
        assert engine.config.budget.monthly_limit_usd == 100.0
        assert engine.config.agent_recovery.timeout_seconds == 120
        assert engine.config.agent_recovery.max_retries == 2

    def test_load_custom_policies(self, temp_policies_file):
        """Test loading custom policies from file."""
        engine = PoliciesEngine(temp_policies_file)

        # Should load custom values
        assert engine.config.budget.monthly_limit_usd == 50.0
        assert engine.config.agent_recovery.timeout_seconds == 60
        assert engine.config.agent_recovery.max_retries == 1
        assert engine.config.agent_recovery.fallback_to_llm is False

    def test_check_file_delete_below_limit(self):
        """Test file delete operation below limit."""
        engine = PoliciesEngine()
        op = Operation(type=OperationType.FILE_DELETE, target="test.txt", count=3)

        result = engine.check_operation(op)

        # Should allow or prompt (default is prompt with max 5)
        assert result.action in (PolicyAction.ALLOW, PolicyAction.PROMPT)

    def test_check_file_delete_above_limit(self):
        """Test file delete operation above limit."""
        engine = PoliciesEngine()
        op = Operation(type=OperationType.FILE_DELETE, target="*.txt", count=10)

        result = engine.check_operation(op)

        # Should prompt (exceeds default limit of 5)
        assert result.action == PolicyAction.PROMPT
        assert "10 files" in result.reason

    def test_check_git_force_push_denied(self):
        """Test git force push is denied."""
        engine = PoliciesEngine()
        op = Operation(type=OperationType.GIT_FORCE_PUSH, target="origin/main")

        result = engine.check_operation(op)

        assert result.action == PolicyAction.DENY
        assert "Force push" in result.reason

    def test_check_git_push_main_prompt(self):
        """Test git push to main prompts."""
        engine = PoliciesEngine()
        op = Operation(type=OperationType.GIT_PUSH_MAIN, target="main")

        result = engine.check_operation(op)

        assert result.action == PolicyAction.PROMPT
        assert "main" in result.reason

    def test_check_sql_drop_denied(self):
        """Test SQL DROP TABLE is denied."""
        engine = PoliciesEngine()
        op = Operation(type=OperationType.SQL_DROP, target="users")

        result = engine.check_operation(op)

        assert result.action == PolicyAction.DENY
        assert "DROP TABLE" in result.reason

    def test_check_scope_within_limits(self):
        """Test scope check within limits."""
        engine = PoliciesEngine()

        result = engine.check_scope(files_modified=10, lines_changed=500)

        assert result.action == PolicyAction.ALLOW

    def test_check_scope_exceeds_files(self):
        """Test scope check exceeds file limit."""
        engine = PoliciesEngine()

        result = engine.check_scope(files_modified=25, lines_changed=100)

        assert result.action == PolicyAction.PROMPT
        assert "25 files" in result.reason

    def test_check_scope_exceeds_lines(self):
        """Test scope check exceeds line limit."""
        engine = PoliciesEngine()

        result = engine.check_scope(files_modified=5, lines_changed=2000)

        assert result.action == PolicyAction.PROMPT
        assert "2000 lines" in result.reason

    def test_get_protected_paths(self):
        """Test retrieving protected paths."""
        engine = PoliciesEngine()

        paths = engine.get_protected_paths()

        assert ".git/" in paths
        assert ".env" in paths
        assert "*.pem" in paths

    def test_get_recovery_config(self):
        """Test retrieving recovery config."""
        engine = PoliciesEngine()

        config = engine.get_recovery_config()

        assert config.timeout_seconds == 120
        assert config.max_retries == 2
        assert config.fallback_to_llm is True

    def test_create_default_policies_file(self, tmp_path):
        """Test creating default policies file."""
        policies_path = tmp_path / "test_policies.yaml"
        engine = PoliciesEngine(policies_path)

        created_path = engine.create_default_policies_file()

        assert created_path.exists()
        # Should be able to load it
        engine2 = PoliciesEngine(created_path)
        assert engine2.config is not None
