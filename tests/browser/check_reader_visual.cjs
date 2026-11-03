/* Optional synthetic-fixture checks. Computed styles and geometry are not paint or AT proof. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const origin = 'http://reader.invalid';
const focusOrder = {
  digest: [
    'a:#main', 'a:#stories', 'a:#about',
    'a:https://example.com/news/unknown-date', 'a:https://example.org/news/rumor',
    'a:https://example.com/news/update', 'summary',
    'a:https://example.org/news/update', 'a:https://example.net/news/update', 'a:#top',
  ],
  corrected: ['a:#main', 'a:#stories', 'a:#about', 'a:https://example.org/news/update', 'a:#top'],
  empty: ['a:#main', 'a:#stories', 'a:#about', 'a:#top'],
};
const expectedTextNodes = { digest: 61, corrected: 29, empty: 19 };
let phase = 'startup';

async function assess(page, mode) {
  return page.evaluate(mode => {
    const fail = code => { throw new Error(code); };
    for (const element of [document.documentElement, document.body]) {
      if (['hidden', 'clip'].includes(getComputedStyle(element).overflowY)) fail('unsupported-viewport-overflow');
    }
    function rgba(value) {
      const match = /^rgba?\(([^)]+)\)$/.exec(value);
      if (!match) fail('unsupported-color');
      const parts = match[1].split(',').map(value => Number(value.trim()));
      if (![3, 4].includes(parts.length) || parts.some(value => !Number.isFinite(value))) fail('unsupported-color');
      return [parts[0], parts[1], parts[2], parts.length === 4 ? parts[3] : 1];
    }
    function luminance(color) {
      return color.slice(0, 3).reduce((sum, value, index) => {
        const channel = value / 255;
        const linear = channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        return sum + linear * [0.2126, 0.7152, 0.0722][index];
      }, 0);
    }
    function contrast(first, second) {
      const [high, low] = [luminance(first), luminance(second)].sort((a, b) => b - a);
      return (high + 0.05) / (low + 0.05);
    }
    function supported(element) {
      for (let current = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (style.display === 'none' || style.visibility !== 'visible' || Number(style.opacity) === 0) fail('hidden-text');
        if (Number(style.opacity) !== 1) fail('unsupported-opacity');
        const maskBoxSources = ['mask-border-source', '-webkit-mask-box-image-source']
          .map(property => style.getPropertyValue(property).trim());
        if (style.maskImage !== 'none' || style.webkitMaskImage !== 'none' ||
            maskBoxSources.some(value => value !== '' && value !== 'none')) fail('unsupported-mask');
        if (style.transform !== 'none' || style.filter !== 'none' || style.backdropFilter !== 'none' ||
            style.mixBlendMode !== 'normal' || style.clipPath !== 'none' || style.clip !== 'auto' ||
            style.contentVisibility !== 'visible' || style.backgroundImage !== 'none' || style.textShadow !== 'none') {
          fail('unsupported-effect');
        }
      }
    }
    function background(element) {
      for (let current = element; current; current = current.parentElement) {
        const value = rgba(getComputedStyle(current).backgroundColor);
        if (value[3] === 1) return value;
        if (value[3] !== 0) fail('unsupported-background');
      }
      fail('unsupported-background');
    }
    function clipped(rect, element) {
      if (rect.left < -0.5 || rect.right > document.documentElement.clientWidth + 0.5) return true;
      for (let current = element; current && current !== document.documentElement; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX)) {
          const box = current.getBoundingClientRect();
          const left = box.left + current.clientLeft;
          if (rect.left < left - 0.5 || rect.right > left + current.clientWidth + 0.5) return true;
        }
        if (['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY)) {
          const box = current.getBoundingClientRect();
          const top = box.top + current.clientTop;
          if (rect.top < top - 0.5 || rect.bottom > top + current.clientHeight + 0.5) return true;
        }
      }
      return false;
    }
    function text(scope) {
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      let count = 0, minimum = Infinity;
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (!node.textContent.trim()) continue;
        const element = node.parentElement;
        const hidden = element.closest('.visually-hidden');
        if (hidden) {
          if (hidden.tagName !== 'SPAN' || hidden.parentElement.tagName !== 'SUMMARY' ||
              hidden.textContent !== ' for Fictional console update announced' ||
              document.querySelectorAll('.visually-hidden').length !== 1) fail('unexpected-hidden-exemption');
          continue;
        }
        const skip = element.closest('.skip-link');
        if (skip) {
          const expectedSkip = mode.startsWith('stress-') ? 'S'.repeat(80) : 'Skip to content';
          if (skip.tagName !== 'A' || skip.getAttribute('href') !== '#main' ||
              skip.textContent !== expectedSkip || document.querySelectorAll('.skip-link').length !== 1) {
            fail('unexpected-skip-exemption');
          }
          if (document.activeElement !== skip) continue;
        }
        supported(element);
        const style = getComputedStyle(element);
        if (!(parseFloat(style.fontSize) > 0)) fail('unmeasurable-text');
        const foreground = rgba(style.color);
        if (foreground[3] !== 1) fail('unsupported-text-color');
        const fill = rgba(style.webkitTextFillColor);
        if (fill.some((value, index) => value !== foreground[index])) fail('unsupported-text-fill');
        const ratio = contrast(foreground, background(element));
        if (ratio < 4.5) fail('text-contrast');
        const range = document.createRange();
        range.selectNodeContents(node);
        const rectangles = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
        if (!rectangles.length) fail('unmeasurable-text');
        if (rectangles.some(rect => clipped(rect, element))) fail('clipped-text');
        minimum = Math.min(minimum, ratio);
        count++;
      }
      if (!count) fail('unmeasurable-text');
      return { count, minimum };
    }
    if (mode === 'text') return text(document.body);
    if (mode === 'stress-text') return text(document.activeElement);
    if (!['focus', 'stress-focus'].includes(mode)) fail('invalid-mode');
    const element = document.activeElement;
    if (!element || !['A', 'SUMMARY'].includes(element.tagName) || !element.matches(':focus-visible')) fail('focus-target');
    supported(element);
    const style = getComputedStyle(element);
    const width = parseFloat(style.outlineWidth), offset = parseFloat(style.outlineOffset);
    if (style.outlineStyle !== 'solid' || !(width >= 3) || !Number.isFinite(offset) || offset < 0) fail('focus-outline');
    const outline = rgba(style.outlineColor);
    if (outline[3] !== 1) fail('unsupported-outline-color');
    const ratio = contrast(outline, background(element.parentElement));
    if (ratio < 3) fail('focus-contrast');
    const rect = element.getBoundingClientRect(), reach = width + offset;
    const ring = { left: rect.left - reach, right: rect.right + reach,
      top: rect.top - reach, bottom: rect.bottom + reach };
    const viewportWidth = document.documentElement.clientWidth, viewportHeight = document.documentElement.clientHeight;
    if (ring.left < -0.5 || ring.right > viewportWidth + 0.5 || ring.top < -0.5 || ring.bottom > viewportHeight + 0.5 ||
        clipped(ring, element.parentElement)) {
      fail(`unassessed-focus-containment:${Math.round(ring.left)},${Math.round(ring.top)},${Math.round(ring.right)},${Math.round(ring.bottom)}:${viewportWidth}x${viewportHeight}`);
    }
    const focusedText = text(element);
    return { outlineContrast: ratio, textContrast: focusedText.minimum };
  }, mode);
}

async function fixtureContext(browser, assets) {
  const context = await browser.newContext({ javaScriptEnabled: false, serviceWorkers: 'block', reducedMotion: 'reduce' });
  const unexpected = [];
  let faviconProbes = 0;
  await context.route('**/*', async route => {
    const request = route.request(), url = request.url();
    if (request.method() === 'GET' && assets.has(url)) {
      const value = assets.get(url);
      return route.fulfill({ status: 200, contentType: value.type, body: value.body });
    }
    if (request.method() === 'GET' && url === `${origin}/favicon.ico`) {
      faviconProbes++;
      return route.fulfill({ status: 204, body: '' });
    }
    unexpected.push(url);
    return route.abort();
  });
  await context.setOffline(true);
  return { context, unexpected, faviconProbes: () => faviconProbes };
}

