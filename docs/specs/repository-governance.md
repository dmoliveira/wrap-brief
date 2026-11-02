# Repository governance and reporting (T01.01)

## Observed platform rules

The public `dmoliveira/wrap-brief` repository uses protected `main`. API inspection and an isolated protected-branch experiment confirm the rules below are active for this repository; these are not merely proposed settings or claims about another account tier. Public-repository protection features are sufficient for this foundation slice; no paid/private-repository entitlement is assumed or provisioned.

| Control | Observed setting |
| --- | --- |
| Pull request required | Enabled, including administrators |
| Required status | `Planning checks`, bound to GitHub Actions app ID `15368` |
| Up-to-date base required | Strict required-status setting enabled |
| Administrator enforcement | Enabled |
| Force pushes / deletion | Disabled on `main` |
| Required approving peer reviews | **0** |
| Required code-owner review | Disabled |
| Stale-review dismissal | Enabled |
| Default workflow token | Read-only; cannot approve PR reviews |
| Private vulnerability reporting | Enabled |
| Secret scanning / push protection | Enabled; dedicated CI supply-chain/scanner automation remains T01.03 |

The sole current public maintainer is `@dmoliveira`. `.github/CODEOWNERS` routes review requests; it neither changes repository permission nor establishes enforced independent approval. The project requires recorded review and verification, but the platform currently does **not** enforce a two-person gate. Repository administrators retain the platform ability to change settings; no claim of protection from a compromised owner/admin account is made. Routine delivery must not use bypasses, weaken rules or push directly to `main`.

The required job name/app binding is a delivery API: rename it only with coordinated protection updates that preserve enforcement. Merge only the exact checked head after checking current upstream/overlap; record public-safe evidence. Missing, failed or pending required checks block merge. The current job validates the locked package/plan/tests/Ruff, minimum Python, standalone planning and isolated wheel; it does not deploy, collect feeds, access private state or prove all future production security controls.

## Fork contribution trust boundary

The existing workflow runs unprivileged `pull_request`, not `pull_request_target` or a privileged follow-up that executes candidate code. Root permissions are empty; the validation job requests only `contents: read`. Checkout does not persist credentials, and the workflow references no repository secrets, deployment or state-writing capability. Local setup and fork contributions require no production credential or private agent service. GitHub may require maintainer approval before an external contributor's workflow runs; contributors must not supply tokens to evade that gate.

This is **configured-policy/static evidence**, not an executed cross-account fork attack simulation. The normal delivery PR provides actual `pull_request` CI evidence; it must not be described as a fork PR unless it really is one. T01.03 separately owns malicious-contribution, credential-history CI and wider supply-chain proving work. Maintainers must never elevate an untrusted candidate merely to make its check run.

## Safe reporting and ownership

- `CONTRIBUTING.md` documents local setup, one-task worktrees, synthetic inputs, public evidence and fork review flow without private tooling.
- The PR template requires Summary, Validation, Rollback, truthful gates and public-safety checks.
- Public bug/improvement templates warn before reproduction details; blanks are disabled to keep the private security route prominent. Issue templates do not sanitize what someone eventually submits: reporters/maintainers must still review attachments and redact sensitive material.
- `SECURITY.md` and issue contact links point to GitHub's private report route, `security/advisories/new`. API inspection confirms private vulnerability reporting is enabled. No fabricated advisory is submitted just to exercise the form.
- If that private route is unavailable, do not put secrets, exploit payloads or private logs into a public issue/PR as a fallback. No private email address, response SLA, bounty, safe-harbor or unestablished encryption promise is invented.
- No new license or inbound contribution agreement is inferred from public visibility. Those decisions remain T01.04; publisher content and source reuse require separate approval.

## Non-destructive protection sandbox

Do not attempt a write to `main` to “prove” its guard. The T01.01 experiment creates a unique owned sandbox ref at the current main SHA, applies the same essential PR/strict-check/admin-enforcement controls to **that branch only**, and tries a non-force push of a harmless empty commit with the exact same file tree. A passing experiment requires a protected-branch rejection (GH006/GH013), not a generic authentication/network failure, plus an unchanged sandbox ref. Read back configured rules before testing.

Cleanup removes only the experiment's own sandbox protection/ref after the assertions, verifies the ref is absent, and compares main's protection before/after. An unexpected successful push is a failed verification, never a reason to weaken `main`. No repository default/protection is changed by this experiment. The run's public-safe result and delivery PR/CI links belong in `docs/evidence/T01.01-repository-rules.md`, not raw authorization/API logs.

Contribution docs/templates can roll back with a PR revert. Platform reporting/protection settings are outside Git and must be inspected independently; reverting documentation must not disable security reporting or relax `main`. This foundation task does not activate sources, deployment, tracking or commercial services.
