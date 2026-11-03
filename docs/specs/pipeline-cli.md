# Synthetic collect/build/check stages (T04.04)

Status: implemented APIs and CLI; task completion requires release verification and CI evidence. This slice composes existing pure modules, not a live collector, durable backend, scheduler or deployment service.

## Boundaries and stage interface

`python -B -m wrap_brief.cli` exposes independent `collect`, `build` and `check` commands. Every public pipeline entry requires a synthetic Snapshot, all sources disabled and every allowed host reserved under the existing renderer policy—including unrequested sources. No command fetches HTTP, chooses the current time, instantiates SQLite, writes a backend, approves sources or deploys. The observation clock and fetch results are explicit supplied inputs. Reserved hosts/synthetic labels cannot establish authorship: all input must still be genuinely hand-authored fixtures, never copied publisher data.

- **collect:** previous Snapshot + versioned poll plan + caller-supplied code reference → a private collection execution envelope. The existing reducer validates parsing/normalization/identity/last-good/checkpoint transitions. No grouping or rendering. A validated all-failed/deferred/no-source envelope may be written for inspection, but collect returns health exit 3 and produces no site.
- **build:** independently load and revalidate the envelope, replay pure `reduce_polls` and verify its result hash; invoke the real `require_publishable()` before any grouping/rendering. Regroup the full retained inventory with `previous_clusters` and exactly one default `LeadEvidence(item.id)` per Item under fixed **synthetic-lead-v1** policy. This is fixture policy, not publisher-derived editorial authority. Return a complete grouped Snapshot in the API and only HTML/CSS/safe manifest files in a fresh local candidate directory. Never commit state.
- **check:** independently read the envelope, caller-reviewed stylesheet and exact candidate inventory; reproduce the expected build in memory and compare all bytes, including the complete manifest. No hidden fetch, clock lookup, output creation or state write. Replaying pure validation/render computation is not another network collection or external CLI invocation.

Standalone build/check cannot infer success from retained stories or old checkpoints. Current supplied poll results are replayed, so valid 304/empty success remains distinct from errors and zero-request deferrals. All-error with nonempty last-good records, all-deferred and zero-source results fail the health guard. Degraded usable coverage is allowed and reported honestly.

## Version-1 wire and canonical hashes

Poll plans have exactly `schema_version: 1`, `kind: synthetic-fetch-results`, `observed_at`, `expected_source_ids` and `responses`. Each response contains exactly `source_id`, `status`, `requests`, `code`, `body_base64`, `etag`, `last_modified`, `retry_after_seconds`; these reconstruct the existing strict `FetchResult` contract. No URL or file reference is followed from a plan. XML bodies are embedded Base64 **synthetic input only**, not public output.

The execution envelope has exactly `schema_version: 1`, `kind: synthetic-collection`, `previous`, `plan`, `code_ref` and `batch_ref`. It embeds the complete prior Snapshot and plan, not a trusted free-form health string or unchecked serialized PollOutcome. Loading replays the pure reducer and checks `batch_ref`. That hash covers prior-state digest, observation time, every current Item/checkpoint, and **every outcome field**, including warnings, request/count/row/retry information. No normalization state-machine copy is introduced.

All hashes are lowercase SHA-256 of canonical UTF-8 JSON (`sort_keys=True`, compact separators, `ensure_ascii=False`, `allow_nan=False`) or exact file bytes where named. Array order is deterministic: expected IDs/responses sorted by source ID; shared Snapshot/reducer records use their canonical order. Envelope identity hashes its canonical serialization, not input whitespace. `code_ref` is a required lowercase 40-hex **caller claim**, not a runtime attestation or production authorization.

The manifest contains only schema/synthetic/not-deployed labels, supplied UTC, code reference, canonical envelope/prior-state/reduced-batch/grouped-state references, configuration identity, bounded counts/health and fixed warning codes. Configuration identity covers the entire source configuration, declared expected IDs, fixed grouping/lead policy and exact caller-reviewed stylesheet hash. HTML/CSS hashes cover exact output bytes; the manifest does not recursively hash itself. Check compares its complete expected canonical bytes, not merely self-reported hashes. Titles, publisher URLs, GUIDs, validators, headers, paths, exception strings and bodies are excluded from summaries/manifests.

Hashes provide reproducibility and internal consistency, **not tamper-proof coverage**. An editor can change supplied responses—or remove a failed response together with its expected ID—and recompute hashes. Exact coverage means coverage of the declared set, not trustworthy real-world coverage. The fixture restriction and live source/provider/security gates remain essential.

## Limits, files and no-write behavior

Plan/envelope reads and canonical serialization are capped at **4 MiB**, a stricter sublimit than the Snapshot API's 16 MiB. Individual decoded bodies remain ≤2 MiB and their aggregate is ≤2 MiB; encoded lengths are checked before decoding. At most 100 expected sources/results and 500 retained Items are supported in this prototype, with existing parser row and renderer 50-card bounds. Invalid Base64, unknown fields, duplicate JSON keys, unsupported versions, backward/naive clocks, nonfinite numbers and inconsistent results fail closed. Nothing is silently evicted or truncated.

Output parents must already exist. Files/ancestors cannot be symlinks; reads require bounded regular files. Existing output destinations are never intentionally overwritten. Private envelopes are owner-only; candidates use an owned staging directory and final rename, with cleanup limited to owned staging paths. This local tool assumes a single writer and is not a race-proof production artifact/state commit protocol. No deployment consumes its directories automatically.

The exact candidate inventory is `index.html` (≤1 MiB), `styles.css` (≤64 KiB) and `manifest.json` (≤16 KiB). Check rejects extra/missing files, symlinks, nonregular/executable/hard-linked files and oversized/changed reads. The stylesheet is an explicit caller-reviewed input, not feed-controlled data. The private envelope stays outside the candidate and outside artifact scanning/upload inventories.

`--dry-run` performs relevant validation/computation and output precondition checks in memory, emits only a bounded summary, and creates no output directories, temporary files or database. Existing outputs cause the same safe collision failure without changes. Check is always read-only. For strict filesystem-inventory evidence use `-B` or `PYTHONDONTWRITEBYTECODE=1`; interpreter/environment installation and bytecode caches are not pipeline state and must not be implicitly included in that claim.

Exit codes: **0** successful usable stage; **2** invalid input/arguments; **3** unusable source health; **4** filesystem/collision failure; **5** candidate mismatch or unexpected internal failure. Errors/argparse output use fixed bounded summaries, never raw arguments, paths or callback exception text.

## CI and deferred work

Planning CI builds/checks one deterministic CLI bundle after scanner bootstrap. The hardcoded synthetic scan inventory is **nine files**: three legacy HTML/CSS pairs plus the CLI HTML/CSS/manifest. No general format/plugin framework, elevated job, secret or artifact upload is added. The complete workflow change and frozen baseline require review. Live provider durability, persisted scheduling holds/warning history, source permissions, operational rollback, actual assistive-technology and production publishing gates remain separate and blocked. A replayable fixture envelope does not establish production durability.
