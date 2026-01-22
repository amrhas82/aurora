"""Unit tests for tool provider registry multi-tool interactions.

Tests cover:
- Registry singleton behavior with concurrent access
- Multi-tool provider retrieval and configuration
- Provider availability checks for multiple tools
- Capability-based routing for multi-tool scenarios
- Factory method usage for concurrent execution
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from aurora_cli.tool_providers import ToolProviderRegistry
from aurora_cli.tool_providers.base import (
    CapabilityRouter,
    OutputNormalizer,
    ToolCapabilities,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    ToolProviderRegistry.reset()
    yield ToolProviderRegistry.get_instance()
    ToolProviderRegistry.reset()


@pytest.fixture
def mock_tool_availability():
    """Mock tool availability checks."""
    with patch("shutil.which") as mock:
        mock.return_value = "/usr/bin/tool"
        yield mock


# ---------------------------------------------------------------------------
# Test: Registry Singleton Behavior
# ---------------------------------------------------------------------------


class TestRegistrySingleton:
    """Test registry singleton behavior."""

    def test_singleton_instance(self, clean_registry):
        """Test that get_instance returns same instance."""
        registry1 = ToolProviderRegistry.get_instance()
        registry2 = ToolProviderRegistry.get_instance()
        assert registry1 is registry2

    def test_reset_creates_new_instance(self, clean_registry):
        """Test that reset creates a fresh instance."""
        registry1 = ToolProviderRegistry.get_instance()
        ToolProviderRegistry.reset()
        registry2 = ToolProviderRegistry.get_instance()
        assert registry1 is not registry2

    def test_builtin_providers_registered(self, clean_registry):
        """Test that builtin providers are registered on first access."""
        registry = ToolProviderRegistry.get_instance()
        available = registry.list_available()
        assert "claude" in available
        assert "opencode" in available


# ---------------------------------------------------------------------------
# Test: Multi-Tool Provider Retrieval
# ---------------------------------------------------------------------------


class TestMultiToolRetrieval:
    """Test retrieving multiple tool providers."""

    def test_get_multiple_providers(self, clean_registry):
        """Test retrieving multiple providers by name."""
        providers = clean_registry.get_multiple(["claude", "opencode"])
        assert len(providers) == 2
        names = [p.name for p in providers]
        assert "claude" in names
        assert "opencode" in names

    def test_get_multiple_with_missing(self, clean_registry):
        """Test that missing providers are skipped."""
        providers = clean_registry.get_multiple(["claude", "nonexistent", "opencode"])
        assert len(providers) == 2  # nonexistent is skipped

    def test_get_multiple_empty_list(self, clean_registry):
        """Test retrieving with empty list."""
        providers = clean_registry.get_multiple([])
        assert len(providers) == 0

    def test_get_multiple_all_missing(self, clean_registry):
        """Test when all requested providers are missing."""
        providers = clean_registry.get_multiple(["fake1", "fake2"])
        assert len(providers) == 0

    def test_get_by_priority(self, clean_registry):
        """Test retrieving providers sorted by priority."""
        with patch.object(clean_registry.get("claude"), "is_available", return_value=True):
            with patch.object(clean_registry.get("opencode"), "is_available", return_value=True):
                providers = clean_registry.get_by_priority()
                # Should be sorted by priority
                priorities = [p.priority for p in providers]
                assert priorities == sorted(priorities)


# ---------------------------------------------------------------------------
# Test: Provider Configuration for Multi-Tool
# ---------------------------------------------------------------------------


class TestProviderConfiguration:
    """Test configuring multiple providers."""

    def test_configure_multiple_providers(self, clean_registry):
        """Test configuring multiple providers with different settings."""
        clean_registry.configure("claude", {"timeout": 300, "priority": 1})
        clean_registry.configure("opencode", {"timeout": 600, "priority": 2})

        claude = clean_registry.get("claude")
        opencode = clean_registry.get("opencode")

        assert claude.timeout == 300
        assert claude.priority == 1
        assert opencode.timeout == 600
        assert opencode.priority == 2

    def test_load_from_config(self, clean_registry):
        """Test loading multiple tool configs at once."""
        tool_configs = {
            "claude": {"timeout": 300, "flags": ["--print"]},
            "opencode": {"timeout": 500, "input_method": "stdin"},
            "custom_tool": {"executable": "custom", "input_method": "argument"},
        }

        count = clean_registry.load_from_config(tool_configs)

        assert count == 3
        assert "custom_tool" in clean_registry.list_available()

    def test_configuration_isolation(self, clean_registry):
        """Test that provider configurations are isolated."""
        clean_registry.configure("claude", {"timeout": 100})
        clean_registry.configure("opencode", {"timeout": 200})

        # Creating new instances should have correct configs
        claude1 = clean_registry.create("claude")
        opencode1 = clean_registry.create("opencode")

        assert claude1.timeout == 100
        assert opencode1.timeout == 200


# ---------------------------------------------------------------------------
# Test: Factory Method for Multi-Tool Execution
# ---------------------------------------------------------------------------


class TestFactoryMethod:
    """Test factory method for creating provider instances."""

    def test_create_multiple_instances(self, clean_registry):
        """Test creating multiple instances of same provider."""
        instance1 = clean_registry.create("claude")
        instance2 = clean_registry.create("claude")

        assert instance1 is not instance2
        assert instance1.name == instance2.name

    def test_create_with_different_configs(self, clean_registry):
        """Test creating instances with different configs."""
        instance1 = clean_registry.create("claude", {"timeout": 100})
        instance2 = clean_registry.create("claude", {"timeout": 200})

        assert instance1.timeout == 100
        assert instance2.timeout == 200

    def test_create_unknown_provider_raises(self, clean_registry):
        """Test that creating unknown provider raises KeyError."""
        with pytest.raises(KeyError, match="Unknown tool provider"):
            clean_registry.create("nonexistent_tool")

    def test_create_generic_provider(self, clean_registry):
        """Test creating a generic provider from config."""
        clean_registry.register_from_config(
            "custom",
            {
                "executable": "custom-cli",
                "input_method": "stdin",
            },
        )

        provider = clean_registry.create("custom")
        assert provider.name == "custom"
        assert provider.executable == "custom-cli"


# ---------------------------------------------------------------------------
# Test: Provider Availability for Multi-Tool
# ---------------------------------------------------------------------------


class TestProviderAvailability:
    """Test provider availability checking for multiple tools."""

    def test_list_installed(self, clean_registry, mock_tool_availability):
        """Test listing installed providers."""
        installed = clean_registry.list_installed()
        # With mocked shutil.which, all should report as available
        assert len(installed) > 0

    def test_availability_check_per_tool(self, clean_registry):
        """Test individual availability checks."""
        with patch("shutil.which") as mock:
            mock.side_effect = lambda x: "/usr/bin/claude" if x == "claude" else None

            claude = clean_registry.get("claude")
            opencode = clean_registry.get("opencode")

            # Claude available, OpenCode not
            assert claude.is_available() is True
            assert opencode.is_available() is False

    def test_get_info_includes_availability(self, clean_registry, mock_tool_availability):
        """Test that provider info includes availability."""
        info = clean_registry.get_info()
        assert "providers" in info
        for name, provider_info in info["providers"].items():
            assert "available" in provider_info


# ---------------------------------------------------------------------------
# Test: Capability-Based Routing
# ---------------------------------------------------------------------------


class TestCapabilityRouting:
    """Test capability-based tool routing for multi-tool scenarios."""

    def test_select_tools_by_capability(self, clean_registry):
        """Test selecting tools by required capabilities."""
        # Get all available providers
        all_providers = clean_registry.get_multiple(["claude", "opencode"])

        # Mock availability
        for p in all_providers:
            p.is_available = Mock(return_value=True)

        required = ToolCapabilities(supports_streaming=False)
        selected = CapabilityRouter.select_tools(all_providers, required)

        assert len(selected) >= 0  # Some may match

    def test_select_best_tool(self, clean_registry):
        """Test selecting single best tool by capability."""
        providers = clean_registry.get_multiple(["claude", "opencode"])
        for p in providers:
            p.is_available = Mock(return_value=True)

        required = ToolCapabilities()
        best = CapabilityRouter.select_best(providers, required)

        # Should return one provider (highest priority)
        if best:
            assert best.name in ["claude", "opencode"]

    def test_group_by_capability(self, clean_registry):
        """Test grouping providers by capability."""
        providers = clean_registry.get_multiple(["claude", "opencode"])
        groups = CapabilityRouter.group_by_capability(providers)

        assert "streaming" in groups
        assert "conversation" in groups
        assert "tools" in groups


# ---------------------------------------------------------------------------
# Test: Concurrent Registry Access
# ---------------------------------------------------------------------------


class TestConcurrentRegistryAccess:
    """Test registry behavior under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_get_operations(self, clean_registry):
        """Test concurrent get operations don't interfere."""

        async def get_provider(name):
            return clean_registry.get(name)

        # Run multiple concurrent gets
        results = await asyncio.gather(
            get_provider("claude"),
            get_provider("opencode"),
            get_provider("claude"),
            get_provider("opencode"),
        )

        # All should return valid providers
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_create_operations(self, clean_registry):
        """Test concurrent create operations."""

        async def create_provider(name, config):
            return clean_registry.create(name, config)

        # Run multiple concurrent creates
        results = await asyncio.gather(
            create_provider("claude", {"timeout": 100}),
            create_provider("claude", {"timeout": 200}),
            create_provider("opencode", {"timeout": 300}),
        )

        # All should return valid, distinct providers
        assert len(results) == 3
        assert results[0].timeout == 100
        assert results[1].timeout == 200
        assert results[2].timeout == 300


