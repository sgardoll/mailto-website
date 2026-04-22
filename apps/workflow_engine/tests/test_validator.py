"""Tests for apps.workflow_engine.validator."""
from __future__ import annotations

import pytest

from apps.workflow_engine import validator

# ---------------------------------------------------------------------------
# Shared fixture — a valid HTML document repeated to ensure > 800 bytes
# ---------------------------------------------------------------------------

_BASE = """<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
  <div x-data="{ count: 0 }">
    <button @click="count++" class="bg-blue-500 text-white px-4 py-2">Click</button>
    <p x-text="count"></p>
  </div>
</body>
</html>"""

VALID_HTML = _BASE * 3  # ensures > 800 bytes

# ---------------------------------------------------------------------------
# VAL-01: Happy path
# ---------------------------------------------------------------------------


def test_valid_html_returns_empty_list():
    assert validator.validate_module(VALID_HTML) == []


# ---------------------------------------------------------------------------
# VAL-01: x-data presence
# ---------------------------------------------------------------------------


def test_missing_x_data_returns_error():
    html = VALID_HTML.replace('x-data="{ count: 0 }"', "")
    errors = validator.validate_module(html)
    assert any("x-data" in e for e in errors)


# ---------------------------------------------------------------------------
# VAL-01: event handler presence
# ---------------------------------------------------------------------------


def test_missing_event_handler_returns_error():
    html = VALID_HTML.replace('@click="count++"', "")
    errors = validator.validate_module(html)
    assert any("event handler" in e for e in errors)


def test_x_on_handler_accepted():
    """x-on:click is Alpine's full form and must also satisfy the event handler check."""
    html = VALID_HTML.replace('@click="count++"', 'x-on:click="count++"')
    assert validator.validate_module(html) == []


# ---------------------------------------------------------------------------
# VAL-02: CDN pinning
# ---------------------------------------------------------------------------


def test_unpinned_alpine_returns_error():
    """Alpine CDN URL without @version segment should be rejected."""
    html = VALID_HTML.replace(
        "https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js",
        "https://cdn.jsdelivr.net/npm/alpinejs/dist/cdn.min.js",
    )
    errors = validator.validate_module(html)
    assert any("Alpine" in e for e in errors)


def test_missing_tailwind_returns_error():
    """Tailwind CDN script tag missing → error containing 'Tailwind'."""
    html = VALID_HTML.replace(
        '<script src="https://cdn.tailwindcss.com"></script>', ""
    )
    errors = validator.validate_module(html)
    assert any("Tailwind" in e for e in errors)


# ---------------------------------------------------------------------------
# VAL-04: x-if placement
# ---------------------------------------------------------------------------


def test_x_if_on_div_returns_error():
    """x-if on a <div> must be rejected."""
    html = VALID_HTML.replace(
        '<div x-data="{ count: 0 }">',
        '<div x-data="{ count: 0 }"><div x-if="true">inner</div>',
    )
    errors = validator.validate_module(html)
    assert any("x-if" in e for e in errors)


def test_x_if_on_template_passes():
    """x-if on <template> is the correct Alpine v3 pattern — must not produce an error."""
    html = VALID_HTML.replace(
        "<p x-text=\"count\"></p>",
        '<template x-if="true"><span>ok</span></template>',
    )
    # No x-if error expected
    errors = validator.validate_module(html)
    assert not any("x-if" in e for e in errors)


# ---------------------------------------------------------------------------
# SEC-01: x-html directive ban
# ---------------------------------------------------------------------------


def test_x_html_directive_rejected():
    """Any module containing x-html must be rejected (XSS risk)."""
    html = VALID_HTML.replace(
        "<p x-text=\"count\"></p>",
        '<p x-text="count"></p><div x-html="foo"></div>',
    )
    errors = validator.validate_module(html)
    assert errors, "Expected errors list to be non-empty"
    assert any("x-html" in e for e in errors)


def test_x_text_allowed():
    """x-text does not trigger the x-html ban — regression guard."""
    html = VALID_HTML.replace(
        "<p x-text=\"count\"></p>",
        '<p x-text="count"></p><span x-text="foo"></span>',
    )
    errors = validator.validate_module(html)
    assert not any("x-html" in e for e in errors)


