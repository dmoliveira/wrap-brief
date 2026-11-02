# Logical snapshots and local prototype state

The exchange contract is a validated logical `Snapshot`, never SQLite file bytes, a cache, or a set of seen IDs. `wrap_brief.state.snapshot` and `wrap_brief.state.local` use only the standard library and existing domain contracts.

## Complete logical state

Snapshots contain sources, full Items, Clusters, observation time, bounded source checkpoints and minimal tombstones. Every record is immutable/versioned; references, unique IDs, available leads and source attribution validate before persistence. Exact record types prevent undeclared extra fields from being serialized. Sources/items/clusters/checkpoints/tombstones are ordered by ID; set-like allowed hosts and cluster members are sorted. Lead identity is explicit, never inferred from member position.

Canonical UTF-8 JSON uses sorted keys and fixed separators; its SHA256 is an integrity/reproducibility checksum, **not authentication**. Input bytes are capped before strict UTF-8/JSON decoding; duplicate keys, nonfinite numbers, unsupported versions, unknown fields and oversized/invalid arrays fail. Logical snapshot size is capped at 16 MiB and item/cluster/tombstone arrays at 10,000 records. Missing checkpoint/tombstone arrays in the earlier synthetic view fixtures mean empty tuples.

`kind` is descriptive (`synthetic` or `live`), not approval or an execution switch. Local examples are synthetic, and the real source registry remains empty. No Source, checkpoint, or kind flag grants publisher rights or enables collection.

## Checkpoints and deletion markers

`PollCheckpoint` is a data contract, not polling logic. It stores a source ID, UTC attempt/success times, bounded ETag/Last-Modified fields, nullable entry count, oldest/newest known publication boundaries and a fixed success/error status. Failed attempts can preserve prior success; no-success records cannot claim validated headers/window data. It has no generic headers, cookies, credentials, response body or raw error text. Window timestamps remain unknown when publication data is unknown.

`Tombstone` stores only schema, item ID, source ID and UTC removal time. Tombstoned full Items cannot coexist in a snapshot. `merge_items` filters them and suppresses resurfacing, while conflicting source ownership fails. Retraction/status flags are not data erasure; use tombstones and the eventual approved retention/deletion workflow for actual removal obligations.

Pure replay merge preserves earliest observation/known publication and latest observation/known update. Known source-update metadata beats undated metadata; equal or absent update times use the latest observation. A newer observation alone cannot roll back known source-update metadata; terminal retraction/removal is sticky. Same-ID source/canonical-resource conflicts fail rather than overwrite. Contradictory chronology is rejected rather than guessed. Rebuild clusters over the resulting Items before constructing the next validated snapshot.

## Local SQLite adapter

`LocalState(Path(...))` explicitly initializes an owned `.db`/`.sqlite`/`.sqlite3` development file in an existing private directory. New files are exclusively pre-created owner-only before SQLite opens them; parent directories must have no group/world permissions; symlink/nonregular/insecure-parent/file-permission targets are rejected. Application ID, schema version, allowlisted tables/columns and a magic row protect against accidentally opening a foreign database. Existing nonempty foreign databases are not adopted or overwritten.

`load()` returns `Revision(version, snapshot, digest)`. `commit(snapshot, expected_revision=...)` uses a single SQLite transaction with compare-and-swap version validation. Identical payload/current version is a no-op; stale expected versions still conflict. `clear()` removes the logical payload with a monotonic revision so a stale writer cannot restore it. Reader transactions see one consistent revision. Connections are closed on all paths; interrupted transactions roll back. Missing, incompatible or corrupt files/checksums fail closed instead of recreating or treating them as empty state.

Only logical JSON is import/export; **do not open downloaded/untrusted SQLite files**. Ownership markers and checksums are not a defense against a hostile local user with filesystem access. This prototype does not defend against concurrent path replacement, guarantee physical erasure from SSD/OS copies, implement backups/migrations/retention expiry, or satisfy production durability. Secure-delete mode is defense in depth, not that guarantee.

Keep database files, sidecars and any real exports under untracked private storage (`.state/`, `.local/`, or an appropriate private directory), never in Git or public deployment artifacts. Local runner disks remain ephemeral. T04.02 must select and prove a private durable backend before any live collection; no provider/account/credential is introduced here.
