import { Engine } from '@babylonjs/core/Engines/engine';
import { SceneInstrumentation } from '@babylonjs/core/Instrumentation/sceneInstrumentation';
import { createCoastPreviewScene, coastViews } from '../game/coast/coastPreviewScene';
import { FrameStats } from '../diagnostics/frameStats';

export type CoastPreviewReport = ReturnType<Awaited<ReturnType<typeof startCoastPreview>>['snapshot']>;

export async function startCoastPreview(root: HTMLElement) {
  const started = performance.now();
  const abort = new AbortController();
  root.innerHTML = `
    <main class="car-shell coast-shell">
      <header class="car-header"><div><p class="eyebrow">COASTAL RACER / ПОБЕРЕЖЬЕ</p><h1>Солнечный берег <span>40 м</span></h1></div><a href="?view=car-v006">← Машина</a></header>
      <section class="car-stage" aria-label="Просмотр побережья">
        <canvas id="coast-canvas" aria-label="Побережье и машина v006 в Babylon.js"></canvas>
        <p class="car-hint">Проведите пальцем, чтобы осмотреть</p>
        <div class="car-notice" id="coast-notice" role="status">Подготовка света и теней…</div>
      </section>
      <section class="car-panel">
        <div class="car-views" role="group" aria-label="Ракурс">
          <button data-view="game">За машиной</button><button data-view="reference">Как в Blender</button><button data-view="overview">Весь участок</button><button data-view="detail">Берег</button>
        </div>
        <div class="car-report-line"><span>Побережье v006 · свет по v007</span><strong id="coast-metrics">Подготовка…</strong></div>
        <div class="car-bottom"><button id="coast-pause">Пауза</button><button id="coast-export">Отчёт JSON ↗</button><button id="coast-close">Закрыть просмотр</button><span id="coast-build"></span></div>
        <p class="car-footnote">Статичный образец · мягкие тени · локальное небо для отражений</p>
      </section>
    </main>`;
  const el = <T extends HTMLElement = HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const canvas = el<HTMLCanvasElement>('#coast-canvas');
  const engine = new Engine(canvas, true, { stencil: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' }, false);
  let world: Awaited<ReturnType<typeof createCoastPreviewScene>> | undefined;
  let resizeObserver: ResizeObserver | undefined;
  let instrumentation: SceneInstrumentation | undefined;
  try {
    if (engine.webGLVersion !== 2) throw new Error('Для просмотра требуется WebGL2.');
    world = await createCoastPreviewScene(engine, canvas, AbortSignal.any([abort.signal, AbortSignal.timeout(30_000)]));
    const scene = world;
    instrumentation = new SceneInstrumentation(scene.scene);
    const instrument = instrumentation;
    const preparationMs = performance.now() - started;
    const stats = new FrameStats();
    let paused = false;
    let landscape = false;
    let contextLost = false;
    
    
    let last: number | undefined;
    let lastUi = 0;
    let disposed = false;
    const options = { signal: abort.signal };
    el('#coast-build').textContent = __BUILD__.revision;

    function updateState() {
      const notice = el('#coast-notice');
      notice.hidden = !paused && !landscape;
      notice.textContent = contextLost ? 'Графический контекст потерян. Обновите страницу.' : landscape ? 'Поверните устройство вертикально' : 'Пауза. Нажмите «Продолжить».';
      el('#coast-pause').textContent = paused ? 'Продолжить' : 'Пауза';
      el<HTMLButtonElement>('#coast-pause').disabled = landscape || contextLost;
      for (const button of root.querySelectorAll<HTMLButtonElement>('[data-view]')) button.disabled = landscape || contextLost;
    }
    function pause() { paused = true; last = undefined; updateState(); }
    function resize() {
      landscape = matchMedia('(pointer: coarse)').matches && innerWidth > innerHeight;
      if (landscape) pause();
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(devicePixelRatio || 1, 2, Math.sqrt(1_000_000 / Math.max(1, rect.width * rect.height)));
      engine.setHardwareScalingLevel(1 / ratio);
      engine.resize();

      updateState();
    }
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();
    for (const view of coastViews) el('[data-view="' + view + '"]').addEventListener('click', () => {
      scene.setView(view);
      for (const button of root.querySelectorAll<HTMLButtonElement>('[data-view]')) button.setAttribute('aria-pressed', String(button.dataset.view === view));
    }, options);
    el('[data-view="game"]').setAttribute('aria-pressed', 'true');
    el('#coast-pause').addEventListener('click', () => {
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
        schemaVersion: 1, build: __BUILD__, capturedAt: new Date().toISOString(), scenario: 'coast-art-sample-40m',
        coast: scene.report(), preparationMs, paused,
        canvas: { width: engine.getRenderWidth(), height: engine.getRenderHeight() },
        renderer: engine.getGlInfo(), userAgent: navigator.userAgent,
        frames: stats.snapshot(), drawCalls: instrument.drawCallsCounter.current,
        notes: 'Static 40m sample, original v006 layout + car; lighting reference v007. PCSS shadows and local sky reflections approximate Cycles. CPU timings exclude GPU execution; no device FPS acceptance.',
      };
    }
    el('#coast-export').addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot(), null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'coastal-coast-v006-' + Date.now() + '.json';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, options);
    const render = () => {
      if (disposed || contextLost) return;
      const start = performance.now();
      const interval = last === undefined ? 0 : start - last;
      last = paused ? undefined : start;

      scene.scene.render();
      if (!paused && interval) stats.add(interval, performance.now() - start);
      if (start - lastUi > 500) {
        const frames = stats.snapshot();
        el('#coast-metrics').textContent = (frames.fps ? frames.fps.toFixed(0) : '—') + ' FPS · ' + instrument.drawCallsCounter.current + ' draw calls';
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
        delete window.coastalCoastPreview;
        window.dispatchEvent(new CustomEvent('coast-preview-disposed', { detail: {
          sceneDisposed: scene.scene.isDisposed, meshes: scene.scene.meshes.length,
          textures: scene.scene.textures.length, renderLoops: engine.activeRenderLoops.length,
        } }));
      },
    };
    window.coastalCoastPreview = { snapshot };
    el('#coast-close').addEventListener('click', () => {
      preview.dispose();
      root.innerHTML = '<main class="loading"><h1>Просмотр закрыт</h1><p>Ресурсы сцены освобождены.</p><a href="?view=coast-v006">Открыть снова</a></main>';
    }, options);
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
