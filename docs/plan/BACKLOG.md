# Wrap Brief — epics, tasks, and subtasks

> Generated from backlog.json; do not edit. Product work is unimplemented unless explicitly done with evidence.

Every task also inherits the global definition of done in [delivery workflow](../delivery-workflow.md). Later scopes are refinement plans, not a commitment to build every feature.

## E00 — Planning and evidence-driven execution

**Owner:** Delivery lead. **Outcome:** A reviewed, testable plan with truthful progress. [Specification](../plan/new/roadmap.md).

### T00.01 — Deliver the reviewed planning pack and progress tooling

**Status:** done · **Scope:** planning · **Milestone:** M0 · **Risk:** low · **Size:** M
**Owner:** Delivery lead
**Dependencies:** none
**Reserved paths:** `README.md`, `AGENTS.md`, `SECURITY.md`, `docs/`, `tools/plan.py`, `tests/test_plan.py`, `Makefile`, `.gitignore`

**Deliverable:** Versioned roadmap, component specs, complete backlog, deterministic tracker and evidence.

**Done criteria:**
- Every component has owned tasks, dependencies, subtasks and measurable done criteria.
- Planning and product progress are separate; disabled work cannot block the MVP or appear ready.
- All named checks pass: plan-check, plan-tests, public-safety; independent review and public-safe evidence recorded.

**Subtasks:**
- [x] **T00.01.1** Define architecture, UX, safety and phased business gates — `done`. Done when: Specifications and roadmap cover the smallest launch and safe extension seams.
- [x] **T00.01.2** Encode epics, tasks, subtasks, dependencies and progress — `done`. Done when: Canonical backlog and generated views validate and agree.
- [x] **T00.01.3** Review, test and check publication safety — `done`. Done when: Independent review has no blocker; named checks and safe evidence are recorded.

**Completion evidence:** [docs/plan/VALIDATION.md](../../docs/plan/VALIDATION.md)

## E01 — Repository, toolchain, and governance

**Owner:** Platform maintainer. **Outcome:** Safe public collaboration and reproducible development. [Specification](../specs/security-privacy.md).

### T01.01 — Establish public repository rules and reporting

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `.github/`, `SECURITY.md`, `CONTRIBUTING.md`

**Deliverable:** Protected main, PR templates, private vulnerability reporting, public-safe issue guidance and ownership.

**Done criteria:**
- Required PR/check rules protect main without automation bypass.
- A fork contribution needs no secret; reporting route never invites public disclosure of credentials.
- All named checks pass: repository-rule-sandbox, reporting-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T01.01.1** Configure rules and required-check strategy — `not_started`. Done when: Actual account-tier rules are documented and enforced on main.
- [ ] **T01.01.2** Set contributor and sensitive-reporting paths — `not_started`. Done when: Templates and private reporting route are usable without publishing secrets.
- [ ] **T01.01.3** Exercise branch/fork behavior — `not_started`. Done when: Test PR and blocked direct-write evidence is recorded.

### T01.02 — Create reproducible Python and local check setup

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, `src/`, `tests/`

**Deliverable:** uv-managed package, locked minimal dependencies, ruff, unittest/fixture check entry points.

**Done criteria:**
- Fresh clone installs with the lockfile and runs fixture tests without production credentials.
- Make help describes real available targets; no unnecessary runtime framework or service.
- All named checks pass: fresh-clone-setup, lint-and-unit; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T01.02.1** Initialize package and supported Python version — `not_started`. Done when: uv project and lock file resolve reproducibly.
- [ ] **T01.02.2** Add lint/test/fixture commands — `not_started`. Done when: Formatting, lint and unit tests have documented Make targets.
- [ ] **T01.02.3** Prove isolated setup — `not_started`. Done when: A clean environment passes the advertised commands.

### T01.03 — Add dependency, action, and credential safety checks

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T01.01, T01.02
**Reserved paths:** `.github/`, `pyproject.toml`, `uv.lock`, `tests/security/`

**Deliverable:** Pinned actions, locked dependencies, dedicated secret/history scanning and least-privilege CI policy.

**Done criteria:**
- PR code never receives secrets/write permissions; privileged events cannot execute fork code.
- Credential scanner checks tracked tree/history and public artifacts with reviewed false positives.
- All named checks pass: workflow-policy, credential-history-scan, dependency-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T01.03.1** Define trust-separated CI permissions — `not_started`. Done when: No elevated fork checkout or untrusted privileged execution exists.
- [ ] **T01.03.2** Pin and scan supply chain/public data — `not_started`. Done when: Action SHAs, dependency locks and credential scanning run in CI.
- [ ] **T01.03.3** Test malicious contribution scenarios — `not_started`. Done when: A fork PR cannot deploy, write state, or access credentials.

### T01.04 — Clear brand, code license, and policy copy

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** low · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T00.01
**Reserved paths:** `LICENSE`, `README.md`, `content/policies/`, `docs/decisions/`

**Deliverable:** Working-name checks, explicit code license, attribution/disclaimer/privacy/corrections copy.

**Done criteria:**
- Name/domain/trademark checks and unofficial presentation are recorded; no Nintendo assets are copied.
- Code licensing is explicit and separate from publisher content rights; private contact/account details stay private.
- All named checks pass: brand-license-review, policy-copy-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T01.04.1** Check Wrap Brief name and independent identity — `not_started`. Done when: Evidence supports selected name or a documented rename before launch.
- [ ] **T01.04.2** Select project license and contribution terms — `not_started`. Done when: License scope is clear and excludes third-party content.
- [ ] **T01.04.3** Write privacy, source, correction and disclaimer copy — `not_started`. Done when: Reader-facing policy text accurately reflects the no-tracking pilot.

## E02 — Source approval and versioned contracts

**Owner:** Data maintainer. **Outcome:** Small approved source set and stable producer/consumer contracts. [Specification](../specs/data-pipeline.md).

### T02.01 — Implement versioned source/item/cluster contracts

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T01.02
**Reserved paths:** `src/wrap_brief/models.py`, `src/wrap_brief/config.py`, `config/`, `tests/models/`

**Deliverable:** Typed versioned public records, invariants and source registry schema.

