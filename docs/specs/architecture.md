# Architecture and extension boundaries

Status: proposed; see the backlog for implementation status.

## Smallest useful system

Static HTML/CSS on GitHub Pages, produced by a Python batch application. `uv` manages Python/dependency locks; `ruff` handles formatting/lint. Standard library first, with a locked safe XML parser such as `defusedxml` justified for hostile feeds. No runtime web server, managed database, paid AI, reader accounts, or client framework is required.

Use a single package with explicit modules, not microservices. Start with RSS 2.0 and Atom; unsupported formats remain disabled until justified. Prefer a few pure functions and small typed records over generic plugin frameworks.

```text
reviewed source registry + editorial files + overrides (main)
                         ↓
read prior normalized records/checkpoints (state branch)
                         ↓
fetch → parse → normalize → validate candidate snapshot
                         ↓
separate trusted writer validates again → CAS state commit
                         ↓
identity → group → lead selection → render → validate
                         ↓
Pages artifact → deployment → public health/reader smoke check
```

## Proposed repository layout

```text
src/wrap_brief/
  models.py           # Versioned records, invariants, UTC/URL validation
  config.py           # Validated public configuration only
  ingest/             # HTTP client and RSS/Atom adapters
  state/              # Snapshot I/O, migrations, retention, CAS persistence
  grouping/           # Exact identity, conservative similarity, lead ranking
  editorial/          # Reviewed briefs, overrides, corrections/tombstones
  render/             # Pure HTML/JSON/RSS generation; escaped output
  pipeline.py         # Explicit orchestration; stage inputs and outputs
  cli.py              # collect/build/check commands; exit codes and dry run
config/               # Approved sources and nonsecret feature configuration
content/              # Original reviewed briefs, policy copy, overrides
web/                  # CSS and optional progressive-enhancement JavaScript
tests/                # Unit, integration, fixtures, browser/security checks
.github/workflows/    # CI, collection, deployment; no embedded credentials
```

These paths are reservations for future tasks, not existing implementation. Keep `tools/plan.py` independent from product code.

## Contracts and ownership

| Contract | Required fields / invariants | Owner |
| --- | --- | --- |
| Source | stable ID, HTTPS feed/site URLs, allowed hosts, enabled, rights record, attribution, region, review date | Source maintainer |
| Item | schema version, stable ID, source ID, GUID if reliable, safe URL, plain-text title, published time if known, first/last seen UTC, status | Data maintainer |
| Poll checkpoint | source ID, last attempt/success UTC, ETag/Last-Modified, feed coverage boundary, bounded health codes | Data maintainer |
| Cluster | stable cluster ID, event/topic label, member IDs, lead ID, confidence tier, rumor/correction labels, override provenance | Grouping/editorial maintainer |
| Editorial brief | original text, author/byline, reviewed source IDs/links, publish/update time, review state | Editor |
| Build manifest | schema/config/code/state references, generated UTC, source results/counts, public-safe health, artifact hash | Release maintainer |

Unknown publication time is `null`, not fabricated. Display “first seen” with that label. Parseable times normalize to UTC; missing/ambiguous dates never become today's publication date silently.

## Stage semantics

1. **Collect, read-only token:** allowlisted URLs only, bounded requests; reuse last-good records for failed sources. Write a bounded candidate data artifact, not executable files.
2. **Persist, contents-write token:** trusted code from the default branch verifies candidate schema, allowed paths/fields, limits, and expected state head; creates a fast-forward commit on `state`. No force push, `main` write, or execution of artifact content. The token is repository-scoped; branch rules enforce boundaries.
3. **Build, read-only token:** read the explicit new state SHA and reviewed code/config SHA. Group and render *all retained records*, not just newly seen IDs. A failed build after persistence cannot strand news permanently.
4. **Deploy, Pages/OIDC permissions only:** publish the validated immutable Pages artifact. Do not fetch feeds, install arbitrary candidate code, or commit state in this job.
5. **Verify:** check the actual Pages URL, manifest/freshness, and outbound source path. Record deployment success separately from collection success.

One concurrency group covers scheduled/manual/recovery runs. A head conflict fails safely or triggers at most one complete recollect/revalidate from the new head; never merge unknown state blindly. `contents: write` and Pages OIDC solve different authorization problems.

## Durability and retention

- A dedicated state branch contains normalized public metadata and complete records for the retained site window, not raw feeds or a seen-ID set. Initial live retention: 90 days of item records plus bounded health; make it configurable and rights-aware.
- Initial identity/tombstone horizon: 180 days, containing only minimum non-republished identity data; confirm source terms. Expired records cannot reappear as fresh just because the feed resurfaces an old item.
- Git history retains old state even after file deletion. A source that requires reliable erasure or incompatible archival restrictions is not eligible for this public Git-state design; choose an appropriate private store before enabling it. Do not promise history deletion as an ordinary retention operation.
- Caches optimize only. Expiring Actions artifacts transport builds; neither is the canonical application state.
- Schema versions and pure migrations support a previous snapshot restore. Size alarms trigger archival/storage redesign *before* repo/Pages limits are approached.

## Extension seams

- Feed adapters return the same item contract; adding a publisher normally changes registry + approval + fixtures, not pipeline logic.
- Grouping is a replaceable pure stage with a fixed benchmark. Embeddings/AI remain optional experiments, never a hidden required service.
- Renderer consumes stable view models. Search, source filters, RSS output, or a release calendar are separate features with no changes to fetching.
- State backend exposes load/validate/commit semantics. Replace Git storage only after measured need; migration must preserve IDs, tombstones, and recovery behavior.
- Monetization placements are disabled, separately rendered components. They cannot affect story selection or source ranking.
- Static deployment is portable. Pages policy, traffic, reliability, and cost can trigger a host change without rewriting ingestion/UI.

## Reproducibility and budgets

Use injected clocks and explicit snapshot/config inputs; sort outputs deterministically. Identical inputs produce identical files, including a supplied manifest timestamp. Target a complete daily run under five minutes, with a hard ten-minute collection/build timeout and bounded per-source budgets. Measure rather than promise these targets.

Keep the published site well below 1 GB and track state/repository growth. Start with a conservative 100 MB site budget and much smaller pilot output. Public standard-runner compute is free; storage, provider charges, and operator time still need a budget.
