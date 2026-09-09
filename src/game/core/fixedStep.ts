/** Wall time is bounded: background time is discarded, never replayed. */
export class FixedStep {
  readonly seconds = 1 / 60;
  private accumulator = 0;
  droppedSeconds = 0;
  ticks = 0;

  advance(elapsedSeconds: number, step: (seconds: number) => void): number {
    if (!Number.isFinite(elapsedSeconds) || elapsedSeconds <= 0) return this.accumulator / this.seconds;
    const accepted = Math.min(elapsedSeconds, this.seconds * 4);
    this.droppedSeconds += elapsedSeconds - accepted;
    this.accumulator += accepted;
    let count = 0;
    while (this.accumulator + 1e-10 >= this.seconds && count < 4) {
      step(this.seconds);
      this.accumulator = Math.max(0, this.accumulator - this.seconds);
      this.ticks++;
      count++;
    }
    return this.accumulator / this.seconds;
  }

  reset(): void { this.accumulator = 0; }
}
