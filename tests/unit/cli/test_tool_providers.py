"""Unit tests for tool providers.

Tests cover:
- ToolProviderRegistry singleton and factory pattern
- ClaudeToolProvider implementation
- OpenCodeToolProvider implementation
- Base ToolProvider interface
- GenericToolProvider for config-driven tools
- New providers: Cursor, Gemini, Codex
- Registry configuration and discovery
"""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_cli.tool_providers import (
    CapabilityRouter,
    ClaudeToolProvider,
    CodexToolProvider,
    CursorToolProvider,
    GeminiToolProvider,
    GenericToolProvider,
    InputMethod,
    OpenCodeToolProvider,
    OutputFormat,
    OutputNormalizer,
    ToolAdapter,
    ToolCapabilities,
    ToolProvider,
    ToolProviderRegistry,
    ToolResult,
    ToolStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_registry():
    """Reset the registry singleton before and after each test."""
    ToolProviderRegistry.reset()
    yield
    ToolProviderRegistry.reset()


@pytest.fixture
def mock_claude_available():
    """Mock Claude CLI as available."""
    with patch("shutil.which") as mock:
        mock.return_value = "/usr/bin/claude"
        yield mock


@pytest.fixture
def mock_opencode_available():
    """Mock OpenCode CLI as available."""
    with patch("shutil.which") as mock:
        mock.return_value = "/usr/bin/opencode"
        yield mock


# ---------------------------------------------------------------------------
# Test: ToolProviderRegistry
# ---------------------------------------------------------------------------


class TestToolProviderRegistry:
    """Tests for the ToolProviderRegistry."""

    def test_singleton_pattern(self, reset_registry):
        """Test that registry returns same instance."""
        registry1 = ToolProviderRegistry.get_instance()
        registry2 = ToolProviderRegistry.get_instance()

        assert registry1 is registry2

    def test_reset_creates_new_instance(self, reset_registry):
        """Test that reset creates a new instance."""
        registry1 = ToolProviderRegistry.get_instance()
        ToolProviderRegistry.reset()
        registry2 = ToolProviderRegistry.get_instance()

        assert registry1 is not registry2

    def test_builtin_providers_registered(self, reset_registry):
        """Test that built-in providers are registered automatically."""
        registry = ToolProviderRegistry.get_instance()
        available = registry.list_available()

        assert "claude" in available
        assert "opencode" in available

    def test_get_provider(self, reset_registry):
        """Test getting a provider by name."""
        registry = ToolProviderRegistry.get_instance()

        claude = registry.get("claude")

        assert claude is not None
        assert isinstance(claude, ClaudeToolProvider)

    def test_get_nonexistent_provider(self, reset_registry):
        """Test getting a non-existent provider returns None."""
        registry = ToolProviderRegistry.get_instance()

        result = registry.get("nonexistent")

        assert result is None

    def test_get_caches_instances(self, reset_registry):
        """Test that get() caches provider instances."""
        registry = ToolProviderRegistry.get_instance()

        claude1 = registry.get("claude")
        claude2 = registry.get("claude")

        assert claude1 is claude2

    def test_create_returns_new_instance(self, reset_registry):
        """Test that create() always returns new instance."""
        registry = ToolProviderRegistry.get_instance()

        claude1 = registry.create("claude")
        claude2 = registry.create("claude")

        assert claude1 is not claude2

    def test_create_unknown_raises(self, reset_registry):
        """Test that create() raises for unknown provider."""
        registry = ToolProviderRegistry.get_instance()

        with pytest.raises(KeyError, match="Unknown tool provider"):
            registry.create("unknown")

    def test_get_multiple(self, reset_registry):
        """Test getting multiple providers."""
        registry = ToolProviderRegistry.get_instance()

        providers = registry.get_multiple(["claude", "opencode", "unknown"])

        assert len(providers) == 2
        assert all(isinstance(p, ToolProvider) for p in providers)

    def test_register_custom_provider(self, reset_registry):
        """Test registering a custom provider."""

        class CustomProvider(ToolProvider):
            @property
            def name(self) -> str:
                return "custom"

            def is_available(self) -> bool:
                return True

            def execute(self, context, working_dir=None, timeout=600):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="Custom output",
                    stderr="",
                    return_code=0,
                )

            def build_command(self, context):
                return ["custom", context]

        registry = ToolProviderRegistry.get_instance()
        registry.register(CustomProvider)

        assert "custom" in registry.list_available()
        custom = registry.get("custom")
        assert custom is not None
        assert custom.name == "custom"

    def test_unregister_provider(self, reset_registry):
        """Test unregistering a provider."""
        registry = ToolProviderRegistry.get_instance()

        assert "claude" in registry.list_available()

        result = registry.unregister("claude")

        assert result is True
        assert "claude" not in registry.list_available()
        assert registry.get("claude") is None

    def test_unregister_nonexistent(self, reset_registry):
        """Test unregistering a non-existent provider."""
        registry = ToolProviderRegistry.get_instance()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_list_installed(self, reset_registry):
        """Test listing installed providers."""
        registry = ToolProviderRegistry.get_instance()

        with patch("shutil.which") as mock_which:
            # Only Claude is installed
            mock_which.side_effect = lambda x: "/usr/bin/claude" if x == "claude" else None

            installed = registry.list_installed()

            assert "claude" in installed
            assert "opencode" not in installed


