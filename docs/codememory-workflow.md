# Optional private execution memory

The public project must remain usable without Codememory or any private agent service. When available, use it for resumable task/session context; do not publish its database, export, internal actor/session IDs, local paths, or raw handoff logs.

## Startup

1. Read `AGENTS.md`, current public progress, and remote/issue/PR state.
2. Inspect installed `oc --help`; use `oc current`, `oc next --scope dmoliveira/wrap-brief --limit 5`, and `oc queue --scope dmoliveira/wrap-brief --limit 10`.
3. Resume a matching task/session rather than create duplicates. Stable public IDs (`T01.01`, etc.) identify mirrored private records by title.
4. Bind one session to the actual dedicated worktree and one active focused task. Use the runtime's exact current session ID in private actor/log metadata, never in public project files.

## Tracker split

- `backlog.json`: reviewed public scope/dependencies/status/evidence snapshot; generated progress.
- GitHub: delivery issues, PRs, required checks, merge/release state.
- Codememory: private execution context, decisions, blockers, recovery, task/session mirrors. It is not an alternate public completion authority.

Mirror epic/task dependency links internally; keep public-to-private mappings local/ignored. Do not export an entire database just to share a plan. Subtask acceptance is already explicit in the public backlog; only promote a subtask to a separate execution record when it needs independent ownership/handoff.

## During work and closeout

Capture durable decisions, assumptions, blockers, and handoff facts—not every command. On completion update the public evidence/status, merge/check the delivery state, then close private task/session with the outcome. When continuing, keep the session truthful and focused.

## Bounded outage fallback

If the optional tool/config/database is unavailable, record the exact failure without credentials, use the public stable task ID plus GitHub issue/PR and a short public-safe evidence note, and keep the worktree/check/review lifecycle unchanged. Do not create an ad-hoc replacement private database in the public tree. Reconcile private context once available; public completed status still requires actual evidence.
