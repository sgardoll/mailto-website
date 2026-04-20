# packages/

Shared scaffolding behind every site the workflow builds.

## `site-template/`

The Astro 5 template that gets copied to `runtime/sites/<inbox-slug>/` the first time an inbox receives mail. After that it's owned by the per-inbox copy — updates to the template intentionally do **not** back-port (we don't want to clobber LM-curated content).

The template is deliberately minimal:

- **`src/content/config.ts`** — the Zod content-collection schema. This is the single source of truth for what the LM is allowed to write. `entries` must reference at least one `thread` (the "fold in, don't silo" rule is enforced here, not just in the prompt).
- **`src/layouts/Base.astro`** — site chrome: header, nav, footer. All hrefs prefixed with `import.meta.env.BASE_URL` so the same template works whether deployed at `/`, `/it/`, or any other subpath.
- **`src/pages/`** — home + per-collection list and detail pages. Generic enough to look reasonable for any topic the inboxes evolve into.
- **`public/styles/global.css`** — typography + layout. Restrained on purpose; let the content carry the visual weight.

To regenerate a site from the current template (destructive — drops all LM-curated content for that inbox):

```bash
python -m apps.workflow_engine.site_bootstrap --inbox <slug> --force
```

## `config_contract/`

Typed config schema shared between the setup wizard and the workflow engine. Holds the `DeployProvider` enum, every config dataclass, the validation rules, and the `load_config()` parser.

**Both apps import from here — never duplicate validation or schema logic between the wizard and the engine.** If the contract changes, both apps get the new contract for free.
