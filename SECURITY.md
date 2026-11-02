# Security and public-data policy

## Reporting

Never disclose a suspected secret or exploit payload in a public issue. Use GitHub private vulnerability reporting once enabled. Until a private reporting route is configured, do not post sensitive details; establishing that route is a foundation task and a prerequisite to production collection.

## Never commit or publish

- API keys, tokens, passwords, cookies, private keys, webhook secrets, or cloud credential files.
- `.env` files except a placeholder-only `.env.example` reviewed for public safety.
- Subscriber emails, IP addresses, analytics identifiers, payment/donation records, or exports from service dashboards.
- Agent sessions, Codememory databases/exports, local filesystem paths, debug dumps, raw HTTP headers, or workflow environment dumps.
- Publisher full text, images, feed descriptions, or raw feed responses without a specific approved retention/reuse purpose.

`.gitignore` is defense in depth, not a secret scanner. It does not remove files already tracked or erase Git history. Scan the worktree and history before first public push; keep secret scanning/push protection enabled when supported. Review workflow logs, artifacts, state snapshots, and generated HTML/JSON as additional publication surfaces.

## Credentials and automation

- Use ephemeral `GITHUB_TOKEN` and Pages OIDC, not a long-lived personal access token, for normal publishing.
- Default workflow permissions to none/read; split network collection, state writing, rendering, and Pages deployment into separate jobs.
- A token with `contents: write` is repository-scoped, **not branch-scoped**. Protect `main` with required PR/check rules and no automation bypass; validate actual platform behavior in a sandbox.
- Only reviewed default-branch workflows may persist state or deploy. Fork PR checks get no secrets and no write permission. Do not use `pull_request_target` to execute PR-controlled code.
- Pin Actions to reviewed full commit SHAs. Lock dependencies. Never execute files obtained from feeds or candidate data artifacts.
- Future ad/newsletter/donation credentials belong in provider secret storage or GitHub Secrets/Environments, never browser code. Public provider IDs are not credentials but still require review.

## Incident response

1. Stop the affected workflow/integration and preserve a private incident record.
2. Revoke/rotate exposed credentials first; deleting a file or repository is not revocation.
3. Assess exposure across Git history, Pages, logs, artifacts, state, caches, issues, and third-party mirrors.
4. Follow the provider's recovery process; coordinate any necessary history rewrite privately and explicitly.
5. Restore a reviewed known-good deployment, document public-safe findings, and add a regression check.

No plan can guarantee that sensitive information will never be introduced. Prevention, scanning, least privilege, review, and a tested response are all required.
