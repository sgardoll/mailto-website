"""Tests for proxy.py — /api/ai forwarding, CORS, auth stripping."""
from __future__ import annotations

import json
import threading
from http.server import HTTPServer
from unittest.mock import patch

import httpx
import pytest

from apps.workflow_engine import proxy


@pytest.fixture
def proxy_server():
    server = HTTPServer(("127.0.0.1", 0), proxy.ProxyHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _client() -> httpx.Client:
    """Return a real httpx.Client unaffected by httpx.post patches."""
    return httpx.Client()


def test_post_forwards_to_lm_studio(proxy_server):
    fake_response = {"choices": [{"message": {"content": "hi"}}]}
    with patch.object(proxy.httpx, "post") as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            content=json.dumps(fake_response).encode(),
            headers={"Content-Type": "application/json"},
        )
        r = _client().post(
            f"{proxy_server}/api/ai",
            json={"messages": [{"role": "user", "content": "hi"}]},
            timeout=5,
        )
    assert r.status_code == 200
    assert r.json() == fake_response
    mock_post.assert_called_once()
    # Confirm the URL forwarded to is LM Studio:
    assert mock_post.call_args.args[0] == proxy.LM_STUDIO_URL


def test_options_returns_cors_preflight(proxy_server):
    r = _client().request("OPTIONS", f"{proxy_server}/api/ai", timeout=5)
    assert r.status_code == 200
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    assert "POST" in r.headers.get("Access-Control-Allow-Methods", "")


def test_authorization_header_stripped(proxy_server):
    with patch.object(proxy.httpx, "post") as mock_post:
        mock_post.return_value = httpx.Response(200, content=b"{}")
        _client().post(
            f"{proxy_server}/api/ai",
            json={"messages": []},
            headers={"Authorization": "Bearer secret-token"},
            timeout=5,
        )
    forwarded_headers = mock_post.call_args.kwargs["headers"]
    assert "Authorization" not in forwarded_headers
    assert forwarded_headers.get("Content-Type") == "application/json"


def test_non_api_ai_path_returns_404(proxy_server):
    r = _client().post(f"{proxy_server}/wrong/path", json={}, timeout=5)
    assert r.status_code == 404


def test_lm_studio_unreachable_returns_502(proxy_server):
    with patch.object(proxy.httpx, "post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("refused")
        r = _client().post(
            f"{proxy_server}/api/ai",
            json={"messages": []},
            timeout=5,
        )
    assert r.status_code == 502
    assert r.json()["error"] == "proxy error"
    # CORS header present even on error (per CONTEXT.md — always set on /api/ai)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
