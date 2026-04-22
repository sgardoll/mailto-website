---
phase: 18-integrate-orchestrator
plan: "03"
subsystem: workflow_engine
tags: [proxy, http, cors, lm-studio, spa]
dependency_graph:
  requires: []
  provides: [proxy.ProxyHandler, proxy.start_proxy_server, listener.main proxy-port]
  affects: [apps/workflow_engine/listener.py]
tech_stack:
  added: []
  patterns: [stdlib HTTPServer handler, httpx forwarding, unittest.mock.patch with Client fixture]
key_files:
  created:
    - apps/workflow_engine/proxy.py
    - apps/workflow_engine/tests/test_proxy.py
  modified:
    - apps/workflow_engine/listener.py
decisions:
  - Use httpx.Client() fixture in tests to avoid mock collision with httpx.post patching
  - Alias proxy import as _proxy_mod in listener.py to avoid naming conflicts
  - Build forwarded headers dict from scratch (Content-Type only) rather than copying request headers
metrics:
  duration: "~10 minutes"
  completed: "2026-04-22T08:00:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 18 Plan 03: /api/ai Proxy + Listener Wiring Summary

**One-liner:** stdlib HTTPServer proxy forwarding POST /api/ai to LM Studio with Authorization stripped, wired into listener.main() alongside the health server.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create proxy.py + tests | 0b3f85d | apps/workflow_engine/proxy.py, apps/workflow_engine/tests/test_proxy.py |
| 2 | Wire proxy into listener, remove duplicates | 466ebaf | apps/workflow_engine/listener.py |

## What Was Built

### proxy.py

`ProxyHandler` (stdlib `BaseHTTPRequestHandler`) with two methods:

- `do_OPTIONS` — responds 200 with CORS headers (`Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: POST, OPTIONS`, `Access-Control-Allow-Headers: Content-Type, Authorization`)
- `do_POST` — reads body, builds fresh `{"Content-Type": "application/json"}` header dict (Authorization never forwarded), calls `httpx.post(LM_STUDIO_URL, ...)`, streams response back with CORS headers; returns 404 for wrong paths, 502 on `httpx.HTTPError`

`start_proxy_server(port=8900)` creates an `HTTPServer` on `127.0.0.1:{port}`, runs it in a daemon thread.

### test_proxy.py

Five tests using a `proxy_server` fixture (ephemeral `HTTPServer` on port 0) and `_client()` helper returning `httpx.Client()` to avoid mock collision:

1. `test_post_forwards_to_lm_studio` — verifies forwarding URL and response passthrough
2. `test_options_returns_cors_preflight` — verifies 200 + CORS headers
3. `test_authorization_header_stripped` — verifies Authorization absent from forwarded headers
4. `test_non_api_ai_path_returns_404` — verifies path guard
5. `test_lm_studio_unreachable_returns_502` — verifies 502 with CORS + error JSON on `ConnectError`

### listener.py changes

- Import: `from . import dispatcher, orchestrator, proxy as _proxy_mod`
- `--proxy-port` argparse argument (default 8900) added to `main()`
- `_proxy_mod.start_proxy_server(args.proxy_port)` called after `_start_health_server`
- First duplicate `_HealthHandler` class and `_start_health_server` function definitions removed (26 lines deleted)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] httpx.post mock collision in tests**
- **Found during:** Task 1, first test run
- **Issue:** `patch.object(proxy.httpx, "post")` patches the shared `httpx` module, so the test's own `httpx.post(proxy_server_url, ...)` call was captured by the mock instead of reaching the proxy server. The assertion `mock_post.call_args.args[0] == proxy.LM_STUDIO_URL` failed because `call_args.args[0]` was the test's proxy URL, not LM Studio's URL.
- **Fix:** Introduced `_client()` helper that returns `httpx.Client()`. `Client.post()` is a method on the instance and is not affected by patching the module-level `httpx.post` function.
- **Files modified:** apps/workflow_engine/tests/test_proxy.py
- **Commit:** 0b3f85d (included in initial commit)

## Threat Model Compliance

All T-18-09 through T-18-13 mitigations implemented:

| Threat ID | Status | Evidence |
|-----------|--------|---------|
| T-18-09 (Authorization forwarding) | Mitigated | `headers = {"Content-Type": "application/json"}` built from scratch |
| T-18-10 (Allow-Origin: *) | Accepted | No authenticated context; tightening deferred |
| T-18-11 (Unbounded body read) | Accepted | Content-Length honoured; HTTPServer defaults cap applied |
| T-18-12 (Path routing) | Mitigated | `self.path != "/api/ai"` guard returns 404 |
| T-18-13 (LM Studio unreachable) | Mitigated | `httpx.HTTPError` caught, 502 + CORS returned |

## Known Stubs

None. The proxy is fully wired: listener.main() starts it, ProxyHandler forwards real requests.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| apps/workflow_engine/proxy.py | FOUND |
| apps/workflow_engine/tests/test_proxy.py | FOUND |
| apps/workflow_engine/listener.py | FOUND |
| .planning/phases/18-integrate-orchestrator/18-03-SUMMARY.md | FOUND |
| Commit 0b3f85d (feat(18-03): add /api/ai proxy) | FOUND |
| Commit 466ebaf (feat(18-03): wire proxy server into listener) | FOUND |