# ---------------------------------------------------------------------------
# VAL-03: Stub phrases (full HTML scan, case-insensitive)
# ---------------------------------------------------------------------------


def test_stub_phrase_todo_returns_error():
    """TODO (all case variants) must be rejected."""
    for phrase in ("TODO: fix this", "todo", "Todo"):
        html = VALID_HTML + f"\n<!-- {phrase} -->"
        errors = validator.validate_module(html)
        assert errors, f"Expected error for phrase: {phrase!r}"


def test_stub_phrase_fixme_returns_error():
    html = VALID_HTML + "\n<!-- FIXME -->"
    assert validator.validate_module(html)


def test_stub_phrase_placeholder_returns_error():
    html = VALID_HTML + "\n<p>placeholder</p>"
    assert validator.validate_module(html)


def test_stub_phrase_coming_soon_returns_error():
    html = VALID_HTML + "\n<p>coming soon</p>"
    assert validator.validate_module(html)


def test_stub_phrase_implement_returns_error():
    html = VALID_HTML + "\n<script>// implement the logic here</script>"
    assert validator.validate_module(html)


# ---------------------------------------------------------------------------
# VAL-03: Ellipsis — script-only scope
# ---------------------------------------------------------------------------


def test_ellipsis_in_script_returns_error():
    """Ellipsis inside a <script> block must be rejected."""
    html = VALID_HTML + "\n<script>function todo() { ... }</script>"
    errors = validator.validate_module(html)
    assert any("llipsis" in e or "..." in e for e in errors)


def test_ellipsis_in_html_text_passes():
    """Ellipsis in a <p> tag text (not in a script) must NOT trigger the ellipsis error."""
    html = VALID_HTML + "\n<p>The answer is...</p>"
    errors = validator.validate_module(html)
    # The ellipsis rule must not fire for HTML body text
    assert not any("llipsis" in e or "..." in e for e in errors)


# ---------------------------------------------------------------------------
# VAL-05: External fetch / XHR
# ---------------------------------------------------------------------------


def test_external_fetch_returns_error():
    """fetch() to an external domain must be rejected."""
    html = VALID_HTML + '\n<script>fetch("https://evil.com/data")</script>'
    errors = validator.validate_module(html)
    assert errors


def test_localhost_fetch_passes():
    """fetch() to localhost must NOT be rejected."""
    html = VALID_HTML + '\n<script>fetch("http://localhost:1234/api")</script>'
    errors = validator.validate_module(html)
    assert not any("fetch" in e.lower() or "xhr" in e.lower() for e in errors)


def test_xhr_external_returns_error():
    """XMLHttpRequest.open() to an external domain must be rejected."""
    html = VALID_HTML + (
        "\n<script>"
        'var x = new XMLHttpRequest(); x.open("GET", "https://evil.com");'
        "</script>"
    )
    errors = validator.validate_module(html)
    assert errors


# ---------------------------------------------------------------------------
# VAL-06: Minimum length
# ---------------------------------------------------------------------------


def test_too_short_returns_error():
    """HTML shorter than 800 bytes must be rejected; error message must mention '800'."""
    short_html = "x" * 50
    errors = validator.validate_module(short_html)
    assert any("800" in e for e in errors)


def test_html_length_boundary():
    """Exactly 800 UTF-8 bytes of a structurally valid HTML should not trigger the length error."""
    # Build a minimal HTML containing all required elements padded to >= 800 bytes
    base = """<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
  <div x-data="{ v: 0 }">
    <button @click="v++" class="p-2">Go</button>
    <p x-text="v"></p>
  </div>
</body>
</html>"""
    # Pad inside a comment until we reach exactly 800 bytes
    current = base.encode("utf-8")
    if len(current) < 800:
        padding = "x" * (800 - len(current))
        base = base.replace("</html>", f"<!-- {padding} --></html>")
    html_800 = base
    assert len(html_800.encode("utf-8")) >= 800
    errors = validator.validate_module(html_800)
    assert not any("800" in e for e in errors)
