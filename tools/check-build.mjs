import { readdir, readFile, stat, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { gzipSync } from 'node:zlib';

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  return (await Promise.all(entries.map(entry => entry.isDirectory() ? walk(join(dir, entry.name)) : join(dir, entry.name)))).flat();
}
await mkdir('dist/licenses', { recursive: true });
await copyFile('node_modules/@babylonjs/core/license.md', 'dist/licenses/Babylon.txt');
await copyFile('node_modules/@babylonjs/havok/LICENSE', 'dist/licenses/Havok.txt');
const files = await walk('dist');
const wasmFiles = files.filter(file => file.endsWith('.wasm'));
if (wasmFiles.length !== 1) throw new Error(`Expected one bundled WASM, found ${wasmFiles.length}`);
const wasm = await readFile(wasmFiles[0]);
if (wasm.subarray(0, 4).toString('hex') !== '0061736d') throw new Error('Invalid WASM header');
const html = await readFile('dist/index.html', 'utf8');
for (const [, url] of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
  if (!url.startsWith('./')) throw new Error(`Non-relative entry resource: ${url}`);
}
if (files.some(file => /\.(blend|py|map)$/.test(file))) throw new Error('Source-only assets in dist');
const sizes = await Promise.all(files.map(async file => ({ file: relative('dist', file).replaceAll('\\', '/'), bytes: (await stat(file)).size, gzipBytes: gzipSync(await readFile(file)).length })));
const report = { files: sizes, rawBytes: sizes.reduce((sum, file) => sum + file.bytes, 0), gzipEstimateBytes: sizes.reduce((sum, file) => sum + file.gzipBytes, 0), note: 'gzip estimate is not a measured GitHub Pages transfer size' };
await writeFile('dist/build-report.json', JSON.stringify(report, null, 2));
console.log(`Build verified: local WASM, relative entry URLs. Raw ${(report.rawBytes / 1e6).toFixed(2)} MB; gzip estimate ${(report.gzipEstimateBytes / 1e6).toFixed(2)} MB.`);
