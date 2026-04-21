"""Validate LM-generated Alpine/Tailwind HTML modules."""
from __future__ import annotations

import re
from html.parser import HTMLParser

# HTMLParseError was removed in Python 3.14; use Exception for parse failure guard.
try:
    from html.parser import HTMLParseError  # type: ignore[attr-defined]
except ImportError:
    HTMLParseError = Exception  # type: ignore[assignment,misc]

from .logging_setup import get

log = get("validator")

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_STUB_PHRASES = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bplaceholder\b",
    r"coming soon",
    r"//\s*implement",
]
_STUB_RE = re.compile("|".join(_STUB_PHRASES), re.IGNORECASE)
_ELLIPSIS_RE = re.compile(r"\.\.\.")

# Alpine CDN must have @semver in path; Tailwind CDN is a fixed literal (no version in path).
_ALPINE_CDN_RE = re.compile(r"cdn\.jsdelivr\.net/npm/alpinejs@[\d.]+/")
_TAILWIND_CDN = "cdn.tailwindcss.com"

# fetch() URL argument extraction
_FETCH_URL_RE = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']')
# XMLHttpRequest.open() URL argument (second argument)
_XHR_URL_RE = re.compile(r'\.open\s*\(\s*["\'][^"\']*["\']\s*,\s*["\']([^"\']+)["\']')

_LOCALHOST_PREFIXES = (
    "http://localhost",
    "http://127.0.0.1",
    "https://localhost",
    "https://127.0.0.1",
)


# ---------------------------------------------------------------------------
# HTML Inspector (single-pass HTMLParser subclass)
# ---------------------------------------------------------------------------


class _Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_x_data: bool = False
        self.has_event_handler: bool = False
        self.x_if_on_div: bool = False
        self.cdn_src_urls: list[str] = []
        self.script_texts: list[str] = []
        self._in_script: bool = False
        self._script_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if "x-data" in attr_dict:
            self.has_x_data = True
        if tag == "div" and "x-if" in attr_dict:
            self.x_if_on_div = True
        for key in attr_dict:
            if key in ("@click", "@input", "@change") or key.startswith("x-on:"):
                self.has_event_handler = True
        if tag == "script":
            src = attr_dict.get("src") or ""
            if src:
                self.cdn_src_urls.append(src)
            self._in_script = True
            self._script_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_script = False
            self.script_texts.append("".join(self._script_buf))

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_buf.append(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_module(html: str) -> list[str]:
    """Validate an LM-generated Alpine/Tailwind HTML module.

    Returns a list of error strings.  An empty list means the module is valid.
    """
    errors: list[str] = []

    # VAL-06: byte-length check
    if len(html.encode("utf-8")) < 800:
        errors.append("HTML shorter than 800 bytes")

    # VAL-03: stub phrase scan on the full HTML (except ellipsis — see below)
    if _STUB_RE.search(html):
        errors.append(
            "Stub phrase detected (TODO/FIXME/placeholder/coming soon/implement)"
        )

    # Parse HTML
    inspector = _Inspector()
    try:
        inspector.feed(html)
    except HTMLParseError as exc:
        errors.append(f"HTML not parseable: {exc}")
        return errors  # further checks are meaningless without a parse result

    # VAL-01: x-data
    if not inspector.has_x_data:
        errors.append("Missing x-data attribute")

    # VAL-01: event handler
    if not inspector.has_event_handler:
        errors.append(
            "Missing event handler (@click/@input/@change/x-on:*)"
        )

    # VAL-04: x-if on div
    if inspector.x_if_on_div:
        errors.append("x-if used on <div> element (must be on <template>)")

    # VAL-02: Alpine CDN (must have @version in path)
    if not any(_ALPINE_CDN_RE.search(u) for u in inspector.cdn_src_urls):
        errors.append("Missing pinned Alpine.js CDN <script> tag")

    # VAL-02: Tailwind CDN (literal hostname — no version in path by convention)
    if not any(_TAILWIND_CDN in u for u in inspector.cdn_src_urls):
        errors.append("Missing Tailwind CDN <script> tag")

    # VAL-03: ellipsis — only in script text content, not in HTML body text
    for script_text in inspector.script_texts:
        if _ELLIPSIS_RE.search(script_text):
            errors.append("Ellipsis (...) found in script block")
            break

    # VAL-05: external fetch / XHR
    _check_external_requests(inspector.script_texts, errors)

    log.debug("validate_module: %d error(s)", len(errors))
    return errors


def _check_external_requests(script_texts: list[str], errors: list[str]) -> None:
    """Append errors for any fetch() or XHR calls to non-localhost URLs."""
    for text in script_texts:
        for url in _FETCH_URL_RE.findall(text):
            if not url.startswith(_LOCALHOST_PREFIXES):
                errors.append(f"External fetch/XHR to non-localhost: {url}")
        for url in _XHR_URL_RE.findall(text):
            if not url.startswith(_LOCALHOST_PREFIXES):
                errors.append(f"External fetch/XHR to non-localhost: {url}")
