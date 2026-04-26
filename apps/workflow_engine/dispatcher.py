"""Route an inbound message to the right inbox orchestrator."""
from __future__ import annotations
from typing import Iterable

from .config import Config, InboxConfig
from .logging_setup import get

log = get("dispatcher")


def _normalise(addr: str) -> str:
    return addr.strip().lower()


def _candidates(headers: dict[str, str]) -> Iterable[str]:
    """Yield addresses we should try to route on, in priority order."""
    for key in ("delivered-to", "x-original-to", "to", "envelope-to"):
        v = headers.get(key) or headers.get(key.title()) or ""
        for raw in v.split(","):
            addr = raw.strip()
            # Strip "Name <addr@x>"
            if "<" in addr and ">" in addr:
                addr = addr[addr.index("<") + 1 : addr.index(">")]
            if addr:
                yield _normalise(addr)


def _matches_alias(candidate: str, configured: str) -> bool:
    """Match configured inbox aliases without collapsing plus tags.

    A message to foo@gmail.com must not match foo+guitar@gmail.com; otherwise
    ordinary unread mail in the base inbox is routed into every plus-alias site.
    """
    if candidate == configured:
        return True
    cand_local, _, cand_domain = candidate.partition("@")
    conf_local, _, conf_domain = configured.partition("@")
    if cand_domain != conf_domain:
        return False
    if "+" not in cand_local or "+" not in conf_local:
        return False
    cand_base, cand_tag = cand_local.split("+", 1)
    conf_base, conf_tag = conf_local.split("+", 1)
    return cand_base == conf_base and cand_tag == conf_tag


def route(cfg: Config, headers: dict[str, str]) -> InboxConfig | None:
    for cand in _candidates(headers):
        for ib in cfg.inboxes:
            if _matches_alias(cand, _normalise(ib.address)):
                log.info("routed %s -> inbox %s", cand, ib.slug)
                return ib
    log.warning("no inbox matched headers: %s", {k: headers.get(k) for k in ("To", "Delivered-To")})
    return None
