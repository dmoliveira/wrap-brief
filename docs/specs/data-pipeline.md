# Sources, ingestion, durable data, and story grouping

## Source onboarding

Start with 3–5 sources whose current feed terms support the exact proposed use. Nintendo's official channels and specialist/general gaming publishers are candidates, not preapproved sources. No automatic top-site crawling or search-engine scraping.

T02.04 records the source investigation and a reviewed synthetic-prototype-only go. It does not activate feeds; T02.02 remains the blocked live-source gate. T02.02 owns final approval plus a repeatable source-add/disable checklist. For every enabled source, review and record:

- Feed owner, exact feed/site URLs, allowed redirect hosts, stable ID, language, and region.
- Terms/license URL, review date, permitted fields, attribution wording, retention/archival constraints, and any permission correspondence reference **without private correspondence content**.
- Whether titles/snippets may be displayed. Default to the minimal permitted title/link/source/time; if rights are unresolved, disable the source rather than assume a universal exception.
- No publisher images/full text by default. Excerpts are optional and rights-gated; RSS availability is not a license. Robots guidance is not permission either.
- Conditional-request support, permitted polling frequency, expected feed window/volume, and correction/removal path.
- Quality/reliability tier and coverage scope. Source prestige does not override permissions.

At least one primary channel is desirable but cannot be invented if no suitable approved feed exists. A source change requires rights review and fixtures before activation.

## Fetching and parsing

- HTTPS only, finite source allowlist, honest bot/user-agent identity and contact once configured.
- Initial defaults: at most 3 concurrent requests, 15-second request timeout, 2 MiB decompressed response limit, 100 entries/feed, three redirects, and one transient retry with jitter/backoff. Tune only with measured need and publisher rules.
- The implemented [HTTP boundary](feed-http.md) is serial per source/call, with no batch/concurrent poll API. It adds an independent encoded-entity cap, five total hops and a 60-second combined budget; callers must enforce per-source serialization, pipeline-wide concurrency and persisted scheduling/backoff before live operation.
- Validate every redirect and resolved destination: prohibit loopback/private/link-local/metadata targets and unexpected hosts/schemes. Do not trust a safe initial URL alone.
- Support `ETag` and `Last-Modified`; `304` is a successful poll, not an empty feed. Change checkpoints only after validated success.
- Safe XML parsing: external entities/DTD/entity expansion disabled; byte, nesting, text, and item limits enforced before expensive work.
- Treat feed markup as data. No fetching arbitrary enclosure/thumbnail URLs. Drop raw HTML from the public model; escape all rendered values.
- Parse publication/update times with offsets; normalize UTC. Missing dates use separately labeled first-seen time; implausible future dates are quarantined/flagged, not promoted as breaking news.
- Separate source-level errors from item-level quarantine. A broken source cannot erase its last-good records or abort all healthy sources.

## Daily coverage limitations

A once-daily job may miss items removed from a short feed between polls. Compare the new feed window, prior successful poll boundary, IDs, and count to flag **possible gaps**, not guaranteed completeness. Newly onboarded sources have no historical completeness claim. Surface a bounded warning in the run summary and methodology.

Move to twice daily only if source volume/gap evidence or reader freshness justifies it. A severely truncated source may need another approved channel/API or exclusion; two runs are not a universal fix.

## Identity and durable state

- Initial MVP identity is a versioned hash of source ID and conservatively canonicalized URL. GUID remains provenance only; no reliable-GUID mode is enabled without later reviewed evidence and collision handling. See [identity policy](identity.md).
- Remove only reviewed tracking parameters. Preserve query fields that may identify different articles, editions, languages, or pagination. Do not invent canonical URLs by crawling full articles.
- Exact identity updates the existing record without bumping publication time or creating another card. Material corrections retain provenance.
- State completeness, atomic persistence, private retention/deletion and public artifact/cache constraints are canonical in [architecture](architecture.md). Privileged writer validation is canonical in [security/privacy](security-privacy.md). The ingestion stage emits data-only validated candidates, never executable state.

## Grouping and lead-source selection

Separate exact deduplication from related-event clustering. Never delete the alternate articles merely because they look similar.

MVP grouping uses normalized title tokens + named game/company + event type + a conservative 48-hour candidate window. Disallow merges across incompatible event types or distinct game/edition identities. Uncertain matches remain separate. Stable cluster IDs and reviewed merge/split overrides prevent links reshuffling every run.

Lead selection is deterministic: relevant primary announcement → original reporting → substantive reliable coverage; then explicit quality/recency tie-breakers. A primary source is not always the right lead for analysis/review. Commercial relationships never enter ranking. Rumor and confirmation remain distinguishable; correction/retraction state can demote or withdraw a lead.

Gold benchmark before launch: at least 100 labeled story pairs, with Direct multi-announcements, same-game different events, reviews/previews, localization, rumors/confirmation, syndication, resurfaced articles, tracking parameters, and corrections. Target ≥98% automatic-merge precision on that sample; report sample size and recall rather than optimizing away every duplicate. Review all pilot automatic merges for the first week; a false-merge spike disables fuzzy grouping while exact dedup continues.

MVP T05.04 owns attribution and correction/retraction/takedown controls. Original brief authoring, review-state models and recurring editorial production are growth T09.02; the launch can remain clearly attributed listings without invented summaries.

## Required fixtures and failure cases

RSS, Atom, namespaces, encoding/Unicode, missing GUID, duplicate GUID, changed URL, unsafe schemes, malicious HTML, entity expansion, oversized/slow response, redirect to forbidden target, 304, 429/5xx, empty feed, bad timezone, future/missing date, interrupted state write, CAS conflict, cache loss, state restore, feed truncation, failed build after persistence, corrections/takedowns, and legitimate zero-new-news runs.

No test needs live production credentials. Synthetic fixtures must not copy publisher article bodies or private response headers.
