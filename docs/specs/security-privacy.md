# Threat model, privacy, and public-repository controls

## Assets and trust boundaries

Protect repository/workflow integrity, state correctness, reader safety, source rights, credentials, and private operational/user data. Public surfaces include Git branches/history, generated site/JSON/RSS, Actions logs/artifacts, issues/PRs, analytics dashboards, and third-party ad/support scripts.

Trust reviewed code/config—not feed input, contributor code, action updates, remote URLs, candidate artifacts, or provider responses. GitHub Pages serves static public content; anything shipped to the browser is visible. There is no safe client-side secret.

## Threats and required controls

| Threat | Control and proving test |
| --- | --- |
| Malicious feed XML/HTML | Safe parser, strict bounds, plain-text models, output escaping; entity/HTML/encoding fixtures |
| SSRF/redirect abuse | Registry allowlist, HTTPS, destination/redirect validation, private-IP rejection; hostile URL fixtures |
| Candidate artifact modifies code | Exact JSON schema/path/file-mode/size allowlist; reject symlinks, traversal, scripts, workflows; writer sandbox tests |
| Fork PR steals secrets or deploys | Read-only PR jobs, no secrets, no privileged PR-controlled code; fork test and permission audit |
| Persistence crosses trust boundary | Private backend, scoped credentials, atomic version validation; candidate/credential sandbox tests |
| Compromised dependency/action | Lock dependencies, pin action SHAs, review updates, enable supported scans |
| Workflow/log secret disclosure | No environment/header dumps, redaction, safe summaries, no raw feeds; scan all publication surfaces |
| Source poisoning/ranking abuse | Quality tiers, provenance, conservative grouping, rumor labels, reviewed overrides and corrections |
| Third-party ads track readers | Disabled by default; provider/privacy/consent review, script/performance budget, reversible placement |
| Donation/payment data leak | Hosted approved payment flow; no payment/subscriber exports in Git or Pages |

## Workflow policy

- Checks on pull requests run untrusted code without secrets or write scopes. Avoid cache poisoning across trust boundaries. No `pull_request_target`/`workflow_run` pattern that checks out and executes untrusted contributions with privileges.
- Scheduled/manual production workflows operate only from the reviewed default branch. Deployment environment restricts allowed refs. If platform rules are unavailable at the account tier, document and implement a tested equivalent or stop before live release.
- Default `permissions: {}`; read jobs receive only `contents: read`; private persistence uses separately scoped provider access; deployment gets `pages: write` and `id-token: write` only. `GITHUB_TOKEN` is ephemeral but not intrinsically branch-limited.
- Main is protected, required checks and PR merge; no bot/admin bypass for routine automation. Publisher item state never uses a public Git branch. Demonstrate private persistence and protected-deployment behavior before enabling the schedule.
- Candidate artifacts are data only. Privileged writers use reviewed code, never execute candidate scripts, and revalidate file paths, record schema, URL fields, timestamps, bytes, file count, encodings and mode.
- One concurrency group for all state/deploy mutation routes, atomic expected-version writes, no repository state commits, bounded conflict retry, immutable artifacts, minimal retention. Third-party Actions pinned to SHAs.

## Public-data classification

**Allowed:** reviewed source URLs/attribution, public normalized metadata, original published briefs, public site/provider identifiers confirmed nonsecret, aggregate non-identifying health counts, public-safe release evidence.

**Private:** credentials, tokens, cookies, correspondence, internal task/session databases, raw request logs, user identifiers, analytics exports, subscriber emails, payment details, incident payloads, machine-specific config/paths. Store outside the repo and never copy into source fixtures or issue bodies.

Publisher item/checkpoint state is private and deletable, never tracked. M1 input is hand-authored synthetic data with an empty live registry. Minimum state records only; no raw feed response or unnecessary author email. A publisher-supplied contact field is not automatically appropriate to republish. Source approval covers private retention/deletion and public output, deployment-artifact and owned-cache removal. Publisher data is prohibited from Git; accidental publication is an incident.

## Measurement and consent

MVP ships without analytics. Aggregate page counts do not prove unique users, return rate, or donor attribution. A later analytics selection must document data collected, legal basis/consent requirements by target regions, retention, access, provider, opt-out, deletion process, and acceptable performance. “Cookieless” does not automatically mean no privacy obligations. No fingerprinting or cross-site identity stitching.

Email remains off until consent, unsubscribe, suppression, retention, provider free-tier limits, and private storage are implemented. Financial/tax/account onboarding and private legal determinations are real external gates; record public-safe decisions, never private account details.

## Gates and incident evidence

Before first public push: inspect the staged tree/history and ignored files, run a credential scanner plus manual review, use a public noreply commit identity, and confirm no agent database/log is tracked. Before live collection: adversarial tests and workflow/branch-rule sandbox. Before tracking or money: provider/legal/privacy/hosting review. See [SECURITY.md](../../SECURITY.md) and [operations](../operations.md) for response and rollback.

The current plan's built-in publication-safety checks are heuristics, not a substitute for a dedicated scanner or security review.
