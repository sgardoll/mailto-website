# Prompt Lab

A small Flask microsite for iterating on the prompts that tell an open-weight
LLM how to build / rebuild a user's site.

During experimentation, local LM Studio is swapped out for the *same* open-weight
models hosted on **OpenRouter** (faster wall-clock per try; no GPU contention).
Everything else mirrors production: the same system prompt, the same user
payload shape, the same `apply_changes.apply()` validator, the same
`packages/site-template` copied and `npm run build`-ed for preview.

## Features

- **Multi-select models** — tick any subset of the five M4-viable candidates and
  race them in parallel on the same prompt:
  - Qwen3-Coder-30B-A3B (Q4_K_M)
  - Qwen3-Coder-14B (Q4_K_M or Q6_K)
  - Gemma 4 26B A4B
  - Devstral-Small-2507
  - Kimi K2.5

  OpenRouter slugs are editable per row in case identifiers drift.

- **Editable prompts** — the system prompt and the full user-prompt JSON
  (`site_topic`, `existing_threads`, `existing_entries`, `incoming_email`,
  `expected_output_schema`) are both pre-filled from
  `apps/workflow_engine/prompt.py` and freely editable.

- **Per-model result cards** — rationale, operation list, reply summary,
  duration, token usage, raw JSON.

- **Simulated deployment** — click *Build & preview* on any result and the
  server:
  1. copies `packages/site-template` to `runtime/sites/prompt-lab/<preview-id>/`
  2. seeds it with the existing threads/entries from the prompt
  3. runs `apply_changes.apply()` — the real validator
  4. symlinks a shared `node_modules` (one-time install)
  5. runs `npm run build`
  6. serves the resulting `dist/` at `/preview/<preview-id>/`, exactly as a
     hosting provider would serve its document root

  The iframe in the result card lets you poke at the generated site without
  leaving the page.

## Install

```bash
pip install -r apps/prompt_lab/requirements.txt
# site-template deps are installed lazily the first time you hit "Build & preview"
```

Python 3.11+ and Node.js 20+ required (same as the rest of the repo).

## Run

```bash
# Option A — paste the key in the UI each session
python -m apps.prompt_lab.server

# Option B — set it in .env and never think about it again
echo 'OPENROUTER_API_KEY=sk-or-...' >> .env
python -m apps.prompt_lab.server
```

Then open <http://localhost:5050>.

Override the port with `PROMPT_LAB_PORT=5555 python -m apps.prompt_lab.server`.

## How deployment parity works

| Real pipeline (`orchestrator.py`)                 | Prompt Lab (`deploy_sim.py`)                      |
|---------------------------------------------------|---------------------------------------------------|
| `site_bootstrap.ensure_site(inbox)`               | `_copy_template(site_dir)`                        |
| `apply_changes.apply(site_dir, plan, dry_run=…)`  | same function — imported directly                 |
| `build_and_deploy.build(site_dir, inbox=…)`       | `_build(site_dir)` — same `npm run build`         |
| `build_and_deploy.deploy(result, cfg=…)` (SFTP)   | Flask serves `dist/` at `/preview/<id>/`          |

The Astro build is given `SITE_BASE=/preview/<preview-id>/` so internal links
resolve correctly inside the iframe.

## Files

```
apps/prompt_lab/
├── __init__.py
├── README.md              ← you are here
├── requirements.txt
├── server.py              ← Flask app + API routes
├── openrouter.py          ← thin OpenAI-compatible client pointed at OpenRouter
├── models.py              ← catalogue of LM-Studio-viable models -> OR slugs
├── defaults.py            ← system/user prompt + sample email/site index
├── deploy_sim.py          ← copy template, apply plan, npm build, serve dist/
├── static/{app.css,app.js}
└── templates/index.html
```

## Notes / gotchas

- **First preview is slow.** `npm install` runs once into a shared directory
  (~60s). Subsequent previews symlink into it and are typically < 15s end-to-end.
- **Build failures surface the Astro log tail** in the preview panel — useful
  for spotting schema errors in the plan.
- **API keys are never persisted.** The UI sends them with each request; the
  server only falls back to `OPENROUTER_API_KEY` from the env if you leave the
  field blank.
- The `runtime/sites/prompt-lab/` directory accumulates preview builds; delete
  it whenever you want a clean slate.
