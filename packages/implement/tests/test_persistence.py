"""Tests for SpawnRunStore persistence."""

import json

from implement.persistence import SpawnRunStore


def test_create_run(tmp_path):
    """create_run() creates run directory with tasks.md and meta.json."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    content = "- [ ] 1. Test task"

    run_dir = store.create_run(content)

    assert run_dir.exists()
    assert (run_dir / "tasks.md").read_text() == content
    assert (run_dir / "results").is_dir()

    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "running"
    assert "tasks_hash" in meta


def test_save_task_result(tmp_path):
    """save_task_result() persists per-task JSON."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    run_dir = store.create_run("- [ ] 1. Test")

    store.save_task_result(run_dir, "1.0", success=True, output="Done!")

    result_file = run_dir / "results" / "task-1.0.json"
    assert result_file.exists()
    data = json.loads(result_file.read_text())
    assert data["task_id"] == "1.0"
    assert data["success"] is True
    assert data["output"] == "Done!"


def test_save_task_result_failure(tmp_path):
    """save_task_result() persists failure info."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    run_dir = store.create_run("- [ ] 1. Test")

    store.save_task_result(run_dir, "1.0", success=False, error="Timed out")

    data = json.loads((run_dir / "results" / "task-1.0.json").read_text())
    assert data["success"] is False
    assert data["error"] == "Timed out"


def test_finalize_run(tmp_path):
    """finalize_run() writes summary.json and updates meta status."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    run_dir = store.create_run("- [ ] 1. Test")

    store.finalize_run(run_dir, total=3, completed=2, failed=1)

    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["total"] == 3
    assert summary["completed"] == 2
    assert summary["failed"] == 1
    assert summary["status"] == "completed"

    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed"


def test_load_previous_results_matching(tmp_path):
    """load_previous_results() finds matching run and returns outputs."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    content = "- [ ] 1.0 Task A\n- [ ] 2.0 Task B"

    run_dir = store.create_run(content)
    store.save_task_result(run_dir, "1.0", success=True, output="Output A")
    store.save_task_result(run_dir, "2.0", success=True, output="Output B")
    store.finalize_run(run_dir, total=2, completed=2, failed=0)

    results = store.load_previous_results(content)

    assert results is not None
    assert results["1.0"] == "Output A"
    assert results["2.0"] == "Output B"


def test_load_previous_results_no_match(tmp_path):
    """load_previous_results() returns None when no matching run."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    store.create_run("- [ ] 1.0 Original")

    result = store.load_previous_results("- [ ] 1.0 Different content")
    assert result is None


def test_load_previous_results_no_runs(tmp_path):
    """load_previous_results() returns None when no runs exist."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    assert store.load_previous_results("anything") is None


def test_load_previous_results_skips_failed_tasks(tmp_path):
    """load_previous_results() only returns successful task outputs."""
    store = SpawnRunStore(aurora_dir=tmp_path)
    content = "- [ ] 1.0 Task A\n- [ ] 2.0 Task B"

    run_dir = store.create_run(content)
    store.save_task_result(run_dir, "1.0", success=True, output="Output A")
    store.save_task_result(run_dir, "2.0", success=False, error="Failed")

    results = store.load_previous_results(content)

    assert results is not None
    assert "1.0" in results
    assert "2.0" not in results


def test_hash_consistency():
    """Same content always produces the same hash."""
    content = "test content"
    h1 = SpawnRunStore._hash_content(content)
    h2 = SpawnRunStore._hash_content(content)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex length
