"""Maintain the rolling topic hypothesis for an inbox."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from . import lm_studio, prompt
from .config import LmStudioConfig
from .logging_setup import get
from .site_index import SiteIndex

log = get("topic_curator")


def update_topic(
    *, site_dir: Path, idx: SiteIndex, email: dict[str, Any],
    lm_cfg: LmStudioConfig, dry_run: bool = False,
) -> str:
    user = prompt.topic_prompt_user(idx, email)
    sys = prompt.system_for("topic_curation")
    try:
        result = lm_studio.chat_json(lm_cfg, system=sys, user=user, task="topic_curation")
        new_topic = (result.get("topic_md") or "").strip() or idx.topic
    except (ValueError, KeyError) as e:
        log.warning("topic_curation JSON parse failed (%s); keeping existing topic", e)
        new_topic = idx.topic
    if dry_run:
        log.info("[dry-run] new topic:\n%s", new_topic)
        return new_topic
    (site_dir / "topic.md").write_text(new_topic + "\n")
    log.info("topic.md updated (%d chars)", len(new_topic))
    return new_topic
