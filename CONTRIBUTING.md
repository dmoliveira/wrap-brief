# Contributing to Wrap Brief

Wrap Brief is currently an offline synthetic prototype, not a live news service. Start with [AGENTS.md](AGENTS.md), [current progress](docs/plan/STATUS.md) and one dependency-ready task in the [backlog](docs/plan/BACKLOG.md). Discuss scope before adding services, dependencies or integrations. Later roadmap entries are not activation permission.

## Safe reporting first

**Issues, pull requests, attachments and Actions logs are public.** Never paste credentials, exploit payloads, private logs, machine paths, publisher feeds, private correspondence, user/payment data or runtime databases. Use minimal hand-authored synthetic examples and reserved example-domain URLs instead. A screenshot can disclose private tabs, names or account details: inspect/redact it before sharing.

For vulnerabilities or suspected exposed credentials, use the **private** route in [SECURITY.md](SECURITY.md), not a public bug report. If the private form is unavailable, stop without posting sensitive details; do not fall back to public issues. Revoking an exposed credential comes before deleting its visible copy.

## Local setup and checks

Use Python 3.13 for development; compatibility tests also cover 3.11. Install UV 0.13.4 or newer, then:

```sh
make help
make sync
make validate
make test-wheel
```

The locked package includes Ruff and unittest-based tests. See the [validation policy](docs/validation-policy.md) for the touched-surface risk bundle. Tests do not need publisher credentials or private agent tooling. Optional browser checks use external developer tools as described in [web/README.md](web/README.md); they are not site dependencies. Do not weaken a lock, test, protection rule or permission to get a green result.

## Fork and PR workflow

1. Fork the public repository, clone your fork and add the upstream repository as a remote. No service account, personal token, publisher credential, repository secret or Codememory installation is required to change code and run local checks.
2. Use a focused branch and dedicated worktree for the chosen task; preserve unrelated work. Never work directly on `main`.
3. Make a small deterministic change with synthetic fixtures, type hints at public Python boundaries and accompanying tests. Python uses UV/Ruff. HTML must remain usable without JavaScript and escape hostile source fields.
4. Edit `docs/plan/backlog.json` only when task status/evidence actually changes; run `make render-plan`. Never hand-edit generated `BACKLOG.md` or `STATUS.md`.
5. Run relevant checks, inspect the exact staged files, scan candidate/history for credentials and review your public commit identity. `.gitignore` does not erase already tracked data or replace scanning. Do not commit generated sites, local databases, caches, private logs or agent state.
6. Open a PR against upstream `main`. Fill in Summary, Validation and Rollback with actual commands/results, stable task ID and public-safe evidence. Name missing checks/blockers explicitly. A specification or passing unit test alone does not complete its product task.
7. Wait for the required **Planning checks** job and resolve review findings. Fork Actions may require maintainer approval; that platform gate is not a request to send credentials. Maintainers must not run untrusted fork code with secrets or write permissions.

The current PR workflow uses unprivileged `pull_request`, root `permissions: {}`, job `contents: read`, no secret references and checkout credentials disabled. It does not deploy or write state. This is the configured contribution path, **not** a claim that every malicious fork scenario has been executed; the broader adversarial workflow drill belongs to T01.03.

## Ownership, review and licensing

The public maintainer is [@dmoliveira](https://github.com/dmoliveira). [CODEOWNERS](.github/CODEOWNERS) routes review requests; it does not grant permissions. Current account-tier enforcement requires a PR and current required check even for admins, but **zero independent approvals are platform-mandatory**. Recorded review is a project delivery requirement, not a claim of enforced two-person approval. See [repository governance](docs/specs/repository-governance.md).

Do not assume public visibility grants a code license or invent contribution terms. Explicit code licensing and inbound contribution terms remain T01.04; no CLA or license grant is introduced here. Publisher content is separately rights-gated. Submit only changes you are authorized to propose and do not copy unapproved articles, artwork or private data into fixtures.

Live source permissions, private durable state, real screen-reader validation and commercial gates remain strict. Contributors must not activate collection, deployment, analytics, payments or ads through an unrelated PR.
