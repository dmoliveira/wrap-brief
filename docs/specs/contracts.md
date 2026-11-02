# Domain and source-configuration contracts, version 1

Implemented by `wrap_brief.models` and `wrap_brief.config`. These are pure metadata boundaries, not a feed client, parser, state backend, grouping algorithm, editorial system or renderer. No runtime dependency was added.

## Records

Frozen, slotted dataclasses reject unknown JSON fields, require explicit serialized `schema_version=1`, and expose `to_dict()` / `from_dict()` round trips. Mutable output mappings/arrays do not mutate their immutable source records. IDs are bounded lowercase ASCII identifiers; source GUIDs remain a separate optional field.

- **Source:** `id`, `name`, HTTPS `site_url`/`feed_url`, canonical `allowed_hosts`, `attribution`, `region`, `enabled`, `approval_status`, `approval_ref`, nullable `reviewed_at`, and schema version. Sources default disabled/unreviewed. An approved record requires dated evidence; enabling requires approved status. A record of approval is not a legal determination or permission created by code.
- **Item:** `id`, `source_id`, `title`, HTTPS `url`, explicit `first_seen_at`/`last_seen_at`, nullable `published_at`/`updated_at`, optional `guid`, lifecycle `status`, separate `claim_status`, and schema version. No body, description, image, author email, credentials, or editorial prose field exists.
- **Cluster:** `id`, unique `member_ids`, `lead_id`, `topic`, `confidence`, `claim_status`, `correction_status`, optional public `override_ref`, and schema version. Manual confidence requires provenance. A cluster with no available items can have no lead; visible items require one.

`validate_references(sources, items, clusters)` checks unique IDs, known sources/items, item-host attribution, available cluster leads, rumor labeling and unsupported confirmation claims. It does not determine story similarity or independently verify claims.

## Time and text

Callers supply clocks: models never call `now()`. Aware datetimes normalize to UTC and serialize as ISO-8601 `Z`. Naive/invalid dates and reversed seen/update ranges fail. Unknown publication remains `null`; first seen is never substituted as publication.

Titles and labels are bounded text **data**, not interpreted markup. `<`, `&` and Unicode are preserved as data; the future ingestion normalizer and renderer still own markup normalization and output escaping. Do not infer that validation alone makes a string safe for direct HTML insertion.

Control characters, unpaired surrogates, Unicode line/paragraph separators and the bidi-control marks/formatting characters are rejected. Ordinary RTL letters and emoji ZWJ sequences remain supported. Public URL errors use a fixed internal field label, never caller-provided error-format text.

## URLs and references

URL validation requires absolute HTTPS, rejects userinfo, known credential query keys, controls/whitespace, unexpected ports, malformed/local hosts and non-global IP literals. Source and item hosts must match the reviewed allowlist. Meaningful query parameters are retained; deduplication/canonicalization is a separate task.

This is **not SSRF protection for a network client**: there is no DNS resolution or fetching. The future HTTP stage must validate every actual resolved address and redirect and enforce its own request/size/time budgets. Approval/override references accept public HTTPS or safe repository-relative paths, never local machine paths or traversal.

## Registry and fixtures

`config/sources.json` is versioned and deliberately empty. `load_registry(Path(...))` reads bounded UTF-8 JSON, rejects duplicate keys/nonfinite values/unknown fields/symlinks, and returns an immutable `SourceRegistry`. No environment expansion, secrets, backend credentials or network requests are supported.

`tests/models/fixtures/v1.json` is a hand-authored compatibility vector using reserved example domains and explicitly fictional content. It is not a source approval or a live feed. Larger RSS/Atom/adversarial pipeline fixtures remain T02.03.

Model/config validation raises `ContractError` with bounded field/reason messages rather than echoing hostile values or configuration paths. Source eligibility and live publication still require T02.02/T04.02/T07.02; [ADR 0001](../decisions/0001-fixtures-and-private-state.md) permits only offline synthetic work now.
