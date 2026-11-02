# Shared synthetic fixture contract

All data here is hand-authored development material, **not real news or publisher content**. No source is enabled or approved. The live registry remains `config/sources.json`, not this library. Never replace these files with downloaded feeds or private logs.

`manifest.json` version 1 declares a fixed observation clock, source records, cases, expected provisional metadata, transport examples, and view-model snapshots. Consumers share these inputs rather than invent incompatible schemas.

## Feed cases

- `feeds/`: small valid RSS 2.0/Atom, namespaces/XHTML title text, Unicode, missing dates/GUIDs, updates, empty feeds, duplicate entries, and an actual ISO-8859-1 byte fixture.
- `adversarial/`: malformed/unsupported XML, DTD/entity/external-reference probes, ignored hostile descriptions/enclosures, mixed valid/invalid entries, unsafe links, invalid/naive/future dates, and an escaped bidi-control title.
- A successful adapter result has `entries`, each with exactly `source_id`, `title`, `url`, nullable `guid`, nullable `published`, and nullable `updated`. Dates remain source strings at this stage. Missing dates are `null`; `updated` must not be substituted for publication.
- Entry metadata is still untrusted. The future normalizer owns final URL/time/text/domain validation and quarantines invalid values. `normalization` expectations describe those later semantic outcomes, not defenses implemented by this fixture task.
- Feed failures use the declared parser error code. Mixed-item issues retain only a zero-based index and bounded code. Duplicate entries are not deduplicated by the parser.
- Descriptions, bodies, images and enclosures never become metadata output. There are no enclosure downloads.

Only small trusted `feeds/` cases are structurally checked with the standard-library XML parser, after a DTD/entity denial check. **Never parse adversarial XML with that parser.** The safe-adapter task must prove the declared rejection behavior with its hardened parser.

## Limits and transport

`support.recipe_bytes()` generates only four bounded probe types (byte size, XML depth, title size, entry count). No code evaluation, external input, filesystem reference, or network access occurs. Large payloads are generated in memory rather than committed. The future parser must enforce size before parsing and reject declared depth/text/item excesses.

`transport.json` contains only synthetic 304, redirect, rate-limit, server-error and timeout responses. They are data for future client tests, not HTTP requests. Redirect destinations must be revalidated; the loopback example must never be fetched. No cookies, authorization headers, tokens, or private contacts are present.

## View models

`views/` contains complete version-1 core records for a grouped digest, empty state and correction/retraction. Sources are disabled/unreviewed. Unknown publication, rumor labels and an available replacement lead are intentional. These are independent renderer examples, not output claimed to be produced by the future parser/grouping algorithm.

The clock and all IDs are fixed. Record round trips and cross-references are tested with `wrap_brief.models`. The original `tests/models/fixtures/v1.json` remains the small schema-compatibility vector; this library is the broader pipeline/reader test dataset.
