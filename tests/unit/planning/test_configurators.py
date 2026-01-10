"""Tests for ToolRegistry."""

import pytest

from aurora_planning.configurators.registry import ToolRegistry


class MockConfigurator:
    """Mock tool configurator for testing."""

    def __init__(self, name: str, available: bool = True):
        self.name = name
        self.config_file_name = f"{name.lower()}.md"
        self.is_available = available

    def configure(self, project_path: str, aurora_dir: str) -> None:
        """Mock configure method."""
        pass


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before and after each test."""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_and_get_tool(self):
        """Test registering and retrieving a tool."""
        tool = MockConfigurator("Test Tool")
        ToolRegistry.register(tool)

        retrieved = ToolRegistry.get("test-tool")
        assert retrieved is not None
        assert retrieved.name == "Test Tool"

    def test_register_multiple_tools(self):
        """Test registering multiple tools."""
        tool1 = MockConfigurator("Tool One")
        tool2 = MockConfigurator("Tool Two")

        ToolRegistry.register(tool1)
        ToolRegistry.register(tool2)

        all_tools = ToolRegistry.get_all()
        assert len(all_tools) == 2

    def test_get_nonexistent_tool_returns_none(self):
        """Test getting a non-existent tool returns None."""
        result = ToolRegistry.get("nonexistent")
        assert result is None

    def test_get_available_filters_unavailable_tools(self):
        """Test that get_available only returns available tools."""
        available_tool = MockConfigurator("Available", available=True)
        unavailable_tool = MockConfigurator("Unavailable", available=False)

        ToolRegistry.register(available_tool)
        ToolRegistry.register(unavailable_tool)

        available = ToolRegistry.get_available()
        assert len(available) == 1
        assert available[0].name == "Available"

    def test_clear_removes_all_tools(self):
        """Test that clear removes all registered tools."""
        tool = MockConfigurator("Test Tool")
        ToolRegistry.register(tool)

        ToolRegistry.clear()

        all_tools = ToolRegistry.get_all()
        assert len(all_tools) == 0

    def test_tool_id_normalization(self):
        """Test that tool names are normalized to IDs."""
        tool = MockConfigurator("My Test Tool")
        ToolRegistry.register(tool)

        # Should be accessible with lowercase hyphenated ID
        retrieved = ToolRegistry.get("my-test-tool")
        assert retrieved is not None
        assert retrieved.name == "My Test Tool"

    def test_get_all_returns_empty_list_when_no_tools(self):
        """Test that get_all returns empty list when no tools registered."""
        all_tools = ToolRegistry.get_all()
        assert all_tools == []

    def test_get_available_returns_empty_list_when_none_available(self):
        """Test that get_available returns empty list when no tools available."""
        unavailable_tool = MockConfigurator("Unavailable", available=False)
        ToolRegistry.register(unavailable_tool)

        available = ToolRegistry.get_available()
        assert available == []
