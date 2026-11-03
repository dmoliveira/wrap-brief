# Wrap Brief — progress

> Generated from backlog.json; do not edit. Task-count progress is not effort-weighted.

Plan updated: 2026-11-03. **Product is not implemented merely because planning is complete.**

## Scope progress

| Scope | Enabled | Completed tasks |
| --- | --- | --- |
| planning | yes | 1/1 (100%) · 0 canceled |
| mvp | yes | 16/33 (48%) · 0 canceled |
| growth | no | 0/4 (0%) · 0 canceled |
| revenue | no | 0/5 (0%) · 0 canceled |
| future | no | 0/5 (0%) · 0 canceled |

## Milestones

| Gate | Outcome | Prerequisite gates | Status |
| --- | --- | --- | --- |
| M0 | Planning ready | none | done |
| M1 | Fixture-only reader prototype | M0 | not complete |
| M2 | Daily supervised noncommercial public pilot | M1 | not complete |
| M3 | Audience and workload validation | M2 | not complete |
| M4 | First revenue experiment validated | M3 | not complete |
| M5 | Selective extension opportunities | M2 | portfolio, select only justified tasks |

## Epics

| ID | Component | Task progress | Subtasks done |
| --- | --- | --- | --- |
| E00 | Planning and evidence-driven execution | 1/1 (100%) · 0 canceled | 3/3 |
| E01 | Repository, toolchain, and governance | 2/4 (50%) · 0 canceled | 8/12 |
| E02 | Source approval and versioned contracts | 3/4 (75%) · 0 canceled | 9/12 |
| E03 | Bounded feed collection and normalization | 4/4 (100%) · 0 canceled | 12/12 |
| E04 | Durable state and pipeline recovery | 2/4 (50%) · 0 canceled | 6/12 |
| E05 | Identity, story grouping, and editorial trust | 3/4 (75%) · 0 canceled | 10/12 |
| E06 | Minimalist static reader experience | 2/4 (50%) · 0 canceled | 6/12 |
| E07 | CI, scheduled automation, publishing, and monitoring | 0/5 (0%) · 0 canceled | 0/15 |
| E08 | Security, UX, and live pilot release | 0/4 (0%) · 0 canceled | 0/12 |
| E09 | Original value and audience validation | 0/4 (0%) · 0 canceled | 0/12 |
| E10 | Gated support and commercial experiments | 0/5 (0%) · 0 canceled | 0/15 |
| E11 | Evidence-led extensions and scale | 0/5 (0%) · 0 canceled | 0/15 |

## Active and blocked

- **T01.03** — Add dependency, action, and credential safety checks · blocked · Read-only CI diagnostics and pinned scans delivered in PR #33, but an authorized cross-account malicious-fork drill is unavailable. Only the owner principal is available; verify real fork secret withholding, write/OIDC rejection and unchanged sacrificial state before completing T01.03.3. Candidate-controlled checks are not immutable admission proof; see issue #32 and docs/evidence/T01.03-ci-safety.md.
- **T02.02** — Approve the first 3–5 sources · blocked · Zero approved live sources. Resolve permitted public fields, attribution, polling, retention/deletion, public rendering/artifacts and commercial restrictions before enabling any source; see docs/sources/FEASIBILITY.md and issue #4.
- **T05.03** — Benchmark grouping and add reviewed split/merge overrides · blocked · Reviewed override/replay and measurement APIs are delivered as a partial slice, but no qualifying rights-safe independently adjudicated real-event corpus or actual >=100-pair >=98%-precision result exists. Frozen synthetic measurement predicts zero merges (undefined precision, zero recall), not a passing gold benchmark. Supply the authorized real corpus and qualifying measurements before completing T05.03.1/.2 or the parent; see issue #38 and docs/evidence/T05.03-grouping-evaluation.md.
- **T06.04** — Prove core accessibility and performance budgets · blocked · Real screen-reader session outstanding: VoiceOver is installed but not running; no-prompt readiness probe returned application-not-running. Authorized real-AT testing is required; automated checks cannot establish spoken behavior. See docs/evidence/T06.04-reader-validation.md.

## Dependency-ready work

Choose at most two disjoint lanes; readiness is not permission to overlap shared files.

- **T01.04** — Clear brand, code license, and policy copy (Platform maintainer)

## Disabled-scope rules

- **growth**: Enable after M2 with recorded milestone evidence; refine just in time.
- **revenue**: Enable after M3; complete T10.01 before any commercial integration.
- **future**: Enable after M2 plus a recorded measured need/budget; select only one relevant slice.

[Full backlog](BACKLOG.md) · [Roadmap](new/roadmap.md) · [Schema](schema.md)
