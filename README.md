# mailto.website

Email source material to an inbox. Get an interactive website module.

[GitHub](.) · [MIT License](LICENSE) · [Setup Guide](docs/SETUP.md)

---

![mailto.website](https://github.com/user-attachments/assets/10f4c64c-ab38-4143-91f0-6a8e2ad9eb6a)

---

## What this is

**mailto.website is an inbox-driven interactive site generator.**

You configure one Gmail account with one or more plus-addressed inboxes. Each inbox maps to a site. When an allowed sender emails text, an article link, or a video link to that inbox, the workflow engine turns the message into an interactive Alpine/Tailwind module, writes it into an Astro site, commits the change, builds the site, and deploys it.

No CMS. No blank editor. No dashboard for writing. The inbox is the interface.

The product has evolved from simple publishing into something more useful: a system that turns incoming material into small interactive tools, explainers, drills, calculators, generators, and guided flows.

---

## Architecture readout

| Area | What the repo shows | Why it matters |
|---|---|---|
| **Product shape** | A Gmail plus-alias maps to a per-inbox Astro site under `runtime/sites/<slug>/`. | The inbox is the capture and publishing interface. Each alias becomes its own growing interactive site. |
| **Runtime pipeline** | `orchestrator.py` runs `INGEST → DISTILL → PLAN → BUILD → INTEGRATE → Astro build → deploy`. | The system is staged rather than one giant prompt. That makes failures easier to isolate and recover from. |
| **Input handling** | `ingest.py` normalises plain email text, article URLs, and video URLs into one `normalized_input` payload. | The model receives clean source material instead of raw email mess. |
| **Article extraction** | Article URLs are extracted with `trafilatura`, with readability/lxml fallback behaviour. | A forwarded link can become usable source text without the sender doing manual copy/paste. |
| **Video extraction** | Video URLs can flow through `yt-dlp`, `ffmpeg`, and `pywhispercpp` when those tools are available. | Talks, demos, clips, and lectures can become source material. If the tools are absent, the system degrades to plain text instead of crashing. |
| **LLM backend** | `lm_studio.py` talks to LM Studio through an OpenAI-compatible API, with model auto-start, fallback loading, task-specific sampling, and structured JSON calls. | The project is built around local-model reality: incomplete JSON, memory pressure, model load failures, and inconsistent response-format support. |
| **Mechanic model** | The shared config contract defines five mechanic kinds: `calculator`, `wizard`, `drill`, `scorer`, and `generator`. | Output variety is constrained by explicit product shapes, which is stronger than asking the model to “make something interesting”. |
| **Distillation** | `distill.py` turns normalized input into a `MechanicSpec`, with retries and a hand-crafted fallback generator. | Every message is pushed toward a usable interactive shape instead of being dropped when the model hesitates. |
| **Planning** | `plan.py` compares the mechanic against `spa_manifest.json` using `sentence-transformers`, then routes to `new_module`, `extend_module`, or `upgrade_state_only`. | Each inbox can grow as a coherent app surface rather than a loose pile of disconnected widgets. |
| **Build strategy** | `build.py` defaults to a multi-step build: deterministic skeleton, then LLM-filled `INPUTS`, `LOGIC`, and `OUTPUT` regions. | Smaller local models struggle to emit one complete HTML document reliably. Smaller region fills are more controllable. |
| **Generated UI** | Modules are self-contained Alpine.js + Tailwind HTML files. | The generated output is static-host friendly, inspectable, and easy to commit. |
| **Validation** | `validator.py` rejects broken HTML, missing Alpine bindings, missing event handlers, unsafe `x-html`, stub text, external fetches, bad `x-if`, and too-short output. | The model does not get blind write access to production-facing HTML. That is the difference between a tool and a liability. |
| **Integration** | `integrate.py` atomically writes `public/spa/<module_id>/index.html`, updates `spa_manifest.json`, and commits the result. | The generated site is file-backed and git-backed. Rollback is practical rather than aspirational. |
| **SPA shell** | `packages/site-template/public/spa/shell.html` loads `spa_manifest.json`, renders navigation, embeds modules in a sandboxed iframe, exposes `window.STATE`, and provides `window.AI()`. | Generated modules run inside a controlled shell instead of owning the whole site. |
| **Setup UX** | `scripts/dev.sh` creates `.venv`, installs dependency sets, and launches the local Flask setup wizard. | First-run setup is a browser flow, not a YAML courage test. |
| **Operations UI** | The listener starts a local dashboard on port `8899` and an AI proxy on port `8900`. | Writing happens by email, but operation still needs visibility. Logs, health, and status matter. |
| **Deploy reality** | The wizard/one-shot deploy path has a provider registry for SiteGround and Vercel. The live post-email deploy path currently uses the SiteGround/SFTP deploy module. | Provider support exists, but SiteGround is the most complete end-to-end path today. The deploy layer still needs consolidation. |

---

## How the pipeline works

```text
Gmail plus-alias
  ↓
IMAP listener
  ↓
Dispatcher routes message to the matching inbox
  ↓
Allowed-sender check
  ↓
INGEST
  text email | article URL | video URL
  ↓
DISTILL
  normalized_input → MechanicSpec
  ↓
PLAN
  compare against spa_manifest.json
  choose new_module | extend_module | upgrade_state_only
  ↓
BUILD
  Alpine/Tailwind module generation
  deterministic shell + LLM-filled regions
  ↓
VALIDATE
  reject unsafe, incomplete, or broken generated HTML
  ↓
INTEGRATE
  write public/spa/<module_id>/index.html
  update public/spa/spa_manifest.json
  commit changes
  ↓
Astro build
  ↓
Deploy
```

The key idea is simple:

```text
source material → local LLM → interactive mechanic spec → generated SPA module → manifest-driven site
```

The pipeline is deliberately split into stages because local LLMs are powerful but messy. A single giant prompt is seductive. It is also a debugging swamp. This repo avoids that by turning the job into smaller contracts.

---

## Quick start

```bash
git clone <repo>
cd mailto-website
./scripts/dev.sh
```

`./scripts/dev.sh` does three things:

1. Creates `.venv` if it does not exist.
2. Installs workflow-engine and setup-wizard requirements.
3. Starts the local setup wizard.

After setup, run the listener directly:

```bash
./scripts/run-workflow.sh
```

The listener dashboard runs at:

```text
http://127.0.0.1:8899/
```

The AI proxy runs on:

```text
http://127.0.0.1:8900/
```

For one-off deployment after setup:

```bash
python -m apps.workflow_engine.deploy_once
```

---

## First-time setup wizard

The setup wizard is a local Flask app. It collects and writes the configuration required by the workflow engine.

<table>
<tr>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-gmail.png" alt="Gmail step" width="100%" />
<br /><sub><b>Step 1</b> - Gmail</sub>
</td>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-lmstudio.png" alt="LM Studio step" width="100%" />
<br /><sub><b>Step 2</b> - LM Studio</sub>
</td>
<td width="33%" align="center">
<img src="docs/screenshots/wizard-inboxes.png" alt="Inboxes step" width="100%" />
<br /><sub><b>Step 4</b> - Inboxes</sub>
</td>
</tr>
</table>

| Step | What you provide | What the wizard does |
|---:|---|---|
| **1. Gmail** | Gmail address and app password | Builds the IMAP/SMTP config used by the listener and failure notifications. |
| **2. LM Studio** | Local model selection and model settings | Discovers local models where possible and writes LM Studio config. |
| **3. Hosting** | SiteGround or Vercel credentials | Stores deploy configuration and provider-specific settings. |
| **4. Inboxes** | One or more site/inbox definitions | Derives plus-alias addresses and per-inbox site metadata. |
| **5. Preview** | Confirmation | Shows masked `.env` and `config.yaml`, then writes both atomically. |

<table>
<tr>
<td width="50%" align="center">
<img src="docs/screenshots/wizard-hosting.png" alt="Hosting step" width="100%" />
<br /><sub><b>Step 3</b> - Hosting picker</sub>
</td>
<td width="50%" align="center">
<img src="docs/screenshots/wizard-preview.png" alt="Preview step" width="100%" />
<br /><sub><b>Step 5</b> - Preview before writing config</sub>
</td>
</tr>
</table>

---

## Core concepts

### Inbox

An inbox is one configured publishing target.

Each inbox has:

- a `slug`
- a plus-addressed email alias
- a site name
- a site URL
- an optional per-inbox model override
- optional allowed senders
- hosting settings

### MechanicSpec

A `MechanicSpec` is the structured contract between the LLM and the builder.

It contains:

- `kind`
- `title`
- `intent`
- `inputs`
- `outputs`
- `content`
- `module_id`
- optional `source_url`

The mechanic kinds are deliberately limited:

| Kind | Intended use |
|---|---|
| `calculator` | Inputs produce a computed result. |
| `wizard` | Step-by-step decision or guidance flow. |
| `drill` | Practice, recall, quiz, repetition. |
| `scorer` | Evaluate something against criteria. |
| `generator` | Produce a variation, suggestion, quote, or transformed output. |

### SPA manifest

Each generated site has a manifest at:

```text
public/spa/spa_manifest.json
```

The SPA shell reads that manifest, builds navigation, and loads each generated module from:

```text
public/spa/<module_id>/index.html
```

### Profile state

`site_bootstrap.py` creates per-inbox profile state at:

```text
runtime/state/<slug>/profile.json
```

That file is runtime state, not public site content.

---

## Project layout

```text
apps/setup_wizard/
  Local Flask setup wizard.
  Collects Gmail, LM Studio, hosting, and inbox config.

apps/workflow_engine/
  Runtime pipeline.
  Listener, dispatcher, ingest, distill, plan, build, validate, integrate, deploy.

apps/workflow_engine/providers/
  Provider registry and deploy adapters.
  Registered providers: SiteGround and Vercel.

packages/config_contract/
  Shared dataclass/enums/validation layer used by setup and runtime.

packages/site-template/
  Astro site template copied into runtime/sites/<slug>/.
  Includes public/spa/shell.html.

runtime/sites/<slug>/
  Generated per-inbox site copy.
  This is where modules are written and committed.

runtime/state/
  Listener logs, processed-message state, locks, SSH keys, and per-inbox profile state.

scripts/
  Entrypoints for setup, listener, and background service installation.

docs/
  Setup documentation and screenshots.
```

---

## Local LLM assumptions

The workflow engine expects LM Studio to expose an OpenAI-compatible API.

Default base URL:

```text
http://localhost:1234/v1
```

The LM client includes several hard-earned local-model concessions:

- structured JSON output where supported
- fallback to plain text JSON parsing where needed
- task-specific sampling overrides
- model auto-start through the `lms` CLI
- preferred-model tracking
- fallback to already-loaded models
- context-length safety checks
- separate build strategies for stronger and weaker local models

The default build strategy is `multi`, because asking a smaller local model to emit an entire complete HTML module in one strict JSON field is fragile.

---

## Build and validation

Generated modules are expected to be:

- self-contained HTML
- Alpine.js v3 powered
- Tailwind CDN styled
- interactive
- static-host friendly
- safe enough to place inside a sandboxed iframe

The validator rejects common local-model failure modes:

- malformed or too-short HTML
- missing `x-data`
- missing event handlers
- unpinned or missing Alpine/Tailwind CDN usage
- `TODO`, `FIXME`, `placeholder`, `coming soon`, or stub code
- `x-if` on `<div>` instead of `<template>`
- `x-html`
- external fetch/XHR calls outside localhost
- ellipses inside script blocks

Generated code without validation is not a feature. It is a future incident report.

---

## Deployment status

There are two deploy paths in the repo, and they should be consolidated.

| Path | Current behaviour |
|---|---|
| **Wizard / one-shot deploy** | `deploy_once.py` uses the provider registry. The registry includes SiteGround and Vercel. |
| **Live post-email deploy** | `orchestrator.py` calls `build_and_deploy.py`, which is SiteGround/SFTP-specific. |
| **Config contract** | The shared contract knows about `siteground`, `ssh_sftp`, and `vercel`, but `ssh_sftp` is not registered as a deploy provider. |

Practical implication:

- SiteGround is the most complete end-to-end path today.
- Vercel is wired through the provider registry, especially for setup and one-shot deploy.
- Generic SSH/SFTP exists conceptually in config, but is not registered as a provider.
- The live deploy path should move behind the same provider registry used by one-shot deployment.

This is the main architectural seam to clean up.

---

## Safety model

This project writes generated code into a real website, so the guardrails are intentionally boring.

- **Allowed senders are checked before processing.** Unknown senders are recorded and ignored.
- **Each inbox has a file lock.** One inbox is processed serially to avoid clobbering generated state.
- **Generated modules are validated before integration.** Broken or unsafe HTML is rejected.
- **Writes are atomic.** Module files and manifests are written through temp files and `os.replace`.
- **Generated modules live under `public/spa/<module_id>/`.** The model is not supposed to rewrite the whole app.
- **The SPA shell uses sandboxed iframes.** Generated modules run in `<iframe sandbox="allow-scripts">`.
- **Changes are committed.** Module integration and manifest updates are git-backed.
- **Failures are reported.** If SMTP is configured, the sender can receive a failure email.

---

## Troubleshooting

Watch the listener log:

```bash
tail -f runtime/state/listener.log
```

Run one poll and exit:

```bash
./scripts/run-workflow.sh --once
```

Open the listener dashboard:

```text
http://127.0.0.1:8899/
```

Check processed messages:

```bash
cat runtime/state/processed.jsonl | tail
```

Re-run the setup wizard:

```bash
./scripts/dev.sh
```

Trigger one-shot deployment:

```bash
python -m apps.workflow_engine.deploy_once
```

---

## Known gaps

These are not cosmetic. They affect how confidently the project can be explained to another developer.

1. **The live deploy path should use the provider registry.** The post-email deploy path still uses the SiteGround-specific deploy module.
2. **Provider support needs sharper boundaries.** SiteGround is the most complete route. Vercel is partially wired. Generic SSH/SFTP is represented in config but not registered as a provider.
3. **Module extension needs product clarity.** PLAN can return `extend_module`, but the write path upserts module files by `module_id`. The difference between extending, replacing, and state-only upgrades needs to be explicit.
4. **The generated module aesthetic needs continued pressure.** The builder already bans some low-quality visual patterns, but this should keep tightening as examples accumulate.
5. **The setup flow and runtime flow should speak the same deploy language.** Right now they almost do. Almost is where future bugs breed.

---

## Philosophy

mailto.website is based on a good, stubborn idea: the inbox is already the lowest-friction capture tool most people have.

The project pushes that further. It does not just publish the email. It tries to turn the input into something usable: a calculator, wizard, drill, scorer, or generator.

That makes the boring parts more important:

- schemas
- validation
- atomic writes
- rollback
- provider boundaries
- explicit runtime state
- logs
- honest docs

The upside is significant: each inbox can become a living, interactive knowledge surface.

The risk is also clear: without tight contracts, this becomes a folder of novelty widgets generated by a model having a loud afternoon.

The repo is at its best when it leans into the disciplined version of the idea: email as input, local LLM as interpreter, static site as durable output, git as memory, validation as the adult in the room.

---

MIT License · [GitHub](.) · [docs/SETUP.md](docs/SETUP.md)

