"""Tests for SlashCommandRegistry with all 20 configurators."""

import pytest

from aurora_cli.configurators.slash.registry import SlashCommandRegistry


# All 20 expected tool IDs
ALL_TOOL_IDS = [
    "amazon-q",
    "antigravity",
    "auggie",
    "claude",
    "cline",
    "codex",
    "codebuddy",
    "costrict",
    "crush",
    "cursor",
    "factory",
    "gemini",
    "github-copilot",
    "iflow",
    "kilocode",
    "opencode",
    "qoder",
    "qwen",
    "roocode",
    "windsurf",
]


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before each test."""
    SlashCommandRegistry.clear()
    yield
    SlashCommandRegistry.clear()


class TestSlashCommandRegistryCount:
    """Tests for registry configurator count."""

    def test_get_all_returns_20_configurators(self):
        """get_all() should return exactly 20 configurators."""
        configurators = SlashCommandRegistry.get_all()
        assert len(configurators) == 20

    def test_get_available_returns_20_configurators(self):
        """get_available() should return 20 (all tools always available per PRD)."""
        configurators = SlashCommandRegistry.get_available()
        assert len(configurators) == 20


class TestSlashCommandRegistryHighPriorityTools:
    """Tests for high-priority tool retrieval."""

    def test_get_claude_returns_claude_configurator(self):
        """get('claude') should return ClaudeSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.claude import ClaudeSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("claude")
        assert configurator is not None
        assert isinstance(configurator, ClaudeSlashCommandConfigurator)
        assert configurator.tool_id == "claude"

    def test_get_cursor_returns_cursor_configurator(self):
        """get('cursor') should return CursorSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.cursor import CursorSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("cursor")
        assert configurator is not None
        assert isinstance(configurator, CursorSlashCommandConfigurator)
        assert configurator.tool_id == "cursor"

    def test_get_gemini_returns_gemini_configurator(self):
        """get('gemini') should return GeminiSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.gemini import GeminiSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("gemini")
        assert configurator is not None
        assert isinstance(configurator, GeminiSlashCommandConfigurator)
        assert configurator.tool_id == "gemini"

    def test_get_codex_returns_codex_configurator(self):
        """get('codex') should return CodexSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.codex import CodexSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("codex")
        assert configurator is not None
        assert isinstance(configurator, CodexSlashCommandConfigurator)
        assert configurator.tool_id == "codex"

    def test_get_windsurf_returns_windsurf_configurator(self):
        """get('windsurf') should return WindsurfSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.windsurf import WindsurfSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("windsurf")
        assert configurator is not None
        assert isinstance(configurator, WindsurfSlashCommandConfigurator)
        assert configurator.tool_id == "windsurf"


