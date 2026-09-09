import { expect, it } from 'vitest';
import { FrameStats, summarize } from '../../src/diagnostics/frameStats';

it('reports nearest-rank percentiles and actual long-frame counts', () => {
  const values = Array.from({ length: 100 }, (_, i) => i + 1);
  expect(summarize(values)).toEqual({ samples: 100, mean: 50.5, p95: 95, p99: 99, max: 100, over25ms: 75 });
  expect(summarize([]).samples).toBe(0);
});
it('bounds memory while retaining lifetime counters and separate work timings', () => {
  const stats = new FrameStats();
  for (let i = 0; i < 2000; i++) stats.add(1000 / 60, 2);
  stats.add(40, 8);
  const report = stats.snapshot();
  expect(report.intervals.samples).toBe(1800);
  expect(report.totalFrames).toBe(2001);
  expect(report.totalLongFrames).toBe(1);
  expect(report.cpuWork.p95).toBe(2);
  expect(report.fps).toBeLessThan(60);
});
