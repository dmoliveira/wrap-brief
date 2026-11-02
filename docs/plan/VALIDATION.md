# Planning-pack validation evidence

This file records only public-safe planning/tool validation. It is **not** evidence of feed rights approval, product implementation, a working deployment, ad/provider approval, or a live accessibility audit.

## Initial planning checkpoint

- Architecture/sequence and reader-experience specialists reviewed the proposed structure.
- Pre-write plan review identified scope-denominator, state-writer, rights, quality and progress risks. The plan addresses them with separate scopes, all-edge dependency validation, explicit privileged-writer tests, source approval records, measurable gates, and separate planning/product completion.
- Final review found two tracker defects: ignored/private evidence could satisfy completion, and malformed check records could crash validation. Both were repaired, regression-tested, and approved in scoped follow-up review. A PR-merge whitespace-check improvement was also applied.
- `make check-plan`: passed for 12 epics, 48 tasks, and 144 subtasks; checks include all-edge dependencies, activation gates, local links, publication heuristics, and generated-view agreement.
- `make test-plan`: 36 deterministic tests passed, including ignored/sensitive/symlink evidence and malformed check/review regressions.
- `ruff check tools tests` and `ruff format --check tools tests`: passed with Ruff 0.16.2.
- `make validate` combines the actual plan, test, Ruff lint and format checks into one reproducible local gate; it requires Ruff in addition to standard-library Python.
- `git diff --cached --check`: passed. Planning-only CI uses a read-only SHA-pinned checkout and checks the candidate against its first parent, including PR merge results.
- `actionlint` 1.7.7: passed for the planning-only workflow. No product collection, tracking, deployment, or payment workflow is enabled.
- Gitleaks 8.24.3, downloaded from its official release and SHA256-verified: staged publication tree scan found zero leaks. Bootstrap history contains no content; full committed history must be rescanned before first push.
- Manual public-data inspection: only 25 intended plan/tool/config files are candidates; local runtime state, private task mappings, scanner output and databases are excluded. Source approval, brand clearance and product security controls remain unimplemented tasks, not implied approvals.
- Independent final verifier reran plan checks, all 36 tests, Ruff lint/format, staged whitespace and actionlint: all passed, no blockers. Graph/status/public-path audit also passed. Only T00.01 (planning) is complete; all 47 product tasks remain not started.
- Final delivery gate: regenerate and recheck after status bookkeeping, rescan the exact committed tree/history before first public push, and require the planning CI checks on the PR. GitHub records the actual remote check/merge result; no site release is implied.

## Required commands

`make check-plan`, `make test-plan`, planning-tool lint/format checks, `git diff --check`, a dedicated credential scan and manual public-data inspection. Record totals/outcomes after execution; do not paste raw logs or internal runtime identifiers.

## Review/refinement checkpoint

The follow-up audit retained the 48 stable task IDs rather than expanding the backlog. Main corrections:

| Finding | Correction |
| --- | --- |
| Launch task required all MVP tasks including itself | T08.03 requires prerequisite tasks and a final security delta check |
| Security review could predate integrated deployment | T08.01 now waits for health and operational recovery integration |
| Source feasibility discovered after prototype work | T02.04 is an early feasibility gate; T02.02 retains final source approval/onboarding |
| Independent monitor both optional and mandatory | M2 is explicitly supervised; T11.01 requires an independent monitor before unattended claims |
| Original-editorial production blocked a metadata MVP | T05.04 keeps corrections/provenance; T09.02 owns original-brief production |
| Recovery and handoff repeated the same drills | Component, operational-drill and evidence-handoff ownership are distinct |
| Milestone lists duplicated earlier tasks and hid optional scope | Explicit predecessor gates and exact primary `gate_required` membership |
| Reopened/malformed states could retain completion claims | Typed nested checks, parent-state consistency and stale-evidence rejection |
| Binary assets crashed publication checks | Byte decoding preserves ASCII-token scanning without rejecting non-UTF-8 assets |
| Local quality checks exceeded CI coverage | CI uses the actual lint/format/test gate with pinned tools and Python 3.11/3.13 |

Final audit results:

- `make validate`: passed with **51 tests**, plan validation, Ruff lint and formatting.
- Python **3.11 and 3.13**: 51 tests passed independently on each; the pinned UV 0.9.7 and Ruff 0.16.2 tooling also executed successfully.
- `actionlint` and diff whitespace checks: passed. CI no longer duplicates push and PR runs for the planning branch and now runs lint/format as well as tests.
- Independent implementation review: no critical/high/medium findings; independent final verifier: passed with no blockers.
- Exact staged publication-tree Gitleaks scan: zero findings. Full committed history is rescanned before push as a delivery gate.
- All 48 stable tasks remain: planning 1 done, product 47 not started. Ready work adds early feasibility T02.04; no product completion is inferred from this audit.
- PR delivery remains separate from planning progress. The existing PR merge is still blocked on a GitHub-approved public noreply identity; no private default email is used or published.