**Done criteria:**
- Unknown dates remain null/first-seen labeled; URLs and cross-record references validate.
- Schema distinguishes source text, original editorial text, rumor/correction status and health.
- All named checks pass: model-unit, schema-compatibility; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T02.01.1** Define minimal record and registry fields — `not_started`. Done when: Data contracts match the architecture without full text/private fields.
- [ ] **T02.01.2** Implement validation and serialization — `not_started`. Done when: Invalid IDs, URLs, dates and references fail with bounded errors.
- [ ] **T02.01.3** Add schema/version fixtures — `not_started`. Done when: Producers and consumers share tested stable fixtures.

### T02.02 — Approve the first 3–5 sources

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01, T01.04
**Reserved paths:** `config/sources/`, `docs/sources/`

**Deliverable:** Small enabled source registry with reviewed rights/retention/attribution evidence.

**Done criteria:**
- Every enabled source has terms review date, permitted fields, polling and archival approval.
- Unclear permission disables the source; no RSS-is-a-license assumption or unlicensed images.
- All named checks pass: source-rights-review, registry-validation; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T02.02.1** Inventory complementary primary/specialist sources — `not_started`. Done when: Candidate list identifies feed availability and coverage gaps.
- [ ] **T02.02.2** Review terms and public-state retention — `not_started`. Done when: Approved fields, attribution, history permanence and removal route are recorded.
- [ ] **T02.02.3** Enable only cleared pilot sources — `not_started`. Done when: Three to five approved sources pass schema/rights gates or pilot scope is reduced explicitly.

### T02.03 — Build synthetic feed and view-model fixtures

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01
**Reserved paths:** `tests/fixtures/`, `tests/contracts/`

**Deliverable:** Rights-safe RSS/Atom, hostile input, and renderer fixtures with injected clocks.

**Done criteria:**
- Offline fixtures cover valid, empty, malformed, hostile and timezone cases.
- No copied article bodies, real tokens, contact emails or private headers appear in fixtures.
- All named checks pass: fixture-contracts, fixture-public-safety; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T02.03.1** Create representative RSS/Atom fixtures — `not_started`. Done when: Namespaces, Unicode, missing dates/GUIDs and updates are represented.
- [ ] **T02.03.2** Create adversarial/edge fixtures — `not_started`. Done when: Redirect, encoding, XML expansion, limits and duplicate cases are synthetic.
- [ ] **T02.03.3** Publish shared fixture contract — `not_started`. Done when: Data and UI lanes can work independently on identical expected models.

### T02.04 — Document and test repeatable source onboarding

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.02, T03.03
**Reserved paths:** `docs/sources/`, `tests/ingest/`, `config/sources/`

**Deliverable:** Source addition/removal recipe requiring approval, fixture and bounded fetch verification.

**Done criteria:**
- A second maintainer can add a source without changing unrelated pipeline modules.
- Removal, expiry/review reminders and malformed-source quarantine are documented.
- All named checks pass: source-onboarding-dry-run, source-removal-test; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T02.04.1** Write source acceptance checklist — `not_started`. Done when: Rights, source quality, fetch window and retention checks are mandatory.
- [ ] **T02.04.2** Exercise addition using fixture and dry run — `not_started`. Done when: New adapter/registry entry emits valid normalized records.
- [ ] **T02.04.3** Exercise disable/removal — `not_started`. Done when: Disabled source is not fetched; existing records follow correction/retention rules.

## E03 — Bounded feed collection and normalization

**Owner:** Data maintainer. **Outcome:** Cheap, polite, secure RSS/Atom collection with honest coverage. [Specification](../specs/data-pipeline.md).

### T03.01 — Implement bounded safe feed HTTP client

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.01, T02.03
**Reserved paths:** `src/wrap_brief/ingest/http.py`, `tests/ingest/`

**Deliverable:** Allowlisted HTTPS requests with limits, conditional headers, timeout and backoff.

**Done criteria:**
- Every redirect/destination is checked; private/metadata targets, oversized bodies and unsafe URLs are rejected.
- Request concurrency/retry budgets respect source policies and do not leak headers in logs.
- All named checks pass: http-adversarial, timeout-retry-budget; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T03.01.1** Implement safe destination and redirect validation — `not_started`. Done when: Only approved hosts/public HTTPS targets can be requested.
- [ ] **T03.01.2** Implement bounded transport and conditional GET — `not_started`. Done when: Timeouts, decompressed byte limit, redirects, retries and 304 are handled.
- [ ] **T03.01.3** Test abuse and partial-source failures — `not_started`. Done when: One malicious/slow feed cannot monopolize the run or erase other data.

### T03.02 — Parse RSS and Atom safely

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T02.03
**Reserved paths:** `src/wrap_brief/ingest/parsers.py`, `tests/ingest/`, `pyproject.toml`, `uv.lock`

**Deliverable:** Pure RSS/Atom adapters using a safe locked XML dependency where justified.

**Done criteria:**
- External entities/DTD/expansion are disabled; depth/text/item bounds apply.
- Parser emits source metadata only, never raw HTML/full article/enclosure downloads.
- All named checks pass: parser-unit, xml-abuse-fixtures; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T03.02.1** Implement small RSS/Atom adapters — `not_started`. Done when: Supported feed formats return the shared candidate record shape.
- [ ] **T03.02.2** Enforce safe XML and field bounds — `not_started`. Done when: Hostile entities, nesting and oversized text fail safely.
- [ ] **T03.02.3** Test format and encoding edge cases — `not_started`. Done when: Fixture suite passes offline with predictable item quarantine.

### T03.03 — Normalize and validate public metadata

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T03.02
**Reserved paths:** `src/wrap_brief/ingest/normalize.py`, `tests/ingest/`

**Deliverable:** Plain-text safe URLs/titles, explicit UTC, provenance, and item quarantine.

**Done criteria:**
- Publication/update/first-seen times remain distinct; ambiguous dates are not fabricated.
- Unsafe links/markup and unapproved fields cannot reach state or rendered output.
- All named checks pass: normalization-unit, url-time-provenance; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T03.03.1** Normalize text, URLs and source references — `not_started`. Done when: Public fields meet length/scheme/provenance constraints.
- [ ] **T03.03.2** Normalize UTC and unknown/future dates — `not_started`. Done when: Dates and labels retain honest semantics under injected clocks.
- [ ] **T03.03.3** Test escaping/quarantine paths — `not_started`. Done when: Invalid entries are bounded and reported without losing valid entries.

