"""Summarise a site's content so the model knows what already exists."""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import frontmatter


WORD_BUDGET_PER_DOC = 80


@dataclass
class DocSummary:
    slug: str
    title: str
    summary: str
    tags: list[str]
    threads: list[str]
    excerpt: str


@dataclass
class SiteIndex:
    inbox_slug: str
    site_name: str
    topic: str
    threads: list[DocSummary]
    entries: list[DocSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "inbox_slug": self.inbox_slug,
            "site_name": self.site_name,
            "topic": self.topic,
            "threads": [asdict(t) for t in self.threads],
            "entries": [asdict(e) for e in self.entries],
        }


def _excerpt(body: str, words: int = WORD_BUDGET_PER_DOC) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    parts = text.split(" ")
    if len(parts) <= words:
        return text
    return " ".join(parts[:words]) + "..."


def _slug_from_path(p: Path, root: Path) -> str:
    return str(p.relative_to(root)).rsplit(".", 1)[0]


def _ref_slug(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("slug") or value.get("id") or "")
    return str(value)


def _read_collection(root: Path) -> list[DocSummary]:
    out: list[DocSummary] = []
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".mdx"}:
            continue
        post = frontmatter.load(path)
        meta = post.metadata or {}
        out.append(
            DocSummary(
                slug=_slug_from_path(path, root),
                title=str(meta.get("title", path.stem)),
                summary=str(meta.get("summary", "")),
                tags=[str(t) for t in (meta.get("tags") or [])],
                threads=[_ref_slug(t) for t in (meta.get("threads") or [])],
                excerpt=_excerpt(post.content),
            )
        )
    return out


def build(site_dir: Path, *, inbox_slug: str, site_name: str) -> SiteIndex:
    topic_path = site_dir / "topic.md"
    topic = topic_path.read_text() if topic_path.exists() else "(no topic inferred yet)"
    return SiteIndex(
        inbox_slug=inbox_slug,
        site_name=site_name,
        topic=topic.strip(),
        threads=_read_collection(site_dir / "src" / "content" / "threads"),
        entries=_read_collection(site_dir / "src" / "content" / "entries"),
    )
