"""Browser smoke test for the SPA shell.

Serves the tests/fixtures/spa/ directory over a local HTTP server and verifies
that shell.html renders a nav item and loads the fixture module into the iframe.

Runs standalone — does NOT require LM Studio or a live pipeline. The fixture
module is committed to the repo under tests/fixtures/spa/test_module/.

Skip if pytest-playwright or the browser binary are unavailable.
"""
from __future__ import annotations

import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

# Skip the whole module if playwright is unavailable (e.g. CI without browser
# binaries installed). This keeps the standard CI suite green even when
# Playwright isn't set up.
playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright, expect  # noqa: E402


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spa"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _FixtureHandler(SimpleHTTPRequestHandler):
    """Serve files from FIXTURES_DIR regardless of pytest's cwd."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    def log_message(self, format, *args):  # silence server logs in test output
        pass


@pytest.fixture
def fixture_server():
    """Start a local HTTP server serving tests/fixtures/spa/ for the duration
    of a test, then shut it down cleanly."""
    port = _find_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_shell_loads_and_renders_nav_item(fixture_server):
    """SC1 (browser portion): shell.html renders h1, fetches manifest, and
    populates one nav item linking to the fixture module."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:
            pytest.skip(f"chromium unavailable: {e}")
        try:
            page = browser.new_page()
            page.goto(f"{fixture_server}/shell.html")

            # Header renders
            expect(page.locator("h1")).to_have_text("SPA Shell")

            # Nav populates with exactly one .nav-item after manifest fetch
            nav_item = page.locator(".nav-item")
            expect(nav_item).to_have_count(1)
            expect(nav_item.first).to_contain_text("test_module")

            # iframe loads the fixture module (frame.src ends with
            # test_module/index.html after init() navigates to the first module)
            frame = page.locator("#module-frame")
            expect(frame).to_have_attribute(
                "src",
                "test_module/index.html",
                timeout=5000,
            )

            # iframe content is reachable (document.title is set by fixture)
            frame_element = page.frame_locator("#module-frame")
            expect(frame_element.locator("#counter")).to_be_visible()
        finally:
            browser.close()
