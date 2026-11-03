# Wrap Brief — epics, tasks, and subtasks

> Generated from backlog.json; do not edit. Product work is unimplemented unless explicitly done with evidence.

Every task also inherits the global definition of done in [delivery workflow](../delivery-workflow.md). Later scopes are refinement plans, not a commitment to build every feature.

## E00 — Planning and evidence-driven execution

**Owner:** Delivery lead. **Outcome:** A reviewed, testable plan with truthful progress. [Specification](../plan/new/roadmap.md).

### T00.01 — Deliver the reviewed planning pack and progress tooling

**Status:** done · **Scope:** planning · **Milestone:** M0 (required) · **Risk:** low · **Size:** M
**Owner:** Delivery lead
**Dependencies:** none
**Reserved paths:** `README.md`, `AGENTS.md`, `SECURITY.md`, `docs/`, `tools/plan.py`, `tests/test_plan.py`, `Makefile`, `.gitignore`

**Deliverable:** Versioned roadmap, component specs, complete backlog, deterministic tracker and evidence.

**Done criteria:**
- Every component has owned tasks, dependencies, subtasks and measurable done criteria.
- Planning and product progress are separate; disabled work cannot block the MVP or appear ready.
**Required checks:** plan-check, plan-tests, public-safety.

**Subtasks:**
- [x] **T00.01.1** Define architecture, UX, safety and phased business gates — `done`. Done when: Specifications and roadmap cover the smallest launch and safe extension seams.
- [x] **T00.01.2** Encode epics, tasks, subtasks, dependencies and progress — `done`. Done when: Canonical backlog and generated views validate and agree.
- [x] **T00.01.3** Review, test and check publication safety — `done`. Done when: Independent review has no blocker; named checks and safe evidence are recorded.

**Completion evidence:** [docs/plan/VALIDATION.md](../../docs/plan/VALIDATION.md)

## E01 — Repository, toolchain, and governance

**Owner:** Platform maintainer. **Outcome:** Safe public collaboration and reproducible development. [Specification](../specs/security-privacy.md).

### T01.01 — Establish public repository rules and reporting