# ---------------------------------------------------------------------------
# Test: ClaudeToolProvider
# ---------------------------------------------------------------------------


class TestClaudeToolProvider:
    """Tests for ClaudeToolProvider."""

    def test_name(self):
        """Test provider name."""
        provider = ClaudeToolProvider()
        assert provider.name == "claude"

    def test_display_name(self):
        """Test provider display name."""
        provider = ClaudeToolProvider()
        assert provider.display_name == "Claude Code"

    def test_is_available_when_installed(self, mock_claude_available):
        """Test is_available returns True when Claude is installed."""
        provider = ClaudeToolProvider()
        assert provider.is_available() is True

    def test_is_available_when_not_installed(self):
        """Test is_available returns False when Claude is not installed."""
        with patch("shutil.which", return_value=None):
            provider = ClaudeToolProvider()
            assert provider.is_available() is False

    def test_build_command(self):
        """Test command building."""
        provider = ClaudeToolProvider()

        cmd = provider.build_command("Test prompt")

        assert cmd == ["claude", "--print", "--dangerously-skip-permissions", "Test prompt"]

    def test_execute_success(self, mock_claude_available):
        """Test successful execution."""
        provider = ClaudeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Success output",
                stderr="",
            )

            result = provider.execute("Test prompt")

            assert result.success is True
            assert result.status == ToolStatus.SUCCESS
            assert result.stdout == "Success output"
            assert result.return_code == 0
            assert result.duration_seconds > 0

    def test_execute_failure(self, mock_claude_available):
        """Test failed execution."""
        provider = ClaudeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error message",
            )

            result = provider.execute("Test prompt")

            assert result.success is False
            assert result.status == ToolStatus.FAILURE
            assert result.stderr == "Error message"
            assert result.return_code == 1

    def test_execute_timeout(self, mock_claude_available):
        """Test timeout handling."""
        provider = ClaudeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=30)

            result = provider.execute("Test prompt", timeout=30)

            assert result.success is False
            assert result.status == ToolStatus.TIMEOUT
            assert "timed out" in result.stderr.lower()

    def test_execute_not_available(self):
        """Test execution when Claude is not available."""
        with patch("shutil.which", return_value=None):
            provider = ClaudeToolProvider()

            result = provider.execute("Test prompt")

            assert result.success is False
            assert result.status == ToolStatus.NOT_FOUND
            assert "not found" in result.stderr.lower()

    def test_execute_with_working_dir(self, mock_claude_available):
        """Test execution with custom working directory."""
        provider = ClaudeToolProvider()
        working_dir = Path("/tmp/test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Output", stderr="")

            provider.execute("Test prompt", working_dir=working_dir)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["cwd"] == working_dir

    def test_execute_exception(self, mock_claude_available):
        """Test handling of unexpected exceptions."""
        provider = ClaudeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Unexpected error")

            result = provider.execute("Test prompt")

            assert result.success is False
            assert result.status == ToolStatus.FAILURE
            assert "Unexpected error" in result.stderr

    def test_get_config_key(self):
        """Test config key generation."""
        provider = ClaudeToolProvider()
        assert provider.get_config_key() == "tool.claude"


