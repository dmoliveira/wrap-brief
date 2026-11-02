# Offline RSS/Atom parser boundary

`wrap_brief.ingest.parsers.parse_feed(data: bytes, source: Source, *, limits=None)` extracts provisional metadata without accepting URLs, files, streams, credentials, clocks, or a network client. A disabled synthetic Source is valid for offline tests; passing one does not enable it or grant publishing rights.

## Supported shape

- RSS 2.0-shaped `rss/channel/item`, with a missing version tolerated but other declared versions rejected. Only direct channel entries count; nested fake items are ignored. Common DC date and Atom updated extensions are read as strings.
- Atom's exact standard `feed/entry` namespace, direct entries only. Alternate HTML/XHTML links are preferred; self/enclosure links are not article fallbacks. Text, declared HTML and XHTML title constructs are supported; unknown title types are quarantined.
- `ParsedFeed` contains a format, immutable entry tuple and issue tuple. Entry fields are exactly `source_id`, `title`, `url`, `guid`, `published`, `updated`, matching the shared fixture contract.
- Missing title/link or invalid title markup is quarantined with a zero-based index and static code while other valid entries survive. Duplicate entries remain duplicates for the identity stage.

## Security and resource contract

One locked runtime dependency, `defusedxml==0.7.1` (PSF license), is justified instead of using an unhardened XML parser. Streaming `iterparse` explicitly sets **all** `forbid_dtd`, `forbid_entities`, and `forbid_external` flags to true. XInclude is never invoked. Comments/processing instructions are not interpreted.

Input must be bytes and is checked before parsing. Hard ceilings are 2 MiB input, depth 64, 10,000 elements, 100 direct entries, and 4,096 characters per selected field. `FeedLimits` can tighten but not raise these ceilings; invalid/bool/subclass limits are rejected. Processed entry elements are cleared. Limit violations reject the feed rather than publish partial over-budget output.

`FeedParseError` exposes only a fixed code. XML/security/encoding failures do not echo payloads, and raw entry representations hide values. HTML-title extraction drops markup/script/style content; malformed title handling does not expose underlying HTML-parser errors. This text extraction is **not an HTML sanitizer for output**: consumers must still treat every string as data and escape it.

There is no fetch, DNS lookup, file/URL XML source, entity resolution, enclosure download, or storage in this component. XML safety does not replace a future HTTP client's destination/redirect/rebinding controls.

## Downstream trust boundary

URLs and date strings deliberately remain untrusted. Unsafe links, invalid/naive/future dates and bidi-control examples are provisional values for T03.03 to reject or quarantine; do not persist or render `RawEntry` directly. Missing `published` remains `None`; `updated` is never substituted, and no observation/publication time is fabricated.

T02.02 live permission, T04.02 private durable persistence and T07.02 collection gates remain unchanged. No real registry entry, provider, account or schedule is enabled by this parser.
