# Email-AI Workflow — Setup

You email an inbox; a local LM Studio model (Gemma) folds the content into
that inbox's evolving website; the site is rebuilt and deployed to your
SiteGround hosting. Each inbox = one site, one topic the framework infers
and refines as more emails arrive.

## What lives where

```
framework/site-template/   the Astro template (copied per inbox on first email)
sites/<slug>/              the actual evolving site for one inbox
workflow/                  Python: IMAP listener, dispatcher, orchestrator,
                           LM Studio client, content writer, build+deploy
scripts/                   foreground runner + install systemd / launchd agents
```

## Prerequisites

- **Python 3.11+**
- **Node 20+ / npm** (for Astro)
- **LM Studio** with the `lms` CLI on PATH (Developer tab → "Install lms")
  and your Gemma model downloaded. Default model tag in the example config
  is `google/gemma-4-26b-a4b` — change it to whatever LM Studio shows.
- A **Gmail account** with an [app password](https://myaccount.google.com/apppasswords).
- A **SiteGround hosting account** with SSH/SFTP enabled (Site Tools →
  Devs → SSH Keys Manager). You'll need: host, port (SiteGround uses a
  non-22 port — copy it from Site Tools), username, and either an SSH
  private key path or an SFTP password.

## First-time setup

```bash
cd /path/to/thoughts-to-platform-builder
cp workflow/config.example.yaml workflow/config.yaml
cp .env.example .env
# Edit .env: set GMAIL_APP_PASSWORD
# Edit workflow/config.yaml: set imap user, smtp user, siteground.*, inboxes
```

## Pick your email-routing scheme

Two simple options for routing one Gmail inbox to many topic-specific inboxes:

**Option A (simplest): Gmail plus-aliases.** No domain setup needed. Use
`youremail+guitar@gmail.com`, `youremail+parenting@gmail.com`, etc. Gmail
delivers them all to your single inbox; the dispatcher routes by `To:`
header. Configure each inbox `address` with the plus-alias you want.

**Option B: catch-all on a custom domain forwarded to Gmail.** Lets you use
`guitar@yourdomain.com` etc. Requires forwarding setup at your DNS host.
Same dispatcher works.

## Run it

```bash
# Dry-run a single pull (won't write, build, or deploy):
./scripts/run-workflow-dry.sh

# Foreground, persistent IMAP IDLE loop:
./scripts/run-workflow.sh

# Install as a background service:
./scripts/install-systemd-user.sh    # Linux
./scripts/install-launchd.sh         # macOS
```

## How an email becomes content

1. **Listener** picks up the unread message via IMAP IDLE.
2. **Dispatcher** routes it to an inbox by matching `To:` against the
   addresses in `inboxes:`.
3. **Site bootstrap** copies `framework/site-template/` to
   `sites/<slug>/` if this is the inbox's first email.
4. **Site index** summarises every existing thread + entry on this site so
   the model knows what already exists.
5. **Topic curator** asks Gemma to refine `sites/<slug>/topic.md` based on
   the new email + the site's history.
6. **Synthesiser** asks Gemma for a JSON plan of `create`/`edit` ops on
   `src/content/entries/` and `src/content/threads/`. The system prompt
   forbids siloing — every new entry must reference an existing thread (or
   create one with justification).
7. **Apply** validates each op (path, slug, frontmatter, schema) and
   writes the markdown.
8. **Build** runs `npm run build` for that site. If it fails, the content
   writes are rolled back via `git restore` so the live site is never
   broken.
9. **Deploy** SFTPs `dist/` to the SiteGround path
   `siteground.base_remote_path/<slug>/`.
10. **Commit + push** to the `git_branch` configured.
11. **Reply email** lands in your inbox: what was integrated, the live URL,
    and the commit SHA.

## End-to-end test

1. `npm --prefix framework/site-template install && npm --prefix framework/site-template run build`
   — proves the template builds.
2. Start LM Studio, load Gemma, confirm `curl localhost:1234/v1/models`
   lists the model id from your config.
3. `./scripts/run-workflow-dry.sh` — should connect IMAP, find no unread
   mail, exit cleanly.
4. From the allowlisted address, email
   `youremail+test@gmail.com` (after adding a `test` inbox to
   `inboxes:`). Watch the logs.
5. After a successful run, visit `siteground.base_remote_path/test/` via
   your domain — you should see the home page with a fresh entry and
   thread.
6. Send a second email on the same topic and confirm Gemma extends the
   existing thread instead of creating a new one.

## Notes on LM Studio

- The OpenAI-compatible server lives at `http://localhost:1234/v1`. The
  workflow uses the `openai` Python SDK pointed at this base URL.
- If `autostart: true`, the workflow shells out to `lms server start` and
  `lms load <model>` before its first call.
- Want to run LM Studio on a different machine? Enable **LM Link** in LM
  Studio, copy the URL it gives you, and set `lm_studio.base_url` to that.
  No other code changes.

## Safety

- **Sender allowlist** is mandatory — unmatched senders are rejected and
  recorded.
- The model can only write inside `sites/<slug>/src/content/`; paths are
  validated server-side.
- Schema validation in `apply_changes.py` plus Astro's content collection
  schema double-check the model's output. Schema violation = nothing
  written.
- Failed build → automatic rollback (`git restore`) + failure email.
- Every successful integration is one git commit; `git revert` is the undo.

## Troubleshooting

- **`lms` not found**: open LM Studio → Developer tab → "Install lms".
- **IMAP `Application-specific password required`**: enable 2FA on your
  Google account, generate an app password, paste into `.env` as
  `GMAIL_APP_PASSWORD`.
- **SiteGround SFTP `Auth failed`**: SiteGround uses a non-22 port; check
  Site Tools → Devs → SSH Keys Manager for the exact port and confirm the
  key you registered matches `siteground.key_path`.
- **Build hangs at `astro sync`**: delete `sites/<slug>/.astro/` and retry.
