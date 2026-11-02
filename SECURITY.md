# Security and public-data policy

## Reporting

Never disclose a suspected secret, vulnerability reproduction payload or private log in a public issue or PR. **GitHub private vulnerability reporting is enabled** for this public repository. Use [Report a vulnerability privately](https://github.com/dmoliveira/wrap-brief/security/advisories/new), also reachable through the repository's Security tab. This creates a private report for maintainers, not a public issue.

Share the affected component/version, impact and the minimum reproduction needed. Prefer synthetic examples; never send active credentials, account exports, publisher feed dumps or unrelated personal data. If a credential may be exposed, revoke/rotate it first. Do not create a fake vulnerability report just to test the form.

If you cannot access the private route, **do not fall back to public issues, PRs or attachments** with sensitive details. Wait for a working private route. The project does not promise a response SLA, bug bounty, legal safe-harbor or encryption mechanism that has not been established. Ordinary non-sensitive bugs use the public-safe issue templates. The maintainer is [@dmoliveira](https://github.com/dmoliveira); no private contact details are published here.

## Never commit or publish

- API keys, tokens, passwords, cookies, private keys, webhook secrets, or cloud credential files.
- `.env` files except a placeholder-only `.env.example` reviewed for public safety.
- Subscriber emails, IP addresses, analytics identifiers, payment/donation records, or exports from service dashboards.
- Agent sessions, Codememory databases/exports, local filesystem paths, debug dumps, raw HTTP headers, or workflow environment dumps.
- Publisher full text, images, feed descriptions, or raw feed responses without a specific approved retention/reuse purpose.

`.gitignore` is defense in depth, not a secret scanner. It does not remove files already tracked or erase Git history. Scan the worktree and history before first public push; keep secret scanning/push protection enabled when supported. Review workflow logs, artifacts, state snapshots, and generated HTML/JSON as additional publication surfaces.

## Credentials and automation

- Use ephemeral `GITHUB_TOKEN` and Pages OIDC, not a long-lived personal access token, for normal publishing.
- The canonical job/token/branch/artifact threat controls and proving tests are in [security/privacy](docs/specs/security-privacy.md). A contents-write token is not branch-scoped; protect main and test the real platform rules.
- Fork checks are unprivileged; only reviewed default-branch code may persist/deploy. Pin Actions and lock dependencies. Never execute downloaded feed/artifact content.
- Future ad/newsletter/donation credentials belong in provider secret storage or GitHub Secrets/Environments, never browser code. Public provider IDs are not credentials but still require review.

## Incident response

1. Stop the affected workflow/integration and preserve a private incident record.
2. Revoke/rotate exposed credentials first; deleting a file or repository is not revocation.
3. Assess exposure across Git history, Pages, logs, artifacts, state, caches, issues, and third-party mirrors.
4. Follow the provider's recovery process; coordinate any necessary history rewrite privately and explicitly.
5. Restore a reviewed known-good deployment, document public-safe findings, and add a regression check.

No plan can guarantee that sensitive information will never be introduced. Prevention, scanning, least privilege, review, and a tested response are all required.
