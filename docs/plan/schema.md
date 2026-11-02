# Backlog and progress contract

`backlog.json` is a dependency graph and public progress snapshot. No private execution IDs, credentials, provider exports, or user data belong in it. Generated Markdown is a view, not a second source of truth.

## Shape

- `schema_version`: integer `1`.
- `project`: public name, planning date, enabled scopes, and parallel-lane limit.
- `scopes`: `planning`, `mvp`, `growth`, `revenue`, `future`, each with an activation rule. Only `planning` and `mvp` initially enabled.
- `milestones`: IDs, `kind` (`gate` or `portfolio`), prerequisite milestone IDs in `depends_on`, owners, entry/exit criteria, and mandatory primary task IDs. A gate completes only when its listed tasks **and predecessor gates** are done. A portfolio is never automatically complete.
- `epics`: ID, title, owner role, objective, and specification path. Epic progress is calculated from its tasks.
- `tasks`: stable ID, epic, scope, primary milestone, `gate_required` boolean, title, owner role, allowed paths, dependencies, risk, size, deliverable, acceptance criteria, verification names, subtasks, status, block reason, completion record.
- Each subtask has a stable ID, title, status, explicit `done_when`, and public evidence paths.
- Completion records have evidence paths, named check results, and a reviewed/pass evidence record. They are intentionally empty on unimplemented tasks.

IDs are stable (`E01`, `T01.01`, `T01.01.1`). Do not renumber shipped tasks. Replacement work gets a new ID and a traceable cancellation note.

## Status and transitions

`not_started → in_progress → review → done`; use `blocked` with a concrete reason when safe progress is impossible. `canceled` is explicit scope removal, not successful completion. A task in `review` is still incomplete. Reopening means clearing stale completion claims, recording why, and returning to `in_progress`.

Readiness is derived, not manually stored: enabled scope, `not_started` status, and every dependency `done`. A blocked task is not ready. Dependencies are AND edges over task IDs. **There are no conditional edges or OR dependencies**: optional work belongs to disabled scopes and all edges are checked for cycles, even when disabled. MVP tasks cannot depend on disabled later scopes. Scope activation requires a recorded decision, satisfied gate tasks, and review, as described in the roadmap; the tool never activates a feature automatically.

Milestone predecessor edges govern **completion**, not task readiness: foundation work assigned to M2 can start before M1 is complete when its task prerequisites allow it. Each milestone lists exactly its primary tasks marked `gate_required=true`. M2 inherits M1 through a milestone edge rather than repeating its task list. Optional M4 channels and M5 portfolio tasks have `gate_required=false`; they do not silently become launch requirements. Both dependency graphs are cycle-checked.

The validator checks current-state consistency, not an append-only history of transitions. Git diffs, PR review, GitHub history, and private task events provide transition history.

## Completion and percentages

- Done tasks need done dependencies, all subtasks done with evidence, acceptance criteria, every named verification marked pass with evidence, and passing review evidence.
- Every non-done task has the empty completion record (`evidence=[]`, `checks=[]`, `review=null`). Reopening clears stale claims. A not-started task cannot contain active/done subtasks; unfinished subtasks cannot retain completion evidence. In-progress parents may have completed subtasks with their own evidence.
- Evidence must be a repository-relative existing file, not an absolute path, URL with a token, private log, or generated status page. External CI/PR references can be summarized in a public-safe evidence file.
- Planning tasks demonstrate only planning/tool completion. Product implementation has its own denominator.
- Report `done / non-canceled tasks` separately by scope and epic; canceled count remains visible. No invented percentage from hours or subtask estimates.
- Also show subtask counts; do not equate task-count progress with effort-weighted progress.
- `BACKLOG.md` and `STATUS.md` are generated deterministically, without a changing build-time timestamp. `project.updated` changes only with a meaningful plan/status update.
- Later-task subtasks are refinement checklists, not fixed commitments. Refine them just before activating the corresponding scope.

## Checks

`make check-plan` checks field types, real calendar dates, IDs, references, parent/state consistency, task and milestone DAGs, exact gate membership, disabled-scope dependency leaks, completion evidence, local Markdown links, publication-safety heuristics, and generated-file drift. Publication checks accept binary assets while still detecting ASCII token patterns; a dedicated scanner remains required. See [validation policy](../validation-policy.md) for checks and limitations.
