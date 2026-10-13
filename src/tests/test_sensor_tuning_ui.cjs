/* Run with node --test. Playwright is a development-only dependency. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const staticRoot = path.resolve(__dirname, '../server/static');

function telemetry() {
  const node = {index: 0, frequency: 5658, rssi: 30, enter: 72, exit: 68, inside: false, peak: 40, nadir: 20};
  return {providers: [{name: 'test', label: 'Split test', connected: true, can_capture: true,
    max_rssi: 255, nodes: [node, {...node, index: 1}]}]};
}

async function fixture(t) {
  const options = {headless: true};
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE) options.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  const browser = await chromium.launch(options);
  t.after(() => browser.close());
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, []));
  await page.setContent('<style>.rssi-graph {width:300px;height:160px} canvas {width:100%;height:100%}</style><div id="additional-sensor-tuning"></div>');
  for (const file of ['jquery-3.6.4/jquery-3.6.4.min.js', 'smoothie/smoothie-1.37.js']) {
    await page.addScriptTag({content: fs.readFileSync(path.join(staticRoot, file), 'utf8')});
  }
  const rh = fs.readFileSync(path.join(staticRoot, 'rotorhazard.js'), 'utf8');
  await page.addScriptTag({content: rh.slice(rh.indexOf('function nodeModel()'), rh.indexOf('/* Data model for timer */'))});
  await page.evaluate(() => {
    window.__ = text => text;
    window.svg_asset = {pause: 'Pause', play: 'Play'};
    window.rotorhazard = {nodes: Array(8), seriesStyle: {rssi: {}, crossing: {}}};
    window.models = [];
    const Original = nodeModel;
    window.nodeModel = function () { const model = new Original(); models.push(model); return model; };
    window.pollCallbacks = [];
    window.pendingWrites = [];
    window.pendingRead = null;
    const realTimeout = window.setTimeout;
    window.setTimeout = (callback, delay, ...args) => {
      if (delay === 250) { pollCallbacks.push(callback); return 100000 + pollCallbacks.length; }
      return realTimeout(callback, delay, ...args);
    };
    $.ajax = options => {
      const deferred = $.Deferred();
      const request = deferred.promise();
      request.abort = () => deferred.reject({});
      if (options.method === 'POST') pendingWrites.push({deferred, url: options.url, data: JSON.parse(options.data)});
      else pendingRead = deferred;
      return request;
    };
    window.tick = data => {
      const read = pendingRead;
      pendingRead = null;
      read.resolve(data);
      const next = pollCallbacks.shift();
      if (next) next();
    };
  });
  await page.addScriptTag({content: fs.readFileSync(path.join(staticRoot, 'sensor-tuning.js'), 'utf8')});
  await page.waitForFunction(() => window.pendingRead !== null);
  const data = telemetry();
  await page.evaluate(data => tick(data), data);
  return {page, data};
}

test('additional receivers leave race seats unchanged and show live thresholds', async t => {
  const {page} = await fixture(t);
  assert.equal(await page.locator('[data-sensor-provider="test"] canvas').count(), 2);
  assert.equal(await page.evaluate(() => rotorhazard.nodes.length), 8);
  assert.equal(await page.locator('#sensor-test-0-enter').inputValue(), '72');
});

test('removed nodes and providers stop their graphs and remove their controls', async t => {
  const {page, data} = await fixture(t);
  data.providers[0].nodes.pop();
  await page.evaluate(data => tick(data), data);
  assert.equal(await page.locator('#sensor-test-1-enter').count(), 0);
  assert.equal(await page.evaluate(() => Boolean(models[1].graph.frame)), false);
  await page.evaluate(() => tick({providers: []}));
  assert.equal(await page.locator('[data-sensor-provider]').count(), 0);
  assert.equal(await page.evaluate(() => Boolean(models[0].graph.frame)), false);
});

test('paused RSSI and crossing histories stay bounded while telemetry continues', async t => {
  const {page, data} = await fixture(t);
  const card = page.locator('.node').filter({has: page.locator('#sensor-test-0-enter')});
  await card.locator('.rssi-graph button').click();
  const state = await page.evaluate(data => {
    let clock = Date.now();
    const originalNow = Date.now;
    Date.now = () => clock;
    for (let i = 0; i < 1200; i++) { clock += 250; tick(data); }
    Date.now = originalNow;
    return {paused: models[0].graphPaused, rssi: models[0].series.data.length,
      crossing: models[0].crossingSeries.data.length, frozen: models[0].pauseSeries.data.length};
  }, data);
  assert(state.paused);
  assert(state.rssi <= 242, JSON.stringify(state));
  assert(state.crossing <= 242, JSON.stringify(state));
  assert(state.frozen < state.rssi);
  await card.locator('.rssi-graph button').click();
  assert.equal(await page.evaluate(() => models[0].graphPaused), false);
});

test('capture calls the receiver callback instead of saving one cached reading', async t => {
  const {page} = await fixture(t);
  const card = page.locator('.node').filter({has: page.locator('#sensor-test-0-enter')});
  const buttons = card.locator('.sensor-capture');
  assert.equal(await buttons.count(), 2);
  await buttons.nth(0).click();
  assert.equal(await page.locator('#sensor-test-0-enter').isDisabled(), true);
  const request = await page.evaluate(() => {
    const pending = pendingWrites.shift();
    const info = {url: pending.url, data: pending.data};
    pending.deferred.resolve({ok: true, enter: 80, exit: 68});
    return info;
  });
  assert.deepEqual(request, {url: '/sensor-tuning/test/0/capture', data: {level: 'enter'}});
  assert.equal(await page.locator('#sensor-test-0-enter').inputValue(), '80');
});

test('failed saves restore confirmed levels and show an error', async t => {
  const {page} = await fixture(t);
  const enter = page.locator('#sensor-test-0-enter');
  await enter.fill('75');
  await enter.dispatchEvent('change');
  await page.evaluate(() => { pendingWrites.shift().deferred.reject({responseJSON: {message: 'Write failed'}}); });
  assert.equal(await enter.inputValue(), '72');
  assert.equal(await page.evaluate(() => models[0].enter_at_level), 72);
  assert.equal(await page.getByText('Write failed', {exact: true}).count(), 1);
});

test('a poll started before a save cannot overwrite the acknowledged levels', async t => {
  const {page, data} = await fixture(t);
  const enter = page.locator('#sensor-test-0-enter');
  await enter.fill('75');
  await enter.dispatchEvent('change');
  await page.evaluate(() => pendingWrites.shift().deferred.resolve({ok: true, enter: 75, exit: 68}));
  await page.evaluate(data => tick(data), data);
  assert.equal(await enter.inputValue(), '75');
  data.providers[0].nodes[0].enter = 75;
  await page.evaluate(data => tick(data), data);
  assert.equal(await enter.inputValue(), '75');
});

test('receivers without capture support hide Capture and back-forward restoration resumes polling', async t => {
  const {page, data} = await fixture(t);
  data.providers[0].can_capture = false;
  await page.evaluate(data => tick(data), data);
  assert.equal(await page.locator('.sensor-capture:visible').count(), 0);
  await page.evaluate(() => {
    window.dispatchEvent(new Event('pagehide'));
    window.pendingRead = null;
    window.dispatchEvent(new Event('pageshow'));
  });
  assert.equal(await page.evaluate(() => pendingRead !== null), true);
  await page.evaluate(data => tick(data), data);
  assert.equal(await page.locator('#sensor-test-0-enter').isDisabled(), false);
});