# ---------------------------------------------------------------------------
# Test: OpenCodeToolProvider
# ---------------------------------------------------------------------------


class TestOpenCodeToolProvider:
    """Tests for OpenCodeToolProvider."""

    def test_name(self):
        """Test provider name."""
        provider = OpenCodeToolProvider()
        assert provider.name == "opencode"

    def test_display_name(self):
        """Test provider display name."""
        provider = OpenCodeToolProvider()
        assert provider.display_name == "OpenCode"

    def test_is_available_when_installed(self, mock_opencode_available):
        """Test is_available returns True when OpenCode is installed."""
        provider = OpenCodeToolProvider()
        assert provider.is_available() is True

    def test_is_available_when_not_installed(self):
        """Test is_available returns False when OpenCode is not installed."""
        with patch("shutil.which", return_value=None):
            provider = OpenCodeToolProvider()
            assert provider.is_available() is False

    def test_build_command(self):
        """Test command building (OpenCode uses stdin)."""
        provider = OpenCodeToolProvider()

        cmd = provider.build_command("Test prompt")

        # OpenCode doesn't include prompt in command (uses stdin)
        assert cmd == ["opencode"]

    def test_execute_success(self, mock_opencode_available):
        """Test successful execution."""
        provider = OpenCodeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Success output",
                stderr="",
            )

            result = provider.execute("Test prompt")

            assert result.success is True
            assert result.status == ToolStatus.SUCCESS
            assert result.stdout == "Success output"

            # Verify stdin was used
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["input"] == "Test prompt"

    def test_execute_failure(self, mock_opencode_available):
        """Test failed execution."""
        provider = OpenCodeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error message",
            )

            result = provider.execute("Test prompt")

            assert result.success is False
            assert result.status == ToolStatus.FAILURE

    def test_execute_timeout(self, mock_opencode_available):
        """Test timeout handling."""
        provider = OpenCodeToolProvider()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["opencode"], timeout=30)

            result = provider.execute("Test prompt", timeout=30)

            assert result.success is False
            assert result.status == ToolStatus.TIMEOUT

    def test_execute_not_available(self):
        """Test execution when OpenCode is not available."""
        with patch("shutil.which", return_value=None):
            provider = OpenCodeToolProvider()

            result = provider.execute("Test prompt")

            assert result.success is False
            assert result.status == ToolStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Test: ToolResult
