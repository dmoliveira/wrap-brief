# Offline shell preview

Open `web/index.html` directly in a browser. It uses the sibling `styles.css`, system fonts and local fragment navigation only. No server, build, JavaScript, network request, account or image is required. This is a static layout preview, not the grouped digest or a published news site.

`styles.css` is the canonical token and shell stylesheet. The chosen direction is warm paper, dark editorial typography and a restrained teal accent; there are no Nintendo logos, character assets or generated illustrations. The HTML keeps the working-name/unofficial notice and explicitly says that no news has been collected or published. No collection time, source count or news item is invented.

The later T06.02 task owns data rendering, HTML escaping, story cards and source disclosures. These repository-level preview assets are not installed Python-package resources.

## Checks

The normal `make validate` includes standard-library shell structure, fragment, local-asset, contrast and CSS contract tests. Actual foreground/surface usage pairs must meet 4.5:1; focus indicators must meet 3:1. The light separator token is decorative, not a text or interactive-control color.

For the optional live-browser check, use an existing external Playwright installation (tested with 1.62.1) and its installed Chromium, or select an installed Chrome executable using `BROWSER_EXECUTABLE`:

```sh
# NODE_PATH may point to the node_modules directory of your external installation.
node tests/render/check_shell_browser.cjs
```

`SCREENSHOT_DIR=.local/screenshots` optionally saves local-only preview captures. Do not add environment-specific paths, browser caches or screenshots containing private data to Git. Playwright is a developer validation tool, not a site/runtime dependency or a new dependency in this project's lock.

The check runs one isolated headless browser with document JavaScript disabled. It verifies 320px/1280px reflow, actual text/focus contrast, all five keyboard links and fragment targets, 44px targets, very long strings, and 200% text enlargement. A 320×225 CSS viewport represents the reflow area of 1280×900 at 400% browser zoom; this is explicitly an equivalent layout check, not control of browser-chrome zoom. Full digest accessibility, assistive-technology review and performance measurement remain T06.04.