### T03.04 — Add incremental polling, health and gap detection

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Data maintainer
**Dependencies:** T03.01, T03.03
**Reserved paths:** `src/wrap_brief/ingest/`, `tests/ingest/`

**Deliverable:** Per-source checkpoints, 304 handling, last-good fallback and possible truncation warnings.

**Done criteria:**
- Checkpoints advance only after validated source success; legitimate no-news is not a failure.
- Potential missed feed windows and partial/all-source failures are surfaced honestly.
- All named checks pass: incremental-polling, truncation-and-outage; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T03.04.1** Persist conditional-request checkpoints — `not_started`. Done when: ETag/Last-Modified and poll boundaries survive independent runs.
- [ ] **T03.04.2** Implement healthy/degraded/no-new outcomes — `not_started`. Done when: Source errors preserve prior records; all-source failure stops publication.
- [ ] **T03.04.3** Detect possible feed-window gaps — `not_started`. Done when: Truncation fixtures produce warnings without false completeness claims.

## E04 — Durable state and pipeline recovery

**Owner:** Platform maintainer. **Outcome:** Complete replayable state, safe persistence, and recovery. [Specification](../specs/architecture.md).

### T04.01 — Implement full normalized snapshot store

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T05.01
**Reserved paths:** `src/wrap_brief/state/snapshot.py`, `tests/state/`

**Deliverable:** Deterministic local snapshot read/validate/write API and retained complete records.

**Done criteria:**
- State stores complete metadata and checkpoints, not only seen IDs.
- Identical inputs produce stable IDs/order; schema and references reject corrupt snapshots.
- All named checks pass: snapshot-unit, idempotent-replay; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T04.01.1** Implement snapshot serialization and validation — `not_started`. Done when: Versioned complete records round-trip deterministically.
- [ ] **T04.01.2** Implement idempotent update/tombstone semantics — `not_started`. Done when: Repeated items do not duplicate or become artificially fresh.
- [ ] **T04.01.3** Test cache/artifact independence — `not_started`. Done when: Loss of optional caches does not change identity or retained records.

### T04.02 — Implement isolated state-branch CAS persistence

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T01.03, T04.01
**Reserved paths:** `src/wrap_brief/state/git_store.py`, `.github/workflows/`, `tests/state/`

**Deliverable:** Trusted default-branch writer with exact data allowlist and expected-head fast-forward commits.

**Done criteria:**
- Writer rejects path traversal, symlinks, executable/workflow/config artifacts and invalid/oversized JSON.
- No force push or main bypass; conflict causes safe bounded retry/failure under shared concurrency.
- All named checks pass: writer-permission-sandbox, cas-and-artifact-abuse; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T04.02.1** Define state branch rules and writer contract — `not_started`. Done when: Actual branch protections support intended writes without main bypass.
- [ ] **T04.02.2** Implement revalidation and expected-parent commit — `not_started`. Done when: Only bounded allowed public JSON paths can be committed.
- [ ] **T04.02.3** Exercise conflict and hostile candidate scenarios — `not_started`. Done when: CAS conflicts and injected executable/path payloads fail safely.

### T04.03 — Prove retention, migrations, restore and failed-publish recovery

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T04.02, T03.04
**Reserved paths:** `src/wrap_brief/state/`, `tests/state/`, `docs/operations.md`

**Deliverable:** Versioned migration/retention policy and tested state restore/replay.

**Done criteria:**
- State committed before a failed build remains available to the next complete build.
- Retention/tombstones are rights-aware; Git-history permanence is explicit and restore preserves IDs.
- All named checks pass: state-recovery-drill, migration-retention; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T04.03.1** Implement bounded retention and tombstones — `not_started`. Done when: Expired/resurfaced/retracted records follow explicit non-fabricated freshness rules.
- [ ] **T04.03.2** Implement migration and known-good restore — `not_started`. Done when: Previous state version/snapshot restores with validated records/checkpoints.
- [ ] **T04.03.3** Simulate failure after state commit — `not_started`. Done when: Next build includes every retained item without depending on a lost artifact.

### T04.04 — Compose explicit collect/build/check CLI stages

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Platform maintainer
**Dependencies:** T04.01, T03.04, T05.02
**Reserved paths:** `src/wrap_brief/pipeline.py`, `src/wrap_brief/cli.py`, `tests/integration/`

**Deliverable:** Composable stage commands, dry run, injected time/network and safe manifest/exit codes.

**Done criteria:**
- Each stage has explicit input/output contracts and can run from fixtures independently.
- Dry run performs no state mutation/deployment; partial failures are represented in bounded health.
- All named checks pass: pipeline-fixture-e2e, dry-run-no-write; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T04.04.1** Implement orchestration over pure modules — `not_started`. Done when: Stages do not mix network, grouping, persistence and rendering concerns.
- [ ] **T04.04.2** Add dry-run and safe manifest output — `not_started`. Done when: Outputs identify code/config/state and health without private fields.
- [ ] **T04.04.3** Test whole-pipeline replay and failure exits — `not_started`. Done when: Fixture pipeline is deterministic and returns actionable bounded failures.

## E05 — Identity, story grouping, and editorial trust

**Owner:** Editorial maintainer. **Outcome:** Less repetition without losing perspectives or provenance. [Specification](../specs/data-pipeline.md).

### T05.01 — Implement exact identity and conservative URL cleanup

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T03.03
**Reserved paths:** `src/wrap_brief/grouping/identity.py`, `tests/grouping/`

**Deliverable:** Source-scoped stable identity and reviewed tracking-parameter normalization.

**Done criteria:**
- Tracking variants deduplicate; article-identifying query fields remain distinct.
- Source GUID collisions/changes do not silently overwrite unrelated articles.
- All named checks pass: identity-unit, canonicalization-benchmark; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T05.01.1** Define GUID/URL identity precedence — `not_started`. Done when: Identity rules are deterministic and versioned.
- [ ] **T05.01.2** Implement reviewed URL normalization — `not_started`. Done when: Only known tracking parameters are stripped.
- [ ] **T05.01.3** Test duplicate/collision/resurfacing cases — `not_started`. Done when: Same item is stable while distinct editions/events remain separate.

### T05.02 — Group same-event coverage and choose lead source

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T05.01, T02.03
**Reserved paths:** `src/wrap_brief/grouping/`, `tests/grouping/`