async function verifyStyles(page) {
  const css = await page.evaluate(() => ({
    sheets: [...document.styleSheets].filter(sheet => sheet.href && sheet.href.endsWith('/styles.css')).length,
    paper: getComputedStyle(document.documentElement).getPropertyValue('--paper').trim(),
  }));
  assert.equal(css.sheets, 1, 'fixture-stylesheet-missing');
  assert.equal(css.paper, '#f7f5ef', 'fixture-stylesheet-token');
}

async function load(page, name) {
  await page.goto(`${origin}/${name}/index.html`, { waitUntil: 'load' });
  await verifyStyles(page);
}

async function verifyFocusEnd(page) {
  await page.keyboard.press('Tab');
  const end = await page.evaluate(() => {
    const element = document.activeElement;
    if (!document.hasFocus()) return 'outside';
    if ((element === document.body || element === document.documentElement) && !element.hasAttribute('tabindex')) return 'root';
    if (element === document.querySelector('.skip-link') && element.getAttribute('href') === '#main') return 'wrapped';
    return 'unexpected';
  });
  if (end === 'unexpected') throw new Error('unexpected-trailing-focus');
}

async function verifyKeyboardScroll(page, timeout = 5_000) {
  await page.bringToFront();
  await page.keyboard.press('Tab');
  const focus = await page.evaluate(() => ({
    documentFocused: document.hasFocus(), href: document.activeElement.getAttribute('href'),
  }));
  assert.ok(focus.documentFocused && focus.href === '#main', 'scrollable-viewport-focus');

  // Wait for any focus-induced scrolling to settle before attributing movement to End.
  let before = await page.evaluate(() => window.scrollY), stable = 0;
  const settlingDeadline = Date.now() + 2_000;
  while (stable < 3 && Date.now() < settlingDeadline) {
    await delay(50);
    const current = await page.evaluate(() => window.scrollY);
    stable = Math.abs(current - before) < 0.5 ? stable + 1 : 0;
    before = current;
  }
  assert.equal(stable, 3, 'scrollable-viewport-not-settled');
  await page.keyboard.press('End');
  // Page-side polling callbacks may not run when document JavaScript is disabled.
  const deadline = Date.now() + timeout;
  let after = before;
  do {
    after = await page.evaluate(() => window.scrollY);
    if (after <= before + 0.5) await delay(50);
  } while (after <= before + 0.5 && Date.now() < deadline);
  assert.ok(after > before + 0.5, 'scrollable-viewport-no-scroll');
}

