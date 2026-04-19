"""Tracks processed messages and per-inbox build/deploy locks."""
from __future__ import annotations
import contextlib
import fcntl
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class ProcessedLog:
    """Append-only JSONL of message-id -> outcome. Used for idempotency."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._cache: set[str] = set()
        for line in self.path.read_text().splitlines():
            try:
                rec = json.loads(line)
                if mid := rec.get("message_id"):
                    self._cache.add(mid)
            except json.JSONDecodeError:
                continue

    def seen(self, message_id: str) -> bool:
        return message_id in self._cache

    def record(self, message_id: str, inbox: str, outcome: str, **extra) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "message_id": message_id,
            "inbox": inbox,
            "outcome": outcome,
            **extra,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        self._cache.add(message_id)


@contextlib.contextmanager
def file_lock(lock_path: Path, timeout_s: float = 1800.0) -> Iterator[None]:
    """Process-safe lock so two emails for the same inbox don't trample."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() > deadline:
                f.close()
                raise TimeoutError(f"Could not acquire lock {lock_path} within {timeout_s}s")
            time.sleep(0.5)
    try:
        yield
    finally:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()
