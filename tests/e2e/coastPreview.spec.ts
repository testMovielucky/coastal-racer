import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import layout from '../../public/assets/themes/coast/sample-v006/sample_layout.json' with { type: 'json' };

const report = (page: Page) => page.evaluate(() => window.coastalCoastPreview!.snapshot());
async function open(page: Page) {
  await page.goto('./?view=coast-v006');
  await page.waitForFunction(() => Boolean(window.coastalCoastPreview));
  await expect.poll(async () => (await report(page)).frames.totalFrames).toBeGreaterThan(3);
}
test('coast imports the original 40m layout and frames the accepted car in portrait', async ({ page }, testInfo) => {
  test.setTimeout(90_000); // Software-rendered captures are artifacts, not device FPS measurements.
  const errors: string[] = [], requests: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => requests.push(r.url()));
  page.on('response', r => { if (r.status() >= 400) errors.push(r.status() + ' ' + r.url()); });
  await open(page);
  const data = await report(page);
  expect(data.coast.lengthMetres).toBe(40);
  expect(data.coast.seed).toBe(909061);
  expect(data.coast.placementCount).toBe(76);
  expect(data.coast.moduleCount).toBe(14);
  expect(data.coast.environmentTriangles).toBe(48216);
  expect(data.coast.carTriangles).toBe(21114);
  expect(data.coast.carSha256).toBe(layout.review_car.sha256);
  expect(data.coast.physicsEnabled).toBe(false);
  for (const [i, entry] of layout.placements.entries()) {
    const actual = data.coast.placements[i]!;
    const [x,y,z] = entry.position_blender_m;
    expect(actual.position).toEqual([x,z,-y!]);
    expect(actual.scale).toBe(entry.uniform_scale);
    expect(actual.rotation[1]).toBeCloseTo(Math.sin(entry.rotation_z_radians / 2), 6);
    expect(actual.rotation[3]).toBeCloseTo(Math.cos(entry.rotation_z_radians / 2), 6);
  }
  // Assert all eight bounds corners, including the rear bumper, inside the actual canvas.
  for (const [x,y,z] of data.coast.carProjectedBounds) {
    expect(x).toBeGreaterThan(.02); expect(x).toBeLessThan(.98);
    expect(y).toBeGreaterThan(.02); expect(y).toBeLessThan(.98);
    expect(z).toBeGreaterThan(0); expect(z).toBeLessThan(1);
  }
  expect(data.canvas.width * data.canvas.height).toBeLessThanOrEqual(1_003_000);
  expect(data.drawCalls).toBeGreaterThan(0);
  expect(requests.filter(url => url.endsWith('.glb'))).toHaveLength(15);
  expect(requests.some(url => url.endsWith('.wasm'))).toBe(false);
  const appOrigin = new URL(page.url()).origin;
  expect(requests.filter(url => !url.startsWith('http://127.0.0.1:4173/coastal-racer/') && !url.startsWith('blob:' + appOrigin + '/'))).toEqual([]);
  expect(errors).toEqual([]);
  await testInfo.attach('coast-report', { body: JSON.stringify(data, null, 2), contentType: 'application/json' });
  await page.screenshot({ path: testInfo.outputPath('game.png'), scale: 'css' });
  const resources = data.coast.resources;
  for (const view of ['reference', 'overview', 'detail', 'game']) await page.locator('[data-view="'+view+'"]').click();
  expect((await report(page)).coast.resources).toEqual(resources);
  expect((await report(page)).coast.view).toBe('game');
});

test('coast handles pause, visibility, orientation, resize and disposal', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await open(page);
  await page.locator('#coast-pause').click();
  const frames = (await report(page)).frames.totalFrames;
  await page.waitForTimeout(200);
  expect((await report(page)).frames.totalFrames).toBe(frames);
  await page.locator('#coast-pause').click();
  await expect.poll(async () => (await report(page)).frames.totalFrames).toBeGreaterThan(frames);
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
  await page.locator('#coast-pause').click();
  if (testInfo.project.name.includes('touch')) {
    await page.setViewportSize({ width: 1180, height: 820 });
    await expect(page.locator('#coast-notice')).toContainText('вертикально');
    await page.setViewportSize({ width: 820, height: 1180 });
    await expect(page.locator('#coast-pause')).toBeEnabled();
    expect((await report(page)).paused).toBe(true);
    await page.locator('#coast-pause').click();
  } else {
    await page.setViewportSize({width:1000,height:1100});
  }
  expect((await report(page)).canvas.width * (await report(page)).canvas.height).toBeLessThanOrEqual(1_003_000);
  await page.evaluate(() => window.addEventListener('coast-preview-disposed', e => {
    document.documentElement.dataset.coastDisposed = JSON.stringify((e as CustomEvent).detail);
  }, {once:true}));
  await page.locator('#coast-close').click();
  await expect(page.getByRole('heading', {name:'Просмотр закрыт'})).toBeVisible();
  expect(await page.evaluate(() => window.coastalCoastPreview === undefined)).toBe(true);
  expect(await page.evaluate(() => JSON.parse(document.documentElement.dataset.coastDisposed!))).toEqual({sceneDisposed:true, meshes:0, textures:0, renderLoops:0});
  await expect(page.locator('#coast-canvas')).toHaveCount(0);
});

test('coast rejects changed layout bytes and offers retry', async ({page}) => {
  await page.route('**/sample_layout.json', route => route.fulfill({status:200,body:'{}'}));
  await page.goto('./?view=coast-v006');
  await expect(page.getByRole('alert')).toContainText('отличается');
  await expect(page.getByRole('button',{name:'Повторить'})).toBeVisible();
});