# ---------------------------------------------------------------------------


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_property_true(self):
        """Test success property when status is SUCCESS and return_code is 0."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            stdout="output",
            stderr="",
            return_code=0,
        )
        assert result.success is True

    def test_success_property_false_status(self):
        """Test success property when status is not SUCCESS."""
        result = ToolResult(
            status=ToolStatus.FAILURE,
            stdout="output",
            stderr="",
            return_code=0,
        )
        assert result.success is False

    def test_success_property_false_return_code(self):
        """Test success property when return_code is non-zero."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            stdout="output",
            stderr="",
            return_code=1,
        )
        assert result.success is False

    def test_duration_default(self):
        """Test default duration is 0."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            stdout="",
            stderr="",
            return_code=0,
        )
        assert result.duration_seconds == 0.0


# ---------------------------------------------------------------------------
# Test: Base ToolProvider
# ---------------------------------------------------------------------------


class TestToolProviderBase:
    """Tests for base ToolProvider interface."""

    def test_default_display_name(self):
        """Test default display_name capitalizes name."""

        class TestProvider(ToolProvider):
            @property
            def name(self) -> str:
                return "testprovider"

            def is_available(self) -> bool:
                return True

            def execute(self, context, working_dir=None, timeout=600):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="",
                    stderr="",
                    return_code=0,
                )

            def build_command(self, context):
                return ["test"]

        provider = TestProvider()
        assert provider.display_name == "Testprovider"

    def test_get_config_key(self):
        """Test get_config_key returns tool.<name>."""

        class TestProvider(ToolProvider):
            @property
            def name(self) -> str:
                return "mytest"

            def is_available(self) -> bool:
                return True

            def execute(self, context, working_dir=None, timeout=600):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="",
                    stderr="",
                    return_code=0,
                )

            def build_command(self, context):
                return ["test"]

        provider = TestProvider()
        assert provider.get_config_key() == "tool.mytest"


# ---------------------------------------------------------------------------
# Test: Multi-Tool Scenarios
# ---------------------------------------------------------------------------


class TestMultiToolScenarios:
    """Test scenarios involving multiple tool providers."""

    def test_get_all_providers(self, reset_registry):
        """Test getting all available providers."""
        registry = ToolProviderRegistry.get_instance()

        providers = registry.get_multiple(registry.list_available())

        assert len(providers) >= 2
        names = [p.name for p in providers]
        assert "claude" in names
        assert "opencode" in names

    def test_provider_isolation(self, reset_registry):
        """Test that providers are isolated from each other."""
        registry = ToolProviderRegistry.get_instance()

        claude = registry.get("claude")
        opencode = registry.get("opencode")

        assert claude is not opencode
        assert claude.name != opencode.name
        assert claude.build_command("test") != opencode.build_command("test")

    def test_mixed_availability(self, reset_registry):
        """Test scenario where some providers are available and some aren't."""
        registry = ToolProviderRegistry.get_instance()

        with patch.object(ClaudeToolProvider, "is_available", return_value=True):
            with patch.object(OpenCodeToolProvider, "is_available", return_value=False):
                installed = registry.list_installed()

                assert "claude" in installed
                assert "opencode" not in installed


# ---------------------------------------------------------------------------
# Test: GenericToolProvider
# ---------------------------------------------------------------------------


class TestGenericToolProvider:
    """Tests for GenericToolProvider."""

    def test_name_from_config(self):
        """Test provider name is set from initialization."""
        provider = GenericToolProvider("mytool", {"display_name": "My Tool"})
        assert provider.name == "mytool"

    def test_display_name_from_config(self):
        """Test display name is read from config."""
        provider = GenericToolProvider("mytool", {"display_name": "My Custom Tool"})
        assert provider.display_name == "My Custom Tool"

    def test_input_method_from_config(self):
        """Test input method is read from config."""
        provider = GenericToolProvider("mytool", {"input_method": "argument"})
        assert provider.input_method == InputMethod.ARGUMENT

    def test_input_method_default(self):
        """Test input method defaults to stdin."""
        provider = GenericToolProvider("mytool", {})
        assert provider.input_method == InputMethod.STDIN

    def test_flags_from_config(self):
        """Test flags are read from config."""
        provider = GenericToolProvider("mytool", {"flags": ["--verbose", "--quiet"]})
        assert provider.default_flags == ["--verbose", "--quiet"]

    def test_timeout_from_config(self):
        """Test timeout is read from config."""
        provider = GenericToolProvider("mytool", {"timeout": 300})
        assert provider.timeout == 300

    def test_priority_from_config(self):
        """Test priority is read from config."""
        provider = GenericToolProvider("mytool", {"priority": 50})
        assert provider.priority == 50

    def test_is_available(self):
        """Test is_available checks executable."""
        provider = GenericToolProvider("mytool", {"executable": "mytool"})

        with patch("shutil.which", return_value="/usr/bin/mytool"):
            assert provider.is_available() is True

        with patch("shutil.which", return_value=None):
            assert provider.is_available() is False

    def test_build_command_stdin(self):
        """Test command building for stdin input."""
        provider = GenericToolProvider(
            "mytool",
            {
                "input_method": "stdin",
                "flags": ["--no-color"],
            },
        )

        cmd = provider.build_command("test prompt")
        assert cmd == ["mytool", "--no-color"]

    def test_build_command_argument(self):
        """Test command building for argument input."""
        provider = GenericToolProvider(
            "mytool",
            {
                "input_method": "argument",
                "flags": ["--prompt"],
            },
        )

        cmd = provider.build_command("test prompt")
        assert cmd == ["mytool", "--prompt", "test prompt"]

    def test_execute_success(self):
        """Test successful execution."""
        provider = GenericToolProvider("mytool", {"executable": "mytool"})

        with patch("shutil.which", return_value="/usr/bin/mytool"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="Success",
                    stderr="",
                )

                result = provider.execute("test")

                assert result.success is True
                assert result.stdout == "Success"