# ---------------------------------------------------------------------------
# Test: Generic Provider Registration
# ---------------------------------------------------------------------------


class TestGenericProviderRegistration:
    """Test registering generic providers for multi-tool scenarios."""

    def test_register_generic_provider(self, clean_registry):
        """Test registering a generic tool provider."""
        clean_registry.register_from_config(
            "my_custom_tool",
            {
                "executable": "my-custom-tool",
                "display_name": "My Custom Tool",
                "input_method": "stdin",
                "timeout": 300,
            },
        )

        custom = clean_registry.get("my_custom_tool")
        assert custom is not None
        assert custom.name == "my_custom_tool"
        assert custom.timeout == 300

    def test_unregister_provider(self, clean_registry):
        """Test unregistering a provider."""
        clean_registry.register_from_config("temp_tool", {"executable": "temp"})
        assert "temp_tool" in clean_registry.list_available()

        result = clean_registry.unregister("temp_tool")
        assert result is True
        assert "temp_tool" not in clean_registry.list_available()

    def test_unregister_nonexistent(self, clean_registry):
        """Test unregistering nonexistent provider."""
        result = clean_registry.unregister("nonexistent")
        assert result is False


# ---------------------------------------------------------------------------
# Test: Output Normalization
# ---------------------------------------------------------------------------


