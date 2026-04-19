"""Provider registry — resolves provider by name and enforces capability checks."""
from __future__ import annotations

from .base import DeployProvider as DeployProviderProtocol
from .siteground import SiteGroundProvider

# ── Provider Registry ────────────────────────────────────────────────────────

_PROVIDERS: dict[str, DeployProviderProtocol] = {
    "siteground": SiteGroundProvider(),
}


def get_provider(name: str) -> DeployProviderProtocol:
    """Get a provider by name. Raises ValueError if unknown."""
    if name not in _PROVIDERS:
        available = sorted(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown deploy provider: {name!r}. "
            f"Available providers: {available}. "
            f"To implement a new provider, create a class in providers/ "
            f"and register it in the _PROVIDERS dict."
        )
    return _PROVIDERS[name]


def register_provider(name: str, provider: DeployProviderProtocol) -> None:
    """Register a new provider at runtime."""
    _PROVIDERS[name] = provider


def list_providers() -> list[str]:
    """List all registered provider names."""
    return sorted(_PROVIDERS.keys())


def validate_provider_config(name: str, config: dict) -> list[str]:
    """Validate config for a specific provider. Returns list of errors."""
    provider = get_provider(name)
    return provider.validate_config(config)
