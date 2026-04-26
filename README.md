# mailto.website

Email an idea. Get a website.

[GitHub](.) · [MIT License](LICENSE) · [Setup Guide](docs/SETUP.md)

---

![mailto.website](https://github.com/user-attachments/assets/10f4c64c-ab38-4143-91f0-6a8e2ad9eb6a)

---

**Dedicate a Gmail plus-alias to any goal and that alias becomes a living website.** Forward articles. Jot voice-to-text thoughts. Paste quotes. A local LLM folds each one into the existing narrative, rebuilds the site, and pushes it live.

No CMS. No editor. No "let me just open the dashboard real quick." Just send mail.

```bash
git clone <repo> && cd mailto-website
./scripts/dev.sh
```

---

## The wizard

**Every other self-hosted publishing tool makes you copy YAML, generate app passwords, paste API tokens, and stare at SFTP errors.** This one ships with a five-step browser wizard that validates every credential before it lets you continue.

<table>
<tr>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-gmail.png" alt="Gmail step" width="100%" />
<br /><sub><b>Step 1</b> — Gmail</sub>
</td>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-lmstudio.png" alt="LM Studio step" width="100%" />
<br /><sub><b>Step 2</b> — LM Studio</sub>
</td>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-inboxes.png" alt="Inboxes step" width="100%" />
<br /><sub><b>Step 4</b> — Inboxes</sub>
</td>
</tr>
</table>

| Step | What you do | What the wizard does |
|:---:|:---|:---|
| **1. Gmail** | Paste your address + app password | Pings IMAP to confirm the credentials work before letting you continue |
| **2. LM Studio** | Pick a model | Auto-discovers every model loaded in your local LM Studio |
| **3. Hosting** | Choose SiteGround / Vercel / SSH | Validates the credentials, derives the deploy paths |
| **4. Inboxes** | Name each idea you want a site for | Derives the plus-alias and the site URL automatically |
| **5. Preview** | Eyeball the `.env` and `config.yaml` | Writes them atomically — and only if you click confirm |

<table>
<tr>
<td width="50%" align="center">
<img src="docs/screenshots/wizard-hosting.png" alt="Hosting step" width="100%" />
<br /><sub><b>Step 3</b> — Hosting picker with SSH key auto-discovery</sub>
</td>
<td width="50%" align="center">
<img src="docs/screenshots/wizard-preview.png" alt="Preview step" width="100%" />
<br /><sub><b>Step 5</b> — Preview every line of YAML before it's written</sub>
</td>
</tr>
</table>

<img src="docs/screenshots/wizard-done.png" alt="The wizard's done screen, post-deploy" width="70%" />

_The wizard's done screen — five steps earlier you ran one command. Now your sites are live and your aliases are in your contacts._

From `git clone` to a live, listening site: **under five minutes.**

---

## How it works

**After the wizard finishes, one loop runs forever.** An email arrives, the listener wakes up, and the pipeline turns it into a committed, deployed page.

```
 One Gmail account, many plus-aliases  (you+guitar@…, you+parenting@…)
        │
        │  IMAP IDLE  (push, near-instant)
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  listener.py  →  dispatcher  →  orchestrator (per inbox)         │
 │                                                                  │
 │     ├── topic curator (LM)   updates topic.md                    │
 │     ├── synthesiser (LM)     plans entry/thread writes           │
 │     ├── apply_changes        schema-validated frontmatter        │
 │     ├── astro build          on failure → git restore rollback   │
 │     └── deploy provider      SFTP / Vercel                      │
 └──────────────────────────────────────────────────────────────────┘
```

The model operates under two directives, enforced in code:

**Fold in, don't silo.** Every new entry must extend or link to an existing thread. The Astro content schema enforces this — siloed writes don't even validate.

**Take initiative.** Synthesise the email into something useful — questions, next steps, connections to earlier entries — never a verbatim transcription.

---

## Quick start

**`dev.sh` is the single entry point for everything.** It creates `.venv` when needed, installs Python requirements, opens the wizard on first run, and takes returning users straight to a launch screen for the listener dashboard and Astro site preview.

```bash
./scripts/dev.sh
```

For headless or background use after setup:

```bash
./scripts/run-workflow.sh             # foreground, persistent IMAP IDLE
./scripts/install-launchd.sh          # macOS background service
./scripts/install-systemd-user.sh     # Linux background service
```

The listener dashboard runs at `http://127.0.0.1:8899/`, with health details at `http://127.0.0.1:8899/health`.

---

## Hosting

| Provider | Wizard auto-deploy | Notes |
|:---|:---:|:---|
| **SiteGround** (SSH/SFTP) | ✓ | Full one-click deploy from the done screen. Listener can co-locate on the same box, so processing keeps running 24/7 |
| **Vercel** | ✓ | API token; static-only host. The listener has to live elsewhere (your laptop, a VPS) and pushes to Vercel via API |
| **Generic SSH/SFTP** | manual | `python -m apps.workflow_engine.deploy_once` for now |

---

## Project layout

```
apps/setup_wizard/         Flask wizard you just used. Five steps + service launch screens.
apps/workflow_engine/      Python pipeline. IMAP listener → dispatcher → orchestrator → deploy.
packages/site-template/    Astro 5 template. Copied to runtime/sites/<slug>/ on first email.
packages/config_contract/  Typed config schema shared by wizard + engine.
runtime/sites/<slug>/      One evolving site per inbox. LM-owned after bootstrap.
runtime/state/             listener.log, processed.jsonl, SSH keys.
scripts/                   dev.sh (wizard + launcher), run-workflow.sh (foreground), install-* (services).
docs/SETUP.md              Manual config path if you'd rather edit YAML directly.
```

---

## Safety

**The platform writes to a real website on real hosting, so the safety model is intentionally conservative.**

- **Sender allowlist is mandatory.** No allowlist, no processing — even if the address resolves to a configured inbox.
- **The model can only write inside `runtime/sites/<slug>/src/content/`.** Path-checked before every write.
- **Two layers of validation** — Astro's Zod content-collection schema + a second validator in `apply_changes.py`. Anything malformed is rejected before it touches the site.
- **Build failure triggers automatic rollback.** A broken synthesis triggers `git restore` + `git clean` so the live site never breaks. You get an email telling you exactly what failed.
- **Every successful integration is one git commit.** `git revert` is the undo button.

---

## Troubleshooting

```bash
tail -f runtime/state/listener.log              # live pipeline log
curl -s http://127.0.0.1:8899/health            # is the listener alive? which inboxes?
cat runtime/state/processed.jsonl | tail        # last N messages and their outcomes
```

Full troubleshooting and the manual (no-wizard) config path live in **[docs/SETUP.md](docs/SETUP.md)**.

---

## Philosophy

**mailto.website has no CMS, no web editor, no database, and no dashboard.** Those things weren't forgotten — they were rejected.

A CMS means logging in. A web editor means a browser tab left open, a half-finished draft, a mental context switch. A database means a service to run, a schema to migrate, a backup to forget. A dashboard means a place to check, a habit to form, a thing that can be down.

The inbox already exists. Every device already has a mail client. Voice-to-text already works. The marginal effort to publish an idea should be zero — compose, send, done.

The LLM doesn't transcribe your emails verbatim. It synthesises them: finding threads, asking implied questions, connecting new material to what came before. The goal isn't a log of things you sent yourself. It's a site that thinks alongside you.

One constraint enforces all of this: the model can only write inside the content directory. It can't touch templates, configuration, or anything structural. The site is yours. The content is yours. The model is just a very attentive editor with commit access.

---

MIT License · [GitHub](.) · [docs/SETUP.md](docs/SETUP.md)
