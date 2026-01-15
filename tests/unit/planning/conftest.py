"""Shared test fixtures for planning package unit tests."""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_plans_dir(tmp_path: Path) -> Path:
    """Create temporary .aurora/plans directory structure."""
    plans_dir = tmp_path / ".aurora" / "plans"
    (plans_dir / "active").mkdir(parents=True)
    (plans_dir / "archive").mkdir(parents=True)
    return plans_dir


@pytest.fixture
def sample_plan_data() -> dict[str, Any]:
    """Sample plan data for testing."""
    return {
        "plan_id": "0001-test-plan",
        "goal": "Test OAuth Implementation",
        "status": "active",
        "complexity": "medium",
        "created_at": "2026-01-03T10:00:00Z",
        "subgoals": [
            {
                "id": "sg-1",
                "title": "Setup OAuth Provider",
                "description": "Configure OAuth 2.0 provider settings",
                "agent_id": "@backend-dev",
                "status": "pending",
                "dependencies": [],
            },
            {
                "id": "sg-2",
                "title": "Implement Token Exchange",
                "description": "Implement secure token exchange flow",
                "agent_id": "@security-expert",
                "status": "pending",
                "dependencies": ["sg-1"],
            },
        ],
    }


@pytest.fixture
def sample_agents_json(sample_plan_data: dict[str, Any]) -> str:
    """Sample agents.json content."""
    return json.dumps(sample_plan_data, indent=2)


@pytest.fixture
def sample_plan_dir(temp_plans_dir: Path, sample_plan_data: dict[str, Any]) -> Path:
    """Create sample plan directory with files."""
    plan_id = sample_plan_data["plan_id"]
    plan_dir = temp_plans_dir / "active" / plan_id
    plan_dir.mkdir(parents=True)

    # Create agents.json
    agents_file = plan_dir / "agents.json"
    agents_file.write_text(json.dumps(sample_plan_data, indent=2))

    # Create plan.md
    plan_md = plan_dir / "plan.md"
    plan_md.write_text(
        f"""# {sample_plan_data['goal']}

## Subgoals

### SG-1: Setup OAuth Provider
Configure OAuth 2.0 provider settings

### SG-2: Implement Token Exchange
Implement secure token exchange flow
"""
    )

    # Create prd.md
    prd_md = plan_dir / "prd.md"
    prd_md.write_text(
        f"""# PRD: {sample_plan_data['goal']}

## FR-1: Authentication
FR-1.1: User must authenticate via OAuth 2.0
"""
    )

    # Create tasks.md
    tasks_md = plan_dir / "tasks.md"
    tasks_md.write_text(
        """# Task Checklist

- [ ] Setup OAuth provider
- [ ] Implement token exchange
"""
    )

    return plan_dir


@pytest.fixture
def mock_config(tmp_path: Path) -> dict[str, Any]:
    """Mock configuration for testing."""
    plans_dir = tmp_path / ".aurora" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    return {
        "planning": {
            "base_dir": str(plans_dir),
            "auto_increment": True,
            "archive_on_complete": False,
        }
    }