async function negativeControls(browser, assets) {
  const cases = [
    ['missing-outline', 'a.skip-link:focus-visible { outline: none !important; }', 'focus', /focus-outline/],
    ['poor-outline', 'a.skip-link:focus-visible { outline-color: #f7f5ef !important; }', 'focus', /focus-contrast/],
    ['focus-outside-viewport', 'a.skip-link:focus-visible { left: -100px !important; }', 'focus', /unassessed-focus-containment/],
    ['focus-clipped-vertical', 'nav { height: 1px !important; overflow: hidden !important; }', 'focus', /unassessed-focus-containment/, null, 2],
    ['poor-text', '.story-card h2 { color: #f7f5ef !important; }', 'text', /text-contrast/],
    ['transparent-text-fill', '.story-card h2 { -webkit-text-fill-color: transparent !important; }', 'text', /unsupported-text-fill/],
    ['hidden-text', '.story-card h2 { visibility: hidden !important; }', 'text', /hidden-text/],
    ['clipped-text', '.story-card h2 { width: 15px !important; overflow: hidden !important; white-space: nowrap !important; }', 'text', /clipped-text/],
    ['clipped-vertical', '.story-card h2 { height: 1px !important; overflow: hidden !important; }', 'text', /clipped-text/],
    ['unsupported-effect', '.story-card h2 { opacity: 0.5 !important; }', 'text', /unsupported-opacity/],
    ['unsupported-background', '.story-card h2 { background-image: linear-gradient(red, blue) !important; }', 'text', /unsupported-effect/],
    ['unsupported-mask', '.story-card a { mask-image: linear-gradient(transparent, transparent) !important; }', 'text', /unsupported-mask/],
    ['unsupported-mask-box', '.story-card h2 { -webkit-mask-box-image: linear-gradient(transparent, transparent) 1 fill !important; }', 'text', /unsupported-mask/],
    ['unsupported-clip', '.story-card h2 { position: absolute !important; clip: rect(0px, 1px, 1px, 0px) !important; }', 'text', /unsupported-effect/],
    ['unsupported-content-visibility', '.story-card h2 { content-visibility: hidden !important; }', 'text', /unsupported-effect/],
    ['disguised-hidden-text', '', 'text', /unexpected-hidden-exemption/, 'visually-hidden'],
    ['disguised-skip-text', '', 'text', /unexpected-skip-exemption/, 'skip-link'],
    ['root-overflow-hidden', 'html { overflow-y: hidden !important; }', 'text', /unsupported-viewport-overflow/],
    ['root-overflow-clip', 'html { overflow-y: clip !important; }', 'text', /unsupported-viewport-overflow/],
    ['body-overflow-hidden', 'body { overflow-y: hidden !important; }', 'text', /unsupported-viewport-overflow/],
    ['body-overflow-clip', 'body { overflow-y: clip !important; }', 'text', /unsupported-viewport-overflow/],
  ];
  for (const [name, css, mode, failure, disguise, tabs] of cases) {
    phase = `control/${name}`;
    const { context, unexpected } = await fixtureContext(browser, assets);
    try {
      const page = await context.newPage();
      await page.setViewportSize({ width: 320, height: 900 });
      await load(page, 'digest');
      await page.evaluate(({ css, disguise }) => {
        const style = document.createElement('style'); style.textContent = css; document.head.append(style);
        document.querySelectorAll('details').forEach(value => { value.open = true; });
        if (disguise) document.querySelector('.story-card h2').classList.add(disguise);
      }, { css, disguise });
      if (mode === 'focus') for (let index = 0; index < (tabs || 1); index++) await page.keyboard.press('Tab');
      await assert.rejects(() => assess(page, mode), failure, `${name} negative control`);
      assert.deepEqual(unexpected, [], 'Unexpected request in style control');
    } finally { await context.close(); }
  }
  phase = 'control/stylesheet-and-network';
  const { context, unexpected } = await fixtureContext(browser, assets);
  try {
    const page = await context.newPage();
    await load(page, 'empty');
    await page.evaluate(() => document.documentElement.style.setProperty('--paper', '#ffffff'));
    await assert.rejects(() => verifyStyles(page), /fixture-stylesheet-token/, 'Bad stylesheet token control');
    await page.evaluate(() => document.querySelector('link[rel="stylesheet"]').remove());
    await assert.rejects(() => verifyStyles(page), /fixture-stylesheet-missing/, 'Missing stylesheet control');
    const outcome = await page.evaluate(async () => {
      try { await fetch('http://unexpected.invalid/probe'); return 'fulfilled'; }
      catch { return 'rejected'; }
    });
    assert.equal(outcome, 'rejected', 'Unexpected request must not be fulfilled');
    assert.equal(unexpected.length, 1, 'Unexpected request must be recorded and aborted');
  } finally { await context.close(); }
  phase = 'control/trailing-focus';
  const trailing = await fixtureContext(browser, assets);
  try {
    const page = await trailing.context.newPage();
    await page.setViewportSize({ width: 320, height: 900 });
    await load(page, 'digest');
    await page.evaluate(() => {
      const extra = document.createElement('a'); extra.href = '#main';
      extra.setAttribute('aria-label', 'Synthetic extra control'); document.body.append(extra);
    });
    for (const expected of focusOrder.digest) {
      await page.keyboard.press('Tab');
      const actual = await page.evaluate(() => document.activeElement.tagName === 'SUMMARY' ?
        'summary' : `a:${document.activeElement.getAttribute('href')}`);
      assert.equal(actual, expected, 'Unexpected focus during trailing-control test');
      if (expected === 'summary') await page.keyboard.press('Space');
    }
    await assert.rejects(() => verifyFocusEnd(page), /unexpected-trailing-focus/);
    assert.deepEqual(trailing.unexpected, [], 'Unexpected request in trailing-control test');
  } finally { await trailing.context.close(); }
  phase = 'control/scrollable-viewport';
  const scrollable = await fixtureContext(browser, assets);
  try {
    const page = await scrollable.context.newPage();
    await page.setViewportSize({ width: 320, height: 900 });
    await load(page, 'digest');
    assert.ok(await page.evaluate(() => document.scrollingElement.scrollHeight > document.documentElement.clientHeight));
    await verifyKeyboardScroll(page);
    assert.deepEqual(scrollable.unexpected, [], 'Unexpected request in scrollable-viewport test');
  } finally { await scrollable.context.close(); }
  phase = 'control/already-scrolled-viewport';
  const alreadyScrolled = await fixtureContext(browser, assets);
  try {
    const page = await alreadyScrolled.context.newPage();
    await page.setViewportSize({ width: 320, height: 900 });
    await load(page, 'digest');
    await page.evaluate(() => {
      const style = document.createElement('style');
      style.textContent = 'html { overflow-y: hidden !important; } .skip-link { top: 1500px !important; }';
      document.head.append(style);
    });
    await assert.rejects(() => verifyKeyboardScroll(page, 1_000), /scrollable-viewport-no-scroll/);
    assert.ok(await page.evaluate(() => window.scrollY > 0), 'Tab must have scrolled this negative control');
    assert.deepEqual(alreadyScrolled.unexpected, [], 'Unexpected request in already-scrolled test');
  } finally { await alreadyScrolled.context.close(); }
  return [...cases.map(value => value[0]), 'bad-stylesheet-token', 'missing-stylesheet', 'unexpected-request',
    'trailing-focus', 'scrollable-viewport', 'already-scrolled-viewport'];
}

