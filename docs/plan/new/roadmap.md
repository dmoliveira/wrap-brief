# Wrap Brief: staged end-to-end delivery plan

## Intent and boundaries

Maximize useful reader attention and contribution after operator time, not page-view inflation. Begin with a trustworthy daily briefing, then invest only where evidence supports expansion. Depth: large planning scope. Current change risk: low (documentation and local plan tooling); future ingestion, credentials, state writes, tracking, and monetization are high-risk slices.

The full decomposed plan is [generated from the backlog](../BACKLOG.md). Detailed product tasks remain unstarted. The planning package is the current deliverable, not authorization to enable payments, third-party tracking, or unsafe publication.

## Milestones

| Gate | Entry | Exit / evidence | Scope |
| --- | --- | --- | --- |
| M0 Plan ready | Confirm intent and current repository state | Reviewed plan, valid dependency graph, tested tracker, publication-safety checks | planning |
| M1 Fixture prototype | M0; early source-feasibility go/no-go before substantial contracts/UI work | Deterministic fixture → grouped static homepage, mobile/keyboard/no-JS checks, no network/deploy dependency | mvp |
| M2 Daily supervised public pilot | M1; final source/brand clearance, full MVP checks | 3–5 approved feeds or a smaller viable set, durable state, daily Pages release, named daily health check, one operational rollback drill, final integrated security review | mvp |
| M3 Audience validation | M2; at least four weeks of observable operation | Original-content experiment, privacy decision, measured reader-value/workload baseline; no unsupported retention claims | growth |
| M4 Revenue validation | M3; hosting/provider/privacy/commercial gates | One reversible monetization experiment, disclosures, performance/trust checks, net contribution review | revenue |
| M5 Selective expansion | M2 and a concrete measured need | Only selected scale/feature work enabled with budget, migration/rollback, no mandatory platform rewrite | future |

Mandatory task lists and predecessor gates live in `backlog.json`; this table explains intent. M2 inherits M1, M4 requires only the first selected support experiment, and M5 is a portfolio—not a promise to ship every idea. Gate owners record public-safe evidence. Source uncertainty reduces/stops the pilot; absent original content means honest attributed listings, not copied or fabricated prose.

## Sequence and safe parallel work

```text
M0 planning
   ↓
E01 foundations + early E02 source-feasibility check
   ↓
E02 contracts + final source approval
   ├── Lane A: E03 feed client/parser ─→ E04 durable state ─┐
   └── Lane B: E06 static UI against approved fixtures ───┤
                      E05 grouping/editorial ────────────┤
                                                       ↓
                            E07 safe automation/publish
                                                       ↓
                          E08 adversarial + live release gates
                                                       ↓
                                     M2 daily pilot
                      ┌────────────────┼─────────────────┐
                      ↓                ↓                 ↓
                E09 audience     E11 justified      operations
                      ↓          extensions         maintenance
                E10 one gated
              revenue experiment
```

This is a readable overview; **task dependencies are authoritative**. Some foundations can run concurrently after schema/security agreements; final integration gates join them.

### Lane reservations

| Wave | Lane A | Lane B | Join condition |
| --- | --- | --- | --- |
| 0 | Foundation/security setup | Early source feasibility and brand/rights inventory | Feasibility precedes substantial contracts/UI; final activation still needs the registry |
| 1 | Network/parser fixtures (`src/wrap_brief/ingest/`, `tests/ingest/`) | Static UX (`src/wrap_brief/render/`, `web/`, `tests/render/`) | Shared schemas and fixtures frozen for the slice |
| 2 | State/recovery (`src/wrap_brief/state/`, `tests/state/`) | Grouping/editorial (`src/wrap_brief/grouping/`, `content/`, corresponding tests) | Complete deterministic candidate snapshot |
| 3 | Workflow/publish (`.github/workflows/`, deployment tooling) | Reader validation against stable UI; final security review after deployment/recovery exists | One operational recovery drill, integrated review/delta checks, then one owner releases |
| 4 | One measured growth or revenue slice | Independent operation/quality improvements | Disabled scopes activated explicitly; no cross-lane contract edits |

- Maximum two active workers; one integrating writer for shared contracts, lockfiles, source registry, workflows, and progress files.
- Each task has a worktree, owner, reserved paths, dependencies, acceptance checks, and evidence. Read-only review may overlap implementation; two writers cannot overlap paths.
- Shared fixture/schema changes are coordinated first, then rebased into consumers. No long-lived branch train requiring a large unreviewable merge.
- Never parallelize state writes, production deployments, schema migration, credential rotation, or rollback. Use one shared concurrency group for collection/manual/recovery workflows touching production state.

## MVP explicitly excludes

Accounts, comments, user-generated content, personalization, paid AI, embeddings/vector databases, automatic article rewriting, full-text scraping, default publisher images, multi-language duplication, automatic social spam, email delivery, ad networks, and a custom payment backend.

3–5 approved sources are sufficient to validate; increase toward 8–12 only after source quality and workload justify it. Daily collection can miss truncated feeds: detect and disclose possible gaps. Every 12 hours (`23 6,18 * * *`) is an evidence-led configuration change, not contingent on public-repo compute credits.

The pilot is **supervised**: a named maintainer checks health daily. No third-party monitor is needed to test reader value, but unattended operation must not be claimed. T11.01 can later replace supervision with independently tested stale-schedule monitoring. MVP correction/takedown controls are mandatory; original-brief production belongs to growth T09.02, not the launch critical path.

Evidence has one owner: T04.03 tests component recovery/migration; T07.05 owns the end-to-end operational restore; T08.04 checks handoff usability against existing evidence. Repeat a drill only when its behavior or inputs changed.

## Activation and iteration

- Only `planning` and `mvp` are enabled initially. Enable `growth` after M2; enable `revenue` planning after M3, then finish T10.01 before any commercial integration; enable `future` after M2 plus a specific recorded need and budget. Record gate evidence before changing `enabled_scopes`.
- Within an enabled optional scope, do not start every available task. Pick one experiment, refine its three checklist subtasks, cap operator time/cash, and define stop/rollback criteria.
- Weekly during the pilot: review failed/stale sources, false merges, publisher referrals if measured, original editorial value, accessibility/performance, operator minutes, and unresolved risks.
- Every four weeks: keep, change, or stop experiments. Do not claim profitability from gross receipts; subtract fees, tools, and operator time at an agreed rate.
- Revisit the plan when real evidence contradicts assumptions; use small PRs to update criteria, add tasks, or cancel scope with rationale. Do not silently lower a failed release criterion.

## Hard stop gates

No unapproved source publication; no secret in public surfaces; no elevated fork workflow; no untested recovery; no unattended-operation/completeness/freshness claim without evidence; no ranking by commercial value; no monetization before hosting/provider/privacy compatibility is resolved. Ordinary code/check failures are repair work, not routine approval checkpoints.