# ---------------------------------------------------------------------------
# Test: New Built-in Providers
# ---------------------------------------------------------------------------


class TestCursorToolProvider:
    """Tests for CursorToolProvider."""

    def test_name(self):
        """Test provider name."""
        provider = CursorToolProvider()
        assert provider.name == "cursor"

    def test_display_name(self):
        """Test provider display name."""
        provider = CursorToolProvider()
        assert provider.display_name == "Cursor"

    def test_input_method(self):
        """Test input method is stdin."""
        provider = CursorToolProvider()
        assert provider.input_method == InputMethod.STDIN

    def test_capabilities(self):
        """Test capabilities."""
        provider = CursorToolProvider()
        caps = provider.capabilities
        assert caps.supports_streaming is True
        assert caps.supports_vision is True


class TestGeminiToolProvider:
    """Tests for GeminiToolProvider."""

    def test_name(self):
        """Test provider name."""
        provider = GeminiToolProvider()
        assert provider.name == "gemini"

    def test_display_name(self):
        """Test provider display name."""
        provider = GeminiToolProvider()
        assert provider.display_name == "Gemini CLI"

    def test_input_method(self):
        """Test input method is argument."""
        provider = GeminiToolProvider()
        assert provider.input_method == InputMethod.ARGUMENT

    def test_large_context(self):
        """Test Gemini has large context window."""
        provider = GeminiToolProvider()
        caps = provider.capabilities
        assert caps.max_context_length == 1000000


class TestCodexToolProvider:
    """Tests for CodexToolProvider."""

    def test_name(self):
        """Test provider name."""
        provider = CodexToolProvider()
        assert provider.name == "codex"

    def test_display_name(self):
        """Test provider display name."""
        provider = CodexToolProvider()
        assert provider.display_name == "OpenAI Codex"

    def test_default_flags(self):
        """Test default flags include --quiet."""
        provider = CodexToolProvider()
        assert "--quiet" in provider.default_flags


# ---------------------------------------------------------------------------
# Test: Registry Configuration Features
# ---------------------------------------------------------------------------


