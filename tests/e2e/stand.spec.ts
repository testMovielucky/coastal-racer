import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const snapshot = (page: Page) => page.evaluate(() => window.coastalDiagnostics!.snapshot());
async function ready(page: Page) {
  await page.goto('./');
  await expect(page.locator('#status')).toHaveText('СТЕНД АКТИВЕН');
  await expect.poll(async () => (await snapshot(page)).physics.ticks).toBeGreaterThan(10);
}

test('production build runs under a repository path with local WASM and no external requests', async ({ page }, testInfo) => {
  const errors: string[] = [];
  const urls: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => urls.push(request.url()));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await ready(page);
  await expect.poll(async () => (await snapshot(page)).resources.drawCalls).toBeGreaterThan(0);
  const report = await snapshot(page);
  expect(report.resources.dynamicBodies).toBe(6);
  expect(report.resources.bodies).toBe(11);
  expect(report.renderer.api).toBe('WebGL2');
  const layout = await page.evaluate(() => {
    const bounds = document.querySelector('.viewport')!.getBoundingClientRect();
    return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, windowWidth: innerWidth, windowHeight: innerHeight };
  });
  if (testInfo.project.name.includes('touch')) {
    expect(layout.x).toBe(0);
    expect(layout.y).toBe(0);
    expect(layout.width).toBe(layout.windowWidth);
    expect(layout.height).toBe(layout.windowHeight);
    expect(report.canvas.width * report.canvas.height).toBeLessThanOrEqual(1_003_000);
  } else {
    expect(layout.width).toBeLessThanOrEqual(460);
  }
  expect(urls.some(url => url.endsWith('.wasm'))).toBe(true);
  expect(urls.every(url => url.startsWith('http://127.0.0.1:4173/coastal-racer/'))).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('stand.png'), fullPage: false });
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Отчёт JSON' }).click();
  const download = await downloadPromise;
  await download.saveAs(testInfo.outputPath('diagnostics.json'));
  expect(download.suggestedFilename()).toMatch(/^coastal-stage0-.*\.json$/);
});

test('pause freezes bodies and time; resume has no catch-up jump', async ({ page }) => {
  await ready(page);
  await page.getByRole('button', { name: 'Тестовый толчок' }).click();
  await page.getByRole('button', { name: 'Пауза', exact: true }).click();
  const before = await snapshot(page);
  await page.waitForTimeout(350);
  const after = await snapshot(page);
  expect(after.physics.ticks).toBe(before.physics.ticks);
  expect(after.bodies).toEqual(before.bodies);
  await page.getByRole('button', { name: 'Продолжить' }).click();
  await expect.poll(async () => (await snapshot(page)).physics.ticks).toBeGreaterThan(before.physics.ticks);
  expect((await snapshot(page)).physics.ticks - before.physics.ticks).toBeLessThan(20);
});

test('twenty resets retain resource and handler counts', async ({ page }) => {
  await ready(page);
  const baseline = (await snapshot(page)).resources;
  for (let i = 0; i < 20; i++) await page.getByRole('button', { name: 'Перезапустить стенд' }).click();
  const report = await snapshot(page);
  expect(report.restarts).toBe(20);
  for (const key of ['meshes', 'bodies', 'materials', 'textures', 'scenes', 'domListeners', 'resizeObservers', 'observers'] as const) expect(report.resources[key]).toBe(baseline[key]);
  expect(report.resources.scenes).toBe(1);
});

test('focus loss requires explicit resume', async ({ page }) => {
  await ready(page);
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await expect(page.getByRole('button', { name: 'Продолжить' })).toBeVisible();
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  expect((await snapshot(page)).paused).toBe(true);
});

test('touch landscape pauses, portrait resize preserves bounded canvas resolution', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('touch'), 'Touch device orientation only');
  await ready(page);
  await page.setViewportSize({ width: 844, height: 390 });
  await expect(page.getByRole('heading', { name: 'Поверните устройство' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Продолжить' })).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('button', { name: 'Продолжить' })).toBeEnabled();
  expect((await snapshot(page)).paused).toBe(true);
  await page.getByRole('button', { name: 'Продолжить' }).click();
  const report = await snapshot(page);
  expect(report.canvas.width * report.canvas.height).toBeLessThanOrEqual(1_003_000);
});

test('WASM failure gives a retry screen', async ({ page }) => {
  await page.route('**/*.wasm', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('./');
  await expect(page.getByRole('alert')).toContainText('503');
  await expect(page.getByRole('button', { name: 'Повторить' })).toBeVisible();
});
