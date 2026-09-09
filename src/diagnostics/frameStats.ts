export interface Distribution { samples: number; mean: number; p95: number; p99: number; max: number; over25ms: number }

export function summarize(values: readonly number[]): Distribution {
  if (!values.length) return { samples: 0, mean: 0, p95: 0, p99: 0, max: 0, over25ms: 0 };
  const ordered = [...values].sort((a, b) => a - b);
  const percentile = (p: number) => ordered[Math.max(0, Math.ceil(p * ordered.length) - 1)] ?? 0;
  return {
    samples: values.length,
    mean: values.reduce((sum, value) => sum + value, 0) / values.length,
    p95: percentile(0.95), p99: percentile(0.99), max: ordered.at(-1) ?? 0,
    over25ms: values.filter(value => value > 25).length,
  };
}

/** Bounded rolling window; no array growth or sorting in the render loop. */
export class FrameStats {
  private readonly intervals = new Float64Array(1800);
  private readonly work = new Float64Array(1800);
  private cursor = 0;
  private count = 0;
  totalFrames = 0;
  totalLongFrames = 0;

  add(intervalMs: number, workMs: number): void {
    if (!Number.isFinite(intervalMs) || !Number.isFinite(workMs) || intervalMs <= 0 || workMs < 0) return;
    this.intervals[this.cursor] = intervalMs;
    this.work[this.cursor] = workMs;
    this.cursor = (this.cursor + 1) % this.intervals.length;
    this.count = Math.min(this.count + 1, this.intervals.length);
    this.totalFrames++;
    if (intervalMs > 25) this.totalLongFrames++;
  }

  snapshot() {
    const intervals = summarize(Array.from(this.intervals.subarray(0, this.count)));
    return { intervals, cpuWork: summarize(Array.from(this.work.subarray(0, this.count))), fps: intervals.mean ? 1000 / intervals.mean : 0, totalFrames: this.totalFrames, totalLongFrames: this.totalLongFrames, windowCapacity: this.intervals.length };
  }
}
