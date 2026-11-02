# Small-slice delivery workflow

## 1. Pick and align

Run `make next`; choose one dependency-ready task in an enabled scope. Read its spec, acceptance criteria, and dependencies. Check latest remote/issue/PR state before implementation. A task's allowed paths are a reservation, not permission to edit another worker's files.

Create a dedicated worktree/branch and attach private task context when available. Capture objective, owner, input contracts, path reservation, named checks, completion evidence, and rollback. Keep one focused task active per worktree and at most two active parallel workers.

## 2. Define and implement the smallest useful slice

Mark task and active subtask `in_progress`. Agree fixture/schema changes before splitting producer and consumer work. Prefer pure tested stages, explicit error handling, deterministic fixtures, small commits, and minimal dependencies. No new service/framework without a task-specific reason and cost/security review.

Parallelize only disjoint paths. One integrator owns schema, shared fixtures, lockfiles, registry, workflows, and progress; peers submit changes rather than race-edit them. Never run production state mutation or deployment in parallel.

## 3. Validate and review

Run the task's named checks and the [risk bundle](validation-policy.md). Repair failures within scope; do not hand routine failed-check decisions to the user. Move to `review` only with evidence. Reviews check acceptance, security, rights, UX, modularity, and regression risk; no repeat unchanged-diff review loops.

If blocked by a secret/provider account, policy decision, rights uncertainty, or platform limitation, record exact reason/evidence/next action, set `blocked`, and select another independent ready task. Do not fabricate account details or mark a blocked task complete.

## 4. Complete and deliver

- All dependencies and subtasks done; every task verification has a pass/evidence entry; review passes with public-safe evidence.
- Merge only through the repository's PR flow with required checks/protections. Recheck latest upstream and overlapping work before merge.
- Evidence file summarizes commands/results, relevant commit/PR/CI references, manual/browser checks, and rollout/rollback when appropriate. Never include private logs, credentials, machine paths, or internal session IDs.
- Update `backlog.json` completion fields and status, run `make render-plan`, `make check-plan`, `make test-plan`, and `git diff --check`. This public snapshot must agree with the delivery result.
- Update private task/session context separately; never publish its database/export. Close completed task/session only after evidence passes.

## 5. Operate and iterate

For release slices, perform a real public-URL smoke check and monitor the next scheduled cycle. Record outcomes, not promises. Review the pilot weekly and experiment economics every four weeks. Keep high-value maintenance visible in the backlog; refine later work just in time.

## Global definition of done

Acceptance is demonstrably met; tests/checks pass; no high-severity review blocker; security/rights/privacy gates satisfied; user-facing flows accessible; documentation/status updated; deployment/rollback proven when touched; no private information in public surfaces. A task-count percentage is not an effort estimate, and a specification is not product implementation.

## GitHub delivery tracking

The initial public backlog lives in version control. Create GitHub issues for the **current milestone's** epics/tasks as work starts, retaining stable backlog IDs in titles and links; do not create hundreds of stale issues up front. PRs reference those IDs. GitHub issues/PRs own delivery lifecycle; the JSON is the reviewed public scope/status snapshot. Resolve any mismatch before marking a task done. This avoids both tracker spam and an unmaintained second truth.