async function longSkipControl(browser, assets) {
  const results = [];
  for (const height of [900, 225]) {
    phase = `long-skip/320x${height}`;
    const { context, unexpected } = await fixtureContext(browser, assets);
    try {
      const page = await context.newPage();
      await page.setViewportSize({ width: 320, height });
      await load(page, 'digest');
      await page.evaluate(() => {
        document.documentElement.style.fontSize = '200%';
        document.querySelector('.skip-link').textContent = 'S'.repeat(80);
      });
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), '#main');
      await assess(page, 'stress-text');
      const geometry = await page.evaluate(() => {
        const rect = document.activeElement.getBoundingClientRect(), style = getComputedStyle(document.activeElement);
        return { height: rect.height + 2 * (parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset)),
          viewport: document.documentElement.clientHeight };
      });
      let containment = 'contained';
      if (geometry.height > geometry.viewport) {
        await assert.rejects(() => assess(page, 'stress-focus'), /unassessed-focus-containment/);
        containment = 'unassessed-too-tall';
      } else {
        await assess(page, 'stress-focus');
      }
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'main', 'Skip link must reach main');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')),
        'https://example.com/news/unknown-date', 'Tab must continue into main content');
      assert.deepEqual(unexpected, [], 'Unexpected request in long skip control');
      results.push({ width: 320, height, fontSize: '200%', containment, keyboardNavigation: 'passed' });
    } finally { await context.close(); }
  }
  return results;
}

