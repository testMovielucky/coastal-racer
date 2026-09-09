import { defineConfig } from 'vitest/config';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const { version } = JSON.parse(readFileSync('./package.json', 'utf8')) as { version: string };
let revision = 'local';
try { revision = execFileSync('git', ['-c', `safe.directory=${process.cwd()}`, 'rev-parse', '--short', 'HEAD'], { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* Uncommitted project. */ }

export default defineConfig({
  base: './',
  define: {
    __BUILD__: JSON.stringify({ version, revision: process.env.GITHUB_SHA?.slice(0, 7) ?? revision, builtAt: new Date().toISOString() }),
  },
  build: { target: 'es2022', assetsInlineLimit: 0 },
  test: { include: ['tests/unit/**/*.test.ts', 'tests/integration/**/*.test.ts'] },
});
