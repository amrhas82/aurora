"""Topological sort for dependency-aware task execution.

Groups tasks into waves where each wave's tasks can run in parallel,
and all dependencies are satisfied by prior waves.
"""

from collections import deque

from implement.models import ParsedTask


def topological_sort_tasks(tasks: list[ParsedTask]) -> list[list[ParsedTask]]:
    """Sort tasks into dependency-ordered waves using Kahn's algorithm.

    Each wave contains tasks whose dependencies are all satisfied by
    previous waves. Tasks within a wave can safely run in parallel.

    Args:
        tasks: List of ParsedTask objects (may have depends_on references)

    Returns:
        List of waves, where each wave is a list of parallel-safe tasks

    Raises:
        ValueError: If circular dependency detected

    """
    if not tasks:
        return []

    task_map = {t.id: t for t in tasks}
    in_degree: dict[str, int] = {t.id: 0 for t in tasks}

    # Build in-degree counts (only count deps that exist in our task set)
    for task in tasks:
        for dep_id in task.depends_on:
            if dep_id in task_map:
                in_degree[task.id] += 1

    # Start with tasks that have no dependencies
    queue: deque[str] = deque(tid for tid, deg in in_degree.items() if deg == 0)
    waves: list[list[ParsedTask]] = []

    processed = 0
    while queue:
        # All tasks currently in queue form one parallel wave
        wave_ids = list(queue)
        queue.clear()
        wave = [task_map[tid] for tid in wave_ids]
        waves.append(wave)
        processed += len(wave)

        # Reduce in-degree for dependents
        for tid in wave_ids:
            for task in tasks:
                if tid in task.depends_on and task.id in in_degree:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)

    if processed < len(tasks):
        raise ValueError("Circular dependency detected among tasks")

    return waves