**Deliverable:** Conservative event clusters, stable IDs, deterministic evidence-based lead ranking.

**Done criteria:**
- Rumor/confirmation, distinct Direct announcements, reviews and news do not collapse blindly.
- All alternate members retain links/provenance; commercial value never affects ranking.
- All named checks pass: grouping-unit, lead-ranking-rules; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T05.02.1** Implement bounded similarity candidate stage — `not_started`. Done when: Entities/event types/time window constrain title similarity.
- [ ] **T05.02.2** Implement stable groups and transparent lead choice — `not_started`. Done when: Primary/original/substantive coverage rules have deterministic tie-breakers.
- [ ] **T05.02.3** Test ambiguous and conflicting coverage — `not_started`. Done when: Uncertain matches split; rumors/corrections retain explicit labels.

### T05.03 — Benchmark grouping and add reviewed split/merge overrides

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T05.02
**Reserved paths:** `tests/benchmarks/`, `config/overrides/`, `src/wrap_brief/grouping/`

**Deliverable:** Labeled benchmark, measured precision/recall, reversible manual corrections.

**Done criteria:**
- At least 100 labeled pairs include known hard cases; automatic merge precision is at least 98% on sample.
- Overrides are reviewed, deterministic and traceable; fuzzy grouping can be disabled safely.
- All named checks pass: grouping-gold-benchmark, override-replay; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T05.03.1** Label representative real-event metadata pairs — `not_started`. Done when: Rights-safe benchmark covers event/edition/rumor/correction edge cases.
- [ ] **T05.03.2** Measure and tune conservative thresholds — `not_started`. Done when: Precision, recall, sample size and false merges are reported.
- [ ] **T05.03.3** Implement split/merge and disable controls — `not_started`. Done when: Reviewed overrides survive reruns without deleting source provenance.

### T05.04 — Add original briefs, corrections and takedown workflow

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Editorial maintainer
**Dependencies:** T02.01, T05.02
**Reserved paths:** `content/`, `src/wrap_brief/editorial/`, `tests/editorial/`

**Deliverable:** Reviewed original-context model and correction/retraction/tombstone controls.

**Done criteria:**
- Original text has byline, sources and review status; absent briefs remain labeled listings.
- A correction/removal exercise retains honest provenance and handles public-state rights constraints.
- All named checks pass: editorial-provenance, correction-takedown-drill; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T05.04.1** Implement reviewed editorial content records — `not_started`. Done when: Source headlines and Wrap Brief context are distinguishable.
- [ ] **T05.04.2** Implement correction/retraction display and exclusion — `not_started`. Done when: Withdrawn/changed claims cannot remain silently promoted.
- [ ] **T05.04.3** Exercise source-requested removal — `not_started`. Done when: Document storage/history implications without claiming ordinary deletion erases Git history.

## E06 — Minimalist static reader experience

**Owner:** Web maintainer. **Outcome:** Attractive, accessible, fast reading without required JavaScript. [Specification](../specs/reader-experience.md).

### T06.01 — Create responsive visual tokens and semantic shell

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T02.03
**Reserved paths:** `web/`, `src/wrap_brief/render/`, `tests/render/`

**Deliverable:** Original minimalist mobile-first shell, typography, spacing and contrast-tested colors.

**Done criteria:**
- No copied Nintendo identity/assets, external fonts or required client framework.
- Semantic landmarks, skip link, visible focus and readable 320px layout are present.
- All named checks pass: design-token-contrast, shell-mobile-keyboard; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T06.01.1** Translate UX spec into a small token set — `not_started`. Done when: Typography, spacing and accent colors pass contrast targets.
- [ ] **T06.01.2** Build semantic responsive shell — `not_started`. Done when: Header/content/footer reflow cleanly from mobile to desktop.
- [ ] **T06.01.3** Validate long text and focus states — `not_started`. Done when: No clipped links/labels or invisible keyboard focus.

### T06.02 — Render grouped digest with accessible alternate sources

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.01, T05.02, T04.01
**Reserved paths:** `src/wrap_brief/render/`, `tests/render/`, `web/`

**Deliverable:** Escaped static story cards with lead links, native disclosures and honest labels.

**Done criteria:**
- Core reading and all source links work with JavaScript disabled.
- Title/source/known time/rumor status are visible; other coverage remains reachable by keyboard.
- All named checks pass: renderer-golden-html, no-js-source-navigation; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T06.02.1** Implement pure view models and HTML escaping — `not_started`. Done when: Hostile source fields render as safe text/links.
- [ ] **T06.02.2** Implement cards and native coverage disclosure — `not_started`. Done when: Lead action and alternate publishers have descriptive links.
- [ ] **T06.02.3** Build deterministic fixture homepage — `not_started`. Done when: Same supplied inputs/clock yield identical output files.

### T06.03 — Render policies, honest health and empty/degraded states

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.02, T01.04
**Reserved paths:** `src/wrap_brief/render/`, `content/policies/`, `tests/render/`, `web/`

**Deliverable:** About/sources/privacy/corrections, absolute check time and safe empty/stale states.

**Done criteria:**
- Failed feeds are not described as no news; no-JS readers always see the absolute check timestamp.
- 30-hour stale behavior is truthful, including limits of static HTML and any optional local-clock enhancement.
- All named checks pass: policy-and-health-render, empty-degraded-stale; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T06.03.1** Render methodology and required policy links — `not_started`. Done when: Independent status, rights, privacy and correction route are reachable.
- [ ] **T06.03.2** Implement healthy/empty/degraded states — `not_started`. Done when: Source failures and genuine zero-new-news have different copy.
- [ ] **T06.03.3** Implement/test freshness display — `not_started`. Done when: Publication, first-seen, last-check and deployment times are not conflated.

### T06.04 — Prove core accessibility and performance budgets

**Status:** not_started · **Scope:** mvp · **Milestone:** M1 · **Risk:** medium · **Size:** S
**Owner:** Web maintainer
**Dependencies:** T06.02
**Reserved paths:** `tests/browser/`, `tests/render/`, `web/`, `docs/evidence/`

**Deliverable:** Repeatable browser/a11y/no-JS and compressed-size checks against fixture site.

