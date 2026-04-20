---
phase: 14-foundation
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/config_contract/__init__.py
  - apps/workflow_engine/config.py
  - packages/config_contract/spa_manifest_schema.json
  - packages/site-template/public/spa/spa_manifest.json
  - packages/site-template/public/spa/shell.html
  - apps/workflow_engine/site_bootstrap.py
  - .gitignore
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Seven files reviewed covering the config contract, workflow engine config loader, SPA manifest schema, site template shell, site bootstrap, and gitignore. The code is generally well-structured with clear separation of concerns. Two critical issues were found: path traversal in the SPA shell (user-controlled hash fed directly into iframe src) and malformed JSON output in site_bootstrap (f-string JSON construction without escaping). Four warnings cover a duplicate dataclass field bug that causes silent data loss, dead code in load_config, broken gitignore patterns (double runtime/ prefix), and credential fields with no repr suppression. Two info items cover a hardcoded localhost endpoint in the template and a minor duplicate-slug false-positive in validate_config.

## Critical Issues

### CR-01: Path Traversal via User-Controlled iframe src

**File:** `packages/site-template/public/spa/shell.html:107`

**Issue:** `moduleId` in the `navigate()` function is sourced from `window.location.hash.slice(1)`, which is fully user-controlled. It is set directly as `frame.src` without any validation or sanitization. A URL like `#../../etc/passwd` would resolve to `../../etc/passwd/index.html` relative to the current page. While browsers restrict cross-origin loads, this can load arbitrary local files within the same origin (e.g. `#../other-site/secret`) or cause unexpected behavior. The manifest-sourced path during `init()` is safe, but the `hashchange` handler bypasses that constraint entirely.

**Fix:**
```javascript
// Allowlist approach: only navigate to module IDs present in the manifest.
var _validModuleIds = new Set();

function buildNav(modules) {
  _validModuleIds = new Set(modules.map(function(m) { return m.module_id; }));
  // ... rest of existing buildNav logic
}

function navigate(moduleId) {
  // Reject any moduleId not in the manifest
  if (moduleId && !_validModuleIds.has(moduleId)) return;
  // ... rest of existing navigate logic
}
```

---

### CR-02: Malformed JSON from f-string Construction in site_bootstrap.py

**File:** `apps/workflow_engine/site_bootstrap.py:31`

**Issue:** `.inbox.json` is written using a manually constructed f-string. If `inbox.slug`, `inbox.address`, or `inbox.site_name` contains a double-quote, backslash, or newline, the output will be invalid JSON, causing a parse error in any downstream consumer that reads `.inbox.json`. For example, `inbox.address = 'user+"test"@example.com'` would produce a broken JSON file.

**Fix:**
```python
(target / ".inbox.json").write_text(
    json.dumps({
        "slug": inbox.slug,
        "address": inbox.address,
        "site_name": inbox.site_name or inbox.slug,
    }) + "\n"
)
```
`json` is already imported at the top of the file.

---

## Warnings

### WR-01: Duplicate Dataclass Fields in Config — Silent Data Loss

**File:** `packages/config_contract/__init__.py:178-185`

**Issue:** `repo_root`, `sites_dir`, `template_dir`, and `state_dir` are each defined twice in the `Config` dataclass (lines 178-181 and 182-185). In Python, the second definition silently replaces the first in the class namespace. Both have the same default values so no functional difference exists in the dataclass definition itself — but this causes the type checker to lose track of the fields (hence the `type: ignore[attr-defined]` in `config.py:49-51`). It also indicates that any future divergence between the two sets of defaults would go undetected. The duplicate definitions should be removed.

**Fix:** Remove lines 182-185 (the second set of identical field definitions):
```python
# Remove these four duplicate lines:
repo_root: Path = Path(".")
sites_dir: Path = Path("runtime/sites")
template_dir: Path = Path("packages/site-template")
state_dir: Path = Path("runtime/state")
```

Once removed, the `type: ignore` comments in `config.py:49-51` can also be removed.

---

### WR-02: Dead Code — `generic_ssh` Lookup in load_config

