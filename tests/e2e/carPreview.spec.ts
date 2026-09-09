import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const report = (page: Page) => page.evaluate(() => window.coastalCarPreview!.snapshot());
async function open(page: Page) {
  await page.goto('./?view=car-v006');
  await page.waitForFunction(() => Boolean(window.coastalCarPreview));
  await expect.poll(async () => (await report(page)).frames.totalFrames).toBeGreaterThan(5);
}

test('accepted v006 renders locally with its geometry, materials and named pivots', async ({ page }, testInfo) => {
  // Four software-rendered screenshots can take >45s in CI; this is an artifact deadline, not an FPS criterion.
  test.setTimeout(90_000);
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  page.on('response', response => { if (response.status() >= 400) errors.push(String(response.status()) + ' ' + response.url()); });
  await open(page);
  const result = await report(page);
  expect(result.model.sha256).toBe('ada35c65b99507aa1f019be017b2c7d0ba3f9e222bc7e496686e13539c7c38dd');
  expect(result.model.triangles).toBe(21114);
  expect(result.model.materialCount).toBe(4);
  expect(result.model.renderMeshes).toBe(16);
  expect(result.model.vertexColorMeshes).toBe(16);
  for (const [axis, value] of [2.254, 1.215, 4.468].entries()) expect(result.model.dimensions[axis]).toBeCloseTo(value, 3);
  expect(result.model.wheels.map(wheel => wheel.name)).toEqual(['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR']);
  expect(result.drawCalls).toBeGreaterThan(0);
  expect(result.canvas.width * result.canvas.height).toBeLessThanOrEqual(1_003_000);
  expect(requests.filter(url => url.endsWith('.glb'))).toHaveLength(2);
  expect(requests.every(url => url.startsWith('http://127.0.0.1:4173/coastal-racer/'))).toBe(true);
  expect(errors).toEqual([]);
  await testInfo.attach('browser-report', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  for (const view of ['game', 'rear', 'front', 'side']) {
    await page.locator('[data-view="' + view + '"]').click();
    await page.screenshot({ path: testInfo.outputPath(view + '.png'), fullPage: false, scale: 'css' });
  }
});

test('color, wheel rotation and collider preserve accepted model structure', async ({ page }) => {
  await open(page);
  const initial = await report(page);
  await page.locator('#car-color').selectOption('#318bea');
  expect((await report(page)).model.colorLinear).not.toEqual(initial.model.colorLinear);
  await page.locator('#car-color').selectOption('original');
  expect((await report(page)).model.colorLinear).toEqual(initial.model.colorLinear);
  await page.locator('#car-wheels').click();
  await expect.poll(async () => (await report(page)).model.wheels[0]!.rotation).not.toEqual(initial.model.wheels[0]!.rotation);
  const rotating = await report(page);
  expect(rotating.model.wheels.map(wheel => wheel.pivot)).toEqual(initial.model.wheels.map(wheel => wheel.pivot));
  await page.locator('#car-collider').click();
  expect((await report(page)).model.colliderVisible).toBe(true);
  for (let i = 0; i < 10; i++) await page.locator('#car-collider').click();
  expect((await report(page)).model.resources).toEqual(initial.model.resources);
  await page.locator('#car-pause').click();
  const paused = await report(page);
  await page.waitForTimeout(200);
  expect((await report(page)).model.wheels).toEqual(paused.model.wheels);
  await page.locator('#car-pause').click();
  await expect.poll(async () => (await report(page)).model.wheels[0]!.rotation).not.toEqual(paused.model.wheels[0]!.rotation);
});

test('preview pauses on visibility events and touch orientation then resizes safely', async ({ page }, testInfo) => {
  await open(page);
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect((await report(page)).paused).toBe(true);
  await page.evaluate(() => {
    delete (document as unknown as { hidden?: boolean }).hidden;
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect((await report(page)).paused).toBe(true);
  await page.locator('#car-pause').click();
  expect((await report(page)).paused).toBe(false);
  if (testInfo.project.name.includes('touch')) {
    await page.setViewportSize({ width: 1180, height: 820 });
    await expect(page.locator('#car-notice')).toContainText('вертикально');
    await page.setViewportSize({ width: 820, height: 1180 });
    await expect(page.locator('#car-pause')).toBeEnabled();
    expect((await report(page)).paused).toBe(true);
    expect((await report(page)).canvas.width * (await report(page)).canvas.height).toBeLessThanOrEqual(1_003_000);
  }
});

test('changed or missing GLB produces a retry screen', async ({ page }) => {
  await page.route('**/cr_sport_01_v006.glb', route => route.fulfill({ status: 200, body: 'invalid asset' }));
  await page.goto('./?view=car-v006');
  await expect(page.getByRole('alert')).toContainText('отличается');
  await expect(page.getByRole('button', { name: 'Повторить' })).toBeVisible();
});