**Done criteria:**
- 320px, desktop, keyboard, screen-reader checks, 200/400% reflow and reduced-motion behavior pass.
- Initial HTML/CSS/JS <=150 KB compressed; mobile LCP/CLS targets measured with environment noted.
- All named checks pass: browser-a11y-no-js, performance-budget; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T06.04.1** Add repeatable browser/static checks — `not_started`. Done when: Core read/expand/outbound tasks are tested without JS and by keyboard.
- [ ] **T06.04.2** Measure size and mobile rendering — `not_started`. Done when: Compressed payload, LCP/CLS and test environment are recorded.
- [ ] **T06.04.3** Fix UX/a11y regressions — `not_started`. Done when: No release-blocking overflow, contrast, focus or source-navigation failure remains.

## E07 — CI, scheduled automation, publishing, and monitoring

**Owner:** Release maintainer. **Outcome:** A daily protected release pipeline that fails safely. [Specification](../operations.md).

### T07.01 — Wire credential-free PR CI and full fixture build

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T01.03, T06.04, T05.03
**Reserved paths:** `.github/workflows/`, `Makefile`, `tests/integration/`

**Deliverable:** Required read-only lint/unit/fixture/schema/render/workflow checks on pull requests.

**Done criteria:**
- Fork PR check paths cannot mutate state/deploy or obtain secrets.
- CI rejects invalid source/config/grouping/output and generated-plan drift.
- All named checks pass: ci-fork-sandbox, full-fixture-build; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T07.01.1** Assemble named required checks — `not_started`. Done when: Lint, unit, integration, schemas, HTML/links and plan checks have stable names.
- [ ] **T07.01.2** Run fixture build on fork PR — `not_started`. Done when: No production network credentials or write scopes are needed.
- [ ] **T07.01.3** Test intentionally failing changes — `not_started`. Done when: Broken contracts/unsafe workflows are blocked before merge.

### T07.02 — Schedule daily collection and isolated persistence

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.01, T04.04, T04.02, T02.04
**Reserved paths:** `.github/workflows/`, `tests/workflows/`, `docs/operations.md`

**Deliverable:** Default-branch daily/manual collect -> validate -> persist pipeline with one mutation lock.

**Done criteria:**
- Only cron 23 6 * * * is enabled initially; UTC/cadence and manual default-branch restrictions are explicit.
- Read-only fetch and trusted state-write jobs are separated; all-source failure/conflict cannot corrupt state.
- All named checks pass: workflow-policy, scheduled-state-sandbox; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T07.02.1** Configure schedule/manual triggers and lock — `not_started`. Done when: All production mutation/recovery routes share concurrency control.
- [ ] **T07.02.2** Wire bounded collect and data-only writer artifact — `not_started`. Done when: Privileged job revalidates the exact approved candidate contract.
- [ ] **T07.02.3** Run real-source dry run and persistence sandbox — `not_started`. Done when: Approved source polling and state boundaries pass without deploying.

### T07.03 — Deploy validated static artifact through protected Pages

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.02, T06.03
**Reserved paths:** `.github/workflows/`, `tests/workflows/`, `docs/operations.md`

**Deliverable:** Read-only build from explicit state/code refs, one-day Pages artifact, restricted OIDC deploy.

**Done criteria:**
- Deploy job has Pages/OIDC permissions only and runs after every build gate.
- Invalid/empty-on-failure output cannot replace live site; actual public URL/manifest is smoke-tested.
- All named checks pass: pages-deployment-sandbox, public-url-smoke; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T07.03.1** Configure Pages source and environment restrictions — `not_started`. Done when: Only reviewed default-branch releases can deploy.
- [ ] **T07.03.2** Wire build/validate/upload/deploy jobs — `not_started`. Done when: Artifact root, entry point, retention and manifest are correct.
- [ ] **T07.03.3** Exercise successful and failed publication — `not_started`. Done when: Known-good site survives a pre-deploy failure; live output matches manifest.

### T07.04 — Add source health, stale-run monitor and safe alerts

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.03
**Reserved paths:** `.github/workflows/`, `src/wrap_brief/health.py`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** Public minimal health manifest plus independent 30-hour stale check and private notifications.

**Done criteria:**
- Disabled/missed collection schedules are detected independently, not only by same-workflow checks.
- Alerts are deduplicated and rate-limited; webhook/contact credentials never enter site/repo/logs.
- All named checks pass: stale-schedule-drill, alert-redaction-and-dedupe; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T07.04.1** Emit bounded source/run/deploy health — `not_started`. Done when: Health distinguishes collection from deployment success and feed gaps.
- [ ] **T07.04.2** Select approved independent free/cheap monitor — `not_started`. Done when: Provider limits, private notification route and no-secret setup are documented.
- [ ] **T07.04.3** Induce disabled and failed schedule alerts — `not_started`. Done when: 30-hour threshold and recovery notifications are demonstrated.

### T07.05 — Rehearse known-good rollback and state restore

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.03, T04.03
**Reserved paths:** `.github/workflows/`, `tests/recovery/`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** Reviewed code/state pair rebuild, deployment rollback and mutation pause procedure.

**Done criteria:**
- Rollback does not depend only on expiring artifacts and does not erase valid unseen state.
- Practical restore time is measured against a 30-minute target and public URL is checked.
- All named checks pass: deployment-rollback-drill, state-restore-drill; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T07.05.1** Implement guarded manual recovery route — `not_started`. Done when: Only reviewed refs can be selected under the same production lock.
- [ ] **T07.05.2** Restore known-good site and state in sandbox — `not_started`. Done when: IDs/checkpoints/tombstones and live manifest remain coherent.
- [ ] **T07.05.3** Record operational recovery evidence — `not_started`. Done when: Elapsed time, outcomes, resume criteria and residual limitations are documented.

## E08 — Security, UX, and live pilot release

**Owner:** Release maintainer. **Outcome:** Demonstrated readiness, not completion inferred from green unit tests. [Specification](../validation-policy.md).

### T08.01 — Complete adversarial and public-surface security review

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.02, T04.03
**Reserved paths:** `tests/security/`, `docs/evidence/`, `SECURITY.md`

**Deliverable:** Threat-driven tests and scan evidence across repo/history/state/artifacts/logs/output.

