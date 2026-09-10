import { defineConfig } from 'vitest/config';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import car from './config/car-v006.json' with { type: 'json' };
import coast from './config/coast-v006.json' with { type: 'json' };

const { version } = JSON.parse(readFileSync('./package.json', 'utf8')) as { version: string };
let revision = 'local';
try { revision = execFileSync('git', ['-c', `safe.directory=${process.cwd()}`, 'rev-parse', '--short', 'HEAD'], { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* Uncommitted project. */ }

export default defineConfig({
  base: './',
  define: {
    __BUILD__: JSON.stringify({ version, revision: process.env.GITHUB_SHA?.slice(0, 7) ?? revision, builtAt: new Date().toISOString() }),
  },
  plugins: [{
    name: 'selected-runtime-assets',
    generateBundle() {
      for (const file of [car.model, car.collider, coast.layout, ...coast.assets]) this.emitFile({ type: 'asset', fileName: file.path, source: readFileSync('public/' + file.path) });
    },
  }],
  build: { target: 'es2022', assetsInlineLimit: 0, copyPublicDir: false },
  test: { include: ['tests/unit/**/*.test.ts', 'tests/integration/**/*.test.ts'] },
});
