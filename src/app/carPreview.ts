import { Engine } from '@babylonjs/core/Engines/engine';
import { SceneInstrumentation } from '@babylonjs/core/Instrumentation/sceneInstrumentation';
import { createCarPreviewScene, viewNames } from '../game/vehicle/carPreviewScene';
import { FrameStats } from '../diagnostics/frameStats';

export type CarPreviewReport = ReturnType<Awaited<ReturnType<typeof startCarPreview>>['snapshot']>;

export async function startCarPreview(root: HTMLElement) {
  const started = performance.now();
  const abort = new AbortController();
  root.innerHTML = `
    <main class="car-shell">
      <header class="car-header"><div><p class="eyebrow">COASTAL RACER / МОДЕЛЬ</p><h1>CR Sport 01 <span>v006</span></h1></div><a href="./">← Стенд</a></header>
      <section class="car-stage" aria-label="Просмотр автомобиля">
        <canvas id="car-canvas" aria-label="Модель v006 в Babylon.js"></canvas>
        <p class="car-hint">Проведите пальцем, чтобы осмотреть</p>
        <div class="car-notice" id="car-notice" role="status">Загрузка принятого GLB…</div>
      </section>
      <section class="car-panel" aria-label="Проверка модели">
        <div class="car-views" role="group" aria-label="Ракурс">
          <button data-view="game">За машиной</button><button data-view="rear">Сзади</button><button data-view="front">Спереди</button><button data-view="side">Сбоку</button>
        </div>
        <div class="car-options"><label>Цвет <select id="car-color"><option value="original">Исходный</option><option value="#318bea">Синий</option><option value="#eeeeee">Белый</option><option value="#e2334e">Красный</option></select></label>
          <button id="car-wheels" aria-pressed="false">Вращать колёса</button><button id="car-collider" aria-pressed="false">Коллайдер</button>
        </div>
        <div class="car-report-line"><span>21 114 △ · 4 материала · 811 КиБ</span><strong id="car-metrics">Подготовка…</strong></div>
        <div class="car-bottom"><button id="car-pause">Пауза</button><button id="car-export">Отчёт JSON ↗</button><span id="car-build"></span></div>
        <p class="car-footnote">Проверка одного GLB · тестовое освещение · управление гонкой ещё не подключено</p>
      </section>
    </main>`;
  const el = <T extends HTMLElement = HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const canvas = el<HTMLCanvasElement>('#car-canvas');
  const engine = new Engine(canvas, true, { stencil: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' }, false);
  let world: Awaited<ReturnType<typeof createCarPreviewScene>> | undefined;
  let resizeObserver: ResizeObserver | undefined;
  let instrumentation: SceneInstrumentation | undefined;
  try {
    if (engine.webGLVersion !== 2) throw new Error('Для просмотра требуется WebGL2.');
    world = await createCarPreviewScene(engine, canvas, AbortSignal.any([abort.signal, AbortSignal.timeout(30_000)]));
    const scene = world;
    instrumentation = new SceneInstrumentation(scene.scene);
    const instrument = instrumentation;
    const preparationMs = performance.now() - started;
    const stats = new FrameStats();
    let paused = false;
    let landscape = false;
    let contextLost = false;
    let spinning = false;
    let colliderVisible = false;
    let last: number | undefined;
    let lastUi = 0;
    let disposed = false;
    const options = { signal: abort.signal };
    el('#car-build').textContent = __BUILD__.revision;

    function updateState() {
      const notice = el('#car-notice');
      notice.hidden = !paused && !landscape;
      notice.textContent = contextLost ? 'Графический контекст потерян. Обновите страницу.' : landscape ? 'Поверните устройство вертикально' : 'Пауза. Нажмите «Продолжить».';
      el('#car-pause').textContent = paused ? 'Продолжить' : 'Пауза';
      el<HTMLButtonElement>('#car-pause').disabled = landscape || contextLost;
      for (const button of root.querySelectorAll<HTMLButtonElement>('[data-view], #car-wheels, #car-collider')) button.disabled = landscape || contextLost;
    }
    function pause() { paused = true; last = undefined; updateState(); }
    function resize() {
      landscape = matchMedia('(pointer: coarse)').matches && innerWidth > innerHeight;
      if (landscape) pause();
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(devicePixelRatio || 1, 2, Math.sqrt(1_000_000 / Math.max(1, rect.width * rect.height)));
      engine.setHardwareScalingLevel(1 / ratio);
      engine.resize();
      scene.fitCamera();
      updateState();
    }
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();
    for (const view of viewNames) el('[data-view="' + view + '"]').addEventListener('click', () => {
      scene.setView(view);
      for (const button of root.querySelectorAll<HTMLButtonElement>('[data-view]')) button.setAttribute('aria-pressed', String(button.dataset.view === view));
    }, options);
    el('[data-view="game"]').setAttribute('aria-pressed', 'true');
    el('#car-color').addEventListener('change', () => scene.setPaint(el<HTMLSelectElement>('#car-color').value), options);
    el('#car-wheels').addEventListener('click', () => {
      spinning = !spinning;
      el('#car-wheels').setAttribute('aria-pressed', String(spinning));
    }, options);
    el('#car-collider').addEventListener('click', () => {
      colliderVisible = !colliderVisible;
      scene.setCollider(colliderVisible);
      el('#car-collider').setAttribute('aria-pressed', String(colliderVisible));
    }, options);
    el('#car-pause').addEventListener('click', () => {
      if (landscape || document.hidden || contextLost) return;
      paused = !paused;
      last = undefined;
      updateState();
    }, options);
    window.addEventListener('blur', pause, options);
    window.addEventListener('pagehide', pause, options);
    document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); }, options);
    canvas.addEventListener('webglcontextlost', () => { contextLost = true; pause(); }, options);
    if (document.hidden) pause();

    function snapshot() {
      return {
        schemaVersion: 1, build: __BUILD__, capturedAt: new Date().toISOString(), scenario: 'car-v006-single-visual-check',
        model: scene.report(), preparationMs, paused, spinning,
        canvas: { width: engine.getRenderWidth(), height: engine.getRenderHeight() },
        renderer: engine.getGlInfo(), userAgent: navigator.userAgent,
        frames: stats.snapshot(), drawCalls: instrument.drawCallsCounter.current,
        notes: 'One car, no Havok or bots. Neutral generated 32px cubemap + directional/fill lights. CPU timing excludes GPU execution. This is not full-race or target-device acceptance.',
      };
    }
    el('#car-export').addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot(), null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'coastal-v006-' + Date.now() + '.json';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, options);
    const render = () => {
      if (disposed || contextLost) return;
      const start = performance.now();
      const interval = last === undefined ? 0 : start - last;
      last = paused ? undefined : start;
      if (!paused && spinning) scene.stepWheels(Math.min(interval / 1000, 1 / 15));
      scene.scene.render();
      if (!paused && interval) stats.add(interval, performance.now() - start);
      if (start - lastUi > 500) {
        const frames = stats.snapshot();
        el('#car-metrics').textContent = (frames.fps ? frames.fps.toFixed(0) : '—') + ' FPS · ' + instrument.drawCallsCounter.current + ' draw calls';
        lastUi = start;
      }
    };
    engine.runRenderLoop(render);
    const preview = {
      snapshot,
      dispose() {
        if (disposed) return;
        disposed = true;
        abort.abort();
        resizeObserver?.disconnect();
        engine.stopRenderLoop(render);
        instrument.dispose();
        scene.dispose();
        engine.dispose();
        delete window.coastalCarPreview;
      },
    };
    window.coastalCarPreview = { snapshot };
    return preview;
  } catch (error) {
    abort.abort();
    resizeObserver?.disconnect();
    instrumentation?.dispose();
    world?.dispose();
    engine.dispose();
    throw error;
  }
}
