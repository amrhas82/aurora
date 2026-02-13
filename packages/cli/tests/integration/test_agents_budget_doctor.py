"""Integration tests for CLI agent search/similarity, doctor helpers.

Tests pure logic — no Click runner, no LLM calls.
"""

from unittest.mock import MagicMock

import pytest

from aurora_cli.agent_discovery.models import AgentInfo, AgentManifest
from aurora_cli.commands.agents import _find_similar_agents, _search_agents, _truncate
from aurora_cli.commands.doctor import (
    _apply_fixes,
    _collect_issues,
    _format_check,
    _is_project_initialized,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_agent(**overrides) -> AgentInfo:
    """Create an AgentInfo with sensible defaults."""
    defaults = {
        "id": "test-agent",
        "role": "Test Role",
        "goal": "Test goal description",
        "category": "general",
        "skills": [],
        "examples": [],
        "when_to_use": "",
    }
    defaults.update(overrides)
    return AgentInfo(**defaults)


def _make_manifest(agents: list[AgentInfo]) -> AgentManifest:
    """Create a minimal AgentManifest."""
    return AgentManifest(agents=agents, version="1.0.0")


@pytest.fixture
def sample_manifest():
    """Manifest with several agents for search testing."""
    return _make_manifest(
        [
            _make_agent(
                id="quality-assurance",
                role="Test Architect",
                goal="Ensure quality",
                skills=["test strategy", "coverage analysis"],
                when_to_use="Use for testing",
            ),
            _make_agent(
                id="code-reviewer",
                role="Code Review Specialist",
                goal="Review code changes",
                skills=["code review", "best practices"],
                examples=["Review this PR"],
            ),
            _make_agent(
                id="planner",
                role="Project Planner",
                goal="Plan and organize work",
                skills=["planning", "estimation"],
            ),
            _make_agent(
                id="qa-automation",
                role="Automation Engineer",
                goal="Automate test execution",
                skills=["selenium", "pytest"],
            ),
        ]
    )


# ---------------------------------------------------------------------------
# _search_agents
# ---------------------------------------------------------------------------


class TestSearchAgents:
    """Tests for keyword-based agent search scoring."""

    def test_search_exact_id_match(self, sample_manifest):
        """Exact ID → score 100, match_info 'exact id match'."""
        results = _search_agents(sample_manifest, "quality-assurance", limit=10)
        assert len(results) >= 1
        agent, match_info = results[0]
        assert agent.id == "quality-assurance"
        assert match_info == "exact id match"

    def test_search_partial_id_match(self, sample_manifest):
        """Partial ID → score 80."""
        results = _search_agents(sample_manifest, "quality", limit=10)
        assert len(results) >= 1
        agent, match_info = results[0]
        assert agent.id == "quality-assurance"
        assert match_info == "partial id match"

    def test_search_role_match(self, sample_manifest):
        """Role keyword → score 70."""
        results = _search_agents(sample_manifest, "architect", limit=10)
        assert len(results) >= 1
        agent, match_info = results[0]
        assert agent.id == "quality-assurance"
        assert match_info == "in role"

    def test_search_skill_match(self, sample_manifest):
        """Skill keyword → score 50."""
        results = _search_agents(sample_manifest, "selenium", limit=10)
        assert len(results) >= 1
        agent, match_info = results[0]
        assert agent.id == "qa-automation"
        assert "skill" in match_info

    def test_search_ranking_order(self, sample_manifest):
        """Higher scores appear first; ties sorted by ID."""
        # "code" matches code-reviewer (partial id, 80) and others at lower scores
        results = _search_agents(sample_manifest, "code", limit=10)
        assert len(results) >= 1
        # Highest-scoring match should come first
        assert results[0][0].id == "code-reviewer"
        assert results[0][1] == "partial id match"

    def test_search_limit(self, sample_manifest):
        """limit caps results."""
        results = _search_agents(sample_manifest, "a", limit=2)
        assert len(results) <= 2

    def test_search_no_match(self, sample_manifest):
        """No match → empty list."""
        results = _search_agents(sample_manifest, "zzzznonexistent", limit=10)
        assert results == []

    def test_search_when_to_use_match(self, sample_manifest):
        """when_to_use keyword → score 40."""
        results = _search_agents(sample_manifest, "testing", limit=10)
        assert any(a.id == "quality-assurance" for a, _ in results)

    def test_search_examples_match(self, sample_manifest):
        """Examples keyword → score 30."""
        results = _search_agents(sample_manifest, "PR", limit=10)
        assert any(a.id == "code-reviewer" for a, _ in results)


# ---------------------------------------------------------------------------
# _find_similar_agents
# ---------------------------------------------------------------------------


class TestFindSimilarAgents:
    """Tests for fuzzy agent ID matching (SequenceMatcher)."""

    def test_find_similar_above_threshold(self, sample_manifest):
        """Similar IDs (ratio > 0.4) included."""
        results = _find_similar_agents(sample_manifest, "quality-assuranc")
        ids = [a.id for a in results]
        assert "quality-assurance" in ids

    def test_find_similar_below_threshold(self, sample_manifest):
        """Completely different IDs excluded."""
        results = _find_similar_agents(sample_manifest, "xyzxyzxyzxyzxyz")
        assert len(results) == 0

    def test_find_similar_limit_5(self):
        """Max 5 returned even with many similar agents."""
        agents = [_make_agent(id=f"agent-{i}") for i in range(20)]
        manifest = _make_manifest(agents)
        results = _find_similar_agents(manifest, "agent-0")
        assert len(results) <= 5


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    """Tests for text truncation utility."""

    def test_truncate_short(self):
        """Short text unchanged."""
        assert _truncate("hello", 10) == "hello"

    def test_truncate_exact(self):
        """Exact length unchanged."""
        assert _truncate("hello", 5) == "hello"

    def test_truncate_long(self):
        """Long text gets '...' suffix."""
        result = _truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8


# ---------------------------------------------------------------------------
# Doctor helpers
# ---------------------------------------------------------------------------


class TestDoctorHelpers:
    """Tests for doctor.py helper functions."""

    def test_doctor_is_initialized(self, tmp_path, monkeypatch):
        """.aurora + memory.db → True."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "memory.db").write_text("")
        monkeypatch.chdir(tmp_path)
        assert _is_project_initialized()

    def test_doctor_not_initialized(self, tmp_path, monkeypatch):
        """Missing .aurora → False."""
        monkeypatch.chdir(tmp_path)
        assert not _is_project_initialized()

    def test_doctor_not_initialized_no_db(self, tmp_path, monkeypatch):
        """.aurora exists but no memory.db → False."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        assert not _is_project_initialized()

    def test_doctor_format_check_pass(self):
        """Pass status → green checkmark."""
        result = _format_check("pass", "Python OK")
        assert "✓" in result
        assert "green" in result
        assert "Python OK" in result

    def test_doctor_format_check_warning(self):
        """Warning status → yellow warning icon."""
        result = _format_check("warning", "Outdated")
        assert "⚠" in result
        assert "yellow" in result

    def test_doctor_format_check_fail(self):
        """Fail status → red cross."""
        result = _format_check("fail", "Missing")
        assert "✗" in result
        assert "red" in result

    def test_doctor_format_check_skip(self):
        """Skip status → dim style."""
        result = _format_check("skip", "Skipped")
        assert "⊘" in result
        assert "dim" in result

    def test_doctor_collect_issues(self):
        """Aggregates fixable + manual from check instances."""
        check1 = MagicMock()
        check1.get_fixable_issues.return_value = [{"name": "fix1"}]
        check1.get_manual_issues.return_value = [{"name": "manual1", "solution": "do X"}]

        check2 = MagicMock()
        check2.get_fixable_issues.return_value = [{"name": "fix2"}]
        check2.get_manual_issues.return_value = []

        fixable, manual = _collect_issues([check1, check2])
        assert len(fixable) == 2
        assert len(manual) == 1
        assert fixable[0]["name"] == "fix1"
        assert fixable[1]["name"] == "fix2"

    def test_doctor_collect_issues_no_methods(self):
        """Objects without get_fixable_issues/get_manual_issues handled gracefully."""
        obj = object()  # no hasattr match
        fixable, manual = _collect_issues([obj])
        assert fixable == []
        assert manual == []

    def test_doctor_apply_fixes_success(self, capsys):
        """Fixes run, count returned."""
        issues = [
            {"name": "fix1", "fix_func": lambda: None},
            {"name": "fix2", "fix_func": lambda: None},
        ]
        count = _apply_fixes(issues)
        assert count == 2

    def test_doctor_apply_fixes_error(self, capsys):
        """Exception caught, continues to next fix."""

        def failing_fix():
            raise RuntimeError("boom")

        issues = [
            {"name": "fix1", "fix_func": failing_fix},
            {"name": "fix2", "fix_func": lambda: None},
        ]
        count = _apply_fixes(issues)
        assert count == 1  # fix2 succeeded
