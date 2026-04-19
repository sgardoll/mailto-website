"""Deploy provider system.

Usage:
    from apps.workflow_engine.providers import get_provider, list_providers

    provider = get_provider("vercel")
    result = provider.deploy(build_result, config)
"""
from .base import BuildResult, DeployResult, DeployProvider
from .registry import get_provider, list_providers, register_provider, validate_provider_config
from .siteground import SiteGroundProvider
from .vercel import VercelProvider

__all__ = [
    "BuildResult",
    "DeployResult",
    "DeployProvider",
    "SiteGroundProvider",
    "VercelProvider",
    "get_provider",
    "list_providers",
    "register_provider",
    "validate_provider_config",
]