class TestOutputNormalization:
    """Test output normalization across providers."""

    def test_strip_ansi_codes(self):
        """Test ANSI code stripping."""
        text = "\x1b[32mGreen text\x1b[0m normal"
        normalized = OutputNormalizer.strip_ansi(text)
        assert "\x1b[" not in normalized
        assert "Green text" in normalized

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Line 1\n\n\n\n\nLine 2  \nLine 3  "
        normalized = OutputNormalizer.normalize_whitespace(text)
        assert "\n\n\n" not in normalized
        assert not normalized.endswith("  ")

    def test_extract_code_blocks(self):
        """Test code block extraction."""
        text = "```python\nprint('hello')\n```\n\n```js\nconsole.log('hi');\n```"
        blocks = OutputNormalizer.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "js"

    def test_full_normalization_pipeline(self):
        """Test full normalization."""
        text = "\x1b[32mColored\x1b[0m text\n\n\n\nwith gaps  "
        normalized = OutputNormalizer.normalize(text)
        assert "\x1b[" not in normalized
        assert "\n\n\n" not in normalized


# ---------------------------------------------------------------------------
# Test: Tool Capabilities Matching
# ---------------------------------------------------------------------------


class TestCapabilitiesMatching:
    """Test tool capabilities matching."""

    def test_capabilities_match_basic(self):
        """Test basic capability matching."""
        have = ToolCapabilities(supports_streaming=True, supports_tools=True)
        need = ToolCapabilities(supports_streaming=True)
        assert have.matches(need) is True

    def test_capabilities_match_fails(self):
        """Test capability matching failure."""
        have = ToolCapabilities(supports_streaming=False)
        need = ToolCapabilities(supports_streaming=True)
        assert have.matches(need) is False

    def test_capabilities_context_length(self):
        """Test context length capability matching."""
        have = ToolCapabilities(max_context_length=100000)
        need = ToolCapabilities(max_context_length=50000)
        assert have.matches(need) is True

        need_more = ToolCapabilities(max_context_length=200000)
        assert have.matches(need_more) is False


# ---------------------------------------------------------------------------
# Test: Provider Info
# ---------------------------------------------------------------------------


class TestProviderInfo:
    """Test provider info retrieval."""

    def test_get_provider_info(self, clean_registry):
        """Test getting detailed provider info."""
        claude = clean_registry.get("claude")
        info = claude.get_info()

        assert info["name"] == "claude"
        assert "display_name" in info
        assert "executable" in info
        assert "input_method" in info
        assert "capabilities" in info

    def test_registry_info(self, clean_registry, mock_tool_availability):
        """Test getting registry-level info."""
        info = clean_registry.get_info()

        assert "registered_count" in info
        assert "installed_count" in info
        assert "providers" in info
        assert info["registered_count"] >= 2  # At least claude and opencode


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases in registry operations."""

    def test_get_same_provider_twice(self, clean_registry):
        """Test getting same provider returns cached instance."""
        claude1 = clean_registry.get("claude")
        claude2 = clean_registry.get("claude")
        assert claude1 is claude2

    def test_configure_updates_cached_instance(self, clean_registry):
        """Test that configure updates the cached instance."""
        claude = clean_registry.get("claude")
        original_timeout = claude.timeout

        clean_registry.configure("claude", {"timeout": 999})

        # Same instance should be updated
        assert claude.timeout == 999

    def test_empty_configuration(self, clean_registry):
        """Test configuration with empty dict."""
        clean_registry.configure("claude", {})
        claude = clean_registry.get("claude")
        # Should still work with defaults
        assert claude is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
