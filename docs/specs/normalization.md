# Pure metadata normalization

`normalize_entry(RawEntry, Source, *, observed_at, identity)` converts one provisional entry into a validated immutable `Item` or a fixed quarantine code. It has no I/O, clock lookup, storage, source activation, or editorial confirmation logic. The identity argument is an explicitly supplied **trusted pure Python callable**, not a function name loaded from configuration. The exact identity policy is a separate component.

## Input and transformation rules

- Raw fields are type/size/Unicode-checked before stripping, splitting, date parsing or tag detection. The core Unicode policy is shared, not copied. Forbidden controls, line separators and bidi controls are rejected, not silently erased by whitespace normalization.
- Safe title spacing is collapsed. Empty/oversized and tag-looking ambiguous titles are quarantined rather than rewritten. Ordinary Unicode, emoji ZWJ, ampersands and mathematical angle text remain data. No title becomes trusted HTML; future output still requires escaping.
- URL boundary spacing and a fragment can be removed. HTTPS syntax, credential/literal-local safeguards and the reviewed source host allowlist must pass. No relative resolution, HTTP upgrade, DNS, redirect, query reordering, tracking removal or path rewriting occurs here.
- GUIDs remain optional bounded opaque metadata. Invalid control/type/size values quarantine the row; GUID policy never silently changes the identity algorithm.
- Bounded ISO/RFC dates require explicit recognized timezone information and normalize to UTC. Missing publication stays `None`, independently of update or observation time. Invalid, ambiguous, reversed publication/update ranges, and either date more than five minutes ahead of the supplied observation clock are quarantined.
- New candidate first/last seen timestamps equal the supplied observation clock. Later state merging, not this stateless function, preserves an existing record's original first-seen timestamp.

## Outcomes, identity and privacy

Source, aware observation clock and callable identity are programmer arguments; invalid arguments raise bounded `ContractError`. Untrusted row problems return `NormalizationResult(item=None, rejection=<fixed-code>)` without logging or echoing raw values. Results are immutable, have redacted representations, and enforce exactly one accepted/rejected outcome.

All candidate fields and cross-record source attribution are validated before identity is called, exactly once with `(source_id, validated_url, validated_guid)`. The internal validation-only candidate identifier is reserved and never returned. Callback failure or invalid identity aborts with a bounded programmer error; it is not disguised as an ordinary rejected news row.

The callback may not perform I/O or obtain metadata from untrusted code. The future identity module will satisfy this callable seam without introducing a dependency cycle. A caller-supplied callback is trusted application code, not an extension point exposed to feed content.

Accepted metadata is not publisher permission, a complete SSRF fetch defense, or a live release. The live registry remains empty, with T02.02/T04.02/T07.02 gates unchanged. No raw parser entry may bypass this boundary into persistence or HTML.