class TestSlashCommandRegistryRemainingTools:
    """Tests for remaining 15 tool retrieval."""

    def test_get_amazon_q_returns_amazon_q_configurator(self):
        """get('amazon-q') should return AmazonQSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.amazon_q import AmazonQSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("amazon-q")
        assert configurator is not None
        assert isinstance(configurator, AmazonQSlashCommandConfigurator)
        assert configurator.tool_id == "amazon-q"

    def test_get_antigravity_returns_antigravity_configurator(self):
        """get('antigravity') should return AntigravitySlashCommandConfigurator."""
        from aurora_cli.configurators.slash.antigravity import (
            AntigravitySlashCommandConfigurator,
        )

        configurator = SlashCommandRegistry.get("antigravity")
        assert configurator is not None
        assert isinstance(configurator, AntigravitySlashCommandConfigurator)
        assert configurator.tool_id == "antigravity"

    def test_get_auggie_returns_auggie_configurator(self):
        """get('auggie') should return AuggieSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.auggie import AuggieSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("auggie")
        assert configurator is not None
        assert isinstance(configurator, AuggieSlashCommandConfigurator)
        assert configurator.tool_id == "auggie"

    def test_get_cline_returns_cline_configurator(self):
        """get('cline') should return ClineSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("cline")
        assert configurator is not None
        assert isinstance(configurator, ClineSlashCommandConfigurator)
        assert configurator.tool_id == "cline"

    def test_get_codebuddy_returns_codebuddy_configurator(self):
        """get('codebuddy') should return CodeBuddySlashCommandConfigurator."""
        from aurora_cli.configurators.slash.codebuddy import (
            CodeBuddySlashCommandConfigurator,
        )

        configurator = SlashCommandRegistry.get("codebuddy")
        assert configurator is not None
        assert isinstance(configurator, CodeBuddySlashCommandConfigurator)
        assert configurator.tool_id == "codebuddy"

    def test_get_costrict_returns_costrict_configurator(self):
        """get('costrict') should return CostrictSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.costrict import CostrictSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("costrict")
        assert configurator is not None
        assert isinstance(configurator, CostrictSlashCommandConfigurator)
        assert configurator.tool_id == "costrict"

    def test_get_crush_returns_crush_configurator(self):
        """get('crush') should return CrushSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.crush import CrushSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("crush")
        assert configurator is not None
        assert isinstance(configurator, CrushSlashCommandConfigurator)
        assert configurator.tool_id == "crush"

    def test_get_factory_returns_factory_configurator(self):
        """get('factory') should return FactorySlashCommandConfigurator."""
        from aurora_cli.configurators.slash.factory import FactorySlashCommandConfigurator

        configurator = SlashCommandRegistry.get("factory")
        assert configurator is not None
        assert isinstance(configurator, FactorySlashCommandConfigurator)
        assert configurator.tool_id == "factory"

    def test_get_github_copilot_returns_github_copilot_configurator(self):
        """get('github-copilot') should return GitHubCopilotSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.github_copilot import (
            GitHubCopilotSlashCommandConfigurator,
        )

        configurator = SlashCommandRegistry.get("github-copilot")
        assert configurator is not None
        assert isinstance(configurator, GitHubCopilotSlashCommandConfigurator)
        assert configurator.tool_id == "github-copilot"

    def test_get_iflow_returns_iflow_configurator(self):
        """get('iflow') should return IflowSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.iflow import IflowSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("iflow")
        assert configurator is not None
        assert isinstance(configurator, IflowSlashCommandConfigurator)
        assert configurator.tool_id == "iflow"

    def test_get_kilocode_returns_kilocode_configurator(self):
        """get('kilocode') should return KiloCodeSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.kilocode import KiloCodeSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("kilocode")
        assert configurator is not None
        assert isinstance(configurator, KiloCodeSlashCommandConfigurator)
        assert configurator.tool_id == "kilocode"

    def test_get_opencode_returns_opencode_configurator(self):
        """get('opencode') should return OpenCodeSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.opencode import OpenCodeSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("opencode")
        assert configurator is not None
        assert isinstance(configurator, OpenCodeSlashCommandConfigurator)
        assert configurator.tool_id == "opencode"

    def test_get_qoder_returns_qoder_configurator(self):
        """get('qoder') should return QoderSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.qoder import QoderSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("qoder")
        assert configurator is not None
        assert isinstance(configurator, QoderSlashCommandConfigurator)
        assert configurator.tool_id == "qoder"

    def test_get_qwen_returns_qwen_configurator(self):
        """get('qwen') should return QwenSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.qwen import QwenSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("qwen")
        assert configurator is not None
        assert isinstance(configurator, QwenSlashCommandConfigurator)
        assert configurator.tool_id == "qwen"

    def test_get_roocode_returns_roocode_configurator(self):
        """get('roocode') should return RooCodeSlashCommandConfigurator."""
        from aurora_cli.configurators.slash.roocode import RooCodeSlashCommandConfigurator

        configurator = SlashCommandRegistry.get("roocode")
        assert configurator is not None
        assert isinstance(configurator, RooCodeSlashCommandConfigurator)
        assert configurator.tool_id == "roocode"


class TestSlashCommandRegistryAllToolIds:
    """Tests for all tool IDs being retrievable."""

    @pytest.mark.parametrize("tool_id", ALL_TOOL_IDS)
    def test_all_tool_ids_retrievable(self, tool_id: str):
        """All 20 tool IDs should be retrievable."""
        configurator = SlashCommandRegistry.get(tool_id)
        assert configurator is not None, f"Tool '{tool_id}' not found in registry"

    def test_all_tool_ids_present_in_get_all(self):
        """All 20 tool IDs should appear in get_all()."""
        configurators = SlashCommandRegistry.get_all()
        tool_ids = {c.tool_id for c in configurators}
        expected_ids = set(ALL_TOOL_IDS)
        assert tool_ids == expected_ids


class TestSlashCommandRegistryNormalization:
    """Tests for tool ID normalization."""

    def test_get_with_uppercase(self):
        """get() should normalize uppercase to lowercase."""
        configurator = SlashCommandRegistry.get("CLAUDE")
        assert configurator is not None
        assert configurator.tool_id == "claude"

    def test_get_with_mixed_case(self):
        """get() should normalize mixed case."""
        configurator = SlashCommandRegistry.get("GiTHub-Copilot")
        assert configurator is not None
        assert configurator.tool_id == "github-copilot"

    def test_get_with_spaces_instead_of_dashes(self):
        """get() should normalize spaces to dashes."""
        configurator = SlashCommandRegistry.get("amazon q")
        assert configurator is not None
        assert configurator.tool_id == "amazon-q"


class TestSlashCommandRegistryAvailability:
    """Tests for configurator availability."""

    def test_all_configurators_are_available(self):
        """All 20 configurators should have is_available=True."""
        configurators = SlashCommandRegistry.get_all()
        for configurator in configurators:
            assert configurator.is_available is True, (
                f"Configurator '{configurator.tool_id}' should be available"
            )


class TestSlashCommandRegistryClear:
    """Tests for registry clear functionality."""

    def test_clear_removes_all_configurators(self):
        """clear() should remove all registered configurators."""
        # First ensure registry is initialized
        assert len(SlashCommandRegistry.get_all()) == 20

        # Clear and verify
        SlashCommandRegistry.clear()
        assert len(SlashCommandRegistry._configurators) == 0
        assert SlashCommandRegistry._initialized is False

    def test_registry_reinitializes_after_clear(self):
        """Registry should reinitialize after clear."""
        SlashCommandRegistry.clear()
        configurators = SlashCommandRegistry.get_all()
        assert len(configurators) == 20


class TestSlashCommandRegistryLazyLoading:
    """Tests for lazy loading behavior."""

    def test_registry_initializes_on_first_get(self):
        """Registry should initialize lazily on first get() call."""
        SlashCommandRegistry.clear()
        assert SlashCommandRegistry._initialized is False

        SlashCommandRegistry.get("claude")
        assert SlashCommandRegistry._initialized is True

    def test_registry_initializes_on_first_get_all(self):
        """Registry should initialize lazily on first get_all() call."""
        SlashCommandRegistry.clear()
        assert SlashCommandRegistry._initialized is False

        SlashCommandRegistry.get_all()
        assert SlashCommandRegistry._initialized is True

    def test_registry_initializes_on_first_get_available(self):
        """Registry should initialize lazily on first get_available() call."""
        SlashCommandRegistry.clear()
        assert SlashCommandRegistry._initialized is False

        SlashCommandRegistry.get_available()
        assert SlashCommandRegistry._initialized is True
