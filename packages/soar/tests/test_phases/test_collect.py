"""Tests for SOAR collect phase (topological sort)."""

from aurora_soar.phases.collect import topological_sort


# ============================================================================
# Helpers
# ============================================================================


def _subgoal(index: int, prompt: str, depends_on: list[int] | None = None) -> dict:
    return {
        "subgoal_index": index,
        "description": prompt,
        "prompt": prompt,
        "depends_on": depends_on or [],
    }


# ============================================================================
# Topological Sort
# ============================================================================


class TestTopologicalSort:
    def test_no_deps_single_wave(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B"),
            _subgoal(3, "C"),
        ])
        assert len(waves) == 1
        assert {sg["subgoal_index"] for sg in waves[0]} == {1, 2, 3}

    def test_linear_deps_three_waves(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C", depends_on=[2]),
        ])
        assert len(waves) == 3
        assert waves[0][0]["subgoal_index"] == 1
        assert waves[1][0]["subgoal_index"] == 2
        assert waves[2][0]["subgoal_index"] == 3

    def test_diamond_deps(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C", depends_on=[1]),
            _subgoal(4, "D", depends_on=[2, 3]),
        ])
        assert len(waves) == 3
        assert waves[0][0]["subgoal_index"] == 1
        assert {sg["subgoal_index"] for sg in waves[1]} == {2, 3}
        assert waves[2][0]["subgoal_index"] == 4

    def test_parallel_chains(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C"),
            _subgoal(4, "D", depends_on=[3]),
        ])
        assert len(waves) == 2
        assert {sg["subgoal_index"] for sg in waves[0]} == {1, 3}
        assert {sg["subgoal_index"] for sg in waves[1]} == {2, 4}
