"""Structured logging shared across the workflow."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

_CONFIGURED = False


def setup(level: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    global _CONFIGURED
    root = logging.getLogger("workflow")
    if _CONFIGURED:
        return root

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s : %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False
    _CONFIGURED = True
    return root


def get(name: str) -> logging.Logger:
    return logging.getLogger(f"workflow.{name}")
