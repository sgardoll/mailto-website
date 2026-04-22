"""Tests for apps.workflow_engine.integrate — RED phase.

These tests cover:
- INT-01: atomic write of module HTML
- INT-02: commit of module + manifest
- INT-03: manifest version = 7-char short SHA
- INT-04: startup_assert_gitignore detects public/spa/ exclusions
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import pytest

from apps.workflow_engine import integrate
from apps.workflow_engine.integrate import IntegrateFailed, startup_assert_gitignore
from apps.workflow_engine.schemas.envelope import MechanicSpec
from packages.config_contract import MechanicKind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(module_id: str = "calc_1", kind: str = "calculator", title: str = "Test Calc") -> MechanicSpec:
    return MechanicSpec.model_validate({
        "kind": kind,
        "title": title,
        "intent": "test intent",
        "inputs": ["x"],
        "outputs": ["y"],
        "content": {
            "kind": "calculator",
            "formula_description": "x + 1",
            "variables": [{"name": "x", "unit": "units", "default": 1}],
            "unit": "units",
        },
        "module_id": module_id,
    })


def _make_html_b64(html: str = "<!doctype html><html><body>x</body></html>") -> str:
    return base64.b64encode(html.encode()).decode()


@pytest.fixture
def site_dir(tmp_path) -> Path:
    d = tmp_path / "site"
    (d / "public" / "spa").mkdir(parents=True)
    # seed empty manifest
    (d / "public" / "spa" / "spa_manifest.json").write_text(
        json.dumps({"schema_version": "1", "modules": []})
    )
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_integrate_writes_module_atomically(site_dir):
    """INT-01: integrate() writes public/spa/<module_id>/index.html atomically."""
    spec = _make_spec(module_id="calc_1")
    html = "<!doctype html><html><body>hello</body></html>"
    html_b64 = _make_html_b64(html)

    integrate.integrate(spec, html_b64, site_dir)

    module_path = site_dir / "public" / "spa" / "calc_1" / "index.html"
    assert module_path.exists(), "module HTML file should exist after integrate()"
    assert module_path.read_bytes() == html.encode(), "file content should match decoded HTML"


def test_integrate_upserts_manifest_with_new_module(site_dir):
    """INT-02/INT-03: manifest has one entry with module_id/kind/title/version (7-char SHA)."""
    spec = _make_spec(module_id="calc_1", kind="calculator", title="Test Calc")
    html_b64 = _make_html_b64()

    sha = integrate.integrate(spec, html_b64, site_dir)

    manifest_path = site_dir / "public" / "spa" / "spa_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    modules = manifest["modules"]
    assert len(modules) == 1, "manifest should have exactly one entry"
    entry = modules[0]
    assert entry["module_id"] == "calc_1"
    assert entry["kind"] == "calculator"
    assert entry["title"] == "Test Calc"
    assert entry["version"] == sha, "manifest version should equal returned SHA"
    assert re.match(r"^[0-9a-f]{7}$", entry["version"]), "version should be 7-char lowercase hex"


def test_integrate_upserts_manifest_updates_existing_module(site_dir):
    """INT-02: pre-seed manifest with same module_id; after call, entry is UPDATED (still length 1)."""
    spec = _make_spec(module_id="calc_1")
    # Pre-seed manifest with old entry
    manifest_path = site_dir / "public" / "spa" / "spa_manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1",
        "modules": [{"module_id": "calc_1", "kind": "calculator", "title": "Old Title", "version": "0000000"}],
    }))

    sha = integrate.integrate(spec, _make_html_b64(), site_dir)

    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["modules"]) == 1, "should not duplicate — must UPDATE existing entry"
    assert manifest["modules"][0]["version"] != "0000000", "version should be updated to new SHA"
    assert manifest["modules"][0]["version"] == sha


def test_integrate_initializes_git_repo_on_first_run(site_dir):
    """INT-02: site_dir with no .git gets git init on first call; git log shows one commit."""
    assert not (site_dir / ".git").exists(), "test pre-condition: no .git directory"

    integrate.integrate(_make_spec(), _make_html_b64(), site_dir)

    assert (site_dir / ".git").exists(), ".git directory should exist after integrate()"
    import subprocess
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=site_dir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) >= 1, "git log should show at least one commit"


def test_integrate_raises_when_nothing_committed(site_dir):
    """INT-02: second call with identical input raises IntegrateFailed (nothing to commit)."""
    spec = _make_spec()
    html_b64 = _make_html_b64()

    # First call should succeed
    integrate.integrate(spec, html_b64, site_dir)

    # Second call with identical input: module file unchanged → commit_and_push returns None
    with pytest.raises(IntegrateFailed):
        integrate.integrate(spec, html_b64, site_dir)


def test_integrate_returns_short_sha(site_dir):
    """INT-03: returned string is exactly 7 chars matching ^[0-9a-f]{7}$."""
    sha = integrate.integrate(_make_spec(), _make_html_b64(), site_dir)

    assert len(sha) == 7, f"SHA should be 7 chars, got {len(sha)}"
    assert re.match(r"^[0-9a-f]{7}$", sha), f"SHA should be lowercase hex, got {sha!r}"


def test_startup_assert_gitignore_noop_when_missing(tmp_path):
    """INT-04: no .gitignore in site_dir → function returns None, no raise."""
    result = startup_assert_gitignore(tmp_path)
    assert result is None


def test_startup_assert_gitignore_raises_on_public_spa_exclusion(tmp_path):
    """INT-04: .gitignore contains 'public/spa/' → raises RuntimeError."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\npublic/spa/\n")

    with pytest.raises(RuntimeError, match="public/spa"):
        startup_assert_gitignore(tmp_path)


def test_startup_assert_gitignore_ignores_negation(tmp_path):
    """INT-04: .gitignore contains '!public/spa/' → no raise (negation = include, not exclude)."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("!public/spa/\n")

    # Should not raise
    startup_assert_gitignore(tmp_path)


def test_startup_assert_gitignore_raises_on_public_root(tmp_path):
    """INT-04: .gitignore contains 'public/' or 'public' → raises RuntimeError."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("public/\n")

    with pytest.raises(RuntimeError):
        startup_assert_gitignore(tmp_path)
