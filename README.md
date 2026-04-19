# thoughts-to-platform-builder

Turn emails into an evolving, topic-specific website. Each inbox you dedicate
to a goal or idea in your life becomes its own self-extending platform. You
email an idea, quote, article, or scrap to the inbox; a local LM Studio
model (Gemma) synthesises it, folds it into what's already there, and the
site is rebuilt and redeployed — automatically.

## How it works

```
 One Gmail account, many plus-aliases (you+guitar@..., you+parenting@...)
        │  IMAP IDLE (push)
        ▼
 apps/workflow_engine/listener.py  ─►  dispatcher  ─►  orchestrator(inbox=guitar)
                                        ─►  orchestrator(inbox=parenting)
                                        ─►  ...
                                                │
                    per-inbox site at runtime/runtime/sites/<slug>/ (Astro)
                                                │
          topic curator (Gemma) → synthesiser (Gemma) →
          schema-validated writes → astro build →
          SFTP mirror to SiteGround → git commit → reply email
```

Two prime directives for the model:

1. **Fold in, don't silo.** Every new entry must extend or link to an
   existing thread on the site. The content schema enforces this — a
   silo'd write won't even validate.
2. **Take initiative.** Synthesise the email into something useful
   (tools, questions, next steps, connections to earlier entries), not a
   verbatim transcription.

## Project layout

```
packages/site-template/   Astro 5 template. Copied to runtime/runtime/sites/<slug>/ on an
                           inbox's first email. Inbox-owned thereafter.
runtime/runtime/sites/<slug>/              One evolving site per inbox.
apps/workflow_engine/                  Python pipeline. Imports into a single venv.
scripts/                   Foreground runner, systemd / launchd installers.
docs/SETUP.md              Full wiring guide. Read this first.
```

## Quick start

```bash
cp apps/workflow_engine/config.example.yaml apps/workflow_engine/config.yaml
cp .env.example .env
# Edit .env: set GMAIL_APP_PASSWORD
# Edit apps/workflow_engine/config.yaml: imap user, smtp user, siteground.*, inboxes

./scripts/run-workflow-dry.sh        # safe smoke test
./scripts/run-workflow.sh            # foreground, persistent IMAP IDLE
./scripts/install-systemd-user.sh    # or install-launchd.sh on macOS
```

Full setup + troubleshooting in [docs/SETUP.md](docs/SETUP.md).

## Prerequisites

- Python 3.11+, Node 20+.
- LM Studio with the `lms` CLI on PATH and a Gemma model loaded. Default
  config tag is `google/gemma-4-26b-a4b`; change to whatever LM Studio
  shows for your model.
- Gmail with an [app password](https://myaccount.google.com/apppasswords).
- SiteGround hosting with SSH/SFTP enabled.

## Safety

- Sender allowlist is mandatory.
- Model's file writes are path-restricted to `runtime/runtime/sites/<slug>/src/content/`.
- Astro content-collection Zod schema + a second validator in
  `apply_changes.py` double-check every op.
- Build failure triggers a `git restore` rollback so the live site never breaks.
- Every successful integration is one git commit — `git revert` is the undo.