class TestRegistryConfiguration:
    """Tests for registry configuration features."""

    def test_configure_provider(self, reset_registry):
        """Test configuring an existing provider."""
        registry = ToolProviderRegistry.get_instance()

        registry.configure("claude", {"timeout": 300, "flags": ["--fast"]})

        claude = registry.get("claude")
        assert claude.timeout == 300
        assert claude.default_flags == ["--fast"]

    def test_register_from_config(self, reset_registry):
        """Test registering a provider from config."""
        registry = ToolProviderRegistry.get_instance()

        registry.register_from_config(
            "newtool",
            {
                "executable": "newtool",
                "display_name": "New Tool",
                "input_method": "stdin",
                "flags": ["--ai"],
                "timeout": 120,
                "priority": 25,
            },
        )

        assert "newtool" in registry.list_available()

        provider = registry.get("newtool")
        assert provider is not None
        assert provider.name == "newtool"
        assert provider.display_name == "New Tool"
        assert provider.input_method == InputMethod.STDIN
        assert provider.timeout == 120
        assert provider.priority == 25

    def test_load_from_config(self, reset_registry):
        """Test loading multiple providers from config dict."""
        registry = ToolProviderRegistry.get_instance()

        tool_configs = {
            "claude": {"timeout": 300},  # Existing provider
            "customtool": {  # New generic provider
                "executable": "customtool",
                "input_method": "stdin",
            },
        }

        count = registry.load_from_config(tool_configs)

        assert count == 2
        assert registry.get("claude").timeout == 300
        assert "customtool" in registry.list_available()

    def test_get_by_priority(self, reset_registry):
        """Test getting providers sorted by priority."""
        registry = ToolProviderRegistry.get_instance()

        providers = registry.get_by_priority()

        # Claude has priority 1, should be first
        names = [p.name for p in providers if p.is_available()]
        if names:
            # Just verify sorting works (actual availability depends on system)
            priorities = [p.priority for p in providers]
            assert priorities == sorted(priorities)

    def test_get_info(self, reset_registry):
        """Test getting registry info."""
        registry = ToolProviderRegistry.get_instance()

        info = registry.get_info()

        assert "registered_count" in info
        assert "installed_count" in info
        assert "providers" in info
        assert info["registered_count"] >= 5  # claude, opencode, cursor, gemini, codex

    def test_all_builtin_providers_registered(self, reset_registry):
        """Test all built-in providers are registered."""
        registry = ToolProviderRegistry.get_instance()
        available = registry.list_available()

        assert "claude" in available
        assert "opencode" in available
        assert "cursor" in available
        assert "gemini" in available
        assert "codex" in available


# ---------------------------------------------------------------------------
# Test: Provider Capabilities
# ---------------------------------------------------------------------------


class TestProviderCapabilities:
    """Tests for provider capabilities."""

    def test_capabilities_dataclass(self):
        """Test ToolCapabilities dataclass."""
        caps = ToolCapabilities(
            supports_streaming=True,
            supports_vision=True,
            max_context_length=100000,
        )

        assert caps.supports_streaming is True
        assert caps.supports_vision is True
        assert caps.max_context_length == 100000
        assert caps.supports_conversation is False  # default

    def test_claude_capabilities(self):
        """Test Claude has correct capabilities."""
        provider = ClaudeToolProvider()
        caps = provider.capabilities

        assert caps.supports_streaming is True
        assert caps.supports_conversation is True
        assert caps.supports_system_prompt is True
        assert caps.supports_tools is True
        assert caps.supports_vision is True
        assert caps.priority == 1

    def test_provider_get_info(self):
        """Test provider info includes capabilities."""
        provider = ClaudeToolProvider()
        info = provider.get_info()

        assert "name" in info
        assert "display_name" in info
        assert "input_method" in info
        assert "capabilities" in info
        assert info["capabilities"]["streaming"] is True


# ---------------------------------------------------------------------------
# Test: Input Method Handling
# ---------------------------------------------------------------------------


class TestInputMethodHandling:
    """Tests for different input methods."""

    def test_input_method_enum(self):
        """Test InputMethod enum values."""
        assert InputMethod.ARGUMENT.value == "argument"
        assert InputMethod.STDIN.value == "stdin"
        assert InputMethod.FILE.value == "file"
        assert InputMethod.PIPE.value == "pipe"

    def test_claude_uses_argument(self):
        """Test Claude uses argument input."""
        provider = ClaudeToolProvider()
        assert provider.input_method == InputMethod.ARGUMENT

    def test_opencode_uses_stdin(self):
        """Test OpenCode uses stdin input."""
        provider = OpenCodeToolProvider()
        assert provider.input_method == InputMethod.STDIN

    def test_config_override_input_method(self):
        """Test input method can be overridden via config."""
        provider = ClaudeToolProvider({"input_method": "stdin"})
        assert provider.input_method == InputMethod.STDIN


