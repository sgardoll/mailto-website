---
phase: 14
slug: foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-20
---

# Phase 14 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| config.yaml → load_config() | YAML-supplied strings enter InboxConfig including pipeline_version and slug | Operator-controlled strings (trusted) |
| browser → shell.html | Static HTML loaded by browser; no server-side processing | None at Phase 14 |
| shell.html → spa_manifest.json | Same-origin fetch of JSON; integrity owned by Phase 18 | Module metadata (non-sensitive) |
| shell.html → iframe (module) | Untrusted generated HTML runs inside sandboxed iframe | window.parent.STATE / window.parent.AI via postMessage-safe parent reference |
| ensure_site() → filesystem | Python writes files to slug-derived path; slug from config.yaml | Per-inbox profile JSON (user state) |
| git commit → profile.json | Writes to runtime/state/<slug>/ must not enter commit history | User state (excluded by gitignore) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-14-01-01 | Tampering | InboxConfig.pipeline_version value | accept | Phase 14 treats field as free-form string; no action taken on value. Phase 18 is the routing gate; unknown values simply fail to match any route. | closed |
| T-14-01-02 | Tampering | MechanicKind enum comparison | mitigate | str-based Enum (MechanicKind(str, Enum)) prevents integer-index misuse. Downstream code must compare by value or enum member, never by ordinal. Verified: `MechanicKind(str, Enum)` class present in config_contract. | closed |
| T-14-01-03 | Information Disclosure | Secrets in enum values | accept | Enum values are fixed source literals; no user input flows to enum definition. Code review gates. | closed |
| T-14-02-01 | Tampering | Generated module HTML in iframe | mitigate | iframe `sandbox="allow-scripts"` only — no `allow-same-origin`, `allow-top-navigation`, `allow-forms`. Module cannot read parent DOM or cookies. Verified: Playwright confirmed sandbox="allow-scripts", allow-same-origin absent. | closed |
| T-14-02-02 | Tampering | Nav item module_id rendered as HTML | mitigate | buildNav() constructs links via createElement + textContent + dataset; outerHTML serialised after safe assignment. No direct innerHTML injection path. Verified: innerHTML absent from shell.html routing logic. | closed |
| T-14-02-03 | Information Disclosure | localStorage visible to same-origin iframes | accept | Phase 14 iframe sandbox excludes same-origin; modules cannot read localStorage directly. Modules must funnel reads/writes through window.parent.STATE. Accepted by design (RESEARCH Pitfall 5). | closed |
| T-14-02-04 | Information Disclosure | window.AI() endpoint hardcoded to localhost | accept | Localhost-only by design for Phase 14. HTTPS-deployed SPAs get proxied in Phase 18 (SPA-05). Attacker reaching window.AI in the shell's own context already has full page access. | closed |
| T-14-02-05 | Denial of Service | spa_manifest.json fetch failure | mitigate | init() catches fetch failure and renders error copy ("Could not load spa_manifest.json...") — shell stays navigable. Verified: error copy present in shell.html. | closed |
| T-14-02-06 | Elevation of Privilege | innerHTML usage in shell body | mitigate | Shell uses textContent for all user-variable data (module_id). insertAdjacentHTML used only for nav anchors whose inner text was set via textContent before outerHTML capture. Verified: no innerHTML in shell.html. | closed |
| T-14-02-CR01 | Tampering | Path traversal via user-controlled hash → iframe src | mitigate | **Additional threat found in code review (CR-01).** navigate() now validates moduleId against `_validModuleIds` Set populated by buildNav() from manifest. Any hash value not present in the manifest is rejected — iframe src is not updated. Verified: Playwright confirmed `#../../etc/passwd` hash blocked. | closed |
| T-14-03-01 | Tampering | inbox.slug used in filesystem path construction | accept | InboxConfig.__post_init__ requires non-empty slug. Slug is operator-supplied via config.yaml (not user-web input). Flagged for Phase 15 if slug gains auto-provisioning from untrusted inputs. | closed |
| T-14-03-02 | Information Disclosure | profile.json committed to git | mitigate | Three layers: `runtime/state/**/profile.json` explicit rule + `/runtime` umbrella rule + structural separation (runtime/state/ vs runtime/sites/). Verified: `git check-ignore` confirms match at .gitignore:35. | closed |
| T-14-03-03 | Repudiation | Silent profile clobbering | mitigate | `if not profile_path.exists():` guard prevents overwrites; log.info emitted on write so re-runs are observable. Verified: idempotency test passed (state preserved across force=True re-bootstrap). | closed |
| T-14-03-04 | Denial of Service | STATE_DIR not writable | accept | OS-level PermissionError from Path.mkdir / write_text is same class as existing .inbox.json failure. No new attack surface introduced in Phase 14. | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-14-01 | T-14-01-01 | pipeline_version is free-form in Phase 14; Phase 18 owns routing logic. Unknown values fail silently — no code path acts on the value in Phase 14. | Claude (gsd-security-auditor) | 2026-04-20 |
| AR-14-02 | T-14-01-03 | Enum values are fixed source literals; no user input path to enum definition. Code review gate sufficient. | Claude (gsd-security-auditor) | 2026-04-20 |
| AR-14-03 | T-14-02-03 | localStorage inaccessible to sandboxed iframes by design (RESEARCH Pitfall 5). Modules route state through window.parent.STATE. Accepted as architectural intent. | Claude (gsd-security-auditor) | 2026-04-20 |
| AR-14-04 | T-14-02-04 | localhost endpoint for Phase 14 by design. Phase 18 adds proxy routing for deployed SPAs. Risk is scoped to development environment. | Claude (gsd-security-auditor) | 2026-04-20 |
| AR-14-05 | T-14-03-01 | Slug is operator-controlled config.yaml input (trusted). Flagged for Phase 15 if untrusted provisioning is added. | Claude (gsd-security-auditor) | 2026-04-20 |
| AR-14-06 | T-14-03-04 | PermissionError is same failure class as existing .inbox.json write. No escalation path; no new surface. | Claude (gsd-security-auditor) | 2026-04-20 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-20 | 14 | 14 | 0 | Claude (gsd-security-auditor via /gsd-secure-phase) |

**Notable:** CR-01 (hash-based path traversal) was discovered during code review and fixed before this security audit. The threat is registered as T-14-02-CR01 and confirmed closed by Playwright browser verification.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-20
