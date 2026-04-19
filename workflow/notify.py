"""Send a reply email summarising what was integrated."""
from __future__ import annotations
import smtplib
from email.message import EmailMessage

from .config import SmtpConfig
from .logging_setup import get

log = get("notify")


def send(
    smtp_cfg: SmtpConfig,
    *,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = smtp_cfg.from_address or smtp_cfg.user
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    log.info("Sending reply to %s: %s", to, subject)
    with smtplib.SMTP(smtp_cfg.host, smtp_cfg.port, timeout=30) as s:
        if smtp_cfg.use_starttls:
            s.starttls()
        if smtp_cfg.user:
            s.login(smtp_cfg.user, smtp_cfg.password)
        s.send_message(msg)