async function classicScrollbarProbe(browser, assets) {
  phase = 'classic-scrollbar';
  const { context, unexpected } = await fixtureContext(browser, assets);
  try {
    const page = await context.newPage();
    await page.setViewportSize({ width: 320, height: 900 });
    await load(page, 'digest');
    const viewport = await page.evaluate(() => {
      document.documentElement.style.fontSize = '200%';
      const style = document.createElement('style');
      style.textContent = 'html { overflow-y: scroll !important; } ::-webkit-scrollbar { width: 16px !important; }';
      document.head.append(style);
      return { inner: innerWidth, client: document.documentElement.clientWidth };
    });
    assert.deepEqual(unexpected, [], 'Unexpected request in scrollbar probe');
    if (viewport.inner === viewport.client) return { status: 'UNAVAILABLE', viewport };
    for (const expected of focusOrder.digest) {
      await page.keyboard.press('Tab');
      const actual = await page.evaluate(() => document.activeElement.tagName === 'SUMMARY' ?
        'summary' : `a:${document.activeElement.getAttribute('href')}`);
      assert.equal(actual, expected, 'Unexpected scrollbar focus order');
      await assess(page, 'focus');
      if (expected === 'summary') await page.keyboard.press('Space');
    }
    await assess(page, 'text');
    await verifyFocusEnd(page);
    return { status: 'MEASURED', viewport };
  } finally { await context.close(); }
}

