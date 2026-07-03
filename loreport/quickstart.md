# Loreport quickstart

`Loreport` — это sidecar-сервис, который следит за репозиторием и поддерживает живую инженерную память проекта. В этом репозитории документация живёт в `/loreport` и пишется на русском языке для людей и будущих агентов.

## С чего начать

1. Прочитать [архитектуру](architecture.md), чтобы понять runtime-модель и границы компонентов.
2. Открыть [рабочие процессы](workflows.md), чтобы увидеть, как запускаются `init`, `update`, webhook и polling.
3. Изучить [доменные понятия](domain.md), чтобы не путать lore, snapshot и metadata.
4. Посмотреть [операции](operations.md), если нужно поднять проект локально или в Docker.
5. Проверить [тестирование](testing.md), если вы меняете поведение API, worker или snapshot guard.
6. Использовать [карту исходников](source-map.md), чтобы быстро найти нужный модуль.

## Что это за проект

По текущим документам и коду Loreport — это open-source sidecar в стиле Grafana для инженерных знаний:

- следит за git-репозиторием через webhook и HEAD polling;
- запускает agent-run для `init` и `update`;
- пишет сгенерированную lore обратно в mounted repo в каталог `loreport/`;
- хранит историю sync-jobs в PostgreSQL;
- публикует задания через RabbitMQ;
- отдаёт dashboard и docs browser через FastAPI + React build.

## Текущие основные компоненты

- `backend/loreport_core` — библиотека с agent runner, git evidence, snapshot и prompt logic.
- `backend/loreport_server` — FastAPI API, DB модели, queue publisher и worker consumer.
- `web/` — Vite/React frontend, пока в стадии scaffold.
- `docker/` — Dockerfile и docker-compose для api, worker, postgres и rabbitmq.

## Ключевые маршруты API

- `GET /api/health` — health check.
- `POST /api/sync/trigger` — создать sync job и отправить её в RabbitMQ.
- `GET /api/sync/status` — получить состояние последнего sync.
- `GET /api/sync/history` — история последних jobs.
- `GET /api/sync/snapshot` — текущий snapshot каталога `loreport/`.
- `GET /api/docs/tree` — дерево markdown-документов.
- `GET /api/docs/content` — сырой контент документа.
- `GET /api/docs/render` — HTML-рендер markdown.
- `POST /webhooks/git` — вход для git webhook с `WEBHOOK_SECRET`.
- `GET /api/settings` / `PUT /api/settings` — не секретные настройки.

## Как устроен sync-loop

1. API принимает trigger или webhook.
2. Создаётся `SyncJob` в PostgreSQL.
3. Сообщение публикуется в RabbitMQ.
4. Worker забирает job и запускает `run_loreport_agent()`.
5. До и после запуска считается snapshot каталога `loreport/`.
6. Если содержимое изменилось, пишется `.last-update.json`.
7. UI читает статус и историю через API.

## На что обратить внимание

- Loreport работает с virtual paths внутри агента, например `/README.md` и `/loreport/quickstart.md`.
- Snapshot guard нужен, чтобы не было пустых update loops.
- В документации и prompts нужно использовать `loreport/`, а не `openwiki/`.
- Секреты не хранятся в репозитории и не документируются в lore pages.

## Связанные страницы

- [Архитектура](architecture.md)
- [Рабочие процессы](workflows.md)
- [Доменные понятия](domain.md)
- [Операции](operations.md)
- [Тестирование](testing.md)
- [Карта исходников](source-map.md)
