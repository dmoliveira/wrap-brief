# ADR 0001 — prototype first; publisher state outside Git

Status: accepted for the offline prototype direction; live operation remains blocked. This explicitly refines the earlier feasibility decision, rather than treating a failed live-source gate as permission to publish.

## Decision

- M1 may develop and test with hand-authored synthetic data, reserved example-domain URLs, an empty live-source registry, and no network collection. Synthetic examples must never be presented as current real news.
- T02.04 completes the feasibility investigation with **prototype-only go / live-source no-go**. Its completion approves no publisher. T02.02 owns the unresolved live-source permission gate and remains a prerequisite of T07.02.
- Public Git contains code, reviewed nonsecret configuration/docs, and synthetic fixtures only. Raw feeds, publisher-derived items/checkpoints, runtime databases, and generated live snapshots must not enter Git history.
- State contracts stay backend-neutral. A later offline implementation may use untracked local SQLite plus deterministic logical snapshot import/export. SQLite file bytes are not a reproducibility contract.
- Before live collection, T04.02 must select and prove a private, deletable durable backend, including retention/deletion, atomic version checks, backup/recovery, credentials, and a bounded operating budget. Local SQLite on an ephemeral runner, Actions caches, or expiring transport artifacts are not durable production state.
- No external provider, account, database service, credential, or paid dependency is introduced by this decision. Do not provision Cloudflare or choose a service merely because it has a free tier.

## Gates that remain strict

Private storage does not grant republication rights. T02.02 must still approve exact fields, attribution, request limits, retention/deletion, public rendered output and artifact retention, removal handling, and any commercial restrictions. Zero sources are currently approved or enabled. Donation/ads and unattended operation retain their separate gates.

## Why

The initial state-branch proposal created an unnecessary permanent-archive constraint and coupled safe fixture development to live publisher permissions. Separating the two lets us validate contracts and reader value cheaply without copying publisher material or weakening the live release gate.

## Evidence and consequences

The [source investigation](../sources/FEASIBILITY.md) remains evidence of unresolved permissions, not a license. The user requested continuation using the best available plan; architecture review approved this boundary. The backlog/specs explicitly replace state-branch assumptions before implementation. There is no production data to migrate. Provider selection and source approval remain measurable future work, not completed by this ADR.
