"""TDD Tests for verify_lite function."""

from aurora_soar.agent_registry import AgentInfo


class TestVerifyLite:
    """Tests for verify_lite() function."""

    def test_valid_decomposition_passes(self):
        """Test verify_lite passes when all agents exist and no circular deps."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Test subgoal 1",
                    "suggested_agent": "test-agent-1",
                    "is_critical": True,
                    "depends_on": [],
                },
                {
                    "subgoal_index": 1,
                    "description": "Test subgoal 2",
                    "suggested_agent": "test-agent-2",
                    "is_critical": False,
                    "depends_on": [0],
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent-1",
                name="Test Agent 1",
                description="Agent 1",
                capabilities=["test"],
                agent_type="local",
            ),
            AgentInfo(
                id="test-agent-2",
                name="Test Agent 2",
                description="Agent 2",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is True
        assert len(agent_assignments) == 2
        assert len(issues) == 0

    def test_missing_agent_fails(self):
        """Test verify_lite fails when suggested agent not in registry."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Test subgoal",
                    "suggested_agent": "nonexistent-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(agent_assignments) == 0
        assert len(issues) > 0
        assert "nonexistent-agent" in issues[0]

    def test_circular_dependency_detected(self):
        """Test verify_lite detects circular dependencies in subgoals."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Test subgoal 1",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [1],  # Depends on subgoal 1
                },
                {
                    "subgoal_index": 1,
                    "description": "Test subgoal 2",
                    "suggested_agent": "test-agent",
                    "is_critical": False,
                    "depends_on": [0],  # Depends on subgoal 0 - creates cycle
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(issues) > 0
        assert any("circular" in issue.lower() for issue in issues)

    def test_empty_subgoals_fails(self):
        """Test verify_lite fails when decomposition has no subgoals."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(issues) > 0
        assert any("at least one subgoal" in issue.lower() for issue in issues)

    def test_invalid_subgoal_structure_fails(self):
        """Test verify_lite fails when subgoal missing required fields."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    # Missing 'description' field
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(issues) > 0
        assert any("description" in issue.lower() for issue in issues)

    def test_agent_assignments_created(self):
        """Test verify_lite creates correct agent assignment tuples."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Test subgoal",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is True
        assert len(agent_assignments) == 1
        # Verify tuple format: (subgoal_index, AgentInfo)
        assert isinstance(agent_assignments[0], tuple)
        assert agent_assignments[0][0] == 0  # subgoal_index
        assert isinstance(agent_assignments[0][1], AgentInfo)
        assert agent_assignments[0][1].id == "test-agent"

    def test_issues_list_returned(self):
        """Test verify_lite returns helpful issue messages."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Test subgoal",
                    "suggested_agent": "missing-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(issues) > 0
        # Issues should be descriptive strings
        assert all(isinstance(issue, str) for issue in issues)
        assert all(len(issue) > 0 for issue in issues)

    def test_at_least_one_subgoal_required(self):
        """Test verify_lite requires at least one subgoal."""
        decomposition = {
            "goal": "Test goal",
            "subgoals": [],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(agent_assignments) == 0
        assert len(issues) > 0

    def test_verify_lite_invalid_dependency_ref(self):
        """Test verify_lite rejects plan where subgoal depends on non-existent subgoal.

        sg-2 depends on [1, 99] where 99 doesn't exist.
        Expected: (False, _, ["Subgoal 2 depends on non-existent subgoals: [99]"])
        """
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 1,
                    "description": "Test subgoal 1",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
                {
                    "subgoal_index": 2,
                    "description": "Test subgoal 2",
                    "suggested_agent": "test-agent",
                    "is_critical": False,
                    "depends_on": [1, 99],  # 99 doesn't exist
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is False
        assert len(issues) > 0
        # Should have issue about non-existent subgoal 99
        assert any("non-existent" in issue.lower() and "99" in issue for issue in issues)

    def test_verify_lite_valid_deps_pass(self):
        """Test verify_lite passes plan with valid dependencies.

        sg-2 depends on [1] where sg-1 exists.
        Expected: (True, _, [])
        """
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 1,
                    "description": "Test subgoal 1",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [],
                },
                {
                    "subgoal_index": 2,
                    "description": "Test subgoal 2",
                    "suggested_agent": "test-agent",
                    "is_critical": False,
                    "depends_on": [1],  # Valid reference to subgoal 1
                },
            ],
        }

        available_agents = [
            AgentInfo(
                id="test-agent",
                name="Test Agent",
                description="Agent",
                capabilities=["test"],
                agent_type="local",
            ),
        ]

        from aurora_soar.phases.verify import verify_lite

        passed, agent_assignments, issues = verify_lite(decomposition, available_agents)

        assert passed is True
        assert len(agent_assignments) == 2
        assert len(issues) == 0
