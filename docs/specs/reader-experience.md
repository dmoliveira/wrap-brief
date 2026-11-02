# Minimalist reader experience and design

## Promise

“Nintendo news. Less repetition.” Help a reader understand what happened since their last visit and leave for the best source without friction. Be honest that the initial product is a daily digest, not a real-time breaking-news service.

## MVP information architecture

- Home: compact identity, daily cadence and actual last successful check, chronological story groups, source attribution, optional reviewed brief, small footer.
- About/methodology/sources: how grouping and lead selection work, source rights, limitations, correction route, privacy, and independent-site disclaimer. These may start as one well-structured policy page.
- No automatic per-article doorway pages. Add stable cluster URLs or substantive dated archives only when useful, indexable, and justified; a homepage anchor can serve sharing first.
- Source expansion uses native HTML disclosure. All headlines/source links work without JavaScript. A topic filter may be progressive enhancement later.

```text
WRAP BRIEF                                         About
Nintendo news. Less repetition.
Daily digest · Last checked 06:25 UTC · 5 sources

GAMES                              Reported · 2h ago
Clear story headline, attributed to the lead publisher
Optional original context, only if actually reviewed.
Read at [Publisher] →
▸ Other coverage (3)

HARDWARE                           Confirmed · Today
Next distinct event, not another card for the same story
Read at [Publisher] →

End of today's stories · Sources · Corrections · Privacy
Optional support placement only after commercial gates
```

No invented automated prose. MVP displays honestly attributed headline/link listings; it does not need an original-brief authoring system. Growth T09.02 can add reviewed original context. Do not imply publisher headlines were written by Wrap Brief.

## Visual direction

- Calm editorial design: warm off-white background, near-black text, one restrained teal/indigo accent, light separators, generous whitespace. Exact tokens finalized against contrast tests in the prototype.
- System fonts, 16–18 px body, 1.5–1.7 line height, roughly 65–75 character reading width, fluid 16–32 px outer gutters.
- Strong hierarchy through typography/spacing, not a wall of images. No Nintendo logo/characters, copied artwork, lookalike identity, mandatory remote fonts, autoplay, or decorative image generation.
- Respect system color/reduced-motion preferences when added; no animation required in MVP.
- One clear lead-link action per card. Other-source disclosure and secondary policy links are lower emphasis, not hidden.

## Accessibility acceptance

- Semantic landmarks, skip link, one logical page heading, meaningful heading order and link text.
- WCAG 2.2 AA target; normal text contrast ≥4.5:1, large text and UI ≥3:1; visible keyboard focus, no color-only status.
- At 320 px width: no horizontal overflow or clipped dates/labels. Touch targets target 44×44 px or equivalent spacing; test zoom/reflow at 200% and 400%.
- Keyboard-only reading, source expansion, and outbound navigation; screen-reader labels identify source and rumor status. Do not open new tabs unexpectedly by default.
- Native `<details>/<summary>` works without JS; progressive enhancement cannot remove baseline access.
- Test empty/no-new-stories, partial-source outage, stale data, long headlines, missing dates, many alternate sources, corrections, and ad-block/no-ad states later.

## Trust and freshness

Show source publication time when known and label first-seen time otherwise. Keep “last checked”, “latest story”, and “last deployed” distinct. Confirmed/reported/rumor labels require evidence; lack of an official source does not automatically imply falsehood. Prominent but calm warning if the last successful collection exceeds 30 hours; since static HTML cannot age itself without a reload/build, a small optional local-clock enhancement can update the banner, with an always-visible absolute timestamp as the no-JS fallback.

Corrections/removals are deliberate actions with public-safe context, not silent headline changes. A source failure must not display as “nothing happened today.”

## Performance and engagement budgets

- Initial HTML+CSS+JS ≤150 KB compressed, zero required client framework, no default image/third-party embeds; record the test device/network profile.
- Target LCP ≤2.5 s and CLS ≤0.1 on representative mobile conditions. These are measured targets, not launch guarantees inferred from static output alone.
- Number of cards is bounded; normal links/load-more pages beat infinite scroll. Reader engagement means returning utility, publisher referrals, and optional support—not trapping users.
- Original daily/weekly context and useful release information are future engagement experiments; do not increase automation scope before reader demand.

## Support and ads, later

One quiet support callout after reader value, with footer navigation pointing to the same section. No modal, sticky obstruction, guilt, countdown, default recurring charge, or newsletter wall. Explain what support funds and send payments to an approved hosted provider; never collect payment details on Pages.

Ads require a separate commercial/privacy/provider decision. Label `Advertisement`, reserve dimensions to prevent layout shift, keep placements outside story cards, provide no-ad fallback, and retest performance/keyboard/outbound tasks. Sponsored/affiliate material is visibly separated and disclosed before interaction. No paid placement in lead-source ranking.

Before release: test with at least five representative reader sessions (including mobile and keyboard users when feasible), asking them to find the latest check, distinguish rumor status, compare sources, and leave for publisher coverage. Record failures and repairs, not a blanket “looks good.”
