"""
Unit tests for GitEnforcer.

Tests git branch validation and safety checks including:
- Current branch detection
- Blocked branch enforcement (main/master)
- Required branch validation
- Detached HEAD detection
- Git repository validation
- Error handling and messaging
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora.soar.headless.git_enforcer import (
    GitBranchError,
    GitEnforcer,
    GitEnforcerConfig,
)


class TestGitEnforcerConfig:
    """Test GitEnforcerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GitEnforcerConfig()
        assert config.required_branch == "headless"
        assert config.blocked_branches == ["main", "master"]
        assert config.allow_detached_head is False
        assert config.repo_path is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = GitEnforcerConfig(
            required_branch="experiment-123",
            blocked_branches=["main", "master", "develop"],
            allow_detached_head=True,
            repo_path=Path("/tmp/repo"),
        )
        assert config.required_branch == "experiment-123"
        assert len(config.blocked_branches) == 3
        assert config.allow_detached_head is True
        assert config.repo_path == Path("/tmp/repo")

    def test_no_required_branch(self):
        """Test config with no required branch."""
        config = GitEnforcerConfig(required_branch=None)
        assert config.required_branch is None


class TestGitEnforcerInit:
    """Test GitEnforcer initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        enforcer = GitEnforcer()
        assert enforcer.config.required_branch == "headless"
        assert enforcer.config.blocked_branches == ["main", "master"]

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = GitEnforcerConfig(required_branch="test")
        enforcer = GitEnforcer(config)
        assert enforcer.config.required_branch == "test"


class TestIsGitRepository:
    """Test is_git_repository method."""

    @patch("subprocess.run")
    def test_is_git_repo_true(self, mock_run):
        """Test detecting valid git repository."""
        mock_run.return_value = Mock(returncode=0)
        enforcer = GitEnforcer()
        assert enforcer.is_git_repository() is True

    @patch("subprocess.run")
    def test_is_git_repo_false_not_a_repo(self, mock_run):
        """Test detecting non-git directory."""
        mock_run.side_effect = subprocess.CalledProcessError(128, "git")
        enforcer = GitEnforcer()
        assert enforcer.is_git_repository() is False

    @patch("subprocess.run")
    def test_is_git_repo_false_timeout(self, mock_run):
        """Test handling timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        enforcer = GitEnforcer()
        assert enforcer.is_git_repository() is False

    @patch("subprocess.run")
    def test_is_git_repo_false_git_not_found(self, mock_run):
        """Test handling missing git command."""
        mock_run.side_effect = FileNotFoundError()
        enforcer = GitEnforcer()
        assert enforcer.is_git_repository() is False


class TestGetCurrentBranch:
    """Test get_current_branch method."""

    @patch("subprocess.run")
    def test_get_branch_success(self, mock_run):
        """Test successfully getting current branch."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="feature-branch\n",
            stderr="",
        )
        enforcer = GitEnforcer()
        branch = enforcer.get_current_branch()
        assert branch == "feature-branch"

    @patch("subprocess.run")
    def test_get_branch_strips_whitespace(self, mock_run):
        """Test that branch name is stripped."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="  main  \n",
            stderr="",
        )
        enforcer = GitEnforcer()
        branch = enforcer.get_current_branch()
        assert branch == "main"

    @patch("subprocess.run")
    def test_get_branch_detached_head(self, mock_run):
        """Test detecting detached HEAD state."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="HEAD\n",
            stderr="",
        )
        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.get_current_branch()
        assert "detached head" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_branch_not_a_repo(self, mock_run):
        """Test error when not in git repo."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="not a git repository"
        )
        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.get_current_branch()
        assert "not a git repository" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_branch_timeout(self, mock_run):
        """Test handling git command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.get_current_branch()
        assert "timed out" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_branch_git_not_found(self, mock_run):
        """Test handling missing git command."""
        mock_run.side_effect = FileNotFoundError()
        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.get_current_branch()
        assert "git command not found" in str(exc_info.value).lower()


class TestValidate:
    """Test validate method."""

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_success_on_headless_branch(self, mock_is_repo, mock_get_branch):
        """Test successful validation on headless branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "headless"

        enforcer = GitEnforcer()
        # Should not raise
        enforcer.validate()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_fails_on_main_branch(self, mock_is_repo, mock_get_branch):
        """Test validation fails on main branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "main"

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()
        assert "blocked branch 'main'" in str(exc_info.value).lower()
        assert "git checkout" in str(exc_info.value)

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_fails_on_master_branch(self, mock_is_repo, mock_get_branch):
        """Test validation fails on master branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "master"

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()
        assert "blocked branch 'master'" in str(exc_info.value).lower()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_fails_not_a_repo(self, mock_is_repo):
        """Test validation fails when not in git repo."""
        mock_is_repo.return_value = False

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()
        assert "not in a git repository" in str(exc_info.value).lower()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_fails_wrong_required_branch(self, mock_is_repo, mock_get_branch):
        """Test validation fails when on wrong branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "feature-123"

        config = GitEnforcerConfig(required_branch="headless")
        enforcer = GitEnforcer(config)

        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()
        assert "requires branch 'headless'" in str(exc_info.value).lower()
        assert "currently on 'feature-123'" in str(exc_info.value).lower()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_success_no_required_branch(self, mock_is_repo, mock_get_branch):
        """Test validation succeeds when no required branch set."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "feature-123"

        config = GitEnforcerConfig(
            required_branch=None,
            blocked_branches=["main", "master"],
        )
        enforcer = GitEnforcer(config)

        # Should not raise
        enforcer.validate()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_custom_blocked_branches(self, mock_is_repo, mock_get_branch):
        """Test validation with custom blocked branches."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "develop"

        config = GitEnforcerConfig(
            required_branch=None,
            blocked_branches=["main", "master", "develop", "production"],
        )
        enforcer = GitEnforcer(config)

        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()
        assert "develop" in str(exc_info.value)

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_validate_custom_required_branch(self, mock_is_repo, mock_get_branch):
        """Test validation with custom required branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "experiment-42"

        config = GitEnforcerConfig(required_branch="experiment-42")
        enforcer = GitEnforcer(config)

        # Should not raise
        enforcer.validate()


