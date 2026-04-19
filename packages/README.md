# packages/

Shared scaffolding for the email-driven self-extending sites.

- `site-template/` — the Astro template that gets copied to `runtime/sites/<inbox-slug>/`
  the first time an inbox receives mail. After that, it's owned by the
  per-inbox copy; updates to the template do not back-port automatically
  (intentional — we don't want to clobber model-curated changes).

- `config_contract/` — typed config schema shared between setup wizard and
  workflow engine. Defines `DeployProvider` enum, all config dataclasses,
  validation logic, and the `load_config()` parser. Both apps import from
  here — never duplicate validation or schema logic.

To regenerate a site from the template (destructive), run:

    python -m apps.workflow_engine.site_bootstrap --inbox <slug> --force
