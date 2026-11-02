# Exact identity policy, URL version 1

The initial MVP uses **source-scoped canonical URL identity**. GUIDs are retained as provenance but are not trusted identity keys. No source reliability evidence currently justifies a GUID-preference mode; adding one later requires an explicit reviewed policy and collision handling. This deliberately replaces the earlier proposed reliable-GUID preference.

## Reviewed parameter allowlist

The exact case-sensitive ASCII names are: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `utm_id`, `gclid`, `dclid`, `fbclid`, `msclkid`, `mc_cid`, `mc_eid`.

A trusted immutable source policy may select only a subset, including an empty set. It cannot expand this allowlist or remove arbitrary `utm_*`, `id`, `edition`, `lang`, `ref`, `source`, `page`, or other meaningful fields. Real source approval must confirm the selected cleanup policy; a tracking-named key used as content identity must be retained. Policy changes after live activation require reviewed ID/migration consequences.

## Canonicalization boundary

Input is an already normalized, Core-validated HTTPS URL without a fragment. No fetch, DNS, redirect, HTTP upgrade, fragment guessing, path normalization or article crawling occurs.

- Host case/IDNA, global-IP spelling/IPv6 brackets, and default HTTPS port are normalized.
- Path spelling, percent escapes, case, empty path and trailing slash are preserved.
- Query segments are split on raw `&`. Only the key is percent-decoded to bytes for exact allowlist comparison; `+` is not treated as space. Unknown segments remain byte-for-byte in order, including repeated keys, blank values, malformed escapes and structural empty segments.
- An explicit empty `?` is preserved. It disappears only if every actual segment was a recognized tracking field; an unknown empty segment is not discarded.

The stable ID is `item-v1-` plus SHA256 of the fixed NUL-separated UTF-8 namespace, validated source ID and canonical URL. IDs are identifiers, **not authentication capabilities**. Same source/URL remains stable across GUID/title/time changes; same GUID on different URLs remains distinct. URI reuse for unrelated content needs source-specific review before live use.

Canonicalization is for identity only and does not mutate `Item.url`. It does not make displayed links tracking-free or privacy-safe; outbound link policy, recipient identifiers, public fields and source terms must be reviewed before live publication. No publisher is approved or enabled by this component.
