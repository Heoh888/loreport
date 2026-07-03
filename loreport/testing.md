# Тестирование

## Что уже есть в репозитории

В `backend/tests/` найден как минимум один тест:

- `backend/tests/test_health.py`

Это означает, что базовый health-check уже покрывается тестами, но тестовая поверхность пока очень маленькая.

## На что ориентироваться при добавлении тестов

### API

Проверьте:

- `GET /api/health` возвращает healthy response;
- `POST /api/sync/trigger` создаёт job и отдаёт `job_id`;
- `GET /api/sync/status` корректно сворачивает состояния;
- `GET /api/docs/tree` показывает только markdown внутри `loreport/`;
- `GET /api/docs/content` и `GET /api/docs/render` обрабатывают валидные/невалидные пути.

### Webhooks

Проверьте:

- `X-Webhook-Secret` валиден, если `WEBHOOK_SECRET` задан;
- неверный secret даёт `401`;
- пустой/неполный payload не ломает endpoint.

### Snapshot guard

Критический сценарий для регрессии:

- `before == after` → `changed = false`;
- `.last-update.json` не переписывается без реальных изменений;
- no-op update не создаёт ложный success.

### Agent runner

Проверяйте:

- `chat` не разрешён в worker;
- `init` и `update` используют `loreport/`, а не `openwiki/`;
- git evidence реально попадает в prompt context;
- при отсутствии репозитория выбрасывается понятная ошибка.

## Практический минимум для нового теста

Если вы добавляете фичу, держите в голове минимум:

1. unit-тест на чистую логику;
2. API/integration тест для route;
3. отдельный тест на no-op / snapshot guard, если меняется sync behavior.

## Полезные команды

Точные команды зависят от того, как будет оформлен test harness, но текущая база указывает на `pytest` в `backend/`.
