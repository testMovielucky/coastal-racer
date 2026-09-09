import { describe, expect, it } from 'vitest';
import { FixedStep } from '../../src/game/core/fixedStep';

describe('simulation clock', () => {
  it('advances equally at 30, 60 and 120 Hz', () => {
    for (const hz of [30, 60, 120]) {
      const clock = new FixedStep();
      let time = 0;
      for (let i = 0; i < hz * 10; i++) clock.advance(1 / hz, delta => { time += delta; });
      expect(clock.ticks).toBe(600);
      expect(time).toBeCloseTo(10);
    }
  });
  it('caps catch-up and discards background time', () => {
    const clock = new FixedStep();
    clock.advance(60, () => {});
    expect(clock.ticks).toBe(4);
    expect(clock.droppedSeconds).toBeCloseTo(60 - 4 / 60);
    clock.reset();
    expect(clock.advance(0, () => {})).toBe(0);
  });
  it('clears partial time on pause and rejects invalid deltas', () => {
    const clock = new FixedStep();
    clock.advance(1 / 120, () => {});
    clock.reset();
    clock.advance(1 / 120, () => {});
    for (const delta of [-1, NaN, Infinity]) clock.advance(delta, () => {});
    expect(clock.ticks).toBe(0);
  });
});