# ---------------------------------------------------------------------------
# Test: OutputNormalizer
# ---------------------------------------------------------------------------


class TestOutputNormalizer:
    """Tests for OutputNormalizer utility class."""

    def test_strip_ansi_codes(self):
        """Test stripping ANSI escape codes."""
        text = "\x1b[32mGreen text\x1b[0m and \x1b[1;31mBold red\x1b[0m"
        result = OutputNormalizer.strip_ansi(text)
        assert result == "Green text and Bold red"

    def test_strip_ansi_preserves_plain_text(self):
        """Test that plain text is preserved."""
        text = "Plain text without any codes"
        result = OutputNormalizer.strip_ansi(text)
        assert result == text

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Line 1   \n\n\n\nLine 2  \n\nLine 3"
        result = OutputNormalizer.normalize_whitespace(text)
        assert result == "Line 1\n\nLine 2\n\nLine 3"

    def test_normalize_empty_string(self):
        """Test normalizing empty string."""
        result = OutputNormalizer.normalize("")
        assert result == ""

    def test_extract_code_blocks(self):
        """Test extracting code blocks from markdown."""
        text = """Some text
```python
def foo():
    pass
```
More text
```bash
echo hello
```
"""
        blocks = OutputNormalizer.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert "def foo()" in blocks[0][1]
        assert blocks[1][0] == "bash"

    def test_full_normalize_pipeline(self):
        """Test full normalization pipeline."""
        text = "\x1b[32m[INFO] Processing...\x1b[0m\n\n\n\nResult: success  "
        result = OutputNormalizer.normalize(text)
        assert "[INFO] Processing..." in result
        assert "Result: success" in result
        assert "\x1b[" not in result


# ---------------------------------------------------------------------------
# Test: ToolCapabilities.matches
# ---------------------------------------------------------------------------


class TestCapabilitiesMatching:
    """Tests for capability matching."""

    def test_matches_all_capabilities(self):
        """Test matching when all capabilities are met."""
        provider_caps = ToolCapabilities(
            supports_streaming=True,
            supports_vision=True,
            supports_tools=True,
            max_context_length=200000,
        )
        required = ToolCapabilities(
            supports_streaming=True,
            supports_vision=True,
        )
        assert provider_caps.matches(required) is True

    def test_matches_fails_on_missing_streaming(self):
        """Test matching fails when streaming is required but not supported."""
        provider_caps = ToolCapabilities(supports_streaming=False)
        required = ToolCapabilities(supports_streaming=True)
        assert provider_caps.matches(required) is False

    def test_matches_fails_on_insufficient_context(self):
        """Test matching fails when context is too small."""
        provider_caps = ToolCapabilities(max_context_length=50000)
        required = ToolCapabilities(max_context_length=100000)
        assert provider_caps.matches(required) is False

    def test_matches_succeeds_with_larger_context(self):
        """Test matching succeeds when context is larger."""
        provider_caps = ToolCapabilities(max_context_length=200000)
        required = ToolCapabilities(max_context_length=100000)
        assert provider_caps.matches(required) is True

    def test_matches_empty_requirements(self):
        """Test matching always succeeds with empty requirements."""
        provider_caps = ToolCapabilities()
        required = ToolCapabilities()
        assert provider_caps.matches(required) is True


# ---------------------------------------------------------------------------
# Test: CapabilityRouter
# ---------------------------------------------------------------------------


