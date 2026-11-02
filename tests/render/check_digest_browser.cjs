/* Focused T06.02 proof, using external Playwright; not the T06.04 AT/performance gate. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
async function run() {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
  try {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const allowedFiles = new Set();
    const allowedLinks = new Set();
    const unexpected = [];
    const navigations = [];
    await context.route('**/*', async route => {
      const url = route.request().url();
      if (allowedFiles.has(url.split('#')[0])) await route.continue();
      else if (allowedLinks.has(url)) {
        navigations.push(url);
        await route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="en"><head><title>Intercepted synthetic source</title><link rel="icon" href="data:,"></head><body><h1>Intercepted synthetic source</h1></body></html>' });
      } else { unexpected.push(url); await route.abort(); }
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10_000);
    page.setDefaultNavigationTimeout(10_000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const results = [];
    for (const fixture of ['digest', 'corrected', 'empty']) {
      const data = JSON.parse(await fs.readFile(path.join(root, `tests/fixtures/views/${fixture}.json`), 'utf8'));
      const items = new Map(data.items.map(item => [item.id, item]));
      const groups = data.clusters.filter(group => group.lead_id && group.correction_status !== 'retracted');
      const expected = groups.flatMap(group => group.member_ids.map(id => items.get(id))
        .filter(item => ['active', 'corrected'].includes(item.status)).map(item => item.url)).sort();
      const file = pathToFileURL(path.join(root, `.local/fixture-sites/${fixture}/index.html`)).href;
      const css = pathToFileURL(path.join(root, `.local/fixture-sites/${fixture}/styles.css`)).href;
      allowedFiles.add(file); allowedFiles.add(css);
      expected.forEach(url => allowedLinks.add(url));
      async function reset() {
        await page.goto('about:blank');
        await page.goto(file);
      }
      for (const width of [320, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        await reset();
        assert.equal(await page.locator('article').count(), groups.length);
        assert.deepEqual(await page.locator('article a').evaluateAll(links => links.map(link => link.href).sort()), expected);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Basic responsive overflow');
        assert.ok(await page.getByText('Hand-authored examples only.', { exact: false }).isVisible());
        if (fixture === 'digest') {
          assert.ok(await page.getByText('Rumor — unconfirmed', { exact: true }).first().isVisible());
          assert.ok(await page.getByText('Publication time unavailable', { exact: false }).isVisible());
        }
        if (fixture === 'corrected') {
          assert.ok(await page.getByText('Reported · Corrected coverage', { exact: true }).isVisible());
          assert.equal(await page.locator('a[href="https://example.com/news/update"]').count(), 0);
        }
        if (process.env.SCREENSHOT_DIR) {
          await fs.mkdir(process.env.SCREENSHOT_DIR, { recursive: true });
          await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, `${fixture}-${width}.png`), fullPage: true });
        }
        const summaries = await page.locator('summary').count();
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), '#main');
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'main');
        let expanded = 0;
        for (let step = 0; expanded < summaries && step < 50; step++) {
          await page.keyboard.press('Tab');
          if (await page.evaluate(() => document.activeElement.tagName === 'SUMMARY')) {
            assert.ok(await page.evaluate(() => {
              const style = getComputedStyle(document.activeElement);
              return style.outlineStyle === 'solid' && parseFloat(style.outlineWidth) >= 3;
            }), 'Visible summary focus');
            await page.keyboard.press('Space');
            expanded++;
          }
        }
        assert.equal(expanded, summaries, 'Every native disclosure is keyboard reachable');
        assert.equal(await page.locator('details[open]').count(), summaries);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        for (const link of await page.locator('article a').all()) assert.ok(await link.isVisible());
        for (const target of expected) {
          await reset();
          await page.keyboard.press('Tab');
          await page.keyboard.press('Enter');
          let found = false;
          for (let step = 0; step < 50; step++) {
            await page.keyboard.press('Tab');
            const active = await page.evaluate(() => ({ tag: document.activeElement.tagName, href: document.activeElement.getAttribute('href') }));
            if (active.tag === 'SUMMARY') await page.keyboard.press('Space');
            if (active.href === target) {
              await Promise.all([page.waitForURL(target), page.keyboard.press('Enter')]);
              assert.ok(await page.getByRole('heading', { name: 'Intercepted synthetic source' }).isVisible());
              found = true;
              break;
            }
          }
          assert.ok(found, 'Source link must be reachable by keyboard with no document JS');
        }
        results.push({ fixture, width, sourceLinks: expected.length, keyboardDisclosures: summaries });
      }
    }
    assert.deepEqual(unexpected, []);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ browser: browser.version(), javaScript: false, results,
      interceptedSourceNavigations: navigations.length, unexpectedRequests: 0, pageErrors: 0 }));
    await context.close();
  } finally { await browser.close(); }
}
run().catch(error => { console.error(error); process.exitCode = 1; });
