import './style.css';

const root = document.querySelector<HTMLElement>('#app')!;
root.innerHTML = '<main class="loading"><p class="eyebrow">COASTAL RACER / 00</p><h1>Подготовка стенда</h1><p role="status">Загружаем движок и локальную физику…</p></main>';
let dispose: (() => void) | undefined;

try {
  const { Stand } = await import('./app/stand');
  const stand = await Stand.create(root);
  dispose = () => stand.dispose();
} catch (error) {
  root.innerHTML = '<main class="loading error"><p class="eyebrow">COASTAL RACER / 00</p><h1>Не удалось запустить стенд</h1><p role="alert" id="error-message"></p><p>Проверьте соединение и повторите загрузку.</p><button id="retry">Повторить</button></main>';
  root.querySelector('#error-message')!.textContent = error instanceof Error ? error.message : String(error);
  root.querySelector('#retry')!.addEventListener('click', () => location.reload(), { once: true });
}

if (import.meta.hot) import.meta.hot.dispose(() => dispose?.());
