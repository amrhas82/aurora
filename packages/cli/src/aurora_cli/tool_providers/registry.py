"""Tool provider registry with factory pattern and auto-discovery."""

import importlib
import logging
import pkgutil
from typing import Any

from aurora_cli.tool_providers.base import ToolProvider


logger = logging.getLogger(__name__)


class ToolProviderRegistry:
    """Registry for tool providers with factory pattern.

    Supports dynamic registration and instantiation of tool providers.
    Built-in providers (claude, opencode) are registered by default.
    Can auto-discover providers from packages and configuration.

    Usage:
        # Get singleton instance
        registry = ToolProviderRegistry.get_instance()

        # Get a provider by name
        claude = registry.get("claude")

        # Get multiple providers
        providers = registry.get_multiple(["claude", "opencode"])

        # Register custom provider
        registry.register(MyCustomProvider)

        # Configure a provider
        registry.configure("claude", {"timeout": 300, "flags": ["--print"]})

        # Create provider from config (dynamic/generic)
        registry.register_from_config("cursor", {
            "executable": "cursor",
            "input_method": "stdin",
            "flags": ["--no-tty"],
        })
    """

    _instance: "ToolProviderRegistry | None" = None
    _providers: dict[str, type[ToolProvider]]

    def __init__(self) -> None:
        """Initialize registry with empty provider map."""
        self._providers: dict[str, type[ToolProvider]] = {}
        self._instances: dict[str, ToolProvider] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self._generic_providers: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "ToolProviderRegistry":
        """Get or create the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_builtin_providers()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _register_builtin_providers(self) -> None:
        """Register built-in tool providers."""
        from aurora_cli.tool_providers.claude import ClaudeToolProvider
        from aurora_cli.tool_providers.codex import CodexToolProvider
        from aurora_cli.tool_providers.cursor import CursorToolProvider
        from aurora_cli.tool_providers.gemini import GeminiToolProvider
        from aurora_cli.tool_providers.opencode import OpenCodeToolProvider

        self.register(ClaudeToolProvider)
        self.register(OpenCodeToolProvider)
        self.register(CursorToolProvider)
        self.register(GeminiToolProvider)
        self.register(CodexToolProvider)

    def register(self, provider_class: type[ToolProvider]) -> None:
        """Register a tool provider class.

        Args:
            provider_class: The provider class to register

        """
        # Create temporary instance to get name
        instance = provider_class()
        self._providers[instance.name] = provider_class
        logger.debug(f"Registered tool provider: {instance.name}")

    def register_from_config(self, name: str, config: dict[str, Any]) -> None:
        """Register a generic tool provider from configuration.

        This allows defining new tools without writing provider classes.

        Args:
            name: Unique name for the tool
            config: Configuration dict with:
                - executable: CLI binary name (defaults to name)
                - display_name: Human-readable name
                - input_method: "stdin", "argument", "file", "pipe"
                - flags: List of default command-line flags
                - timeout: Default timeout in seconds
                - priority: Tool priority (lower = higher)

        Example:
            registry.register_from_config("cursor", {
                "executable": "cursor",
                "display_name": "Cursor",
                "input_method": "stdin",
                "flags": ["--no-tty"],
                "timeout": 600,
            })

        """
        self._generic_providers[name] = config
        logger.debug(f"Registered generic tool provider: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister a tool provider by name.

        Args:
            name: The provider name to unregister

        Returns:
            True if provider was unregistered, False if not found

        """
        removed = False
        if name in self._providers:
            del self._providers[name]
            removed = True
        if name in self._generic_providers:
            del self._generic_providers[name]
            removed = True
        self._instances.pop(name, None)
        self._configs.pop(name, None)
        return removed

    def configure(self, name: str, config: dict[str, Any]) -> None:
        """Configure a provider with runtime settings.

        Args:
            name: Provider name
            config: Configuration dict (timeout, flags, input_method, priority)

        """
        self._configs[name] = config
        # Update existing instance if cached
        if name in self._instances:
            self._instances[name].configure(config)
        logger.debug(f"Configured tool provider {name}: {config}")

    def get(self, name: str) -> ToolProvider | None:
        """Get a tool provider instance by name.

        Args:
            name: The provider name

        Returns:
            Provider instance or None if not found

        """
        # Return cached instance if exists
        if name in self._instances:
            return self._instances[name]

        # Check registered class providers
        if name in self._providers:
            config = self._configs.get(name, {})
            self._instances[name] = self._providers[name](config)
            return self._instances[name]

        # Check generic/config-based providers
        if name in self._generic_providers:
            provider = self._create_generic_provider(name)
            self._instances[name] = provider
            return provider

        return None

    def _create_generic_provider(self, name: str) -> ToolProvider:
        """Create a generic tool provider from configuration."""
        from aurora_cli.tool_providers.generic import GenericToolProvider

        config = self._generic_providers[name].copy()
        # Merge runtime config if exists
        if name in self._configs:
            config.update(self._configs[name])
        return GenericToolProvider(name, config)

    def get_multiple(self, names: list[str]) -> list[ToolProvider]:
        """Get multiple tool provider instances by name.

        Args:
            names: List of provider names

        Returns:
            List of provider instances (skips unknown names)

        """
        providers = []
        for name in names:
            provider = self.get(name)
            if provider is not None:
                providers.append(provider)
        return providers

    def get_by_priority(self) -> list[ToolProvider]:
        """Get all available providers sorted by priority.

        Returns:
            List of provider instances sorted by priority (lowest first)

        """
        providers = []
        for name in self.list_available():
            provider = self.get(name)
            if provider and provider.is_available():
                providers.append(provider)
        return sorted(providers, key=lambda p: p.priority)

    def list_available(self) -> list[str]:
        """List all registered provider names."""
        names = set(self._providers.keys())
        names.update(self._generic_providers.keys())
        return list(names)

    def list_installed(self) -> list[str]:
        """List provider names that are available in PATH."""
        installed = []
        for name in self.list_available():
            provider = self.get(name)
            if provider and provider.is_available():
                installed.append(name)
        return installed

    def create(self, name: str, config: dict[str, Any] | None = None) -> ToolProvider:
        """Factory method to create a new provider instance.

        Unlike get(), this always creates a new instance.

        Args:
            name: The provider name
            config: Optional configuration override

        Returns:
            New provider instance

        Raises:
            KeyError: If provider name is not registered

        """
        effective_config = self._configs.get(name, {}).copy()
        if config:
            effective_config.update(config)

        if name in self._providers:
            return self._providers[name](effective_config)

        if name in self._generic_providers:
            from aurora_cli.tool_providers.generic import GenericToolProvider

            generic_config = self._generic_providers[name].copy()
            generic_config.update(effective_config)
            return GenericToolProvider(name, generic_config)

        raise KeyError(f"Unknown tool provider: {name}")

    def discover_providers(self, package_path: str | None = None) -> int:
        """Auto-discover and register tool providers from a package.

        Scans for classes that inherit from ToolProvider.

        Args:
            package_path: Package path to scan (default: aurora_cli.tool_providers)

        Returns:
            Number of providers discovered and registered

        """
        if package_path is None:
            package_path = "aurora_cli.tool_providers"

        count = 0
        try:
            package = importlib.import_module(package_path)
            if not hasattr(package, "__path__"):
                return 0

            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                if modname.startswith("_") or modname in ("base", "registry", "generic"):
                    continue

                try:
                    module = importlib.import_module(f"{package_path}.{modname}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, ToolProvider)
                            and attr is not ToolProvider
                        ):
                            # Check if already registered
                            temp_instance = attr()
                            if temp_instance.name not in self._providers:
                                self.register(attr)
                                count += 1
                except Exception as e:
                    logger.warning(f"Error loading provider from {modname}: {e}")

        except Exception as e:
            logger.warning(f"Error discovering providers: {e}")

        return count

    def load_from_config(self, tool_configs: dict[str, dict[str, Any]]) -> int:
        """Load tool configurations from config file.

        Args:
            tool_configs: Dict of tool name -> config from Config.headless_tool_configs

        Returns:
            Number of providers configured

        """
        count = 0
        for name, config in tool_configs.items():
            # If it's a known provider, just configure it
            if name in self._providers:
                self.configure(name, config)
                count += 1
            else:
                # Register as generic provider
                self.register_from_config(name, config)
                count += 1

        return count

    def get_info(self) -> dict[str, Any]:
        """Get registry information for display/debugging."""
        providers_info = {}
        for name in self.list_available():
            provider = self.get(name)
            if provider:
                providers_info[name] = provider.get_info()

        return {
            "registered_count": len(self.list_available()),
            "installed_count": len(self.list_installed()),
            "providers": providers_info,
        }
