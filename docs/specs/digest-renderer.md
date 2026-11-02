# Fixture-only grouped digest renderer (T06.02)

## Public boundary

`wrap_brief.render.digest.digest_view(snapshot)` projects a validated immutable `Snapshot` into frozen `DigestView`, `StoryView` and `CoverageView` records. `render_digest(snapshot) -> str` performs that projection itself and returns a complete escaped HTML document. Neither function reads assets, looks up the clock, fetches links, mutates records or writes files.

This implementation accepts **synthetic snapshots only**, with source allowlists limited to reserved `example.com`, `example.org`, `example.net`, their subdomains, or `.example` hosts. Live snapshots and non-fixture hosts fail closed. A synthetic label is not publisher permission; the build entry point reads only the committed, hand-authored shared fixtures. Live output requires a later reviewed policy/approval boundary, not changing a CLI input file.

Every record-derived text and attribute value is escaped with `html.escape(..., quote=True)`. Links retain the validated HTTPS source URL and query bytes; the renderer does not guess tracking or rewrite content. IDs use constant prefixes plus validated group IDs. There is no raw-HTML, style, script, URL-template or source-body input. GUIDs, checkpoint/header data and approval references are not projected or exported. External links stay in the same tab and suppress referrers.

## Membership, ordering and labels

- Validate all cross-references, reject overlapping cluster membership, and require every active/corrected Item to belong to a cluster before rendering anything.
- Examine the complete bounded snapshot (up to 10,000 clusters). Classify every group, then reject more than **50 eligible display groups**. Never truncate silently.
- A display group requires the supplied available lead and must not have group correction status `retracted`. Do not choose a substitute lead in presentation.
- Active/corrected alternate Items remain linked separately. Removed/retracted/quarantined Items contribute only to a neutral unavailable-record count; their titles and URLs are absent. Fully unavailable or withdrawn groups contribute only to the omitted-group count.
- Order cards by the lead's publication timestamp descending, or first-seen timestamp when publication is unknown; group ID breaks ties ascending. Order alternates by canonical member ID. Never sort on last-seen/update metadata to manufacture freshness.
- Preserve group claim labels and explicit source correction state. Each alternate has its own claim/date/correction label. Unknown publication says **Publication time unavailable · First seen**; known publication says **Published**. Times remain absolute UTC.
- The snapshot observation is labeled **Fixture observation**, never a successful check or deployment time. The page explicitly states that these are hand-authored, non-news examples. An empty synthetic fixture has “no displayable story groups,” not “no news today.”

The final document must fit **1 MiB of UTF-8 bytes**, or rendering raises a bounded `ContractError` without returning partial HTML. These are component bounds, not the T06.04 compressed-page performance budget.

## No-JavaScript reader structure

Each article has one attributed headline in an h2. `aria-labelledby` points to `story-title-{id}`; `aria-describedby` points to the visible `story-status-{id}` and `story-time-{id}`. All IDs are unique. One clear lead action identifies its publisher; its accessible name includes the visible “Read at …” wording, headline and claim label. Native `<details>/<summary>` exposes the actual eligible alternate count. Alternate headlines, publisher actions and attribution remain available without scripts. Unavailable-record counts are separate from eligible alternate counts.

`web/styles.css` remains the single canonical stylesheet for both the original shell and digest content. Generated HTML references the fixed sibling `styles.css`; the installed Python renderer does not require repository assets. Original typography, tokens, skip link, landmarks, focus styling and disclaimer are retained. No images, framework, external font or invented editorial prose are added.

## Deterministic local fixture build

```sh
uv run --locked python tools/build_fixture_site.py digest
uv run --locked python tools/build_fixture_site.py corrected
uv run --locked python tools/build_fixture_site.py empty
```

The only input is this fixed case enum. Output is the fixed ignored `.local/fixture-sites/<case>/` directory containing exactly `index.html` and `styles.css`. Existing destinations, including dangling symlinks, and symlinked `.local`/`fixture-sites` ancestry are refused. Paired files are prepared in an owned temporary sibling and renamed into a fresh destination; render/write/rename failures leave no partial new destination. This is a local preview helper, not the privileged production artifact writer or deployment/rollback system.

Repeated inputs, including the supplied observation clock, yield identical file bytes. Tests compare independent fresh builds and committed synthetic golden HTML. A build does not replace an existing preview: retain/review it or remove only that known generated directory before rebuilding. Never direct publisher state into Git or a public artifact.

## Validation and remaining boundaries

Unit tests cover independent text/attribute injection, unsafe URLs, source-host restrictions, claim/correction/unknown-date labels, private-field exclusion, membership/eligibility, stable ordering, exact UTF-8 limits and failure cleanup. The wheel smoke calls the renderer with an in-memory synthetic snapshot outside the checkout.

The optional external-Playwright `tests/render/check_digest_browser.cjs` proves native keyboard disclosure and every source navigation with document JavaScript disabled. Source navigation is fulfilled locally under interception, never sent to publishers. It includes basic 320px/desktop smoke views, not comprehensive assistive-technology, stress-reflow or performance certification. It expects the three fixture builds above. T06.03 owns live policies/health/staleness states; T06.04 owns the complete fixture reader's accessibility and measured performance gate. Live collection, deployment, analytics and monetization remain disabled.
