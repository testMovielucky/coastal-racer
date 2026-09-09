import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  expect: { timeout: 15_000 },
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173/coastal-racer/',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: { args: ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
    channel: process.env.CI ? undefined : 'chrome',
  },
  projects: [
    { name: 'desktop-chromium', use: { viewport: { width: 1280, height: 1000 } } },
    { name: 'portrait-touch-chromium', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: { command: 'node tools/serve-dist.mjs', url: 'http://127.0.0.1:4173/coastal-racer/', reuseExistingServer: !process.env.CI, timeout: 30_000 },
});
