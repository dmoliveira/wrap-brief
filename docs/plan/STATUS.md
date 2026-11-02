# Wrap Brief — progress

> Generated from backlog.json; do not edit. Task-count progress is not effort-weighted.

Plan updated: 2026-11-02. **Product is not implemented merely because planning is complete.**

## Scope progress

| Scope | Enabled | Completed tasks |
| --- | --- | --- |
| planning | yes | 1/1 (100%) · 0 canceled |
| mvp | yes | 7/33 (21%) · 0 canceled |
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
| E01 | Repository, toolchain, and governance | 1/4 (25%) · 0 canceled | 3/12 |
| E02 | Source approval and versioned contracts | 3/4 (75%) · 0 canceled | 9/12 |
| E03 | Bounded feed collection and normalization | 2/4 (50%) · 0 canceled | 6/12 |
| E04 | Durable state and pipeline recovery | 0/4 (0%) · 0 canceled | 0/12 |
| E05 | Identity, story grouping, and editorial trust | 1/4 (25%) · 0 canceled | 3/12 |
| E06 | Minimalist static reader experience | 0/4 (0%) · 0 canceled | 0/12 |
| E07 | CI, scheduled automation, publishing, and monitoring | 0/5 (0%) · 0 canceled | 0/15 |
| E08 | Security, UX, and live pilot release | 0/4 (0%) · 0 canceled | 0/12 |
| E09 | Original value and audience validation | 0/4 (0%) · 0 canceled | 0/12 |
| E10 | Gated support and commercial experiments | 0/5 (0%) · 0 canceled | 0/15 |
| E11 | Evidence-led extensions and scale | 0/5 (0%) · 0 canceled | 0/15 |

## Active and blocked

- **T02.02** — Approve the first 3–5 sources · blocked · Zero approved live sources. Resolve permitted public fields, attribution, polling, retention/deletion, public rendering/artifacts and commercial restrictions before enabling any source; see docs/sources/FEASIBILITY.md and issue #4.

## Dependency-ready work

Choose at most two disjoint lanes; readiness is not permission to overlap shared files.

- **T01.01** — Establish public repository rules and reporting (Platform maintainer)
- **T01.04** — Clear brand, code license, and policy copy (Platform maintainer)
- **T03.01** — Implement bounded safe feed HTTP client (Data maintainer)
- **T04.01** — Implement backend-neutral snapshots and local prototype state (Platform maintainer)
- **T05.02** — Group same-event coverage and choose lead source (Editorial maintainer)
- **T06.01** — Create responsive visual tokens and semantic shell (Web maintainer)

## Disabled-scope rules

- **growth**: Enable after M2 with recorded milestone evidence; refine just in time.
- **revenue**: Enable after M3; complete T10.01 before any commercial integration.
- **future**: Enable after M2 plus a recorded measured need/budget; select only one relevant slice.

[Full backlog](BACKLOG.md) · [Roadmap](new/roadmap.md) · [Schema](schema.md)
