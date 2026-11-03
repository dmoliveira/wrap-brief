# Read-only CI diagnostics (partial T01.03)

## Trust and completion boundary

These checks are **candidate-controlled diagnostics, not a tamper-proof admission gate**. A contributor can edit the workflow, driver, policy baseline, scanner pins or tests. Review the complete changes to these control paths at the exact delivered head; a green self-check is not authorization. GitHub currently requires the Actions-app-bound `Planning checks`, but zero independent approvals. That app binding does not identify immutable workflow contents or prevent a candidate workflow from shadowing a check name. This slice adds no required context or privileged event to disguise those limitations.

All current jobs use ordinary `pull_request`, main push or manual dispatch, `permissions: {}` by default and only job-level `contents: read`. Checkouts do not persist credentials. There is no repository/environment secret input, PAT, OIDC permission, production backend, deployment, cache restoration or uploaded artifact/report handoff. Automatic run-scoped credentials still exist; do not describe the runner as having “no credentials.” No `pull_request_target`, `workflow_run`, privileged writer or fork-controlled privileged execution is introduced.

The new `Supply-chain diagnostics` job uses a separate hosted Ubuntu 24.04 runner. It inspects committed data before installing the project and installs only isolated audit tooling. Candidate Python diagnostics/tests still execute without elevation; this separation does not make them trusted. The existing `Planning checks` job separately executes the project and builds/scans synthetic reader output, with the same read-only/no-secret/no-cache boundary.

**T01.03 remains incomplete** until an authorized cross-account fork drill verifies actual secret withholding, read-only token/write rejection, OIDC denial and unchanged sacrificial state. Same-repository PR runs, policy fixtures and the earlier protected-branch sandbox do not provide that proof. Do not activate live collection, storage mutation or deployment based on this increment.

## Pinned tooling and workflow policy

`tools/check_security.py` contains reviewed literal SHA-256 archive digests for Gitleaks **8.30.1** and actionlint **1.7.12**, for Linux x86-64 CI and macOS ARM64 development. Bootstrap uses fixed HTTPS release locations, bounds downloads, verifies the literal digest before parsing an archive, and copies only the expected regular executable member into a new directory. It never extracts arbitrary archive paths or runs an installer. Other platforms fail rather than guess an artifact.

