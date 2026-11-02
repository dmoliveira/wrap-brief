/* External Playwright required. No page scripts, external services or persistent browser profile. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

function cls(events) {
  let maximum = 0, sum = 0, start = 0, last = 0;
  for (const event of events.filter(e => !e.layoutShiftDetails.hadRecentInput).sort((a,b) => a.time-b.time)) {
    if (event.time-last >= 1 || event.time-start > 5) { sum=0; start=event.time; }
    sum += event.layoutShiftDetails.value;
    last=event.time; maximum=Math.max(maximum,sum);
  }
  return maximum;
}

async function main() {
  const root = path.resolve(__dirname, '../..');
  const assets = new Map();
  for (const fixture of ['digest','corrected','empty']) {
    for (const name of ['index.html','styles.css']) {
      assets.set(`/${fixture}/${name}`, await fs.readFile(path.join(root, '.local/fixture-sites', fixture, name)));
    }
    assert.deepEqual(assets.get(`/${fixture}/styles.css`),await fs.readFile(path.join(root,'web/styles.css')),'Stale fixture stylesheet');
    assert.deepEqual(assets.get(`/${fixture}/index.html`),await fs.readFile(path.join(root,`tests/render/goldens/${fixture}.html`)),'Fixture differs from checked golden HTML; run make validate and rebuild fresh fixtures');
  }
  const unexpected=[];
  let faviconProbes=0;
  const server=http.createServer((request,response) => {
    // Browser chrome may probe a favicon even though the fixture declares no icon.
    if (request.url === '/favicon.ico' && request.method === 'GET') { faviconProbes++; response.writeHead(204); response.end(); return; }
    const asset=assets.get(request.url);
    if (!asset || request.method !== 'GET') { unexpected.push(request.url); response.writeHead(404); response.end(); return; }
    response.writeHead(200, {'Content-Type': request.url.endsWith('.css') ? 'text/css' : 'text/html; charset=utf-8', 'Cache-Control':'no-store'});
    response.end(asset);
  });
  let browser;
  try {
    await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
    const origin=`http://127.0.0.1:${server.address().port}`;
    browser=await chromium.launch({ headless:true, ...(process.env.BROWSER_EXECUTABLE ? {executablePath:process.env.BROWSER_EXECUTABLE} : {}) });
    const functional=[];
    for (const fixture of ['digest','corrected','empty']) {
      const context=await browser.newContext({javaScriptEnabled:false,serviceWorkers:'block',reducedMotion:'reduce'});
      try {
        await context.route('**/*',route => {
          const url=new URL(route.request().url());
          if (url.origin === origin && assets.has(url.pathname)) return route.continue();
          unexpected.push(url.href); return route.abort();
        });
        const page=await context.newPage(); page.setDefaultTimeout(10000);
        for (const [width,height] of [[320,900],[1280,900],[320,225]]) {
          await page.setViewportSize({width,height});
          await page.goto(`${origin}/${fixture}/index.html`);
          await page.evaluate(() => document.querySelectorAll('details').forEach(e => {e.open=true;}));
          for (const fontSize of ['100%','200%']) {
            await page.evaluate(size => {document.documentElement.style.fontSize=size;},fontSize);
            const state=await page.evaluate(() => ({
              noOverflow:document.documentElement.scrollWidth<=innerWidth,
              reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,
              motion:[...document.querySelectorAll('body *')].some(e => {
                const style=getComputedStyle(e);
                return style.animationName !== 'none' || style.transitionDuration.split(',').some(t => parseFloat(t)!==0);
              }),
            }));
            assert.ok(state.noOverflow,`${fixture}/${width}/${fontSize}: overflow`);
            assert.ok(state.reduced && !state.motion,'Reduced motion');
          }
          functional.push({fixture,width,height,expandedReflow:true,text200:true,reducedMotion:true});
        }
      } finally {await context.close();}
    }
    const runs=[];
    for (let run=0;run<3;run++) {
      const context=await browser.newContext({javaScriptEnabled:false,serviceWorkers:'block',viewport:{width:375,height:812},deviceScaleFactor:1,isMobile:true,hasTouch:true});
      try {
        await context.route('**/*',route => {
          const url=new URL(route.request().url());
          if(url.origin===origin && (assets.has(url.pathname)||url.pathname==='/favicon.ico'))return route.continue();
          unexpected.push(url.href);return route.abort();
        });
        const page=await context.newPage(); page.setDefaultNavigationTimeout(15000);
        const session=await context.newCDPSession(page);
        await session.send('Network.enable'); await session.send('Network.setCacheDisabled',{cacheDisabled:true});
        await session.send('Network.emulateNetworkConditions',{offline:false,latency:150,downloadThroughput:1600000/8,uploadThroughput:750000/8});
        await session.send('Emulation.setCPUThrottlingRate',{rate:4});
        await session.send('Performance.enable');
        const lcp=[], shifts=[]; let clock, frame;
        session.on('Network.requestWillBeSent',event => {
          if(event.type==='Document' && event.request.url===`${origin}/digest/index.html`) {clock=event.wallTime-event.timestamp;frame=event.frameId;}
        });
        session.on('PerformanceTimeline.timelineEventAdded',({event}) => {
          if(event.frameId!==frame)return;
          if(event.type==='largest-contentful-paint')lcp.push(event);
          if(event.type==='layout-shift')shifts.push(event);
        });
        await session.send('PerformanceTimeline.enable',{eventTypes:['largest-contentful-paint','layout-shift']});
        await page.goto(`${origin}/digest/index.html`,{waitUntil:'load'});
        // Explicit bounded observation window; no interaction before paint metrics finish.
        await page.waitForTimeout(2000);
        const {metrics}=await session.send('Performance.getMetrics');
        const navigation=metrics.find(metric=>metric.name==='NavigationStart')?.value;
        const paint=lcp.at(-1)?.lcpDetails?.renderTime;
        assert.ok(Number.isFinite(clock) && Number.isFinite(navigation) && Number.isFinite(paint),'Missing clock/navigation/LCP candidate');
        const lcpMs=(paint-clock-navigation)*1000;
        assert.ok(Number.isFinite(lcpMs) && lcpMs>0,'Invalid measured LCP');
        const clsValue=cls(shifts);
        assert.ok(lcpMs<=2500,`LCP ${lcpMs}ms exceeds 2500ms`);
        assert.ok(clsValue<=0.1,`CLS ${clsValue} exceeds 0.1`);
        runs.push({run:run+1,lcpMs:Number(lcpMs.toFixed(2)),cls:clsValue,lcpCandidates:lcp.length,layoutShiftEvents:shifts.length});
      } finally {await context.close();}
    }
    assert.deepEqual(unexpected,[],'Unexpected requests');
    console.log(JSON.stringify({browser:browser.version(),documentJavaScript:false,functional,runs,faviconProbes,profile:{viewport:'375x812',cpuSlowdown:4,latencyMs:150,downloadBitsPerSecond:1600000,uploadBitsPerSecond:750000,observationAfterLoadMs:2000,coldContexts:true},realScreenReader:'NOT TESTED'},null,2));
  } finally { if(browser)await browser.close(); await new Promise(resolve=>server.close(resolve)); }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
