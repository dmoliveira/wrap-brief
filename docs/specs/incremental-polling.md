# Incremental source-state reducer (T03.04)

## Boundary and input contract

`wrap_brief.ingest.polling.reduce_polls(previous, polls, *, expected_source_ids, observed_at)` consumes a validated `Snapshot`, a bounded tuple of `SourcePoll(source_id, FetchResult)` and an explicit forward UTC clock. It returns an immutable intermediate `PollBatch`. It does **not** perform HTTP requests, read the system clock, persist state, schedule retries, group items, render or publish anything.

Expected source IDs are explicit, unique and known; result coverage must match exactly, with one result per expected source and at most 100 sources. Registry members that were not requested are not fabricated failures or successes. Live snapshots require enabled/approved, non-future dated source records; offline synthetic snapshots may use disabled synthetic sources. No source registry entry is activated by this reducer.

Every `FetchResult` is checked before any reduction: exact typed record, fixed status/code, strict integer request count 0–5, status-specific body/validator/backoff combinations, body ≤2 MiB and bounded safe validators. Successful results require actual requests and no failure/backoff fields; 200 carries bytes, 304 carries no body. Error/deferred results must not carry content or validators. Zero-request timeout and a legitimate positive zero-request poll-interval deferral are recognized. Invalid/unbounded programmer inputs raise bounded `ContractError`, not a fabricated source success or silently quarantined run.

## Successful source transitions

- **200:** safely parse XML, normalize provisional rows with source-scoped URL-v1 identity, then merge complete validated records. Source success/checkpoint metadata advance only after this processing succeeds. A successful new 200 **replaces** the validator set, clearing old values absent from the response.
- **304:** require a previously successful checkpoint with at least one stored validator. Keep every retained Item, its publication/observation clocks, feed row count and publication window unchanged. Advance attempt/success timestamps, retain absent response validators and replace supplied ones. This is unchanged source content, not an empty feed. Body-based gap heuristics do not run on 304.
- **Valid empty RSS/Atom:** success with physical count 0 and unknown publication window. Retain old Items. It is not a network/parser failure, an erased inventory or proof that nothing happened in the world.
- **Mixed usable/quarantined rows:** keep validated records and expose quarantine counts/warnings; the source remains usable but aggregate health is degraded. A nonempty feed with **all rows quarantined**, including parser-skipped missing fields, fails rather than masquerading as empty news. Its new validators are not saved.

Physical row count is `len(parsed.entries) + len(parsed.issues)` (≤100), including duplicates. Accepted plus quarantined rows equal that count for parsed feeds. New/update counts use distinct retained IDs after merge and tombstone suppression. Observation-clock-only changes are not content updates; publication/update/GUID/title/URL/claim/status changes may be. Unknown publication remains unknown, never substituted with first-seen or updated time for window calculations.

Feed normalization defaults (`active`/`reported`) are **not** authority to lift a stored quarantine, correction, removal/retraction or explicit rumor flag. These are retained until an explicit reviewed control changes them. Confirmed state is preserved when publisher metadata (`title`, display URL, publication/update times and GUID) is unchanged, ignoring seen clocks; changed content loses that automatic carry-forward and must be regrouped/reviewed. No article body is fetched, so unobservable publisher changes cannot be inferred. Existing identity/last-seen/known-update merge and tombstone semantics remain in the shared state module; no schema changes are introduced.

## Failure, deferral and health

Network/status/parser errors, invalid 304 and all-quarantined content preserve previous Items and all last-good success/validator/count/window fields. Only a result with actual requests records a new attempt and checkpoint status `error`. A zero-request deferral leaves its checkpoint entirely unchanged. Deferral after real requests records failed-attempt metadata while retaining last-good success.

Individually valid publisher metadata can conflict with retained chronology—for example, a newly supplied publication later than the last known update. The shared core's fixed `updated_at: precedes publication` merge rejection becomes source-local `metadata_conflict`: reject that response without advancing last-good metadata and let other sources continue. The complete failed response is counted as quarantined. Identity/integrity conflicts and record/serialized-size overflow remain fatal rather than being hidden as ordinary source errors.

The per-source outcome exposes fixed failure codes, counts, warnings and any returned server backoff. A deferred result with unknown delay remains distinct from zero delay: **never automatically retry it immediately**. The existing checkpoint schema does not persist retry deadlines, unknown-backoff holds or warning history. A future private scheduler must durably retain/honor these outcomes and source policies before live operation; checkpoint persistence alone is not restart-safe scheduling. This component does not satisfy that later integration/production-storage gate.

Aggregate denominator is the expected-source set:

| Health | Meaning |
| --- | --- |
| `no_sources` | No sources were requested; not proof of a healthy no-news run |
| `blocked` | No expected source produced usable validated success |
| `degraded` | At least one usable success, but some expected coverage failed/deferred or has warnings |
| `healthy` | All expected sources succeeded and no current-outcome warnings remain |

`no_new` is true only when every expected source succeeded and no distinct retained identity was added; it does not mean there were no content changes or no worldwide news. `require_publishable()` raises for `blocked`/`no_sources` so callers can stop an all-source-failure publication. It is a **source-health guard**, not rights, grouping, accessibility or deployment authorization. Failed-attempt state may still be persisted without calling this guard. T04.04/T07 must wire the guard into a real publication flow; no publication workflow exists here.

## Possible-window warnings, not completeness guarantees

- `baseline_unknown`: no earlier validated success exists.
- `publication_unknown`: a nonempty accepted response has no known publication date.
- `possible_gap`: the oldest known current accepted publication is strictly later than the previous **successful** poll boundary, not the latest failed attempt.
- `feed_window_shrank`: physical row count fell below the previous count, including a fall to zero.
- `saturated_no_overlap`: the feed reached the 100-row cap without stable-ID overlap against retained source inventory.
- `quarantined_entries`: some physical rows were skipped/rejected.

Windows use only accepted publication dates in the **current** response, not retained inventory, updated times or first-seen substitutes. Retained inventory is not exact previous-feed membership. Warnings are conservative possibilities and may have benign explanations; they never prove completeness or definite loss. Current-attempt health and warning disappearance do not repair historic gaps. Persisted warning/audit history belongs to later private operational state, not new public Git data.

## Explicit grouping and private persistence handoff

The batch deliberately is not a Snapshot. Use `previous_clusters` as input to the separate grouping stage; `requires_regrouping` detects any changed Item record. `to_snapshot(*, clusters=...)` requires an explicit current-item grouping tuple, verifies a complete nonoverlapping partition and cross-record references, and checks the 16 MiB logical serialized size before returning a candidate Snapshot. There is no implicit old-cluster reuse or hidden lead choice. Reference validation is not semantic freshness proof: callers must actually regroup changed metadata; only unchanged 304/error-only records justify explicit group retention.

The shared merge rejects retained-item overflow beyond 10,000 rather than evicting/truncating or advancing checkpoints independently. The existing private local SQLite adapter can commit this complete candidate with CAS. Tests exercise regroup → snapshot → commit/reopen → injected conditional HTTP/304 → explicit unchanged-group retention → commit/reopen, plus stale-writer rejection. This proves independent local-development runs retain validators/boundaries, **not** live runner durability, production retention or physical erasure. Live collection, durable storage and release gates remain separate.