**Done criteria:**
- Unsafe feed URLs/XML/HTML/artifact paths and privileged fork scenarios are rejected.
- No credentials, user/payment data, private contact fields or runtime state is published.
- All named checks pass: full-adversarial-suite, public-surface-scan, security-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T08.01.1** Test input and privilege attack paths — `not_started`. Done when: SSRF, XML abuse, XSS, writer traversal and fork escalation cases pass.
- [ ] **T08.01.2** Inspect all public publication surfaces — `not_started`. Done when: Dedicated scanner plus manual classification review finds no unresolved secret.
- [ ] **T08.01.3** Resolve high-severity findings — `not_started`. Done when: Security review signs off the actual integrated release candidate.

### T08.02 — Validate the integrated reader flow with users

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T06.03, T06.04, T05.03
**Reserved paths:** `docs/evidence/`, `web/`, `tests/browser/`

**Deliverable:** Observed reader tasks, accessibility/performance results and repaired usability failures.

**Done criteria:**
- At least five representative sessions test check time, rumor, source comparison and publisher navigation.
- Core mobile/keyboard/no-JS flow and performance guardrails pass on the integrated candidate.
- All named checks pass: reader-task-sessions, integrated-a11y-performance; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T08.02.1** Prepare realistic story scenarios — `not_started`. Done when: Long headlines, rumors, corrections, many sources and stale/empty states are covered.
- [ ] **T08.02.2** Observe reader tasks and accessibility — `not_started`. Done when: Findings distinguish observed behavior from assumptions.
- [ ] **T08.02.3** Repair and recheck material failures — `not_started`. Done when: No blocker remains in core comprehension or outbound reading.

### T08.03 — Release and verify the daily public pilot

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** high · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T08.01, T08.02, T07.04, T07.05, T05.04, T08.04
**Reserved paths:** `docs/evidence/`, `docs/plan/`, `.github/`

**Deliverable:** Noncommercial pilot release with cleared sources, live checks and first scheduled cycle evidence.

**Done criteria:**
- All MVP tasks and source/brand/security/recovery gates pass; no tracking or monetization enabled.
- Actual Pages site and next scheduled cycle are checked; limitations and operator ownership are visible.
- All named checks pass: release-gate-checklist, live-pilot-and-next-cycle; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T08.03.1** Audit integrated launch checklist — `not_started`. Done when: Rights, data, grouping, UX, security, monitoring and rollback evidence is complete.
- [ ] **T08.03.2** Publish and smoke-check pilot — `not_started`. Done when: Public URL has expected content, links, policies, safe state and freshness.
- [ ] **T08.03.3** Verify next daily cycle and handoff — `not_started`. Done when: Scheduled update, alerts and operator runbook work in live operation.

### T08.04 — Finish contributor and incident operations handoff

**Status:** not_started · **Scope:** mvp · **Milestone:** M2 · **Risk:** medium · **Size:** S
**Owner:** Release maintainer
**Dependencies:** T07.05, T01.03
**Reserved paths:** `CONTRIBUTING.md`, `docs/operations.md`, `docs/evidence/`

**Deliverable:** Practical source/correction/contribution/incident playbooks and ownership.

**Done criteria:**
- A maintainer can disable a source, triage a failure, rotate an integration and restore safely.
- Contributors can run fixture checks without credentials or private agent tooling.
- All named checks pass: operator-tabletop, contributor-clean-clone; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T08.04.1** Document routine maintenance and ownership — `not_started`. Done when: Weekly source/quality/cost and permission reviews have an accountable role.
- [ ] **T08.04.2** Run incident and correction tabletop — `not_started`. Done when: Secret revocation, source removal and deployment failure actions are clear.
- [ ] **T08.04.3** Test independent contributor setup — `not_started`. Done when: Fresh clone and public docs suffice for a safe fixture PR.

## E09 — Original value and audience validation

**Owner:** Product/editorial maintainer. **Outcome:** Measure useful repeat readership and operator workload before growth. [Specification](../specs/growth-monetization.md).

### T09.01 — Decide and implement minimal privacy-safe measurement

**Status:** not_started · **Scope:** growth · **Milestone:** M3 · **Risk:** high · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T08.03
**Reserved paths:** `docs/decisions/`, `content/policies/`, `web/`, `tests/privacy/`

**Deliverable:** Explicit analytics decision, definitions, retention and consent/opt-out behavior if enabled.

**Done criteria:**
- No instrumentation ships before provider/data/legal/performance review.
- No claimed unique-reader/retention/attribution metric lacks an actual approved method.
- All named checks pass: privacy-data-inventory, measurement-accuracy; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T09.01.1** Choose no-tracking or minimal approved provider — `not_started`. Done when: Data categories, region/consent basis, retention and access are recorded.
- [ ] **T09.01.2** Implement only approved measurement — `not_started`. Done when: No fingerprinting, private exports or hidden cross-site tracking.
- [ ] **T09.01.3** Validate counts and honest reporting — `not_started`. Done when: Known test events match documented metric denominators/limitations.

### T09.02 — Publish original digest, public RSS and selective SEO

**Status:** not_started · **Scope:** growth · **Milestone:** M3 · **Risk:** medium · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T08.03, T05.04
**Reserved paths:** `content/`, `src/wrap_brief/render/`, `tests/seo/`, `docs/evidence/`

**Deliverable:** Original reviewed weekly value, syndication output and quality-first search metadata.

**Done criteria:**
- Only substantive original/curated pages are indexed; no thin per-keyword page explosion.
- Canonical/sitemap/robots/feed links are accurate and all publisher attribution is preserved.
- All named checks pass: editorial-and-seo-review, rss-and-metadata-validation; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T09.02.1** Publish useful original recurring digest — `not_started`. Done when: Byline, sources, correction route and sustainable editorial effort are recorded.
- [ ] **T09.02.2** Add RSS and accurate discovery metadata — `not_started`. Done when: Feed, canonical, sitemap and share metadata validate without unlicensed assets.
- [ ] **T09.02.3** Review indexability and acquisition channels — `not_started`. Done when: Thin/duplicate pages are excluded and community sharing follows rules.

### T09.03 — Establish four-week reader-value and cost baseline

**Status:** not_started · **Scope:** growth · **Milestone:** M3 · **Risk:** medium · **Size:** M
**Owner:** Product/editorial maintainer
**Dependencies:** T09.01, T09.02
**Reserved paths:** `docs/evidence/`, `docs/experiments/`

**Deliverable:** Four-week aggregate reliability, quality, reader-value and operator-effort report.