async function run() {
  const assets = new Map();
  const css = await fs.readFile(path.join(root, 'web/styles.css'));
  for (const name of Object.keys(focusOrder)) {
    assets.set(`${origin}/${name}/index.html`, {
      type: 'text/html; charset=utf-8', body: await fs.readFile(path.join(root, `tests/render/goldens/${name}.html`)),
    });
    assets.set(`${origin}/${name}/styles.css`, { type: 'text/css; charset=utf-8', body: css });
  }
  const browser = await chromium.launch({ headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
  try {
    const results = [];
    let faviconProbes = 0;
    for (const name of Object.keys(focusOrder)) {
      for (const [width, height] of [[320, 900], [1280, 900], [320, 225]]) {
        for (const fontSize of ['100%', '200%']) {
          phase = `fixture/${name}/${width}x${height}/${fontSize}`;
          const { context, unexpected, faviconProbes: probes } = await fixtureContext(browser, assets);
          try {
            const page = await context.newPage();
            page.setDefaultTimeout(10_000);
            await page.setViewportSize({ width, height });
            await load(page, name);
            await page.evaluate(size => { document.documentElement.style.fontSize = size; }, fontSize);
            let minFocus = Infinity, minFocusedText = Infinity;
            for (const [index, expected] of focusOrder[name].entries()) {
              await page.keyboard.press('Tab');
              const actual = await page.evaluate(() => {
                const element = document.activeElement;
                return element.tagName === 'SUMMARY' ? 'summary' : `a:${element.getAttribute('href')}`;
              });
              assert.equal(actual, expected, 'focus-order');
              let values;
              try { values = await assess(page, 'focus'); }
              catch (error) {
                throw new Error(`${name}/${width}x${height}/${fontSize}/focus-${index + 1}: ${error.message.split('\n')[0]}`);
              }
              minFocus = Math.min(minFocus, values.outlineContrast);
              minFocusedText = Math.min(minFocusedText, values.textContrast);
              if (expected === 'summary') {
                await page.keyboard.press('Space');
                assert.equal(await page.locator('details[open]').count(), 1, 'Disclosure did not open');
                values = await assess(page, 'focus');
                minFocus = Math.min(minFocus, values.outlineContrast);
                minFocusedText = Math.min(minFocusedText, values.textContrast);
              }
            }
            const text = await assess(page, 'text');
            assert.equal(text.count, expectedTextNodes[name], 'Fixture text was not fully enumerated');
            await verifyFocusEnd(page);
            assert.deepEqual(unexpected, [], 'Unexpected fixture request');
            faviconProbes += probes();
            results.push({ fixture: name, width, height, fontSize, focusTargets: focusOrder[name].length,
              textNodes: text.count, minTextContrast: Number(text.minimum.toFixed(2)),
              minFocusedTextContrast: Number(minFocusedText.toFixed(2)), minOutlineContrast: Number(minFocus.toFixed(2)) });
          } finally { await context.close(); }
        }
      }
    }
    const controls = await negativeControls(browser, assets);
    const longSkip = await longSkipControl(browser, assets);
    const classicScrollbar = await classicScrollbarProbe(browser, assets);
    console.log(JSON.stringify({ browser: browser.version(), documentJavaScript: false, contextOffline: true,
      results, negativeControls: controls, longSkip, classicScrollbar, unexpectedRequests: 0, faviconProbes,
      paintedPixels: 'NOT TESTED', realScreenReader: 'NOT TESTED' }, null, 2));
  } finally { await browser.close(); }
}

run().catch(error => {
  const message = String(error && error.message || '');
  const code = [
    'unassessed-focus-containment', 'unexpected-trailing-focus', 'unsupported-viewport-overflow',
    'unsupported-text-fill', 'unsupported-mask', 'focus-outline', 'focus-contrast', 'text-contrast',
    'fixture-stylesheet-missing', 'fixture-stylesheet-token', 'scrollable-viewport-focus',
    'scrollable-viewport-not-settled',
    'scrollable-viewport-no-scroll', 'focus-order',
    'hidden-text', 'clipped-text', 'unsupported-effect', 'unsupported-opacity', 'unmeasurable-text',
  ].find(value => message.includes(value)) || 'check-failed';
  const context = /^(?:digest|corrected|empty)\/\d+x\d+\/(?:100%|200%)\/focus-\d+/.exec(message);
  console.error(`Reader visual check failed [${phase}]: ${context ? context[0] + ': ' : ''}${code}`);
  process.exitCode = 1;
});
