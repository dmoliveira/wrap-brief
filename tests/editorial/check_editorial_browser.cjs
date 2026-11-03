/* Optional external Playwright proof; no reader/package dependency or real AT claim. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const producer = `
import sys
from pathlib import Path
from dataclasses import replace
sys.path.insert(0, 'tests')
from editorial.support import fixture, ledger_for, reviewed, PUBLIC_REF
from wrap_brief.editorial.controls import CorrectionControl, metadata_reference
from wrap_brief.render.digest import render_editorial
root = Path(sys.argv[1])
state = fixture()
target = next(item for item in state.items if item.source_id == 'demo-a')
for name, action in (('corrected', 'correct'), ('retracted', 'retract'), ('erased', 'exclude_source')):
    control = CorrectionControl('browser-' + name, target.source_id, action, state.observed_at,
        item_id=None if action == 'exclude_source' else target.id,
        metadata_ref=metadata_reference(target) if action == 'correct' else None,
        public_notice_ref=PUBLIC_REF + ('#correction' if action == 'correct' else '#retraction') if action in {'correct', 'retract'} else None)
    ledger = ledger_for(state, controls=(control,))
    ledger = replace(ledger, claims=tuple(replace(value, evidence_ref='https://example.com/review/' + 'x' * 900) for value in ledger.claims))
    result = reviewed(state, ledger)
    output = root / name
    output.mkdir(mode=0o700)
    (output / 'index.html').write_text(render_editorial(result), encoding='utf-8')
    (output / 'styles.css').write_bytes(Path('web/styles.css').read_bytes())
`;

async function run() {
  const temporary = await fs.mkdtemp(path.join(process.env.BROWSER_TEMP || os.tmpdir(), 'wrap-brief-editorial-'));
  let browser;
  try {
    execFileSync('uv', ['run', '--locked', 'python', '-B', '-c', producer, temporary],
      { cwd: root, timeout: 30_000, stdio: ['ignore', 'pipe', 'pipe'] });
    browser = await chromium.launch({ headless: true,
      ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
    const context = await browser.newContext({ javaScriptEnabled: false, serviceWorkers: 'block', reducedMotion: 'reduce' });
    const allowedFiles = new Set();
    const sourceLinks = new Set(['https://example.com/synthetic-withdrawn-m26q9', 'https://example.org/synthetic-unrelated']);
    const unexpected = [];
    let navigations = 0;
    await context.route('**/*', async route => {
      const url = route.request().url();
      if (allowedFiles.has(url.split('#')[0])) return route.continue();
      if (sourceLinks.has(url)) {
        navigations++;
        return route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="en"><head><title>Synthetic source</title></head><body><h1>Intercepted synthetic source</h1></body></html>' });
      }
      unexpected.push(url);
      return route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10_000);
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    const results = [];
    for (const name of ['corrected', 'retracted', 'erased']) {
      const file = pathToFileURL(path.join(temporary, name, 'index.html')).href;
      allowedFiles.add(file);
      allowedFiles.add(pathToFileURL(path.join(temporary, name, 'styles.css')).href);
      for (const viewport of [{ width: 320, height: 900 }, { width: 1280, height: 900 }, { width: 320, height: 225 }]) {
        for (const textSize of [16, 32]) {
          await page.setViewportSize(viewport);
          await page.goto('about:blank');
          await page.goto(file);
          await page.evaluate(size => { document.documentElement.style.fontSize = `${size}px`; }, textSize);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Editorial reference reflow');
          assert.ok(await page.getByRole('heading', { name: 'Editorial records', exact: true }).isVisible());
          assert.equal(await page.locator('#editorial-records a').count(), 0, 'References are text, not invented links');
          if (name === 'corrected') assert.ok(await page.getByText('Correction acknowledged', { exact: false }).isVisible());
          if (name === 'retracted') assert.ok(await page.getByText('Coverage withdrawn following review', { exact: false }).isVisible());
          if (name !== 'corrected') {
            assert.equal(await page.getByText('Synthetic withdrawn sentinel M26Q9', { exact: true }).count(), 0);
            assert.equal(await page.locator('article a[href="https://example.com/synthetic-withdrawn-m26q9"]').count(), 0);
          }
          await page.keyboard.press('Tab');
          assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), '#main');
          await page.keyboard.press('Enter');
          assert.equal(await page.evaluate(() => document.activeElement.id), 'main');
          let followed = false;
          for (let step = 0; step < 30; step++) {
            await page.keyboard.press('Tab');
            const href = await page.evaluate(() => document.activeElement.getAttribute('href'));
            if (sourceLinks.has(href)) {
              await Promise.all([page.waitForURL(href), page.keyboard.press('Enter')]);
              assert.ok(await page.getByRole('heading', { name: 'Intercepted synthetic source' }).isVisible());
              followed = true;
              break;
            }
          }
          assert.ok(followed, 'Attributed source remains keyboard reachable');
          results.push({ case: name, ...viewport, textSize });
        }
      }
    }
    assert.deepEqual(unexpected, []);
    assert.deepEqual(pageErrors, []);
    console.log(JSON.stringify({ browser: browser.version(), javaScript: false, results,
      interceptedSourceNavigations: navigations, unexpectedRequests: 0, pageErrors: 0, realScreenReader: 'not tested' }));
    await context.close();
  } finally {
    if (browser) await browser.close();
    // This directory was just created by this invocation, not supplied by a user.
    await fs.rm(temporary, { recursive: true, force: true });
  }
}
run().catch(error => { console.error(error); process.exitCode = 1; });