**Done criteria:**
- Report actual available metrics and missing-data limitations, not invented retention.
- Cash costs and operator minutes have reproducible definitions and a sustainable workload cap.
- All named checks pass: baseline-data-review, operator-cost-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T09.03.1** Collect four weeks of approved observations — `not_started`. Done when: Reliability, source quality, editorial effort and measured audience data are complete enough to interpret.
- [ ] **T09.03.2** Compute contribution and workload baseline — `not_started`. Done when: Fees/tools/time are included with an explicit operator rate.
- [ ] **T09.03.3** Decide next smallest improvement — `not_started`. Done when: Keep/change/stop decision cites reader value and actual cost.

### T09.04 — Run one ethical engagement experiment

**Status:** not_started · **Scope:** growth · **Milestone:** M3 · **Risk:** medium · **Size:** S
**Owner:** Product/editorial maintainer
**Dependencies:** T09.03
**Reserved paths:** `docs/experiments/`, `content/`, `web/`, `tests/browser/`

**Deliverable:** One time-boxed experiment such as digest placement or source navigation, with guardrails.

**Done criteria:**
- Hypothesis, time/cash cap, measurement method and stop/rollback rule precede implementation.
- No modal/forced signup/dark pattern; source referrals, accessibility and performance are protected.
- All named checks pass: engagement-experiment-review, ux-guardrail-check; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T09.04.1** Select one evidence-led engagement change — `not_started`. Done when: Baseline supports the chosen reader problem.
- [ ] **T09.04.2** Ship a small reversible experiment — `not_started`. Done when: Only approved data and an accessible no-JS baseline are used.
- [ ] **T09.04.3** Evaluate and keep/change/stop — `not_started`. Done when: Observed benefit and operator cost determine the result.

## E10 — Gated support and commercial experiments

**Owner:** Business maintainer. **Outcome:** One reversible, disclosed, measurable revenue channel at a time. [Specification](../specs/growth-monetization.md).

### T10.01 — Resolve commercial hosting, provider and financial gates

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T09.04
**Reserved paths:** `docs/decisions/`, `content/policies/`, `docs/evidence/`

**Deliverable:** Public-safe go/no-go decision for hosting, provider terms, disclosures, privacy and financial obligations.

**Done criteria:**
- Pages commercial-use uncertainty is resolved appropriately or hosting migrates before money features.
- Provider account/secrets and private tax/payment details are never committed.
- All named checks pass: commercial-policy-review, provider-privacy-finance-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T10.01.1** Review current hosting and provider policies — `not_started`. Done when: Document compatible use or select/migrate to an appropriate host.
- [ ] **T10.01.2** Complete private account/financial setup — `not_started`. Done when: Required verification, fee/tax obligations and private credential storage are addressed.
- [ ] **T10.01.3** Approve public disclosures and experiment cap — `not_started`. Done when: Integration is permitted, transparent, reversible and budgeted.

### T10.02 — Enable one quiet hosted support option

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.01
**Reserved paths:** `web/`, `content/policies/`, `src/wrap_brief/render/`, `tests/browser/`

**Deliverable:** Optional honest support callout linking to an approved hosted payment provider.

**Done criteria:**
- No payment details collected on Pages; no default recurring charge, guilt or blocking popup.
- Support provider is disclosed and core performance/accessibility/referral tasks remain intact.
- All named checks pass: support-provider-sandbox, support-ux-privacy-check; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T10.02.1** Design minimal support placement and copy — `not_started`. Done when: One nonintrusive callout follows reader value and explains use of funds.
- [ ] **T10.02.2** Integrate approved hosted support flow — `not_started`. Done when: Only reviewed public URLs/IDs ship; private payment state stays with provider.
- [ ] **T10.02.3** Test success/failure/disable paths — `not_started`. Done when: No sensitive data leaks and removal is a small configuration change.

### T10.03 — Pilot disclosed affiliate commerce or sponsorship

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.04
**Reserved paths:** `content/commerce/`, `content/policies/`, `web/`, `docs/experiments/`

**Deliverable:** Only one selected later commercial pilot with useful original content and clear separation.

**Done criteria:**
- Program/contract/provider rules are reviewed; disclosures appear before clicks and no source ranking is sold.
- Audience claims are truthful and contribution is evaluated after operator time.
- All named checks pass: affiliate-or-sponsor-policy, commercial-experiment-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T10.03.1** Choose channel based on audience evidence — `not_started`. Done when: Affiliate purchase intent or sponsor fit has a reasoned business case.
- [ ] **T10.03.2** Ship separated disclosed content/placement — `not_started`. Done when: No editorial card or lead ranking masquerades as paid promotion.
- [ ] **T10.03.3** Evaluate contribution and trust guardrails — `not_started`. Done when: Keep/change/stop decision includes fees/time and user impact.

### T10.04 — Evaluate support conversion and net contribution

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 · **Risk:** medium · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.02
**Reserved paths:** `docs/experiments/`, `docs/evidence/`

**Deliverable:** Time-boxed support experiment result and explicit expand/stop decision.

**Done criteria:**
- Gross donations are not called profit; fees, tools and operator hours are subtracted.
- Conversion is reported only with valid exposure measurement; otherwise raw totals/limitations are shown.
- All named checks pass: revenue-evidence-review, contribution-calculation; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T10.04.1** Collect approved aggregate support outcomes — `not_started`. Done when: No donor records or private provider exports enter the repo.
- [ ] **T10.04.2** Calculate net contribution and workload — `not_started`. Done when: Operator rate, expenses and measurement limits are explicit.
- [ ] **T10.04.3** Choose keep/change/stop before expansion — `not_started`. Done when: Negative economics or trust/performance harm can disable the channel.

### T10.05 — Evaluate and optionally pilot display advertising

**Status:** not_started · **Scope:** revenue · **Milestone:** M4 · **Risk:** high · **Size:** S
**Owner:** Business maintainer
**Dependencies:** T10.04
**Reserved paths:** `web/`, `content/policies/`, `docs/experiments/`, `tests/browser/`

**Deliverable:** Ad go/no-go and, only if approved, a bounded labeled placement with consent controls.

