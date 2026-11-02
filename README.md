# Wrap Brief

**Nintendo news. Less repetition.** One story, a well-chosen lead source, and other perspectives a click away.

Independent, unofficial, public-source news aggregation. Not affiliated with, endorsed by, or sponsored by Nintendo. The name is a working selection; brand/domain clearance is still a launch task.

## Current state

This repository contains the **delivery plan and its validation tools**, not a working news site. No feeds, scheduled collection, Pages deployment, tracking, advertising, or payment integration are enabled. Planning completion must never be reported as product completion.

- [Progress and next ready work](docs/plan/STATUS.md)
- [Complete epic/task/subtask backlog](docs/plan/BACKLOG.md)
- [Milestones, parallel lanes, and release gates](docs/plan/new/roadmap.md)
- [Architecture and extension boundaries](docs/specs/architecture.md)
- [Reader experience](docs/specs/reader-experience.md)
- [All documentation](docs/index.md)

## Start small

1. Build a safe, attractive fixture-only digest.
2. Onboard **3–5 approved feeds**, retain complete normalized metadata, and publish daily at **06:23 UTC**.
3. Validate reliability, grouping quality, accessibility, reader value, and operator effort.
4. Add sources, original editorial context, RSS, and useful discovery features incrementally.
5. Enable support or other monetization only after hosting, privacy, provider, and disclosure gates pass.

Proposed product: Python managed with `uv`, `ruff`, a small safe XML parser, static HTML/CSS, optional tiny JavaScript, GitHub Actions, and GitHub Pages. No paid AI, database service, reader accounts, or image scraping in the MVP. A public repository on standard GitHub-hosted runners does not consume the account's included compute allowance; storage, external services, and Pages policy still matter.

## Inspect and maintain the plan

The current planning tools use only Python's standard library; Python 3.11+ is sufficient.

```sh
make help
make check-plan
make test-plan
make next
```

Edit `docs/plan/backlog.json`, then run `make render-plan`. Do not hand-edit generated `BACKLOG.md` or `STATUS.md`. See [delivery workflow](docs/delivery-workflow.md) for state transitions and completion evidence. The tooling reports progress and readiness; it does not implement tasks or deploy anything.

With Ruff installed, `make validate` runs the complete local plan/test/lint/format gate. Validation evidence currently uses Ruff 0.16.2; an isolated installation can be provided with `uv tool install ruff==0.16.2`.

## Public repository safety

Public source does **not** mean public credentials, raw logs, subscriber lists, payment records, or agent databases. Only explicitly public configuration belongs here. Read [SECURITY.md](SECURITY.md) and [the security/privacy spec](docs/specs/security-privacy.md) before adding integrations. Never paste production credentials into issues or pull requests.

Code and third-party feed content need separate licensing decisions. Until an explicit project license is selected in the foundation milestone, public visibility is not a grant of an open-source license. Publisher content is never covered by our eventual code license.
