import { Engine } from '@babylonjs/core/Engines/engine';
import { SceneInstrumentation } from '@babylonjs/core/Instrumentation/sceneInstrumentation';
import { loadHavok } from '../game/physics/havok';
import { createTestWorld } from '../game/physics/testWorld';
import { FixedStep } from '../game/core/fixedStep';
import { FrameStats } from '../diagnostics/frameStats';

export type StandReport = ReturnType<Stand['snapshot']>;

export class Stand {
  private world: ReturnType<typeof createTestWorld>;
  private instrumentation: SceneInstrumentation;
  private clock = new FixedStep();
  private stats = new FrameStats();
  private abort = new AbortController();
  private resizeObserver: ResizeObserver;
  private reasons = new Set<string>();
  private lastFrame: number | undefined;
  private lastUi = 0;
  private disposed = false;
  private dirty = true;
  private restarts = 0;
  private preparationMs = 0;
  private contextLost = false;
  private ready = false;
  private listenCount = 0;

  static async create(root: HTMLElement) {
    const started = performance.now();
    const runtime = await loadHavok();
    root.innerHTML = `
      <main class="shell">
        <section class="viewport" aria-label="Техническая 3D-сцена">
          <canvas id="scene" aria-label="Дорога и шесть физических кузовов"></canvas>
          <header class="masthead"><div><p class="eyebrow">COASTAL RACER <span> / 00</span></p><h1>Испытательный стенд</h1></div><span class="status" id="status">Загрузка</span></header>
          <div class="scene-caption"><span class="marker"></span> ПОБЕРЕЖЬЕ · ФИКСИРОВАННЫЙ УЧАСТОК</div>
          <div class="overlay" id="overlay" hidden><span class="eyebrow">СИМУЛЯЦИЯ ПРИОСТАНОВЛЕНА</span><h2 id="pause-title">Пауза</h2><p id="pause-copy">Продолжите, когда будете готовы.</p><button id="resume">Продолжить</button></div>
          <section class="dashboard" aria-label="Диагностика">
            <div class="panel-heading"><span>ДИАГНОСТИКА</span><span id="build"></span></div>
            <div class="metrics"><div><strong id="fps">—</strong><span>кадров/с</span></div><div><strong id="work">—</strong><span>CPU p95, мс</span></div><div><strong id="bodies">6</strong><span>кузовов</span></div></div>
            <dl class="details"><div><dt>Кадр p95 / p99</dt><dd id="frames">—</dd></div><div><dt>Меши / тела / draw calls</dt><dd id="resources">—</dd></div><div><dt>Canvas / физика</dt><dd id="resolution">—</dd></div></dl>
            <div class="controls"><button id="impulse" class="primary">Тестовый толчок</button><button id="pause">Пауза</button><button id="restart" aria-label="Перезапустить стенд">Сброс</button></div>
            <div class="panel-footer"><span>WebGL2 + Havok · <span id="ticks">0</span> шагов</span><button id="export" class="text-button">Отчёт JSON ↗</button></div>
          </section>
        </section>
        <a class="car-link" href="?view=car-v006">Посмотреть машину v006 →</a>
        <p class="disclaimer">Этап 0 · Технические кузова, не финальные модели. Управление гонкой появится позже.<br>Показатели этого браузера не подтверждают 60 FPS на iPhone или iPad.</p>
      </main>`;
    const canvas = root.querySelector<HTMLCanvasElement>('#scene')!;
    const engine = new Engine(canvas, true, { preserveDrawingBuffer: false, stencil: false, disableWebGL2Support: false, powerPreference: 'high-performance' }, false);
    if (engine.webGLVersion !== 2) { engine.dispose(); throw new Error('Для стенда требуется WebGL2. Попробуйте актуальный браузер с включённым аппаратным ускорением.'); }
    try {
      const stand = new Stand(root, canvas, engine, runtime);
      try {
        await stand.world.scene.whenReadyAsync();
        stand.preparationMs = performance.now() - started;

        window.coastalDiagnostics = { snapshot: () => stand.snapshot() };
        stand.ready = true;
        stand.updateUi();
        stand.engine.runRenderLoop(stand.render);
        return stand;
      } catch (error) { stand.dispose(); throw error; }
    } catch (error) { engine.dispose(); throw error; }
  }

