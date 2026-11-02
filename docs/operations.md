# Operations, cost, and recovery

Status: runbook requirements for future implementation, not an operating service.

## Schedule and budget

- Default cron: `23 6 * * *` (06:23 UTC). Optional later: `23 6,18 * * *` (06:23/18:23 UTC). Use only one of these schedules.
- Runs are best-effort, default-branch only. Avoid top-of-hour load; manual dispatch uses reviewed default-branch code.
- Public-repo schedules can stop after 60 days of repository inactivity. Do not assume a successful run counts as the required activity. Document maintainer reactivation and monitor externally; do not create meaningless commits just to evade inactivity controls.
- Standard public-repo hosted runner compute is free; larger runners are not. Keep artifacts to one day, no unnecessary cache, no paid APIs by default, bounded source requests and retry budgets. Storage is separately metered; inspect account usage and configure appropriate spending controls.
- Optional domain and operator time are real costs. Start with a $0 service budget; any paid provider gets a documented cap and decision before use.

## Health model

Record separately: run start, last source attempt/success, latest story time, validated state SHA, build SHA, last successful deployment, and post-deploy verification. Source failure is not a successful empty day.

- Daily freshness target: successful collection within 30 hours. A named maintainer checks the public health/last-check timestamp daily during the supervised pilot, including when collection never starts.
- On-page absolute “last checked” is always shown. Optional tiny local-time JS can add an age warning; it is not a substitute for independent monitoring.
- GitHub failure notifications catch started-but-failed jobs, not a disabled schedule. T07.04 proves the manual daily check and escalation route; the pilot does not claim unattended operation.
- Before later unattended mode (T11.01), configure and test an **independent** monitor of the public minimal health endpoint with a 30h stale threshold and an approved private notification channel. Check free-tier terms at selection time; no provider is assumed permanently free. Until this gate passes, retain named supervision.
- One deduplicated/rate-limited alert per continuing incident; clear on recovery. Never put webhook addresses or private contacts in the public manifest.

## Failure matrix

| Event | Safe behavior | Recovery evidence |
| --- | --- | --- |
| One source fails | Keep its last-good records/checkpoint, publish healthy sources with honest degraded health | Source fixture + summary |
| All sources fail | Do not advance success/checkpoints or deploy a misleading fresh empty site; fail/alert | Induced outage |
| Legitimate no-new-news/304 | Preserve prior records and record successful check; may deploy refreshed health | 304/zero-new fixture |
| Candidate validation fails | No state write/deployment | Malicious artifact fixture |
| State head conflict | No force push; one complete re-read/revalidate attempt or fail/alert | CAS conflict sandbox |
| Build fails after state commit | Keep live site; complete retained records available for next build | Recovery test |
| Deploy fails | Keep old deployment active, alert; verify actual public state | Failed deploy sandbox |
| Schedule disabled/missed | Pilot supervisor notices stale health and escalates; later unattended mode requires an independent alert | Supervision drill; independent-monitor drill before unattended mode |
| Source retracts/requests removal | Disable source/record, apply tombstone/correction; assess Git-history rights and storage choice | Reviewed correction exercise |
| Secret exposure | Revoke first, stop integration, private incident workflow | Tabletop; never publish real secret |

## Rollback and restore

1. Stop further state/deploy mutation using the shared workflow lock/disable route.
2. Select a recorded known-good reviewed code/config SHA and state SHA. Never fetch arbitrary URLs or execute unreviewed refs from manual inputs.
3. Read-only rebuild and validate from that pair, or use a still-valid known-good artifact where supported; expired artifacts cannot be the only recovery path.
4. Deploy through the normal protected Pages environment; smoke-check content/manifest/source links at the actual site URL.
5. Keep state records/tombstones intact unless a separately reviewed state repair is required. Reconcile subsequent records before resuming collection.
6. Record result and elapsed time; target a practiced restore within 30 minutes. No promise until a drill demonstrates it.

T04.03 proves component checkpoint/identity/migration recovery; T07.05 owns the one integrated operational rollback/restore drill. Handoff/release tasks reference those results rather than repeat them unchanged. If Git-history growth or rights/erasure needs conflict with public state, migrate storage before continuing affected collection.

## Operator review

Weekly pilot review: stale/missing runs, per-source failures/gaps, grouping precision, corrections, performance/a11y regressions, source permissions, storage, operator minutes. Four-week product review: original editorial output, measured audience/referrals where available, revenue experiment contribution, cash/time caps, and next smallest useful improvement.

Pause on source-rights drift, secret disclosure, elevated fork access, failed restore, or unsafe commercial integration. More sources/features are not evidence of success if reader value or operator economics worsen.
