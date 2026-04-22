---
phase: 18-integrate-orchestrator
plan: "04"
subsystem: site-template/spa
tags: [shell, csp, security, window-ai, spa-05, sec-02]
status: complete
requirements: [SEC-02, SPA-05]
key-files:
  modified:
    - packages/site-template/public/spa/shell.html
---

## What Was Built

Updated `shell.html` with two security changes:

1. **CSP meta tag** — restrictive Content-Security-Policy added as first `<head>` child:
   `default-src 'self'; script-src 'self' 'unsafe-inline' ...; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:1234; frame-src 'self'`

2. **Protocol-aware window.AI()** — replaces hard-coded LM Studio endpoint with a protocol ternary: HTTPS deployments route via `/api/ai` (the Plan 03 proxy); local `http://` still hits LM Studio directly. `Authorization: Bearer lm-studio` header removed — the proxy handles auth server-side.

## Deviations

`style-src 'unsafe-inline'` added to CSP during human verification — the inline `<style>` block in shell.html requires it since `default-src` fallback blocks inline styles. This was caught and fixed at the checkpoint.

## Self-Check: PASSED

- CSP meta present with correct directives
- `window.location.protocol === 'https:'` ternary present
- `/api/ai` endpoint in HTTPS branch
- Authorization header absent from fetch call
- `window.STATE` and `iframe sandbox="allow-scripts"` preserved
- Human verified: no CSP violations in browser DevTools, correct console debug line