Sources: [Gitleaks release/checksums](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1), [actionlint release/checksums](https://github.com/rhysd/actionlint/releases/tag/v1.7.12). Both platform archives were checked against published upstream manifests; CI verifies its archive against the separately reviewed literal digest. Release authors/manifests are provenance, not independent signatures.

The policy intentionally freezes the exact two approved workflow files with SHA-256 digests, then runs actual actionlint with a fresh empty configuration and external ShellCheck/Pyflakes integrations disabled. This is a narrow allowlisted workflow baseline, **not a custom YAML parser**. New workflows, changed action pins, permission/event changes, cache/credential changes, interpolation or check-shadowing additions fail the baseline until the complete workflow is reviewed and its literal digest deliberately updated. Updating the driver or baseline is itself a control-plane change requiring review; this self-check cannot enforce that review.

## Exact committed tree and reachable history

`publication` reads the exact checked `HEAD` through `git ls-tree` and `git cat-file`, not the working directory, index or `git archive`. Export-ignore attributes and later working-tree edits therefore cannot hide committed blobs. Local uncommitted work is **not** included: commit a validated slice locally, scan it, then push. Publication staging/evidence updates still need the usual manual staged/ignored-file inspection.

Limits are 2,000 tracked files, 2 MB per blob and 32 MB total. Only regular Git file modes are supported; symlinks/submodules, unsafe paths and incomplete reads fail. Current-tree private-file/machine-path/session-marker checks supplement—not replace—the existing plan publication heuristics and manual privacy/rights review.

History scanning requires a non-shallow checkout and preflights local object counts/sizes (40,000 objects; 2 MB each; 256 MB total). Gitleaks scans **locally fetched reachable refs**, including deleted-file and explicit first-parent merge diffs, using `--all --full-history --diff-merges=first-parent --text --no-ext-diff --no-textconv`. The merge option covers credentials introduced only during a merge and deleted before HEAD. It does not claim to inspect deleted/unreachable objects, every historical GitHub PR or unfetched external fork history. Full-depth CI checkout provides the current fetched inventory; missing/shallow history is not a clean scan. Database sidecar names, including uppercase and journal/WAL/SHM variants, are rejected in the current public tree.

Every scanner call forces a fresh configuration extending embedded defaults, an empty controlled ignore file, ignored `gitleaks:allow` comments and two levels of supported decoding. Candidate `.gitleaks.toml`, ignore files, configuration environment variables, baselines and actionlint suppression files are not used. There are no project-specific credential suppressions. Built-in heuristic allowlists and unsupported encodings/archive formats remain scanner limitations—not proof that all confidential information is absent.

Both tool output streams are withheld; only fixed summaries escape. Redaction is also enabled, but is not relied upon to hide paths, author metadata, malicious error strings or findings. No raw report, SARIF, log or finding artifact is uploaded. Tool errors, limits, timeouts or findings fail closed.

## Complete Python coordinate audit, without dependency resolution

The dependency check validates strict exact name/version/hash metadata from the committed `pyproject.toml`, every external `uv.lock` package, the exact `uv_build`/actual CI UV pins, and the auditor's own transitive lock. The current inventory is **31 package coordinates**, including 28 isolated auditor packages. Every locked wheel/sdist URL must use the canonical HTTPS `files.pythonhosted.org/packages/` origin without credentials, alternate ports, query strings or fragments; a nominal PyPI source field alone is insufficient. Unsupported URLs, editable external packages, requirements directives/extras/markers, dynamic metadata, custom indexes and build hooks are rejected rather than silently omitted. The existing local project entry is not sent as a package. UV separately verifies lock/declaration consistency without builds.

`.github/security/audit-requirements.txt` pins **pip-audit 2.10.1** and its complete tool-only wheel set. It is not a runtime dependency or a change to the product lock. Pins were resolved with UV, then constrained to published hashed wheels: pure Python wheels plus CPython 3.13 macOS ARM64/Linux x86-64 wheels for msgpack. Installation uses a fresh Python 3.13 environment, explicit public PyPI, `--require-hashes --only-binary :all: --strict`, never project installation or source-build hooks. New tooling pins need review just like application dependencies.

The driver emits validated plain requirements, then invokes the isolated auditor with `--strict --no-deps --disable-pip --require-hashes`. It never passes arbitrary candidate requirements to a resolver. Project/build/UV coordinates are queried, not installed. Public package names/versions are disclosed to PyPI's advisory service; no feed, private state or credentials are sent. Complete JSON coverage is required: unknown/skipped/missing/duplicate packages, any known advisory, service failure or malformed results fail. Advisory data is time-dependent and cannot prove the absence of undisclosed vulnerabilities. Action/Go binary internals are pinned/reviewed, not falsely covered by this Python inventory audit.

## Current public-output inventory

The separate project job builds the committed synthetic `digest`, `corrected` and `empty` views plus the independently collected/built/checked [CLI candidate](pipeline-cli.md). `artifacts` requires exactly these four directories: legacy `index.html`/`styles.css` pairs and CLI `index.html`/`styles.css`/`manifest.json`, **nine files total**, no uploads. It rejects symlinks, extra/missing paths, nonregular/executable/hard-linked files, changed reads and oversized HTML (1 MiB), CSS (64 KiB) or CLI manifest (16 KiB), then scans a fresh data-only copy. Enumeration fails as soon as an inventory exceeds its fixed count. Producers must finish before scanning. The private execution envelope remains outside this inventory; the rest of `.local/` is never scanned or uploaded.

This covers only today's hand-authored HTML/CSS previews and bounded CLI safe manifest, **not arbitrary/future Pages/RSS/JSON/analytics artifacts**, publisher retention, cache erasure or production artifact approval. Extend the explicit inventory and tests before adding a new public format.

## Contributor commands and rollback

Start with `make help` and `make validate`. Public scanner bootstrap needs no GitHub token:

```sh
python3 tools/check_security.py bootstrap --directory .local/security-bin
make check-publication GITLEAKS=.local/security-bin/gitleaks ACTIONLINT=.local/security-bin/actionlint
```

The scan targets committed `HEAD`. Build all three legacy views and the CLI candidate as CI does before `make check-artifacts GITLEAKS=.local/security-bin/gitleaks`; existing preview directories must not be overwritten. Use `inventory --directory <fresh-private-directory>` to emit strict `tool.txt`/`all.txt`, install the tool-only hash lock as CI does, then `make audit-dependencies AUDITOR=<isolated-pip-audit-path>`.

Actual scanner regressions require `WRAP_BRIEF_GITLEAKS` pointing to the checksum-verified executable; ordinary offline unit runs explicitly skip those five integration tests when it is absent. CI always supplies it in the separate diagnostics job. Synthetic canaries are constructed only in temporary local repositories/output and never pushed or printed; the new JSON probe covers the CLI manifest too.

Rollback is a reviewed PR revert. No schema, credential, external state, production service or deployment is changed. Preserve existing branch protection; never bypass a required check to repair tooling. Evidence and remaining fork prerequisite: [T01.03](../evidence/T01.03-ci-safety.md).
