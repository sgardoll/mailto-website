"""Deploy provider protocol — the contract all providers must implement."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class DeployResult:
    """Outcome of a single deploy operation."""
    slug: str
    provider: str
    target: str
    url: str
    ok: bool
    error: str | None = None


@runtime_checkable
class DeployProvider(Protocol):
    """Protocol for deploy providers.

    Every provider (SiteGround, Vercel, Netlify, etc.) must implement
    these four methods. The workflow engine calls them in order:
    bootstrap() → build() → deploy() → report()
    """

    @property
    def name(self) -> str:
        """Provider identifier (e.g. 'siteground', 'vercel')."""
        ...

    def build(self, site_dir: Path, site_url: str, site_name: str) -> "BuildResult":
        """Install deps (npm install) and build the Astro site.

        Returns a BuildResult with paths to the built dist directory.
        Raises BuildFailed on npm/build errors.
        """
        ...

    def deploy(self, build_result: "BuildResult", config: dict) -> DeployResult:
        """Deploy the built dist to the provider's target.

        config is the provider-specific section from config.yaml
        (e.g. siteground block, vercel block).
        Raises DeployFailed on deploy errors.
        """
        ...

    def validate_config(self, config: dict) -> list[str]:
        """Return list of error strings for missing/invalid config.
        Empty list means valid.
        """
        ...


@dataclass
class BuildResult:
    """Output of a successful build."""
    site_dir: Path
    dist_dir: Path
