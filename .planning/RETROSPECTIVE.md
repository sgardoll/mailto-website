# Retrospective

Living document. One section per milestone.

## Milestone: v1.0 — Onboarding Wizard + SiteGround Deploy

**Shipped:** 2026-04-20
**Phases:** 4 | **Plans:** 19 | **Commits:** 80 | **Tests:** 92 passing

### What Was Built

A local browser-based onboarding wizard for the email-to-website pipeline. Users clone the repo, run `./scripts/setup.sh`, walk through Gmail → LM Studio → Hosting → Inboxes → Preview → Write → Deploy, and end with config written atomically and — for SiteGround targets — a live deployed site.

### What Worked

- **Pure builder module as the contract seam.** Splitting `setup/builder.py` (pure validator + builder) from `setup/server.py` (Flask + I/O) made the whole thing testable without spinning up Flask. 58 builder tests run in < 200ms with no network.
- **Preview before write.** Catching masking bugs visually during development was faster than writing extra unit tests for them.
- **Atomic pair-write with rollback** was specced up front. When the inevitable mid-write failure mode showed up in tests, the rollback worked on the first try.
- **Shipping the in-wizard deploy as a scope expansion rather than a new phase.** User flagged "run this shell command" as poor UX during Plan 04-03's human-verify checkpoint; we extended the plan to add `POST /deploy` + progress panel same-day. No context lost to replanning.

### What Was Inefficient

- **First-iteration guesses on the success screen.** Shipped a "Start Workflow" log-tail launcher, then replaced it with a "View Your Site" link, then replaced that with a proper "Deploy Site" launcher — three iterations in one afternoon because the goal shifted ("the site should deploy with the config we just set up"). Earlier discussion of the true post-write handoff would have saved two rewrites.
- **SSH key UX was wrong on first ship.** Asked for a file path when SiteGround hands you the key as text. Caught in the wild when deploy failed with `FileNotFoundError`. Textarea + on-submit file persistence at 0600 is the right approach.
- **Paramiko's error messages needed unwrapping.** `AuthenticationException` (passphrase missing) and `OSError: Failure` (path outside home) were both opaque until we added targeted error translation. Next time, wrap third-party exceptions at the boundary before surfacing them.
- **REQUIREMENTS.md checkboxes went stale.** 22 of 33 were unchecked at audit time despite shipped code. The phase-close workflow should check these automatically, not rely on milestone audit to catch up.

### Patterns Established

- **Pre-commit read-before-edit hook is advisory only.** Its `additionalContext` message isn't a block — proceed after reading.
- **Per-plan SUMMARY.md frontmatter should include `requirements-completed`** so milestone audit can cross-reference without reading the whole doc.
- **Wizard state is the authority** — raw form payload is ephemeral. Any secret that needs to persist beyond request scope must be written to disk during its originating step submit, not at `/write-config` time.
- **"Scope expansion" is a first-class move** when the original plan's deliverable misses the actual user need. Document it in SUMMARY.md so it's not lost.

### Key Lessons

1. **Ask the user "what's the actual handoff?" before building the final screen.** I built three different success screens before landing on "button that deploys + link to live URL."
2. **Pasteable textareas beat filesystem paths for secrets providers give you as text.** No copy-save-chmod-type.
3. **Paramiko exceptions lie.** `AuthenticationException` can mean passphrase-protected key with no passphrase provided. Translate at the boundary.
4. **Phase-4 UAT after execute-phase caught zero new issues** — because Stuart had personally used the wizard end-to-end during the day. Formal UAT is still worth writing as verification evidence but the real quality gate was the real deploy against a real SiteGround account.
5. **Config.py silently ignoring unsupported provider blocks was the cleanest deferral mechanism.** Users can write Netlify config today; runtime just doesn't use it yet. Phase 5 lights it up without a migration.

### Cost Observations

- Model mix: mostly Sonnet 4.6; single switch to Opus 4.7 for plan-mode deliberation on the deploy-from-wizard scope question
- Sessions: 2 (one evening + one morning)
- Notable: 80 commits / 22 wall-clock hours → ~3.6 commits/hr average; burst rate during afternoon UI iterations was closer to 10/hr

## Cross-Milestone Trends

*(Populated as future milestones ship.)*