**File:** `packages/config_contract/__init__.py:282`

**Issue:** In `load_config`, the fallback `raw.get("generic_ssh")` on line 282 can never be reached. `_normalize_raw` (called on line 271) already pops `generic_ssh` from the dict and renames it to `ssh_sftp` via `raw["ssh_sftp"] = raw.pop("generic_ssh")`. By the time `load_config` executes the `SshSftpConfig(...)` line, `raw["generic_ssh"]` is always absent.

**Fix:**
```python
ssh_sftp=SshSftpConfig(**(raw.get("ssh_sftp") or {})),
```

---

### WR-03: Broken .gitignore Patterns — Double `runtime/` Prefix

**File:** `.gitignore:10-12`

**Issue:** The patterns on lines 10-12 read:
```
runtime/runtime/sites/*/node_modules/
runtime/runtime/sites/*/dist/
runtime/runtime/sites/*/.astro/
```
The actual directory structure is `runtime/sites/...`, not `runtime/runtime/sites/...`. These patterns will never match anything, leaving `runtime/sites/*/node_modules/`, `runtime/sites/*/dist/`, and `runtime/sites/*/.astro/` unignored and potentially committed to the repository.

**Fix:**
```gitignore
runtime/sites/*/node_modules/
runtime/sites/*/dist/
runtime/sites/*/.astro/
```

---

### WR-04: Credential Fields Without repr=False — Accidental Secret Logging

**File:** `packages/config_contract/__init__.py:84-85, 93-95, 118-120, 130-132, 139`

**Issue:** `ImapConfig.password`, `SmtpConfig.password`, `SiteGroundConfig.password`, `SiteGroundConfig.key_passphrase`, `SshSftpConfig.password`, `SshSftpConfig.key_passphrase`, and `VercelConfig.api_token` are all plain `str` dataclass fields. The default `repr=True` means `repr(cfg.imap)` (or any log statement that includes these objects) will emit passwords and tokens in plaintext. This is a common accidental secret exposure vector.

**Fix:** Use `field(default='', repr=False)` for all credential fields:
```python
from dataclasses import dataclass, field

@dataclass
class ImapConfig:
    host: str
    port: int = 993
    user: str = ""
    password: str = field(default="", repr=False)
    folder: str = "INBOX"
    use_ssl: bool = True
```
Apply the same pattern to `SmtpConfig.password`, `SiteGroundConfig.password`, `SiteGroundConfig.key_passphrase`, `SshSftpConfig.password`, `SshSftpConfig.key_passphrase`, and `VercelConfig.api_token`.

---

## Info

### IN-01: Hardcoded localhost Endpoint in SPA Shell Template

**File:** `packages/site-template/public/spa/shell.html:21`

**Issue:** The LM Studio endpoint is hardcoded as `'http://localhost:1234/v1/chat/completions'` directly in the template. This is a template file that gets copied per-site by `site_bootstrap.py`. There is no mechanism for a site to override this value without editing the deployed HTML file directly. If the LM Studio port or host changes, every deployed site's HTML file must be manually updated. This is a development-time constant baked into a distributed artifact.

**Suggestion:** Consider reading the endpoint from a config JSON file fetched at startup (e.g. alongside `spa_manifest.json`), or injecting it as a template variable during the bootstrap copy step.

---

### IN-02: Spurious Duplicate-Slug Error for Empty Slugs in validate_config

**File:** `packages/config_contract/__init__.py:229`

**Issue:** When multiple inboxes have a missing `slug` field (i.e. `slug = ""`), the empty string is added to the `slugs` set. The second inbox with a missing slug will trigger both "missing 'slug'" and "duplicate slug ''" errors. The duplicate-slug error is spurious and confusing — it implies a slug value exists when it doesn't.

**Suggestion:** Skip the duplicate-slug check when `slug` is empty:
```python
slug = ib.get("slug", "")
if slug and slug in slugs:
    errors.append(f"Inbox {i}: duplicate slug '{slug}'")
if slug:
    slugs.add(slug)
```

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
