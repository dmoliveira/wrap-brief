# Wrap Brief

**Nintendo news. Less repetition.** One story, a well-chosen lead source, and other perspectives a click away.

Independent, unofficial, public-source news aggregation. Not affiliated with, endorsed by, or sponsored by Nintendo. The name is a working selection; brand/domain clearance is still a launch task.

## Current state

This repository contains the **delivery plan, progress tooling, core contracts, synthetic fixture library, and offline RSS/Atom parser**, not a working news site. No live feeds, scheduled collection, Pages deployment, tracking, advertising, or payment integration are enabled. Component completion must never be reported as a working product.

- [Progress and next ready work](docs/plan/STATUS.md)
- [Complete epic/task/subtask backlog](docs/plan/BACKLOG.md)
- [Milestones, parallel lanes, and release gates](docs/plan/new/roadmap.md)
- [Architecture and extension boundaries](docs/specs/architecture.md)
- [Reader experience](docs/specs/reader-experience.md)
- [Implemented data/config API](docs/specs/contracts.md)
- [Shared synthetic pipeline/reader fixtures](tests/fixtures/README.md)
- [Implemented safe feed-parser boundary](docs/specs/feed-parser.md)
- [Offline-prototype and private-state decision](docs/decisions/0001-fixtures-and-private-state.md)
- [All documentation](docs/index.md)

## Start small

1. Build a safe fixture-only prototype from hand-authored synthetic data while final source permissions remain blocked. No publisher material or network collection belongs in this prototype.
2. Onboard **3–5 approved feeds**, retain complete normalized metadata, and publish daily at **06:23 UTC**.
3. Validate reliability, grouping quality, accessibility, reader value, and operator effort under named daily supervision. Prove independent monitoring before later unattended operation.
4. Add sources, original editorial context, RSS, and useful discovery features incrementally.
5. Enable support or other monetization only after hosting, privacy, provider, and disclosure gates pass.

Product direction: Python managed with `uv`, `ruff`, a small safe XML parser when ingestion is implemented, static HTML/CSS, optional tiny JavaScript, GitHub Actions, and GitHub Pages. No paid AI, reader accounts, image scraping, or database service is required for the offline prototype. Live durable storage is selected separately before collection. A public repository on standard GitHub-hosted runners does not consume the account's included compute allowance; storage, external services, and Pages policy still matter.

## Develop locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
make help
make sync
make validate
```

Python 3.13 is the development default; CI also tests Python 3.11. `uv.lock` pins the development tools and the single runtime dependency **defusedxml 0.7.1**, justified for hostile XML. The exact `uv_build` build dependency is declared in `pyproject.toml`. Use UV 0.13.4 or newer; CI pins the audited UV 0.13.6. Run `make lock-check` to verify the lock without updating it. Dependency changes require security review and a reviewed lockfile update.

`src/wrap_brief/` is the installed package boundary. Each feature is implemented only in its own validated task. Offline contracts and synthetic fixtures may proceed under ADR 0001; collection/publication stays behind source and durable-storage approval. Tests do not fetch publisher feeds or require credentials.

The live registry starts empty. To inspect it without fetching anything:

```sh
uv run --locked python -c 'from pathlib import Path; from wrap_brief.config import load_registry; print(load_registry(Path("config/sources.json")).enabled_sources)'
```

`Source`, `Item`, and `Cluster` are immutable version-1 records with strict validation and JSON round trips. Unknown publication dates stay unknown. [Contract fixtures](tests/models/fixtures/v1.json) are hand-authored synthetic examples, never real news or publisher approval.

`wrap_brief.ingest.parsers.parse_feed` accepts bytes only and returns bounded provisional metadata. It never fetches a feed. Raw dates/URLs still require the later normalization stage; parser output must not be persisted or rendered directly.

## Inspect and maintain the plan

Planning tools still use only Python's standard library. The normal Make commands use the locked project environment; an explicit `PYTHON=python3` keeps plan inspection available without installing the package:

```sh
make help
make check-plan PYTHON=python3
make test-plan PYTHON=python3
make next PYTHON=python3
```

Edit `docs/plan/backlog.json`, then run `make render-plan`. Do not hand-edit generated `BACKLOG.md` or `STATUS.md`. See [delivery workflow](docs/delivery-workflow.md) for state transitions and completion evidence. The tooling reports progress and readiness; it does not implement tasks or deploy anything.

`make validate` runs lock consistency, plan checks, all tests, lint, and format checks with the locked Ruff 0.16.2. `make test-plan` selects the planning subset; `make test` includes installed-package checks. `make test-wheel` separately builds and installs the wheel in a temporary environment outside the checkout; CI requires this packaging check too.

## Public repository safety

Public source does **not** mean public credentials, raw logs, subscriber lists, payment records, or agent databases. Only explicitly public configuration belongs here. Read [SECURITY.md](SECURITY.md) and [the security/privacy spec](docs/specs/security-privacy.md) before adding integrations. Never paste production credentials into issues or pull requests.

Code and third-party feed content need separate licensing decisions. Until an explicit project license is selected in the foundation milestone, public visibility is not a grant of an open-source license. Publisher content is never covered by our eventual code license.
