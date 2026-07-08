"""Platform adapter discovery and registration."""

from __future__ import annotations

import importlib

from xpersonas.core.exceptions import AdapterNotAvailable
from xpersonas.platforms.base import PlatformAdapter

_registry: dict[str, type[PlatformAdapter]] = {}

# Known adapter modules to auto-import
_ADAPTER_MODULES = [
    "xpersonas.platforms.x_twitter.adapter",
]


def _ensure_discovered() -> None:
    """Import adapter modules to trigger @register_adapter decorators."""
    if _registry:
        return
    for mod_path in _ADAPTER_MODULES:
        try:
            importlib.import_module(mod_path)
        except ImportError:
            pass


def register_adapter(cls: type[PlatformAdapter]) -> type[PlatformAdapter]:
    """Decorator to register a platform adapter class."""
    instance = cls.__new__(cls)
    _registry[instance.name] = cls
    return cls


def get_adapter(platform: str) -> PlatformAdapter:
    """Get a new adapter instance for the given platform."""
    _ensure_discovered()
    if platform not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise AdapterNotAvailable(
            f"Platform '{platform}' not registered. Available: {available}"
        )
    return _registry[platform]()


def list_platforms() -> list[str]:
    """List all registered platform names."""
    _ensure_discovered()
    return sorted(_registry.keys())
