# Wrap Brief contributor and agent contract

## Scope and startup

- Read `README.md`, `docs/plan/STATUS.md`, and the selected task in `docs/plan/BACKLOG.md`.
- Treat `docs/plan/backlog.json` as the public plan/status snapshot. GitHub owns issue/PR delivery state; Codememory is private execution context, not another public completion authority.
- Before product implementation, inspect current remote, issues, and PRs; use a dedicated worktree and one focused task. Do not build future features just because they appear in the roadmap.
- Follow `docs/codememory-workflow.md` when the optional local tool is available. Contributors must be able to work without private agent tooling.

## Implementation principles

- Small validated vertical slices; one writer per shared path, at most two active parallel lanes.
- Agree schemas and fixtures before parallel producers/consumers. Keep ingestion, state, grouping, editorial, rendering, and deployment separate.
- Python: `uv`, `ruff`, type hints at module boundaries, pure functions where practical, explicit UTC, injected clocks/network, deterministic fixtures. Prefer the standard library; justify and lock additional dependencies.
- Treat feeds, URLs, HTML, metadata, and downloaded artifacts as hostile input. No arbitrary crawling, automatic article rewriting, or unlicensed images.
- Core reading must work without JavaScript. Semantic HTML, accessible contrast/focus, progressive enhancement, fast static output.
- No credentials, personal data, private logs, local machine paths, or runtime databases in tracked files, public artifacts, issues, or comments.

## Delivery and evidence

- Run `make help` first, then follow the current checks and risk bundle in `docs/validation-policy.md`. Product checks remain future tasks, not commands claimed to exist today.
- Follow `docs/delivery-workflow.md` for PR review/evidence and `docs/specs/security-privacy.md` for automation trust boundaries. Do not bypass repository protections.
- Update task/subtask status and public-safe completion evidence together. Regenerate progress. `done` requires dependencies, subtasks, verification results, and review; writing a specification does not finish its product task.
- If blocked, record the precise dependency/reason and next action. Future scopes stay disabled until their activation gate is evidenced.

## References

- `docs/delivery-workflow.md`
- `docs/validation-policy.md`
- `docs/specs/security-privacy.md`
- `docs/operations.md`
