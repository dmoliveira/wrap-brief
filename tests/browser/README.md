# Complete-reader validation (T06.04, partial)

Build the three fixed local fixtures as described in `web/README.md`. Use an existing external Playwright installation (tested with 1.62.1), its installed Chromium, or an installed Chrome selected through `BROWSER_EXECUTABLE`. No Node/browser package is added to the Python lock or site:

```sh
node tests/render/check_digest_browser.cjs
node tests/render/check_shell_browser.cjs
node tests/browser/check_reader.cjs
node tests/browser/check_reader_visual.cjs
```

`NODE_PATH` can identify your external installation's `node_modules`. These commands run sequentially, each using an isolated browser. The first check covers native keyboard disclosure and intercepted source navigation; the second preserves shell contrast/focus/reflow coverage. The new reader check serves only exact synthetic HTML/CSS mappings from a temporary IPv4-loopback server, refuses external requests, and closes its server and browser on failure. Browser favicon probes, if any, receive a bodyless 204 and are counted separately. No directory or general filesystem server is exposed.

The final visual checker reads the three committed golden HTML files and canonical CSS. Run `make validate` first to verify renderer/golden parity. Its offline browser context fulfills only exact synthetic URLs and rejects other document requests; this is not an operating-system network sandbox. Unlike the existing source-navigation check, it does not activate outbound links. Unset `SCREENSHOT_DIR` when running the existing optional checks unless intentionally capturing synthetic local screenshots.

## What the reader check proves

- Document JavaScript disabled; service workers blocked.
- All three fixture pages at 320×900 and 1280×900, with alternate disclosures expanded.
- 200% root text enlargement, reduced-motion preference and no active animations/transitions.
- A 320×225 CSS viewport is the equivalent layout area of 1280×900 at 400% zoom. This is not a claim to manipulate browser-chrome zoom.
- Three cold-context digest measurements at 375×812, 4× CPU slowdown, 150ms latency, 1.6Mbps down and 750kbps up, cache disabled. Native CDP `PerformanceTimeline` receives LCP/layout shifts even with document scripting disabled. An absent LCP fails rather than becoming zero.
- Main-document `wallTime - timestamp` converts monotonic `Performance.NavigationStart` to epoch seconds; LCP render time is subtracted in that clock domain and reported in milliseconds. Only current main-frame events count. CLS excludes recent-input shifts and takes the largest session sum (less than one-second gaps, at most five seconds total).
- A fixed two-second post-load, no-interaction observation ends each run. Every observed LCP must be ≤2500ms and CLS ≤0.1. These are synthetic local lab results, not field data or full-page-lifetime guarantees. HTTP bodies are uncompressed; `test_reader_budget.py` separately computes the sum of individually gzipped HTML/CSS (mtime zero) against 150,000 bytes.

CDP references: [PerformanceTimeline](https://chromedevtools.github.io/devtools-protocol/tot/PerformanceTimeline/), [Network time types](https://chromedevtools.github.io/devtools-protocol/tot/Network/), [CLS session windows](https://web.dev/articles/cls).

## What the visual checker measures

- All three golden fixtures at 320×900, 1280×900 and 320×225 CSS pixels, each at 100% and 200% root text. The smaller viewport is 400%-equivalent layout area, not actual browser-chrome zoom; the additional root-size increase also enlarges `rem` spacing.
- Exact ordered keyboard focus on 10/5/4 controls per digest/corrected/empty fixture, including both summary states, followed by a check that no extra control trails the expected sequence. It checks computed solid-outline width, focus geometry and outline/text contrast against an **inferred** opaque ancestor surface, plus text-range and ancestor-clipping geometry. It does not prove painted pixels, occlusion, every pseudo-element, all fonts or other browsers.
- Enumerated non-whitespace body text, with only the known hidden summary suffix and unfocused skip link exempted. A defined set of ambiguous effects—including translucent surfaces, masks and differing text fill—fails rather than being treated as passing contrast; root/body vertical overflow that may suppress viewport scrolling also fails closed. In-memory controls check those guards, missing/low-contrast outlines, focus containment, low-contrast/hidden/clipped text, missing or modified stylesheet, unexpected requests and trailing controls. A separate positive control checks that keyboard scrolling works in a normal fixture.
- A long, unbroken synthetic skip label must still reach `#main` and continue keyboard navigation. If it is taller than the viewport, full outline containment is reported as **unassessed**, not as a pass or a proven accessibility failure. The checker reports whether it could exercise a classic scrollbar; an unavailable case is not a pass.

## Remaining real-assistive-technology gate

**These checks do not run a screen reader.** DOM/AX snapshots, accessible names and keyboard automation cannot establish actual VoiceOver speech, reading order, rotor behavior or interaction announcements. Run a real screen-reader session against the synthetic digest: traverse landmarks/headings, hear publisher/claim/unknown-date attribution, expand alternate coverage and confirm announced state, follow a source action safely, then inspect the corrected and empty cases.

On the validation host VoiceOver was installed but initially not running. A no-prompt Apple-event readiness probe returned `-600` (application not running), so an actual VoiceOver session could not be established without launching/control authorization. No system preference or permission was changed, no VoiceOver session was started, and no unrelated window or clipboard was inspected. This is unavailable evidence, not an accessibility failure or pass. An authorized operator must run/record the real-AT checks before T06.04 or M1 can be marked complete.