class TestCapabilityRouter:
    """Tests for capability-based routing."""

    def test_select_tools_with_matching_capabilities(self, reset_registry):
        """Test selecting tools that match required capabilities."""
        registry = ToolProviderRegistry.get_instance()
        providers = registry.get_multiple(registry.list_available())

        # Require vision support
        required = ToolCapabilities(supports_vision=True)

        with patch.object(ClaudeToolProvider, "is_available", return_value=True):
            with patch.object(OpenCodeToolProvider, "is_available", return_value=True):
                matching = CapabilityRouter.select_tools(providers, required)

                # Claude supports vision, OpenCode doesn't
                names = [p.name for p in matching]
                assert "claude" in names
                assert "opencode" not in names

    def test_select_best_returns_highest_priority(self, reset_registry):
        """Test selecting best tool returns highest priority."""
        registry = ToolProviderRegistry.get_instance()
        providers = registry.get_multiple(["claude", "opencode"])

        required = ToolCapabilities()  # No specific requirements

        with patch.object(ClaudeToolProvider, "is_available", return_value=True):
            with patch.object(OpenCodeToolProvider, "is_available", return_value=True):
                best = CapabilityRouter.select_best(providers, required)

                # Claude has priority 1, should be selected
                assert best is not None
                assert best.name == "claude"

    def test_select_tools_respects_max_tools(self, reset_registry):
        """Test max_tools limit is respected."""
        registry = ToolProviderRegistry.get_instance()
        providers = registry.get_multiple(registry.list_available())

        required = ToolCapabilities()

        with patch("shutil.which", return_value="/usr/bin/tool"):
            matching = CapabilityRouter.select_tools(providers, required, max_tools=2)
            assert len(matching) <= 2

    def test_group_by_capability(self, reset_registry):
        """Test grouping providers by capability."""
        registry = ToolProviderRegistry.get_instance()
        providers = registry.get_multiple(["claude", "opencode", "gemini"])

        groups = CapabilityRouter.group_by_capability(providers)

        assert "streaming" in groups
        assert "vision" in groups
        assert "large_context" in groups

        # Claude supports streaming
        streaming_names = [p.name for p in groups["streaming"]]
        assert "claude" in streaming_names

    def test_select_best_returns_none_when_no_match(self):
        """Test select_best returns None when no providers match."""
        providers: list[ToolProvider] = []  # Empty list
        required = ToolCapabilities(supports_vision=True)

        best = CapabilityRouter.select_best(providers, required)
        assert best is None


# ---------------------------------------------------------------------------
# Test: ToolAdapter Protocol
# ---------------------------------------------------------------------------


class TestToolAdapterProtocol:
    """Tests for ToolAdapter protocol."""

    def test_claude_implements_protocol(self):
        """Test ClaudeToolProvider implements ToolAdapter protocol."""
        provider = ClaudeToolProvider()
        assert isinstance(provider, ToolAdapter)

    def test_opencode_implements_protocol(self):
        """Test OpenCodeToolProvider implements ToolAdapter protocol."""
        provider = OpenCodeToolProvider()
        assert isinstance(provider, ToolAdapter)

    def test_generic_implements_protocol(self):
        """Test GenericToolProvider implements ToolAdapter protocol."""
        provider = GenericToolProvider("test", {})
        assert isinstance(provider, ToolAdapter)


# ---------------------------------------------------------------------------
# Test: OutputFormat
# ---------------------------------------------------------------------------


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.RAW.value == "raw"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.STREAMING.value == "streaming"

    def test_provider_output_format_default(self):
        """Test default output format is RAW."""
        provider = ClaudeToolProvider()
        assert provider.output_format == OutputFormat.RAW


# ---------------------------------------------------------------------------
# Test: Async Execute
# ---------------------------------------------------------------------------


class TestAsyncExecute:
    """Tests for async execute method."""

    @pytest.mark.asyncio
    async def test_execute_async_wraps_sync(self, mock_claude_available):
        """Test async execute wraps sync execute."""
        provider = ClaudeToolProvider()

        with patch.object(provider, "execute") as mock_execute:
            mock_execute.return_value = ToolResult(
                status=ToolStatus.SUCCESS,
                stdout="Success",
                stderr="",
                return_code=0,
            )

            result = await provider.execute_async("Test prompt")

            assert result.success is True
            assert result.stdout == "Success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
