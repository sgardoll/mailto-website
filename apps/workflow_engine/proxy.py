"""Proxy handler: forwards POST /api/ai to LM Studio (SPA-05)."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

from .logging_setup import get

log = get("proxy")

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
PROXY_TIMEOUT_SECONDS = 120


class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/ai":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        # Strip Authorization header — never forward to LM Studio (CONTEXT.md decision)
        headers = {"Content-Type": "application/json"}
        try:
            resp = httpx.post(
                LM_STUDIO_URL,
                content=body,
                headers=headers,
                timeout=PROXY_TIMEOUT_SECONDS,
            )
            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp.content)
        except httpx.HTTPError as e:
            log.error("proxy error: %s", e)
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"error": "proxy error"}')

    def log_message(self, format, *args) -> None:
        pass  # silence default request logging


def start_proxy_server(port: int = 8900) -> threading.Thread:
    server = HTTPServer(("127.0.0.1", port), ProxyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("AI proxy endpoint running on http://127.0.0.1:%d/api/ai", port)
    return thread