  private constructor(private root: HTMLElement, private canvas: HTMLCanvasElement, private engine: Engine, private runtime: Awaited<ReturnType<typeof loadHavok>>) {
    this.world = createTestWorld(engine, runtime);
    this.instrumentation = new SceneInstrumentation(this.world.scene);
    const options = () => { this.listenCount++; return { signal: this.abort.signal }; };
    this.el('#build').textContent = `v${__BUILD__.version} · ${__BUILD__.revision}`;
    this.el('#impulse').addEventListener('click', () => { if (!this.reasons.size) this.world.impulse(); }, options());
    this.el('#pause').addEventListener('click', () => this.pause('user'), options());
    this.el('#resume').addEventListener('click', () => this.resume(), options());
    this.el('#restart').addEventListener('click', () => this.restart(), options());
    this.el('#export').addEventListener('click', () => this.exportReport(), options());
    document.addEventListener('visibilitychange', () => { if (document.hidden) this.pause('hidden'); else { this.reasons.delete('hidden'); this.updateUi(); } }, options());
    window.addEventListener('blur', () => this.pause('user'), options());
    window.addEventListener('pagehide', () => this.pause('user'), options());
    window.addEventListener('keydown', event => { if (event.key === 'Escape' && !event.repeat) { event.preventDefault(); if (this.reasons.size) this.resume(); else this.pause('user'); } }, options());
    canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); this.contextLost = true; this.pause('context'); }, options());
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    this.resize();
    if (document.hidden) this.pause('hidden');
  }

  private el(selector: string) { return this.root.querySelector<HTMLElement>(selector)!; }

  private resize() {
    const landscape = matchMedia('(pointer: coarse)').matches && innerWidth > innerHeight;
    if (landscape) this.pause('orientation');
    else this.reasons.delete('orientation');
    const { width, height } = this.canvas.getBoundingClientRect();
    const ratio = Math.min(devicePixelRatio || 1, 2, Math.sqrt(1_000_000 / Math.max(1, width * height)));
    this.engine.setHardwareScalingLevel(1 / ratio);
    this.engine.resize();
    this.dirty = true;
    this.updateUi();
  }

  private pause(reason: string) {
    this.reasons.add(reason);
    this.reasons.add('user');
    this.clock.reset();
    this.lastFrame = undefined;
    this.updateUi();
  }

  private resume() {
    if (this.contextLost) { location.reload(); return; }
    if (this.reasons.has('hidden') || this.reasons.has('orientation')) return;
    this.reasons.delete('user');
    this.clock.reset();
    this.lastFrame = undefined;
    this.updateUi();
  }

  private restart() {
    this.instrumentation.dispose();
    this.world.dispose();
    const start = performance.now();
    this.world = createTestWorld(this.engine, this.runtime);
    this.instrumentation = new SceneInstrumentation(this.world.scene);
    this.preparationMs = performance.now() - start;
    this.clock = new FixedStep();
    this.stats = new FrameStats();
    this.lastFrame = undefined;
    this.restarts++;
    this.dirty = true;
    this.updateUi();
  }

  private render = () => {
    if (this.disposed || this.contextLost) return;
    const start = performance.now();
    if (this.reasons.size) {
      if (this.dirty) { this.world.scene.render(false, true); this.dirty = false; }
      return;
    }
    const interval = this.lastFrame === undefined ? 0 : start - this.lastFrame;
    this.lastFrame = start;
    const alpha = this.clock.advance(interval / 1000, seconds => this.world.step(seconds));
    this.world.interpolate(alpha);
    this.world.scene.render(false, true);
    const workMs = performance.now() - start;
    if (interval) this.stats.add(interval, workMs);
    if (start - this.lastUi >= 500) { this.updateUi(); this.lastUi = start; }
    this.dirty = false;
  };

  snapshot() {
    return {
      schemaVersion: 1,
      build: __BUILD__,
      capturedAt: new Date().toISOString(),
      userAgent: navigator.userAgent,
      renderer: { api: 'WebGL2', ...this.engine.getGlInfo() },
      scenario: { id: 'stage0-six-bodies-v1', seed: 0, generatorVersion: null, note: 'Fixed test layout; no procedural generator.' },
      paused: this.reasons.size > 0,
      pauseReasons: [...this.reasons],
      preset: 'stage0-static-1mp',
      canvas: { width: this.engine.getRenderWidth(), height: this.engine.getRenderHeight(), devicePixelRatio },
      resources: { ...this.world.resources(), scenes: this.engine.scenes.length, domListeners: this.listenCount, resizeObservers: 1, drawCalls: this.instrumentation.drawCallsCounter.current, activeTriangles: this.world.scene.getActiveIndices() / 3 },
      physics: { hz: 60, ticks: this.clock.ticks, simulationSeconds: this.clock.ticks / 60, droppedSeconds: this.clock.droppedSeconds },
      preparationMs: this.preparationMs,
      restarts: this.restarts,
      frames: this.stats.snapshot(),
      measurementNotes: { cpuWork: 'Physics + interpolation + JS render submission; excludes asynchronous GPU execution and diagnostic DOM refresh.', intervals: 'Active render-loop intervals; pause/loading excluded. Rolling window up to 1800 frames; lifetime counters since reset.', hardwareAcceptance: 'Not performed; browser emulation is not a device benchmark.' },
      bodies: this.world.cars.map(car => ({ name: car.collider.name, position: car.collider.position.asArray(), velocity: car.aggregate.body.getLinearVelocity().asArray() })),
    };
  }

  private updateUi() {
    const report = this.snapshot();
    this.el('#status').textContent = !this.ready ? 'ЗАГРУЗКА' : report.paused ? 'ПАУЗА' : 'СТЕНД АКТИВЕН';
    this.el('#status').classList.toggle('paused', report.paused);
    this.el('#fps').textContent = report.frames.fps ? report.frames.fps.toFixed(0) : '—';
    this.el('#work').textContent = report.frames.cpuWork.samples ? report.frames.cpuWork.p95.toFixed(1) : '—';
    this.el('#bodies').textContent = String(report.resources.dynamicBodies);
    this.el('#frames').textContent = `${report.frames.intervals.p95.toFixed(1)} / ${report.frames.intervals.p99.toFixed(1)} мс`;
    this.el('#resources').textContent = `${report.resources.meshes} / ${report.resources.bodies} / ${report.resources.drawCalls}`;
    this.el('#resolution').textContent = `${report.canvas.width} × ${report.canvas.height} / 60 Гц`;
    this.el('#ticks').textContent = String(report.physics.ticks);
    this.el('#overlay').hidden = !report.paused;
    const orientation = this.reasons.has('orientation');
    this.el('#pause-title').textContent = this.contextLost ? 'Графический контекст потерян' : orientation ? 'Поверните устройство' : 'Пауза';
    this.el('#pause-copy').textContent = this.contextLost ? 'Перезагрузите стенд, чтобы восстановить 3D-сцену.' : orientation ? 'Стенд работает в портретной ориентации.' : 'Продолжите, когда будете готовы.';
    this.el('#resume').textContent = this.contextLost ? 'Перезагрузить' : 'Продолжить';
    (this.el('#resume') as HTMLButtonElement).disabled = orientation;
    (this.el('#impulse') as HTMLButtonElement).disabled = report.paused;
    (this.el('#pause') as HTMLButtonElement).disabled = report.paused;
    (this.el('#restart') as HTMLButtonElement).disabled = this.contextLost;
  }

  private exportReport() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(this.snapshot(), null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `coastal-stage0-${Date.now()}.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort();
    this.listenCount = 0;
    this.resizeObserver.disconnect();
    this.engine.stopRenderLoop(this.render);
    this.instrumentation.dispose();
    this.world.dispose();
    this.engine.dispose();
    delete window.coastalDiagnostics;
  }
}
