/* Optional developer check: use an externally installed Playwright, not a site dependency. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const url = pathToFileURL(path.join(root, 'web/index.html')).href;
const cssURL = pathToFileURL(path.join(root, 'web/styles.css')).href;

function contrast(first, second) {
  const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(Number).reduce((sum, value, i) => {
    const c = value / 255;
    return sum + (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4) * [0.2126, 0.7152, 0.0722][i];
  }, 0);
  const [high, low] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (high + 0.05) / (low + 0.05);
}

async function check() {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}),
  });
  try {
    const context = await browser.newContext({ javaScriptEnabled: false, reducedMotion: 'reduce' });
    const unexpected = [];
    await context.route('**/*', async route => {
      if ([url, cssURL].includes(route.request().url().split('#')[0])) await route.continue();
      else { unexpected.push(route.request().url()); await route.abort(); }
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10_000);
    page.setDefaultNavigationTimeout(10_000);
    const failures = [];
    page.on('pageerror', error => failures.push(error.message));
    const measurements = [];
    async function reset() {
      await page.goto('about:blank');
      await page.goto(url);
    }
    async function reflow(label) {
      const layout = await page.evaluate(() => ({
        width: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth,
        clipped: [...document.querySelectorAll('body *')].filter(element => {
          const box = element.getBoundingClientRect();
          return box.width && (box.left < -0.5 || box.right > innerWidth + 0.5);
        }).map(element => element.tagName),
      }));
      assert.ok(layout.scroll <= layout.width, `${label}: horizontal overflow`);
      assert.deepEqual(layout.clipped, [], `${label}: clipped element`);
    }
    for (const width of [320, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await reset();
      await reflow(`${width}px`);
      // Automation evaluation remains available; document JavaScript is disabled.
      const ratios = await page.evaluate(() => {
        function rgb(value) { return value.match(/[\d.]+/g).map(Number); }
        function background(element) {
          for (let current = element; current; current = current.parentElement) {
            const color = rgb(getComputedStyle(current).backgroundColor);
            if (color.length === 3 || color[3] === 1) return color;
            if (color[3] !== 0) throw new Error('Unmeasured translucent background');
          }
          throw new Error('No opaque background');
        }
        function luminance(channels) {
          return channels.slice(0, 3).reduce((sum, value, i) => {
            const c = value / 255;
            return sum + (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4) * [0.2126, 0.7152, 0.0722][i];
          }, 0);
        }
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const values = [];
        while (walker.nextNode()) {
          const node = walker.currentNode;
          if (!node.textContent.trim()) continue;
          const element = node.parentElement;
          const rect = element.getBoundingClientRect();
          if (!rect.width || !rect.height || rect.bottom < 0) continue;
          const [high, low] = [luminance(rgb(getComputedStyle(element).color)), luminance(background(element))].sort((a, b) => b - a);
          values.push((high + 0.05) / (low + 0.05));
        }
        return values;
      });
      assert.ok(ratios.length > 15, 'Visible text was not measured');
      assert.ok(Math.min(...ratios) >= 4.5, `${width}px: actual text contrast`);
      if (process.env.SCREENSHOT_DIR) {
        await fs.mkdir(process.env.SCREENSHOT_DIR, { recursive: true });
        await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, `shell-${width}.png`), fullPage: true });
      }
      const links = await page.locator('a').evaluateAll(elements => elements.map(element => element.getAttribute('href')));
      assert.deepEqual(links, ['#main', '#preview', '#about', '#about', '#top']);
      for (let index = 0; index < links.length; index++) {
        await reset();
        for (let tab = 0; tab <= index; tab++) await page.keyboard.press('Tab');
        const focused = await page.evaluate(() => {
          const element = document.activeElement;
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          let adjacent = element.parentElement;
          while (getComputedStyle(adjacent).backgroundColor === 'rgba(0, 0, 0, 0)') adjacent = adjacent.parentElement;
          return { href: element.getAttribute('href'), outline: style.outlineStyle, width: parseFloat(style.outlineWidth),
            color: style.outlineColor, background: getComputedStyle(adjacent).backgroundColor,
            visible: rect.top >= 0 && rect.bottom <= innerHeight && rect.left >= 0 && rect.right <= innerWidth,
            size: [rect.width, rect.height] };
        });
        assert.equal(focused.href, links[index], 'Unexpected keyboard order');
        assert.equal(focused.outline, 'solid');
        assert.ok(focused.width >= 3 && focused.visible, 'Focus must be visible');
        assert.ok(contrast(focused.color, focused.background) >= 3, 'Focus contrast against adjacent surface');
        assert.ok(focused.size.every(size => size >= 44), 'Small touch target');
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(() => document.activeElement.id), links[index].slice(1));
      }
      await reset();
      await page.evaluate(() => {
        for (const selector of ['h1 span', 'h2', 'nav a', 'dt', 'dd', '.site-footer p', '.preview-copy > a']) {
          for (const element of document.querySelectorAll(selector)) element.append(' VeryLongSyntheticPreviewText'.repeat(30));
        }
      });
      await reflow(`${width}px long strings`);
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
      await reflow(`${width}px long strings + 200% text`);
      measurements.push({ width, minTextContrast: Number(Math.min(...ratios).toFixed(2)), keyboardLinks: links.length });
    }
    // 1280 physical pixels at 400% browser zoom has a 320-CSS-pixel reflow width.
    // This is the equivalent layout check, not a claim to control browser chrome zoom.
    await page.setViewportSize({ width: 320, height: 225 });
    await reset();
    await reflow('400% equivalent reflow');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'main');
    assert.deepEqual(unexpected, [], 'Only the local HTML and stylesheet may load');
    assert.deepEqual(failures, []);
    console.log(JSON.stringify({ browser: browser.version(), javaScript: false, measurements, reflow400Equivalent: true, unexpectedRequests: 0 }));
    await context.close();
  } finally {
    await browser.close();
  }
}

check().catch(error => { console.error(error); process.exitCode = 1; });