class TestGetValidationStatus:
    """Test get_validation_status method."""

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_status_valid(self, mock_is_repo, mock_get_branch):
        """Test validation status when valid."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "headless"

        enforcer = GitEnforcer()
        status = enforcer.get_validation_status()

        assert status["is_git_repo"] is True
        assert status["current_branch"] == "headless"
        assert status["is_valid"] is True
        assert status["error_message"] is None

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_status_invalid_blocked_branch(self, mock_is_repo, mock_get_branch):
        """Test validation status on blocked branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "main"

        enforcer = GitEnforcer()
        status = enforcer.get_validation_status()

        assert status["is_git_repo"] is True
        assert status["current_branch"] == "main"
        assert status["is_valid"] is False
        assert status["error_message"] is not None
        assert "blocked branch" in status["error_message"].lower()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_status_not_a_repo(self, mock_is_repo):
        """Test validation status when not in git repo."""
        mock_is_repo.return_value = False

        enforcer = GitEnforcer()
        status = enforcer.get_validation_status()

        assert status["is_git_repo"] is False
        assert status["current_branch"] is None
        assert status["is_valid"] is False
        assert status["error_message"] == "Not in a git repository"

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_status_detached_head(self, mock_is_repo, mock_get_branch):
        """Test validation status in detached HEAD."""
        mock_is_repo.return_value = True
        mock_get_branch.side_effect = GitBranchError("Detached HEAD")

        enforcer = GitEnforcer()
        status = enforcer.get_validation_status()

        assert status["is_git_repo"] is True
        assert status["current_branch"] is None
        assert status["is_valid"] is False
        assert "detached head" in status["error_message"].lower()


class TestErrorMessages:
    """Test error message quality and helpfulness."""

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_error_includes_git_command(self, mock_is_repo, mock_get_branch):
        """Test error message includes helpful git command."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "main"

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()

        error_msg = str(exc_info.value)
        assert "git checkout headless" in error_msg

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_error_lists_blocked_branches(self, mock_is_repo, mock_get_branch):
        """Test error message lists blocked branches."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "master"

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()

        error_msg = str(exc_info.value)
        assert "main" in error_msg
        assert "master" in error_msg

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_error_includes_create_branch_hint(self, mock_is_repo, mock_get_branch):
        """Test error message includes hint to create branch."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "feature"

        enforcer = GitEnforcer()
        with pytest.raises(GitBranchError) as exc_info:
            enforcer.validate()

        error_msg = str(exc_info.value)
        assert "git checkout -b headless" in error_msg.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_blocked_branches_list(self):
        """Test with empty blocked branches list."""
        config = GitEnforcerConfig(
            required_branch="headless",
            blocked_branches=[],
        )
        enforcer = GitEnforcer(config)
        assert enforcer.config.blocked_branches == []

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_branch_name_with_special_characters(self, mock_is_repo, mock_get_branch):
        """Test branch name with special characters."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "feature/PROJ-123_add-headless"

        config = GitEnforcerConfig(required_branch="feature/PROJ-123_add-headless")
        enforcer = GitEnforcer(config)

        # Should not raise
        enforcer.validate()

    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.get_current_branch")
    @patch("aurora_soar.headless.git_enforcer.GitEnforcer.is_git_repository")
    def test_case_sensitive_branch_matching(self, mock_is_repo, mock_get_branch):
        """Test that branch matching is case-sensitive."""
        mock_is_repo.return_value = True
        mock_get_branch.return_value = "Main"  # Capital M

        config = GitEnforcerConfig(
            required_branch=None,  # No required branch
            blocked_branches=["main"],  # lowercase - shouldn't block "Main"
        )
        enforcer = GitEnforcer(config)

        # Should not raise (case-sensitive, Main != main)
        enforcer.validate()
