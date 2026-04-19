# packages/

Shared scaffolding for the email-driven self-extending sites.

- `site-template/` — the Astro template that gets copied to `sites/<inbox-slug>/`
  the first time an inbox receives mail. After that, it's owned by the
  per-inbox copy; updates to the template do not back-port automatically
  (intentional — we don't want to clobber model-curated changes).

To regenerate a site from the template (destructive), run:

    python -m workflow.site_bootstrap --inbox <slug> --force
