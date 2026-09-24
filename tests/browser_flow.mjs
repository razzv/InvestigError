import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from 'playwright';

const root = resolve(import.meta.dirname, '..');
const port = await new Promise((resolvePort, reject) => {
  const server = net.createServer();
  server.once('error', reject);
  server.listen(0, '127.0.0.1', () => {
    const address = server.address();
    server.close(() => resolvePort(address.port));
  });
});
const base = `http://127.0.0.1:${port}`;
const python = resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const server = spawn(python, ['tests/browser_mock_server.py'], {
  cwd: root, env: { ...process.env, INV_BROWSER_TEST_PORT: String(port) }, stdio: 'pipe',
});
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(`Mock server exited ${server.exitCode}`);
    try { ready = (await fetch(`${base}/health`)).ok; } catch { /* starting */ }
    if (ready) break;
    await delay(50);
  }
  assert(ready, 'Mock server did not start');
  browser = await chromium.launch({ channel: process.env.INV_BROWSER_CHANNEL || 'chrome', headless: true });
  const page = await browser.newPage({ acceptDownloads: true });
  await page.goto(base);
  await page.locator('#example').selectOption('example-001');
  await page.getByRole('button', { name: 'Validate & preview' }).click();
  await assertVisible(page, '#coverage', 'selected');
  assert.equal(await page.locator('#consent').isChecked(), false);
  assert.equal(await page.locator('#explain').isDisabled(), true);
  await page.getByRole('button', { name: 'Run rules' }).click();
  await assertVisible(page, '#ai', 'AI is off');
  await assertVisible(page, '#findings', 'Next check:');
  await page.locator('#findings .evidence-link').first().click();
  assert.match(await page.locator('#evidence').innerText(), /"id":/);
  assert.equal(await page.locator('.timeline-item.selected').count(), 1);
  await page.locator('#consent').check();
  await page.getByRole('button', { name: 'Request AI explanation' }).click();
  await assertVisible(page, '#ai', 'Missing worker trace M-17.');
  await assertVisible(page, '#ai', 'Reasoning needs a missing trace.');
  await assertVisible(page, '#ai', 'Missing retry log A-2.');
  await assertVisible(page, '#ai', 'AI limitation L-9: capture is partial.');
  await assertVisible(page, '#ai', 'No evidence cited.');
  await assertVisible(page, '#ai', '<img src=x onerror=alert(1)>');
  assert.equal(await page.locator('#ai img').count(), 0);
  assert.equal(await page.locator('#consent').isChecked(), false);
  const jsonDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download JSON' }).click();
  assert.match((await jsonDownload).suggestedFilename(), /\.json$/);
  const markdownDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download Markdown' }).click();
  assert.match((await markdownDownload).suggestedFilename(), /\.md$/);
  await page.locator('#upload').setInputFiles(resolve(root, 'examples/incidents/example-001.json'));
  assert.equal(await page.locator('#explain').isDisabled(), true);
  await page.getByRole('button', { name: 'Validate & preview' }).click();
  await assertVisible(page, '#sanitized', 'incident_id');
  await page.locator('#example').selectOption('example-001-jsonl');
  await page.getByRole('button', { name: 'Run rules' }).click();
  await assertVisible(page, '#findings', 'R3');
  await page.locator('#upload').setInputFiles({ name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{}') });
  await page.getByRole('button', { name: 'Validate & preview' }).click();
  await assertVisible(page, '#error', 'schema_version');
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.locator('.layout').evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(' ').length), 1);
  console.log('Browser flow passed: preview, consent, rules, evidence, mocked AI, exports, upload, JSONL, error, mobile layout.');
} finally {
  await browser?.close();
  server.kill();
}

async function assertVisible(page, selector, text) {
  await page.locator(selector).getByText(text, { exact: false }).first().waitFor({ state: 'visible' });
}