**Done criteria:**
- Hosting/network/original-content/privacy/consent approval precedes scripts.
- Reserved dimensions, Advertisement labels, no-ad fallback and before/after performance/referral checks pass.
- All named checks pass: ad-provider-privacy-approval, ad-performance-trust-guardrails; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T10.05.1** Validate commercial and network eligibility — `not_started`. Done when: Thin aggregation alone is not assumed sufficient for approval.
- [ ] **T10.05.2** Pilot one safe placement or record no-go — `not_started`. Done when: No deceptive card placement, behavioral tracking by default or layout shift.
- [ ] **T10.05.3** Measure return after all costs and harms — `not_started`. Done when: Ads are removed if contribution/reader-value guardrails fail.

## E11 — Evidence-led extensions and scale

**Owner:** Product maintainer. **Outcome:** Optional modular improvements only when demand or limits justify them. [Specification](../specs/architecture.md).

### T11.01 — Expand cadence or source set only with evidence

**Status:** not_started · **Scope:** future · **Milestone:** M5 · **Risk:** medium · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T08.03
**Reserved paths:** `config/sources/`, `.github/workflows/`, `docs/decisions/`, `tests/ingest/`

**Deliverable:** Measured decision to retain daily or use 06:23/18:23 UTC and/or 8–12 approved sources.

**Done criteria:**
- Feed gap/volume/freshness evidence justifies requests; standard public-runner compute is not confused with private credits.
- Every added source meets rights/quality/budget checks and a rollback is documented.
- All named checks pass: cadence-source-cost-review, expanded-source-regression; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T11.01.1** Review truncation, freshness and workload — `not_started`. Done when: Expansion solves an observed issue rather than adding volume for its own sake.
- [ ] **T11.01.2** Refine selected cadence/source changes — `not_started`. Done when: One approved cron and source allowlist remain bounded.
- [ ] **T11.01.3** Validate and compare after change — `not_started`. Done when: Coverage improves without quality, rights or operator-cost regression.

### T11.02 — Select one discovery feature: search, game page or calendar

**Status:** not_started · **Scope:** future · **Milestone:** M5 · **Risk:** medium · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T09.03
**Reserved paths:** `src/wrap_brief/render/`, `web/`, `tests/browser/`, `docs/experiments/`

**Deliverable:** One modular static discovery feature backed by demand, not a full portal rewrite.

**Done criteria:**
- New pages provide unique value; no empty keyword doorway pages or backend dependency without need.
- Core no-JS reading, performance and source attribution remain intact.
- All named checks pass: discovery-feature-acceptance, seo-a11y-performance; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T11.02.1** Choose and refine the highest-value discovery need — `not_started`. Done when: Reader baseline supports search, selected game page or release calendar.
- [ ] **T11.02.2** Implement against existing view models — `not_started`. Done when: Ingestion/state contracts do not need an unnecessary rewrite.
- [ ] **T11.02.3** Measure usage and maintenance burden — `not_started`. Done when: Feature is retained only if value exceeds its operating complexity.

### T11.03 — Add consented email digest only after demonstrated demand

**Status:** not_started · **Scope:** future · **Milestone:** M5 · **Risk:** high · **Size:** S
**Owner:** Product maintainer
**Dependencies:** T09.03, T09.01
**Reserved paths:** `docs/decisions/`, `content/policies/`, `docs/experiments/`, `web/`

**Deliverable:** Approved provider-based newsletter with consent, unsubscribe, private storage and portability.

**Done criteria:**
- Subscriber/suppression lists never enter Git/Pages; signup and unsubscribe work securely.
- Free-tier limits, consent/retention/privacy, export/exit and workload are reviewed.
- All named checks pass: email-consent-unsubscribe, provider-portability-security; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T11.03.1** Validate demand and choose bounded provider — `not_started`. Done when: Cost, deliverability, privacy and migration options are documented.
- [ ] **T11.03.2** Implement consent and lifecycle via provider — `not_started`. Done when: Signup/confirmation/unsubscribe/deletion work without a custom public data store.
- [ ] **T11.03.3** Pilot digest and measure sustainable value — `not_started`. Done when: No scraped outreach or misleading subscriber metrics; stop/exit path is proven.

### T11.04 — Migrate storage or hosting when policy/limits require it

**Status:** not_started · **Scope:** future · **Milestone:** M5 · **Risk:** high · **Size:** M
**Owner:** Product maintainer
**Dependencies:** T08.03, T04.03
**Reserved paths:** `src/wrap_brief/state/`, `.github/workflows/`, `docs/decisions/`, `docs/operations.md`

**Deliverable:** Portable static host/state backend migration preserving public IDs, URLs and recovery.

**Done criteria:**
- Policy, retention/erasure, state growth or reliability need is measured and budgeted.
- Dual-read/restore verification and cutover rollback protect content, tombstones, links and credentials.
- All named checks pass: migration-dry-run, cutover-restore-drill; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T11.04.1** Define migration trigger and target — `not_started`. Done when: Provider terms/cost/retention and secret boundaries satisfy the actual need.
- [ ] **T11.04.2** Migrate snapshots/URLs with validation — `not_started`. Done when: IDs, records, checkpoints and public links remain consistent.
- [ ] **T11.04.3** Rehearse cutover and rollback — `not_started`. Done when: Known-good site/state restore is proven before irreversible cleanup.

### T11.05 — Evaluate advanced grouping or localization as a separate slice

**Status:** not_started · **Scope:** future · **Milestone:** M5 · **Risk:** medium · **Size:** M
**Owner:** Product maintainer
**Dependencies:** T05.03, T09.03
**Reserved paths:** `src/wrap_brief/grouping/`, `tests/benchmarks/`, `content/`, `docs/experiments/`

**Deliverable:** Refined evidence-led experiment, not automatic AI/multilingual scope expansion.

**Done criteria:**
- Benchmark gain or reader demand justifies cost, rights and editorial complexity.
- Baseline deterministic pipeline still works without paid services; language/rumor/correction semantics remain accurate.
- All named checks pass: advanced-feature-benchmark, cost-rights-fallback-review; independent review and public-safe evidence recorded.

**Subtasks:**
- [ ] **T11.05.1** Select one concrete quality or language problem — `not_started`. Done when: Baseline metrics support a narrow experiment with an explicit budget.
- [ ] **T11.05.2** Prototype behind disabled-by-default configuration — `not_started`. Done when: Provider/privacy/translation rights and fallback are reviewed before use.
- [ ] **T11.05.3** Compare quality, cost and operational burden — `not_started`. Done when: Only a measurable improvement proceeds; failed experiment is removed cleanly.
