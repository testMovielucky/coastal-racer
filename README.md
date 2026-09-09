# Coastal Racer · этап 0

[Открыть стенд](https://testmovielucky.github.io/coastal-racer/) · [Репозиторий](https://github.com/testMovielucky/coastal-racer)

Портретный технический стенд браузерной 3D-гонки. Шесть простых физических кузовов, дорога, Havok, пауза, тестовый импульс, сброс и JSON-диагностика. Это не готовая гонка и не финальные ассеты.

## Локальный запуск

Node.js >=22.12, npm. Blender для этапа 0 не нужен.

```powershell
npm ci
npm run dev
```

В текущем окружении Node есть, но npm отсутствует в PATH. Подготовлен локальный вариант без изменения системы:

```powershell
.\tools\bootstrap-npm.ps1
.\tools\npm.ps1 ci
.\tools\npm.ps1 run dev
```

Откройте адрес Vite в терминале. Проверка production-сборки:

```powershell
.\tools\npm.ps1 run typecheck
.\tools\npm.ps1 test
.\tools\npm.ps1 run build
.\tools\npm.ps1 run test:e2e
```

Если Chrome не установлен, используйте Chromium: установите браузер командой `node node_modules/@playwright/test/cli.js install chromium` и запустите тесты с `$env:CI='true'`. В CI это выполняется автоматически. Установка браузера для обычного запуска игры не нужна.

Для ручной проверки точного вложенного пути production-сборки: `node tools/serve-dist.mjs`, затем [локальный стенд](http://127.0.0.1:4173/coastal-racer/).

## Работа со стендом

Кузова падают на дорогу и остаются на ней. «Тестовый толчок» сообщает первому кузову импульс, который передаётся другим через физический контакт. «Сброс» пересоздаёт сцену; «Пауза»/Esc останавливают время. После потери фокуса, сворачивания или поворота сенсорного устройства требуется «Продолжить». Нажатия на интерфейс не дают газ: игровой контроллер относится к этапу 2.

«Отчёт JSON» сохраняет версию, браузер/рендерер, параметры canvas, ресурсы, статистику кадров и физики. CPU work измеряет работу JS/отправку команд, а не асинхронную работу GPU. Счётчики ресурсов помогают обнаружить рост; они не заменяют профилирование памяти.

## Публикация

Workflow `.github/workflows/pages.yml` выполняет npm ci, typecheck/build, Vitest и Playwright, затем публикует dist через GitHub Actions. В Settings → Pages источник — GitHub Actions. Публикация с main или вручную; pull request выполняет проверки без деплоя.

Относительный base `./` и импорт WASM через Vite сохраняют работоспособность под каталогом репозитория. Исходники, node_modules и инструменты в dist не копируются. Лицензии Babylon/Havok включены в сборку. PWA иконки/manifest относятся к последующей работе, офлайн-режима нет.

[План](docs/GAME_IMPLEMENTATION_PLAN.md) · [Решения](docs/DECISIONS.md) · [Статус](docs/PROGRESS.md) · [Проверка устройств](docs/PERFORMANCE.md)