**Status:** done · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `.github/`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/specs/repository-governance.md`, `docs/evidence/T01.01-repository-rules.md`, `tests/test_governance.py`

**Deliverable:** Protected main, PR templates, private vulnerability reporting, public-safe issue guidance and ownership.

**Done criteria:**
- Required PR/check rules protect main without automation bypass.
- A fork contribution needs no secret; reporting route never invites public disclosure of credentials.
**Required checks:** repository-rule-sandbox, reporting-review.

**Subtasks:**
- [x] **T01.01.1** Configure rules and required-check strategy — `done`. Done when: Actual account-tier rules are documented and enforced on main.
- [x] **T01.01.2** Set contributor and sensitive-reporting paths — `done`. Done when: Templates and private reporting route are usable without publishing secrets.
- [x] **T01.01.3** Exercise branch/fork behavior — `done`. Done when: Test PR and blocked direct-write evidence is recorded.

**Completion evidence:** [docs/evidence/T01.01-repository-rules.md](../../docs/evidence/T01.01-repository-rules.md)

### T01.02 — Create reproducible Python and local check setup

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, `src/`, `tests/`, `README.md`, `.github/workflows/plan.yml`, `docs/evidence/T01.02-foundation.md`, `tools/check_wheel.py`, `docs/validation-policy.md`, `docs/index.md`

**Deliverable:** uv-managed package, locked minimal dependencies, ruff, unittest/fixture check entry points.

**Done criteria:**
- Fresh clone installs with the lockfile and runs fixture tests without production credentials.
- Make help describes real available targets; no unnecessary runtime framework or service.
**Required checks:** fresh-clone-setup, lint-and-unit.

**Subtasks:**
- [x] **T01.02.1** Initialize package and supported Python version — `done`. Done when: uv project and lock file resolve reproducibly.
- [x] **T01.02.2** Add lint/test/fixture commands — `done`. Done when: Formatting, lint and unit tests have documented Make targets.
- [x] **T01.02.3** Prove isolated setup — `done`. Done when: A clean environment passes the advertised commands.

**Completion evidence:** [docs/evidence/T01.02-foundation.md](../../docs/evidence/T01.02-foundation.md)

### T01.03 — Add dependency, action, and credential safety checks

**Status:** blocked · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T01.01, T01.02
**Reserved paths:** `.github/`, `pyproject.toml`, `uv.lock`, `tests/security/`, `tools/check_security.py`, `Makefile`, `README.md`, `docs/specs/ci-safety.md`, `docs/evidence/T01.03-ci-safety.md`, `docs/validation-policy.md`

**Deliverable:** Pinned actions, locked dependencies, dedicated secret/history scanning and least-privilege CI policy.

**Done criteria:**
- PR code never receives secrets/write permissions; privileged events cannot execute fork code.
- Credential scanner checks tracked tree/history and public artifacts with reviewed false positives.
**Required checks:** workflow-policy, credential-history-scan, dependency-review.

**Subtasks:**
- [x] **T01.03.1** Define trust-separated CI permissions — `done`. Done when: No elevated fork checkout or untrusted privileged execution exists.
- [x] **T01.03.2** Pin and scan supply chain/public data — `done`. Done when: Action SHAs, dependency locks and credential scanning run in CI.
- [ ] **T01.03.3** Test malicious contribution scenarios — `blocked`. Done when: A fork PR cannot deploy, write state, or access credentials.

**Block/cancel reason:** Read-only CI diagnostics and pinned scans delivered in PR #33, but an authorized cross-account malicious-fork drill is unavailable. Only the owner principal is available; verify real fork secret withholding, write/OIDC rejection and unchanged sacrificial state before completing T01.03.3. Candidate-controlled checks are not immutable admission proof; see issue #32 and docs/evidence/T01.03-ci-safety.md.

### T01.04 — Clear brand, code license, and policy copy

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** low · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `LICENSE`, `README.md`, `content/policies/`, `docs/decisions/`

**Deliverable:** Working-name checks, explicit code license, attribution/disclaimer/privacy/corrections copy.

**Done criteria:**
- Name/domain/trademark checks and unofficial presentation are recorded; no Nintendo assets are copied.
- Code licensing is explicit and separate from publisher content rights; private contact/account details stay private.
**Required checks:** brand-license-review, policy-copy-review.

**Subtasks:**
- [ ] **T01.04.1** Check Wrap Brief name and independent identity — `not_started`. Done when: Evidence supports selected name or a documented rename before launch.
- [ ] **T01.04.2** Select project license and contribution terms — `not_started`. Done when: License scope is clear and excludes third-party content.
- [ ] **T01.04.3** Write privacy, source, correction and disclaimer copy — `not_started`. Done when: Reader-facing policy text accurately reflects the no-tracking pilot.

## E02 — Source approval and versioned contracts

**Owner:** Data maintainer. **Outcome:** Small approved source set and stable producer/consumer contracts. [Specification](../specs/data-pipeline.md).

### T02.01 — Implement versioned source/item/cluster contracts

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T01.02, T02.04
**Reserved paths:** `src/wrap_brief/models.py`, `src/wrap_brief/config.py`, `config/`, `tests/models/`, `docs/specs/contracts.md`, `docs/evidence/T02.01-contracts.md`, `docs/index.md`, `README.md`, `tools/check_wheel.py`

**Deliverable:** Typed versioned public records, invariants and source registry schema.

**Done criteria:**
- Unknown dates remain null/first-seen labeled; URLs and cross-record references validate.
- Schema distinguishes source text, original editorial text, rumor/correction status and health.
- An empty-by-default registry and disabled unreviewed sources keep synthetic prototype records distinct from approved live collection.
**Required checks:** model-unit, schema-compatibility.

**Subtasks:**
- [x] **T02.01.1** Define minimal record and registry fields — `done`. Done when: Data contracts match the architecture without full text/private fields.
- [x] **T02.01.2** Implement validation and serialization — `done`. Done when: Invalid IDs, URLs, dates and references fail with bounded errors.
- [x] **T02.01.3** Add schema/version fixtures — `done`. Done when: Producers and consumers share tested stable fixtures.

**Completion evidence:** [docs/evidence/T02.01-contracts.md](../../docs/evidence/T02.01-contracts.md)

### T02.02 — Approve the first 3–5 sources

**Status:** blocked · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01, T01.04, T02.04
**Reserved paths:** `config/sources/`, `docs/sources/`

**Deliverable:** Small enabled source registry with reviewed rights/retention/attribution evidence.

**Done criteria:**
- Every enabled live source has dated approval evidence covering exact permitted fields, attribution, polling, private retention/deletion and public rendering/artifact retention.
- Unclear rights leave a source disabled; prototype-only feasibility is not approval, and private storage grants no republication rights.
- Corrections/removal and commercial/donation restrictions are recorded before activation; future additions use the same approval-plus-fixture checklist.
**Required checks:** source-rights-review, registry-validation.

**Subtasks:**
- [ ] **T02.02.1** Select complementary pilot sources — `not_started`. Done when: Candidate feasibility is resolved and final feed URLs/coverage scope are documented.
- [ ] **T02.02.2** Approve exact fields, attribution and history retention — `not_started`. Done when: A dated source-specific record covers public output, private retention/deletion, artifacts, attribution, polling and commercial restrictions; no private correspondence is committed.
- [ ] **T02.02.3** Activate and document repeatable onboarding — `not_started`. Done when: Three to five cleared feeds, or an explicitly smaller viable pilot, pass registry checks and a source addition/disable dry-run recipe.

**Block/cancel reason:** Zero approved live sources. Resolve permitted public fields, attribution, polling, retention/deletion, public rendering/artifacts and commercial restrictions before enabling any source; see docs/sources/FEASIBILITY.md and issue #4.

### T02.03 — Build synthetic feed and view-model fixtures

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01
**Reserved paths:** `tests/fixtures/`, `tests/contracts/`, `docs/evidence/T02.03-fixtures.md`, `docs/index.md`, `README.md`

**Deliverable:** Rights-safe RSS/Atom, hostile input, and renderer fixtures with injected clocks.

**Done criteria:**
- Offline fixtures cover valid, empty, malformed, hostile and timezone cases.
- No copied article bodies, real tokens, contact emails or private headers appear in fixtures.
**Required checks:** fixture-contracts, fixture-public-safety.

**Subtasks:**
- [x] **T02.03.1** Create representative RSS/Atom fixtures — `done`. Done when: Namespaces, Unicode, missing dates/GUIDs and updates are represented.
- [x] **T02.03.2** Create adversarial/edge fixtures — `done`. Done when: Redirect, encoding, XML expansion, limits and duplicate cases are synthetic.
- [x] **T02.03.3** Publish shared fixture contract — `done`. Done when: Data and UI lanes can work independently on identical expected models.

**Completion evidence:** [docs/evidence/T02.03-fixtures.md](../../docs/evidence/T02.03-fixtures.md)

### T02.04 — Review source feasibility and define the safe prototype boundary

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T00.01
**Reserved paths:** `docs/sources/`, `docs/decisions/`, `docs/index.md`, `docs/decisions/0001-fixtures-and-private-state.md`, `docs/specs/architecture.md`, `docs/specs/security-privacy.md`, `docs/specs/data-pipeline.md`, `docs/operations.md`, `README.md`

**Deliverable:** Completed source investigation with an explicit synthetic-prototype-only go; live publisher approvals remain blocked in T02.02.

**Done criteria:**
- At least three candidate feeds and their rights uncertainties are documented without implying permission.
- A reviewed ADR separates offline synthetic M1 work from final live-source approval and forbids publisher state in public Git.
- No source is enabled, provider provisioned, or live collection/publication unlocked by completing this research task.
**Required checks:** source-feasibility-review, prototype-storage-boundary-review.

**Subtasks:**
- [x] **T02.04.1** Inventory candidate feeds and terms — `done`. Done when: Candidate endpoints and publisher-specific permission gaps are recorded.
- [x] **T02.04.2** Choose and review the safe prototype/state boundary — `done`. Done when: An explicit ADR permits synthetic offline work only and requires private deletable live storage; no publisher approval is inferred.
- [x] **T02.04.3** Hand unresolved live approvals to T02.02 — `done`. Done when: The final source gate remains blocked and continues to gate T07.02.

**Completion evidence:** [docs/sources/FEASIBILITY.md](../../docs/sources/FEASIBILITY.md), [docs/decisions/0001-fixtures-and-private-state.md](../../docs/decisions/0001-fixtures-and-private-state.md)

## E03 — Bounded feed collection and normalization

**Owner:** Data maintainer. **Outcome:** Cheap, polite, secure RSS/Atom collection with honest coverage. [Specification](../specs/data-pipeline.md).

### T03.01 — Implement bounded safe feed HTTP client

**Status:** done · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01, T02.03
**Reserved paths:** `src/wrap_brief/ingest/http.py`, `tests/ingest/`, `src/wrap_brief/ingest/_http_worker.py`, `docs/specs/feed-http.md`, `docs/specs/data-pipeline.md`, `docs/evidence/T03.01-feed-http.md`, `README.md`, `tools/check_wheel.py`

**Deliverable:** Allowlisted HTTPS requests with limits, conditional headers, timeout and backoff.

**Done criteria:**
- Every redirect/destination is checked; private/metadata targets, oversized bodies and unsafe URLs are rejected.
- Request concurrency/retry budgets respect source policies and do not leak headers in logs.
**Required checks:** http-adversarial, timeout-retry-budget.

**Subtasks:**
- [x] **T03.01.1** Implement safe destination and redirect validation — `done`. Done when: Only approved hosts/public HTTPS targets can be requested.
- [x] **T03.01.2** Implement bounded transport and conditional GET — `done`. Done when: Timeouts, decompressed byte limit, redirects, retries and 304 are handled.
- [x] **T03.01.3** Test abuse and partial-source failures — `done`. Done when: One malicious/slow feed cannot monopolize the run or erase other data.

**Completion evidence:** [docs/evidence/T03.01-feed-http.md](../../docs/evidence/T03.01-feed-http.md)

### T03.02 — Parse RSS and Atom safely

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.03
**Reserved paths:** `src/wrap_brief/ingest/parsers.py`, `tests/ingest/`, `pyproject.toml`, `uv.lock`, `src/wrap_brief/ingest/__init__.py`, `tests/test_foundation.py`, `tools/check_wheel.py`, `README.md`, `docs/specs/feed-parser.md`, `docs/evidence/T03.02-parser.md`, `docs/index.md`

**Deliverable:** Pure RSS/Atom adapters using a safe locked XML dependency where justified.

**Done criteria:**
- External entities/DTD/expansion are disabled; depth/text/item bounds apply.
- Parser emits source metadata only, never raw HTML/full article/enclosure downloads.
**Required checks:** parser-unit, xml-abuse-fixtures.

**Subtasks:**
- [x] **T03.02.1** Implement small RSS/Atom adapters — `done`. Done when: Supported feed formats return the shared candidate record shape.
- [x] **T03.02.2** Enforce safe XML and field bounds — `done`. Done when: Hostile entities, nesting and oversized text fail safely.
- [x] **T03.02.3** Test format and encoding edge cases — `done`. Done when: Fixture suite passes offline with predictable item quarantine.

**Completion evidence:** [docs/evidence/T03.02-parser.md](../../docs/evidence/T03.02-parser.md)

### T03.03 — Normalize and validate public metadata

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T03.02
**Reserved paths:** `src/wrap_brief/ingest/normalize.py`, `tests/ingest/`, `src/wrap_brief/models.py`, `tools/check_wheel.py`, `README.md`, `docs/specs/normalization.md`, `docs/evidence/T03.03-normalization.md`, `docs/index.md`

**Deliverable:** Plain-text safe URLs/titles, explicit UTC, provenance, and item quarantine.

**Done criteria:**
- Publication/update/first-seen times remain distinct; ambiguous dates are not fabricated.
- Unsafe links/markup and unapproved fields cannot reach state or rendered output.
**Required checks:** normalization-unit, url-time-provenance.

**Subtasks:**
- [x] **T03.03.1** Normalize text, URLs and source references — `done`. Done when: Public fields meet length/scheme/provenance constraints.
- [x] **T03.03.2** Normalize UTC and unknown/future dates — `done`. Done when: Dates and labels retain honest semantics under injected clocks.
- [x] **T03.03.3** Test escaping/quarantine paths — `done`. Done when: Invalid entries are bounded and reported without losing valid entries.

**Completion evidence:** [docs/evidence/T03.03-normalization.md](../../docs/evidence/T03.03-normalization.md)

### T03.04 — Add incremental polling, health and gap detection

**Status:** done · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T03.01, T03.03
**Reserved paths:** `src/wrap_brief/ingest/`, `tests/ingest/`, `docs/specs/incremental-polling.md`, `docs/evidence/T03.04-incremental-polling.md`, `README.md`, `tools/check_wheel.py`

**Deliverable:** Per-source checkpoints, 304 handling, last-good fallback and possible truncation warnings.

**Done criteria:**
- Checkpoints advance only after validated source success; legitimate no-news is not a failure.
- Potential missed feed windows and partial/all-source failures are surfaced honestly.
**Required checks:** incremental-polling, truncation-and-outage.

**Subtasks:**
- [x] **T03.04.1** Persist conditional-request checkpoints — `done`. Done when: ETag/Last-Modified and poll boundaries survive independent runs.
- [x] **T03.04.2** Implement healthy/degraded/no-new outcomes — `done`. Done when: Source errors preserve prior records; all-source failure stops publication.
- [x] **T03.04.3** Detect possible feed-window gaps — `done`. Done when: Truncation fixtures produce warnings without false completeness claims.

**Completion evidence:** [docs/evidence/T03.04-incremental-polling.md](../../docs/evidence/T03.04-incremental-polling.md)

## E04 — Durable state and pipeline recovery

**Owner:** Platform maintainer. **Outcome:** Complete replayable state, safe persistence, and recovery. [Specification](../specs/architecture.md).

### T04.01 — Implement backend-neutral snapshots and local prototype state

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T05.01
**Reserved paths:** `src/wrap_brief/state/snapshot.py`, `tests/state/`, `src/wrap_brief/state/__init__.py`, `src/wrap_brief/state/local.py`, `.gitignore`, `tools/check_wheel.py`, `README.md`, `docs/specs/local-state.md`, `docs/evidence/T04.01-snapshots.md`, `docs/index.md`

**Deliverable:** Deterministic logical snapshot API and optional untracked local SQLite prototype store; no publisher state in Git or claim of runner durability.

**Done criteria:**
- Logical snapshots retain complete approved records/checkpoints and serialize deterministically; local SQLite file bytes are not the deterministic format.
- Identical inputs produce stable IDs/order; schema and references reject corrupt snapshots.
**Required checks:** snapshot-unit, idempotent-replay.

**Subtasks:**
- [x] **T04.01.1** Implement logical snapshots and local prototype store — `done`. Done when: Versioned complete records round-trip; any local database stays untracked and is not treated as live runner-durable storage.
- [x] **T04.01.2** Implement idempotent update/tombstone semantics — `done`. Done when: Repeated items do not duplicate or become artificially fresh.
- [x] **T04.01.3** Test cache/artifact independence — `done`. Done when: Loss of optional caches does not change identity or retained records.

**Completion evidence:** [docs/evidence/T04.01-snapshots.md](../../docs/evidence/T04.01-snapshots.md)

### T04.02 — Select and implement private durable state persistence

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T01.03, T04.01
**Reserved paths:** `src/wrap_brief/state/`, `tests/state/`, `.github/workflows/`, `docs/decisions/`

**Deliverable:** A reviewed private/deletable durable backend with atomic versioned writes, scoped credentials, retention and restore proof before live collection.

**Done criteria:**
- Provider/cost/credential/retention/deletion decisions are documented before use; no new provider or account is assumed available.
- Candidate data is revalidated with bounded schema/fields/bytes/references; no executable data or repository write permission is needed.
- Atomic expected-version conflicts fail safely; backups, deletion, recovery and ephemeral-runner loss are exercised.
**Required checks:** private-backend-security-review, atomic-persistence-and-deletion.

**Subtasks:**
- [ ] **T04.02.1** Select a bounded private durable backend — `not_started`. Done when: Terms, free/paid limits, access, deletion and backup behavior satisfy the approved live-state contract.
- [ ] **T04.02.2** Implement scoped atomic persistence — `not_started`. Done when: Only revalidated data reaches the backend; least-privilege secrets remain outside Git and public artifacts.
- [ ] **T04.02.3** Prove conflict, deletion and recovery behavior — `not_started`. Done when: Version conflicts, runner loss, retention/deletion and known-good restore are tested before live ingestion.

### T04.03 — Test state retention, migrations and component recovery

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T04.02, T03.04
**Reserved paths:** `src/wrap_brief/state/`, `tests/state/`, `docs/operations.md`

**Deliverable:** Component-level retention, schema migration, replay and failed-build recovery tests; operational site rollback belongs to T07.05.

**Done criteria:**
- State committed before a failed build remains available to the next complete build.
- Retention, tombstones, backup expiry and actual deletion follow source policy; restore/migration preserves IDs without depending on public Git history.
**Required checks:** state-component-recovery, migration-retention.

**Subtasks:**
- [ ] **T04.03.1** Implement bounded retention and tombstones — `not_started`. Done when: Expired/resurfaced/retracted records follow explicit non-fabricated freshness rules.
- [ ] **T04.03.2** Implement migration and known-good restore — `not_started`. Done when: Previous state version/snapshot restores with validated records/checkpoints.
- [ ] **T04.03.3** Simulate failure after persistence — `not_started`. Done when: Next build includes every retained item after a failed publish without relying on a lost runner or expiring artifact.

### T04.04 — Compose explicit collect/build/check CLI stages

**Status:** done · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T04.01, T03.04, T05.02
**Reserved paths:** `src/wrap_brief/pipeline.py`, `src/wrap_brief/cli.py`, `tests/integration/`, `tools/check_wheel.py`, `tools/check_security.py`, `tests/security/test_diagnostics.py`, `.github/workflows/plan.yml`, `Makefile`, `README.md`, `docs/specs/pipeline-cli.md`, `docs/evidence/T04.04-pipeline-cli.md`, `docs/specs/ci-safety.md`, `docs/validation-policy.md`

**Deliverable:** Composable stage commands, dry run, injected time/network and safe manifest/exit codes.

**Done criteria:**
- Each stage has explicit input/output contracts and can run from fixtures independently.
- Dry run performs no state mutation/deployment; partial failures are represented in bounded health.
**Required checks:** pipeline-fixture-e2e, dry-run-no-write.

**Subtasks:**
- [x] **T04.04.1** Implement orchestration over pure modules — `done`. Done when: Stages do not mix network, grouping, persistence and rendering concerns.
- [x] **T04.04.2** Add dry-run and safe manifest output — `done`. Done when: Outputs identify code/config/state and health without private fields.
- [x] **T04.04.3** Test whole-pipeline replay and failure exits — `done`. Done when: Fixture pipeline is deterministic and returns actionable bounded failures.

**Completion evidence:** [docs/evidence/T04.04-pipeline-cli.md](../../docs/evidence/T04.04-pipeline-cli.md)

## E05 — Identity, story grouping, and editorial trust

**Owner:** Editorial maintainer. **Outcome:** Less repetition without losing perspectives or provenance. [Specification](../specs/data-pipeline.md).

### T05.01 — Implement exact identity and conservative URL cleanup

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T03.03
**Reserved paths:** `src/wrap_brief/grouping/identity.py`, `tests/grouping/`, `src/wrap_brief/grouping/__init__.py`, `docs/specs/identity.md`, `docs/specs/data-pipeline.md`, `docs/evidence/T05.01-identity.md`, `docs/index.md`, `README.md`, `tools/check_wheel.py`, `docs/specs/architecture.md`

**Deliverable:** Source-scoped stable identity and reviewed tracking-parameter normalization.

**Done criteria:**
- Tracking variants deduplicate; article-identifying query fields remain distinct.
- Source GUID collisions/changes do not silently overwrite unrelated articles.
- Initial URL-first policy ignores GUID for identity; source-specific tracking policy can only tighten the exact reviewed allowlist. No live source is approved by hashing metadata.
**Required checks:** identity-unit, canonicalization-benchmark.

**Subtasks:**
- [x] **T05.01.1** Define GUID/URL identity precedence — `done`. Done when: Identity rules are deterministic and versioned.
- [x] **T05.01.2** Implement reviewed URL normalization — `done`. Done when: Only known tracking parameters are stripped.
- [x] **T05.01.3** Test duplicate/collision/resurfacing cases — `done`. Done when: Same item is stable while distinct editions/events remain separate.

**Completion evidence:** [docs/evidence/T05.01-identity.md](../../docs/evidence/T05.01-identity.md)

### T05.02 — Group same-event coverage and choose lead source

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T05.01, T02.03
**Reserved paths:** `src/wrap_brief/grouping/`, `tests/grouping/`, `docs/specs/story-grouping.md`, `docs/evidence/T05.02-story-grouping.md`, `docs/index.md`, `README.md`, `tools/check_wheel.py`, `Makefile`, `.github/workflows/plan.yml`, `docs/validation-policy.md`

**Deliverable:** Conservative event clusters, stable IDs, deterministic evidence-based lead ranking.

**Done criteria:**
- Rumor/confirmation, distinct Direct announcements, reviews and news do not collapse blindly.
- All alternate members retain links/provenance; commercial value never affects ranking.
**Required checks:** grouping-unit, lead-ranking-rules.

**Subtasks:**
- [x] **T05.02.1** Implement bounded similarity candidate stage — `done`. Done when: Entities/event types/time window constrain title similarity.
- [x] **T05.02.2** Implement stable groups and transparent lead choice — `done`. Done when: Primary/original/substantive coverage rules have deterministic tie-breakers.
- [x] **T05.02.3** Test ambiguous and conflicting coverage — `done`. Done when: Uncertain matches split; rumors/corrections retain explicit labels.

**Completion evidence:** [docs/evidence/T05.02-story-grouping.md](../../docs/evidence/T05.02-story-grouping.md)

### T05.03 — Benchmark grouping and add reviewed split/merge overrides

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T05.02
**Reserved paths:** `tests/benchmarks/`, `config/overrides/`, `src/wrap_brief/grouping/`

**Deliverable:** Labeled benchmark, measured precision/recall, reversible manual corrections.

**Done criteria:**
- At least 100 labeled pairs include known hard cases; automatic merge precision is at least 98% on sample.
- Overrides are reviewed, deterministic and traceable; fuzzy grouping can be disabled safely.
**Required checks:** grouping-gold-benchmark, override-replay.

**Subtasks:**
- [ ] **T05.03.1** Label representative real-event metadata pairs — `not_started`. Done when: Rights-safe benchmark covers event/edition/rumor/correction edge cases.
- [ ] **T05.03.2** Measure and tune conservative thresholds — `not_started`. Done when: Precision, recall, sample size and false merges are reported.
- [ ] **T05.03.3** Implement split/merge and disable controls — `not_started`. Done when: Reviewed overrides survive reruns without deleting source provenance.

### T05.04 — Add provenance, corrections and takedown controls

**Status:** review · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T02.01, T05.02
**Reserved paths:** `content/corrections/`, `src/wrap_brief/editorial/`, `tests/editorial/`, `src/wrap_brief/render/digest.py`, `tools/check_wheel.py`, `docs/specs/editorial-controls.md`, `docs/evidence/T05.04-editorial-controls.md`, `docs/operations.md`, `docs/index.md`, `README.md`

**Deliverable:** Source-attribution, correction/retraction and removal controls; no original-brief production system required for MVP.

**Done criteria:**
- Publisher headlines remain explicitly attributed; an MVP listing never implies original reporting or fabricated editorial context.
- A correction/removal exercise preserves honest provenance, prevents re-promotion, and covers private records, public output, deployment artifacts and owned cache removal without promising control of external copies.
**Required checks:** editorial-provenance, correction-takedown-drill.

**Subtasks:**
- [x] **T05.04.1** Preserve publisher and claim provenance — `done`. Done when: Attribution and confirmed/reported/rumor labels have explicit source evidence; absent editorial text stays absent.
- [x] **T05.04.2** Implement correction/retraction and exclusion controls — `done`. Done when: Withdrawn or changed claims cannot remain silently promoted and overrides retain traceable provenance.
- [x] **T05.04.3** Exercise source-requested removal — `done`. Done when: The reviewed remedy covers private retention/deletion, public HTML/JSON/RSS, deployment artifacts and owned caches; accidental Git publication is handled as an incident, not a storage mechanism.

## E06 — Minimalist static reader experience

**Owner:** Web maintainer. **Outcome:** Attractive, accessible, fast reading without required JavaScript. [Specification](../specs/reader-experience.md).

### T06.01 — Create responsive visual tokens and semantic shell

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T02.03
**Reserved paths:** `web/`, `src/wrap_brief/render/`, `tests/render/`, `docs/specs/reader-experience.md`, `docs/evidence/T06.01-reader-shell.md`, `README.md`, `docs/index.md`

**Deliverable:** Original minimalist mobile-first shell, typography, spacing and contrast-tested colors.

**Done criteria:**
- No copied Nintendo identity/assets, external fonts or required client framework.
- Semantic landmarks, skip link, visible focus and readable 320px layout are present.
**Required checks:** design-token-contrast, shell-mobile-keyboard.

**Subtasks:**
- [x] **T06.01.1** Translate UX spec into a small token set — `done`. Done when: Typography, spacing and accent colors pass contrast targets.
- [x] **T06.01.2** Build semantic responsive shell — `done`. Done when: Header/content/footer reflow cleanly from mobile to desktop.
- [x] **T06.01.3** Validate long text and focus states — `done`. Done when: No clipped links/labels or invisible keyboard focus.

**Completion evidence:** [docs/evidence/T06.01-reader-shell.md](../../docs/evidence/T06.01-reader-shell.md)

### T06.02 — Render grouped digest with accessible alternate sources

**Status:** done · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.01, T05.02, T04.01
**Reserved paths:** `src/wrap_brief/render/`, `tests/render/`, `web/`, `tools/build_fixture_site.py`, `tools/check_wheel.py`, `README.md`, `docs/specs/digest-renderer.md`, `docs/evidence/T06.02-digest-renderer.md`

**Deliverable:** Escaped static story cards with lead links, native disclosures and honest labels.

**Done criteria:**
- Core reading and all source links work with JavaScript disabled.
- Title/source/known time/rumor status are visible; other coverage remains reachable by keyboard.
**Required checks:** renderer-golden-html, no-js-source-navigation.

**Subtasks:**
- [x] **T06.02.1** Implement pure view models and HTML escaping — `done`. Done when: Hostile source fields render as safe text/links.
- [x] **T06.02.2** Implement cards and native coverage disclosure — `done`. Done when: Lead action and alternate publishers have descriptive links.
- [x] **T06.02.3** Build deterministic fixture homepage — `done`. Done when: Same supplied inputs/clock yield identical output files.

**Completion evidence:** [docs/evidence/T06.02-digest-renderer.md](../../docs/evidence/T06.02-digest-renderer.md)

### T06.03 — Render policies, honest health and empty/degraded states

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.02, T01.04
**Reserved paths:** `src/wrap_brief/render/`, `content/policies/`, `tests/render/`, `web/`

**Deliverable:** About/sources/privacy/corrections, absolute check time and safe empty/stale states.

**Done criteria:**
- Failed feeds are not described as no news; no-JS readers always see the absolute check timestamp.
- 30-hour stale behavior is truthful, including limits of static HTML and any optional local-clock enhancement.
**Required checks:** policy-and-health-render, empty-degraded-stale.

**Subtasks:**
- [ ] **T06.03.1** Render methodology and required policy links — `not_started`. Done when: Independent status, rights, privacy and correction route are reachable.
- [ ] **T06.03.2** Implement healthy/empty/degraded states — `not_started`. Done when: Source failures and genuine zero-new-news have different copy.
- [ ] **T06.03.3** Implement/test freshness display — `not_started`. Done when: Publication, first-seen, last-check and deployment times are not conflated.

### T06.04 — Prove core accessibility and performance budgets

**Status:** blocked · **Scope:** mvp · **Milestone:** M1 (required) · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.02
**Reserved paths:** `tests/browser/`, `tests/render/`, `web/`, `docs/evidence/`

**Deliverable:** Repeatable browser/a11y/no-JS and compressed-size checks against fixture site.

**Done criteria:**
- 320px, desktop, keyboard, screen-reader checks, 200/400% reflow and reduced-motion behavior pass.
- Initial HTML/CSS/JS <=150 KB compressed; mobile LCP/CLS targets measured with environment noted.
**Required checks:** browser-a11y-no-js, performance-budget.

**Subtasks:**
- [ ] **T06.04.1** Add repeatable browser/static checks — `in_progress`. Done when: Core read/expand/outbound tasks are tested without JS and by keyboard.
- [ ] **T06.04.2** Measure size and mobile rendering — `in_progress`. Done when: Compressed payload, LCP/CLS and test environment are recorded.
- [ ] **T06.04.3** Fix UX/a11y regressions — `not_started`. Done when: No release-blocking overflow, contrast, focus or source-navigation failure remains.

**Block/cancel reason:** Real screen-reader session outstanding: VoiceOver is installed but not running; no-prompt readiness probe returned application-not-running. Authorized real-AT testing is required; automated checks cannot establish spoken behavior. See docs/evidence/T06.04-reader-validation.md.

## E07 — CI, scheduled automation, publishing, and monitoring

**Owner:** Release maintainer. **Outcome:** A daily protected release pipeline that fails safely. [Specification](../operations.md).

### T07.01 — Wire credential-free PR CI and full fixture build

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T01.03, T06.04, T05.03
**Reserved paths:** `.github/workflows/`, `Makefile`, `tests/integration/`

**Deliverable:** Required read-only lint/unit/fixture/schema/render/workflow checks on pull requests.

**Done criteria:**
- Fork PR check paths cannot mutate state/deploy or obtain secrets.
- CI rejects invalid source/config/grouping/output and generated-plan drift.
**Required checks:** ci-fork-sandbox, full-fixture-build.

**Subtasks:**
- [ ] **T07.01.1** Assemble named required checks — `not_started`. Done when: Lint, unit, integration, schemas, HTML/links and plan checks have stable names.
- [ ] **T07.01.2** Run fixture build on fork PR — `not_started`. Done when: No production network credentials or write scopes are needed.
- [ ] **T07.01.3** Test intentionally failing changes — `not_started`. Done when: Broken contracts/unsafe workflows are blocked before merge.

### T07.02 — Schedule approved collection and isolated private persistence

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.01, T04.04, T04.02, T02.02
**Reserved paths:** `.github/workflows/`, `tests/workflows/`, `docs/operations.md`

**Deliverable:** Default-branch daily/manual collection and validated private persistence, with one mutation lock and final source approval prerequisites.

**Done criteria:**
- Only cron 23 6 * * * is enabled initially; UTC/cadence and manual default-branch restrictions are explicit.
- Read-only network collection and scoped private persistence are separated; no repository state branch is written, and only approved sources may be polled.
**Required checks:** workflow-policy, scheduled-state-sandbox.

**Subtasks:**
- [ ] **T07.02.1** Configure schedule/manual triggers and lock — `not_started`. Done when: All production mutation/recovery routes share concurrency control.
- [ ] **T07.02.2** Wire collection to validated private persistence — `not_started`. Done when: The persistence boundary revalidates exact data contracts and uses only the approved backend credentials; no publisher item data enters Git.
- [ ] **T07.02.3** Run real-source dry run and persistence sandbox — `not_started`. Done when: Approved source polling and state boundaries pass without deploying.

### T07.03 — Deploy validated static artifact through protected Pages

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.02, T06.03
**Reserved paths:** `.github/workflows/`, `tests/workflows/`, `docs/operations.md`

**Deliverable:** Read-only build from reviewed code/config and validated snapshot version; short-lived approved Pages artifact and restricted OIDC deploy.

**Done criteria:**
- Deploy job has Pages/OIDC permissions only and runs after every build gate.
- Invalid/empty-on-failure output cannot replace live site; actual public URL/manifest is smoke-tested.
**Required checks:** pages-deployment-sandbox, public-url-smoke.

**Subtasks:**
- [ ] **T07.03.1** Configure Pages source and environment restrictions — `not_started`. Done when: Only reviewed default-branch releases can deploy.
- [ ] **T07.03.2** Wire build/validate/upload/deploy jobs — `not_started`. Done when: Artifact root, entry point, retention and manifest are correct.
- [ ] **T07.03.3** Exercise successful and failed publication — `not_started`. Done when: Known-good site survives a pre-deploy failure; live output matches manifest.

### T07.04 — Add health reporting and supervised pilot checks

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.03
**Reserved paths:** `.github/workflows/`, `src/wrap_brief/health.py`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** Public minimal health manifest, failed-job notifications and a named daily supervision procedure; independent monitoring gates later unattended mode.

**Done criteria:**
- A named maintainer role checks freshness/source health daily and records escalation for a 30-hour stale result; a disabled schedule is not assumed self-monitoring.
- Alerts and health omit credentials/private contacts; pilot is explicitly supervised until independent stale monitoring is proven.
**Required checks:** health-and-supervision-drill, alert-redaction-and-dedupe.

**Subtasks:**
- [ ] **T07.04.1** Emit bounded collection/source/deployment health — `not_started`. Done when: Manifest distinguishes successful collection, deployment, source failures and possible feed gaps.
- [ ] **T07.04.2** Define named daily supervision and failure notification — `not_started`. Done when: Maintainer role, daily check, 30-hour threshold and escalation are documented without publishing private contacts.
- [ ] **T07.04.3** Exercise failed and disabled schedule detection — `not_started`. Done when: Supervised checks notice stale/missed runs; no claim of unattended operation is made. Independent monitoring moves to T11.01.

### T07.05 — Rehearse known-good rollback and state restore

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.03, T04.03
**Reserved paths:** `.github/workflows/`, `tests/recovery/`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** One operational rollback/restore drill using reviewed code/config refs plus private snapshot versions and reusable public-safe evidence.

**Done criteria:**
- Rollback does not depend only on expiring artifacts and does not erase valid unseen state.
- Practical restore time is measured against a 30-minute target and public URL is checked.
- T08.04 and the release checklist reference this drill; they do not rerun it unless inputs or recovery behavior change.
**Required checks:** deployment-rollback-drill, state-restore-drill.

**Subtasks:**
- [ ] **T07.05.1** Implement guarded manual recovery route — `not_started`. Done when: Reviewed code refs and validated private snapshot versions are selected under the shared production lock; arbitrary downloads are not accepted.
- [ ] **T07.05.2** Restore known-good site and state in sandbox — `not_started`. Done when: IDs/checkpoints/tombstones and live manifest remain coherent.
- [ ] **T07.05.3** Record operational recovery evidence — `not_started`. Done when: Elapsed time, outcomes, resume criteria and residual limitations are documented.

## E08 — Security, UX, and live pilot release

**Owner:** Release maintainer. **Outcome:** Demonstrated readiness, not completion inferred from green unit tests. [Specification](../validation-policy.md).

### T08.01 — Complete adversarial and public-surface security review

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.04, T07.05
**Reserved paths:** `tests/security/`, `docs/evidence/`, `SECURITY.md`

**Deliverable:** Threat-driven tests and scan evidence across repo/history/state/artifacts/logs/output.

**Done criteria:**
- Unsafe feed URLs/XML/HTML/artifact paths and privileged fork scenarios are rejected.
- No credentials, user/payment data, private contact fields or runtime state is published.
**Required checks:** full-adversarial-suite, public-surface-scan, security-review.

**Subtasks:**
- [ ] **T08.01.1** Test input and privilege attack paths — `not_started`. Done when: SSRF, XML abuse, XSS, writer traversal and fork escalation cases pass.
- [ ] **T08.01.2** Inspect all public publication surfaces — `not_started`. Done when: Dedicated scanner plus manual classification review finds no unresolved secret.
- [ ] **T08.01.3** Resolve high-severity findings — `not_started`. Done when: Security review signs off the actual integrated release candidate.

### T08.02 — Validate the integrated reader flow with users

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** medium · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T06.03, T06.04, T05.03
**Reserved paths:** `docs/evidence/`, `web/`, `tests/browser/`

**Deliverable:** Observed reader tasks, accessibility/performance results and repaired usability failures.

**Done criteria:**
- At least five representative sessions test check time, rumor, source comparison and publisher navigation.
- Core mobile/keyboard/no-JS flow and performance guardrails pass on the integrated candidate.
**Required checks:** reader-task-sessions, integrated-a11y-performance.

**Subtasks:**
- [ ] **T08.02.1** Prepare realistic story scenarios — `not_started`. Done when: Long headlines, rumors, corrections, many sources and stale/empty states are covered.
- [ ] **T08.02.2** Observe reader tasks and accessibility — `not_started`. Done when: Findings distinguish observed behavior from assumptions.
- [ ] **T08.02.3** Repair and recheck material failures — `not_started`. Done when: No blocker remains in core comprehension or outbound reading.

### T08.03 — Release and verify the daily public pilot

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T08.01, T08.02, T07.04, T07.05, T05.04, T08.04
**Reserved paths:** `docs/evidence/`, `docs/plan/`, `.github/`

**Deliverable:** Noncommercial pilot release with cleared sources, live checks and first scheduled cycle evidence.

**Done criteria:**
- All prerequisite MVP tasks and source/brand/security/recovery gates pass; no tracking or monetization is enabled.
- Actual Pages site and next scheduled cycle are checked; supervised ownership and limitations are visible.
- Any security-relevant change after T08.01 receives a scoped delta review before release; this task does not require its own prior completion.
**Required checks:** release-gate-checklist, live-pilot-and-next-cycle.

**Subtasks:**
- [ ] **T08.03.1** Audit integrated launch checklist — `not_started`. Done when: Prerequisite evidence is complete and changes since final security review have been checked; T08.03 itself is completed only after release verification.
- [ ] **T08.03.2** Publish and smoke-check pilot — `not_started`. Done when: Public URL has expected content, links, policies, safe state and freshness.
- [ ] **T08.03.3** Verify next daily cycle and handoff — `not_started`. Done when: Scheduled update, alerts and operator runbook work in live operation.

### T08.04 — Review contributor/operator handoff using existing evidence

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 (required) · **Risk:** medium · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.05, T01.03
**Reserved paths:** `CONTRIBUTING.md`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** Usable contributor and incident handoff referencing existing security/recovery evidence rather than duplicating drills.

**Done criteria:**
- A maintainer can follow source-disable, failure-triage and restore instructions using the evidence owned by T07.05 and T08.01.
- Public contributor instructions are verified against the existing T01.02 clean-clone result; only changed steps are rerun.
**Required checks:** operator-handoff-review, contributor-docs-evidence-review.

**Subtasks:**
- [ ] **T08.04.1** Assign routine maintenance and incident ownership — `not_started`. Done when: Weekly source/quality/cost reviews and escalation have an accountable maintainer role.
- [ ] **T08.04.2** Review runbooks against existing drills — `not_started`. Done when: Links to T07.05 recovery and T08.01 security evidence are correct; no redundant restore tabletop is required.
- [ ] **T08.04.3** Check contributor documentation against clean-clone evidence — `not_started`. Done when: Instructions match T01.02 setup and current CI; rerun only behavior changed since that evidence.

## E09 — Original value and audience validation

**Owner:** Product/editorial maintainer. **Outcome:** Measure useful repeat readership and operator workload before growth. [Specification](../specs/growth-monetization.md).

### T09.01 — Decide measurement approach; instrument only if approved

**Status:** not_started · **Scope:** growth · **Milestone:** M3 (required) · **Risk:** high · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T08.03
**Reserved paths:** `docs/decisions/`, `content/policies/`, `web/`, `tests/privacy/`

**Deliverable:** Evidence-based no-tracking or approved-minimal-measurement decision with honest metrics and privacy controls.

**Done criteria:**
- A documented no-tracking decision is a valid completion outcome; operational, editorial-output, workload and cash-cost metrics can support M3.
- Any instrumentation has provider/data/legal/performance review; unique-reader/retention/attribution claims require an actually approved method.
**Required checks:** privacy-data-inventory, measurement-accuracy.

**Subtasks:**
- [ ] **T09.01.1** Choose no-tracking or minimal approved provider — `not_started`. Done when: Data categories, region/consent basis, retention and access are recorded.
- [ ] **T09.01.2** Implement only if approved, or document no-tracking — `not_started`. Done when: No-tracking remains the default; any chosen instrumentation stays within approved consent/data/performance boundaries.
- [ ] **T09.01.3** Validate counts and honest reporting — `not_started`. Done when: Known test events match documented metric denominators/limitations.

### T09.02 — Publish original digest, public RSS and selective SEO

**Status:** not_started · **Scope:** growth · **Milestone:** M3 (required) · **Risk:** medium · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T08.03, T05.04
**Reserved paths:** `content/`, `src/wrap_brief/render/`, `tests/seo/`, `docs/evidence/`

**Deliverable:** Original-brief model and review workflow, useful recurring editorial content, public RSS and quality-first search metadata.

**Done criteria:**
- Only substantive original/curated pages are indexed; no thin per-keyword page explosion.
- Canonical/sitemap/robots/feed links are accurate and all publisher attribution is preserved.
**Required checks:** editorial-and-seo-review, rss-and-metadata-validation.

**Subtasks:**
- [ ] **T09.02.1** Implement and publish a reviewed original digest — `not_started`. Done when: Original briefs have a minimal content model, byline, cited sources and review state; sustainable effort is recorded separately from MVP source listings.
- [ ] **T09.02.2** Add RSS and accurate discovery metadata — `not_started`. Done when: Feed, canonical, sitemap and share metadata validate without unlicensed assets.
- [ ] **T09.02.3** Review indexability and acquisition channels — `not_started`. Done when: Thin/duplicate pages are excluded and community sharing follows rules.

### T09.03 — Establish four-week reader-value and cost baseline

**Status:** not_started · **Scope:** growth · **Milestone:** M3 (required) · **Risk:** medium · **Size:** M
**Owner:** Product/editorial maintainer
**Dependencies:** T09.01, T09.02
**Reserved paths:** `docs/evidence/`, `docs/experiments/`

**Deliverable:** Four-week aggregate reliability, quality, reader-value and operator-effort report.

**Done criteria:**
- Report actual available metrics and missing-data limitations, not invented retention.
- Cash costs and operator minutes have reproducible definitions and a sustainable workload cap.
**Required checks:** baseline-data-review, operator-cost-review.

**Subtasks:**
- [ ] **T09.03.1** Collect four weeks of approved observations — `not_started`. Done when: Reliability, source quality, editorial effort and measured audience data are complete enough to interpret.
- [ ] **T09.03.2** Compute contribution and workload baseline — `not_started`. Done when: Fees/tools/time are included with an explicit operator rate.
- [ ] **T09.03.3** Decide next smallest improvement — `not_started`. Done when: Keep/change/stop decision cites reader value and actual cost.

### T09.04 — Run one ethical engagement experiment

**Status:** not_started · **Scope:** growth · **Milestone:** M3 (required) · **Risk:** medium · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T09.03
**Reserved paths:** `docs/experiments/`, `content/`, `web/`, `tests/browser/`

**Deliverable:** One time-boxed experiment such as digest placement or source navigation, with guardrails.

**Done criteria:**
- Hypothesis, time/cash cap, measurement method and stop/rollback rule precede implementation.
- No modal/forced signup/dark pattern; source referrals, accessibility and performance are protected.
**Required checks:** engagement-experiment-review, ux-guardrail-check.

**Subtasks:**
- [ ] **T09.04.1** Select one evidence-led engagement change — `not_started`. Done when: Baseline supports the chosen reader problem.
- [ ] **T09.04.2** Ship a small reversible experiment — `not_started`. Done when: Only approved data and an accessible no-JS baseline are used.
- [ ] **T09.04.3** Evaluate and keep/change/stop — `not_started`. Done when: Observed benefit and operator cost determine the result.

## E10 — Gated support and commercial experiments

**Owner:** Business maintainer. **Outcome:** One reversible, disclosed, measurable revenue channel at a time. [Specification](../specs/growth-monetization.md).

### T10.01 — Resolve commercial hosting, provider and financial gates

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 (required) · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T09.04
**Reserved paths:** `docs/decisions/`, `content/policies/`, `docs/evidence/`

**Deliverable:** Public-safe go/no-go decision for hosting, provider terms, disclosures, privacy and financial obligations.

**Done criteria:**
- Pages commercial-use uncertainty is resolved appropriately or hosting migrates before money features.
- Provider account/secrets and private tax/payment details are never committed.
**Required checks:** commercial-policy-review, provider-privacy-finance-review.

**Subtasks:**
- [ ] **T10.01.1** Review current hosting and provider policies — `not_started`. Done when: Document compatible use or select/migrate to an appropriate host.
- [ ] **T10.01.2** Complete private account/financial setup — `not_started`. Done when: Required verification, fee/tax obligations and private credential storage are addressed.
- [ ] **T10.01.3** Approve public disclosures and experiment cap — `not_started`. Done when: Integration is permitted, transparent, reversible and budgeted.

### T10.02 — Enable one quiet hosted support option

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 (required) · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.01
**Reserved paths:** `web/`, `content/policies/`, `src/wrap_brief/render/`, `tests/browser/`

**Deliverable:** Optional honest support callout linking to an approved hosted payment provider.

**Done criteria:**
- No payment details collected on Pages; no default recurring charge, guilt or blocking popup.
- Support provider is disclosed and core performance/accessibility/referral tasks remain intact.
**Required checks:** support-provider-sandbox, support-ux-privacy-check.

**Subtasks:**
- [ ] **T10.02.1** Design minimal support placement and copy — `not_started`. Done when: One nonintrusive callout follows reader value and explains use of funds.
- [ ] **T10.02.2** Integrate approved hosted support flow — `not_started`. Done when: Only reviewed public URLs/IDs ship; private payment state stays with provider.
- [ ] **T10.02.3** Test success/failure/disable paths — `not_started`. Done when: No sensitive data leaks and removal is a small configuration change.

### T10.03 — Pilot disclosed affiliate commerce or sponsorship

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 (optional) · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.04
**Reserved paths:** `content/commerce/`, `content/policies/`, `web/`, `docs/experiments/`

**Deliverable:** Only one selected later commercial pilot with useful original content and clear separation.

**Done criteria:**
- Program/contract/provider rules are reviewed; disclosures appear before clicks and no source ranking is sold.
- Audience claims are truthful and contribution is evaluated after operator time.
**Required checks:** affiliate-or-sponsor-policy, commercial-experiment-review.

**Subtasks:**
- [ ] **T10.03.1** Choose channel based on audience evidence — `not_started`. Done when: Affiliate purchase intent or sponsor fit has a reasoned business case.
- [ ] **T10.03.2** Ship separated disclosed content/placement — `not_started`. Done when: No editorial card or lead ranking masquerades as paid promotion.
- [ ] **T10.03.3** Evaluate contribution and trust guardrails — `not_started`. Done when: Keep/change/stop decision includes fees/time and user impact.

### T10.04 — Evaluate support conversion and net contribution

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 (required) · **Risk:** medium · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.02
**Reserved paths:** `docs/experiments/`, `docs/evidence/`

**Deliverable:** Time-boxed support experiment result and explicit expand/stop decision.

**Done criteria:**
- Gross donations are not called profit; fees, tools and operator hours are subtracted.
- Conversion is reported only with valid exposure measurement; otherwise raw totals/limitations are shown.
**Required checks:** revenue-evidence-review, contribution-calculation.

**Subtasks:**
- [ ] **T10.04.1** Collect approved aggregate support outcomes — `not_started`. Done when: No donor records or private provider exports enter the repo.
- [ ] **T10.04.2** Calculate net contribution and workload — `not_started`. Done when: Operator rate, expenses and measurement limits are explicit.
- [ ] **T10.04.3** Choose keep/change/stop before expansion — `not_started`. Done when: Negative economics or trust/performance harm can disable the channel.

### T10.05 — Evaluate and optionally pilot display advertising

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 (optional) · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.04
**Reserved paths:** `web/`, `content/policies/`, `docs/experiments/`, `tests/browser/`

**Deliverable:** Ad go/no-go and, only if approved, a bounded labeled placement with consent controls.

**Done criteria:**
- Hosting/network/original-content/privacy/consent approval precedes scripts.
- Reserved dimensions, Advertisement labels, no-ad fallback and before/after performance/referral checks pass.
**Required checks:** ad-provider-privacy-approval, ad-performance-trust-guardrails.

**Subtasks:**
- [ ] **T10.05.1** Validate commercial and network eligibility — `not_started`. Done when: Thin aggregation alone is not assumed sufficient for approval.
- [ ] **T10.05.2** Pilot one safe placement or record no-go — `not_started`. Done when: No deceptive card placement, behavioral tracking by default or layout shift.
- [ ] **T10.05.3** Measure return after all costs and harms — `not_started`. Done when: Ads are removed if contribution/reader-value guardrails fail.

## E11 — Evidence-led extensions and scale

**Owner:** Product maintainer. **Outcome:** Optional modular improvements only when demand or limits justify them. [Specification](../specs/architecture.md).

### T11.01 — Expand cadence, sources or unattended operation with evidence

**Status:** not_started · **Scope:** future · **Milestone:** M5 (optional) · **Risk:** medium · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T08.03
**Reserved paths:** `config/sources/`, `.github/workflows/`, `docs/decisions/`, `tests/ingest/`

**Deliverable:** A selected expansion: twice-daily polling, additional approved sources, or independently monitored unattended operation.

**Done criteria:**
- Feed gaps, freshness or operator workload justify the chosen change; no expansion is required just because public compute is free.
- Before unattended mode, an independent monitor detects a disabled schedule at a 30-hour threshold using an approved private notification route.
- Additional sources/cadence still meet rights, quality and request budgets; rollback and incremental cost are documented.
**Required checks:** cadence-source-cost-review, expanded-source-regression.

**Subtasks:**
- [ ] **T11.01.1** Select one observed coverage or workload problem — `not_started`. Done when: Evidence supports cadence/source expansion or reducing manual supervision; no automatic expansion is assumed.
- [ ] **T11.01.2** Implement only the selected bounded change — `not_started`. Done when: Use one approved cron/source set; unattended mode requires a separately verified independent monitor and private notification route.
- [ ] **T11.01.3** Compare value, cost and missed-schedule behavior — `not_started`. Done when: Coverage/workload improves without trust/rights regressions; disabled-schedule detection is proven before claiming unattended operation.

### T11.02 — Select one discovery feature: search, game page or calendar

**Status:** not_started · **Scope:** future · **Milestone:** M5 (optional) · **Risk:** medium · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T09.03
**Reserved paths:** `src/wrap_brief/render/`, `web/`, `tests/browser/`, `docs/experiments/`

**Deliverable:** One modular static discovery feature backed by demand, not a full portal rewrite.

**Done criteria:**
- New pages provide unique value; no empty keyword doorway pages or backend dependency without need.
- Core no-JS reading, performance and source attribution remain intact.
**Required checks:** discovery-feature-acceptance, seo-a11y-performance.

**Subtasks:**
- [ ] **T11.02.1** Choose and refine the highest-value discovery need — `not_started`. Done when: Reader baseline supports search, selected game page or release calendar.
- [ ] **T11.02.2** Implement against existing view models — `not_started`. Done when: Ingestion/state contracts do not need an unnecessary rewrite.
- [ ] **T11.02.3** Measure usage and maintenance burden — `not_started`. Done when: Feature is retained only if value exceeds its operating complexity.

### T11.03 — Add consented email digest only after demonstrated demand

**Status:** not_started · **Scope:** future · **Milestone:** M5 (optional) · **Risk:** high · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T09.03, T09.01
**Reserved paths:** `docs/decisions/`, `content/policies/`, `docs/experiments/`, `web/`

**Deliverable:** Approved provider-based newsletter with consent, unsubscribe, private storage and portability.

**Done criteria:**
- Subscriber/suppression lists never enter Git/Pages; signup and unsubscribe work securely.
- Free-tier limits, consent/retention/privacy, export/exit and workload are reviewed.
**Required checks:** email-consent-unsubscribe, provider-portability-security.

**Subtasks:**
- [ ] **T11.03.1** Validate demand and choose bounded provider — `not_started`. Done when: Cost, deliverability, privacy and migration options are documented.
- [ ] **T11.03.2** Implement consent and lifecycle via provider — `not_started`. Done when: Signup/confirmation/unsubscribe/deletion work without a custom public data store.
- [ ] **T11.03.3** Pilot digest and measure sustainable value — `not_started`. Done when: No scraped outreach or misleading subscriber metrics; stop/exit path is proven.

### T11.04 — Migrate storage or hosting when policy/limits require it

**Status:** not_started · **Scope:** future · **Milestone:** M5 (optional) · **Risk:** high · **Size:** M
**Owner:** Product maintainer
**Dependencies:** T08.03, T04.03
**Reserved paths:** `src/wrap_brief/state/`, `.github/workflows/`, `docs/decisions/`, `docs/operations.md`

**Deliverable:** Portable static host/state backend migration preserving public IDs, URLs and recovery.

**Done criteria:**
- Policy, retention/erasure, state growth or reliability need is measured and budgeted.
- Dual-read/restore verification and cutover rollback protect content, tombstones, links and credentials.
**Required checks:** migration-dry-run, cutover-restore-drill.

**Subtasks:**
- [ ] **T11.04.1** Define migration trigger and target — `not_started`. Done when: Provider terms/cost/retention and secret boundaries satisfy the actual need.
- [ ] **T11.04.2** Migrate snapshots/URLs with validation — `not_started`. Done when: IDs, records, checkpoints and public links remain consistent.
- [ ] **T11.04.3** Rehearse cutover and rollback — `not_started`. Done when: Known-good site/state restore is proven before irreversible cleanup.

### T11.05 — Evaluate advanced grouping or localization as a separate slice

**Status:** not_started · **Scope:** future · **Milestone:** M5 (optional) · **Risk:** medium · **Size:** M
**Owner:** Product maintainer
**Dependencies:** T05.03, T09.03
**Reserved paths:** `src/wrap_brief/grouping/`, `tests/benchmarks/`, `content/`, `docs/experiments/`

**Deliverable:** Refined evidence-led experiment, not automatic AI/multilingual scope expansion.

**Done criteria:**
- Benchmark gain or reader demand justifies cost, rights and editorial complexity.
- Baseline deterministic pipeline still works without paid services; language/rumor/correction semantics remain accurate.
**Required checks:** advanced-feature-benchmark, cost-rights-fallback-review.

**Subtasks:**
- [ ] **T11.05.1** Select one concrete quality or language problem — `not_started`. Done when: Baseline metrics support a narrow experiment with an explicit budget.
- [ ] **T11.05.2** Prototype behind disabled-by-default configuration — `not_started`. Done when: Provider/privacy/translation rights and fallback are reviewed before use.
- [ ] **T11.05.3** Compare quality, cost and operational burden — `not_started`. Done when: Only a measurable improvement proceeds; failed experiment is removed cleanly.
