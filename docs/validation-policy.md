# Validation policy

## Current planning package

```sh
make help
make validate
git diff --check
```

`validate` runs plan checks, unit tests, Ruff lint and format checks. CI runs the same checks with pinned UV/Ruff and Python 3.13, plus tests on the minimum supported Python 3.11. `check-plan` includes task/milestone DAG and exact gate-membership checks, typed state/evidence consistency, local Markdown links, generated views, and limited publication-safety patterns. None proves product behavior. Scan the full candidate tree/history with a dedicated credential scanner before public delivery; record public-safe results in `docs/plan/VALIDATION.md`.

## Future product bundles

The targets below describe requirements to implement in E01/E08; they do not exist yet.

| Risk/slice | Required checks | Review budget |
| --- | --- | --- |
| Docs/config-only | Plan/link checks, workflow/config validation when touched, diff whitespace | One pass |
| Pure model/parser/grouping/render | `ruff` format/lint, focused unit tests, fixture integration/build, plan checks | Two passes for meaningful features |
| Runtime/network/state/workflow/security | Lint, full unit + adversarial fixtures, integrated deterministic build, workflow permission/action lint, recovery/sandbox tests | Three passes across design/implementation/release, up to five if findings warrant |
| Reader UI | Above relevant bundle + browser at 320px/desktop, keyboard/screen-reader/no-JS/zoom, a11y and performance checks | Design + final behavior review |
| Public release | Full suite, rights/source inventory, credential/history scan, real Pages smoke, one operational rollback drill, supervision/freshness check; independent monitoring before unattended mode | Security/release sign-off |
| Analytics/monetization | Privacy/provider/hosting/disclosure decisions, script/data inventory, before/after performance/referral checks, disable drill | High-risk review |

Named task verifications are acceptance-specific checks, not a license to omit the full touched-surface risk bundle. Do not claim green from skipped, unavailable, or unrelated tests. Record a concrete blocker when a required check cannot safely run; reduce scope rather than bypass protections.

## Quality targets

- 100% enabled sources have approval/attribution/retention records; no full text/images without rights.
- ≥98% auto-merge precision on ≥100 labeled benchmark pairs; report recall/sample and inspect pilot errors. No accuracy guarantee from title similarity alone.
- All published items have valid source/link/provenance; unknown dates labeled, not fabricated.
- Core homepage/alternate-source reading works without JS; no overflow at 320px; WCAG 2.2 AA target with human checks.
- Initial HTML/CSS/JS ≤150 KB compressed; target mobile LCP ≤2.5s, CLS ≤0.1 with recorded environment.
- Zero induced pre-deploy failures replace the known-good site. Prove post-state-commit build recovery and known-good code/state rollback.
- Daily collection freshness warning at 30h. Track scheduled-run outcomes over 30 days; do not advertise a strict cron SLA.

## Efficient review loop

Define checks before coding; run cheap targeted checks during work; run the selected full diff bundle once before PR. Fix findings, rerun changed-surface checks, and stop when required checks pass and latest review has no blocker. Do not repeat reviewer/verifier passes on an unchanged diff. Live-state behavior needs realistic live/sandbox evidence, not just static inspection.
