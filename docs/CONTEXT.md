# Контекст проекта Loreport

Документ для передачи полного контекста новому репозиторию, агентам и контрибьюторам.  
Собран из обсуждения идеи, анализа OpenWiki и позиционирования.

---

## Откуда возникла идея

Изучали [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) — TypeScript CLI, который генерирует и поддерживает документацию в `openwiki/` через AI-агента (DeepAgents).

**Что понравилось в OpenWiki:**
- Инкрементальные обновления по git (не полный пересбор)
- Snapshot SHA-256 — metadata не обновляется, если docs не изменились (защита от пустых CI-циклов)
- Git evidence в промпте (status, HEAD, log с last update)
- Авто-вставка секции в `AGENTS.md` / `CLAUDE.md`
- Scheduled update через GitHub Action

**Что не понравилось:**
- Монолитный CLI, не платформа
- Нет web UI (только Ink TUI ~3100 строк)
- Нет daemon / sidecar-модели
- Один тип задачи: документация (`chat | init | update`)
- Требует существующий репозиторий — не работает для greenfield-идеи
- Сложно расширять (security scan, другие view, веб-интерфейс)

---

## Ключевой инсайт

OpenWiki решает проблему **«документация устаревает»** как CLI-утилита.

Loreport решает ту же проблему как **инфраструктурный сервис** — по аналогии с Grafana для логов/метрик.

В мультисервисной архитектуре:
- Grafana — отдельный контейнер для observability runtime
- **Loreport** — отдельный контейнер для observability **знаний о коде**

---

## Почему название Loreport

Обсуждались варианты: Knowdock, Reposсope, Sourcechart и др.

**Выбрано: Loreport** = Lore + Port

- **Lore** — не просто «знания» или «документация». Накопленный контекст, история, причины решений. Как Game Lore — весь мир, связи, backstory. У зрелого проекта появляется свой «lore»:
  - почему существует Billing-сервис
  - почему отказались от Kafka
  - почему endpoint нельзя удалить
  - почему класс нельзя трогать
- **Port** — гавань в docker-compose стеке, sidecar-сервис

Интерпретации:
- *Report about project lore*
- *Living report of project knowledge*

**Слоган:** *Your repository knows more than your documentation.*

---

## Позиционирование

### Не это
- GitBook / Confluence / MkDocs
- «Ещё один AI documentation generator»
- Замена SonarQube + Backstage + Swagger на старте

### Это
- **Grafana для инженерных знаний проекта**
- Операционная система знаний для разработки
- Sidecar, который отвечает: **«Что сейчас представляет собой этот репозиторий?»**

### Рынок
Много инструментов решают один срез:
- Swagger — API
- SonarQube — качество
- Backstage — каталог сервисов
- Dependabot — зависимости
- Grafana — метрики

Почти никто в open source не объединяет это в **единую живую картину** как sidecar-сервис с web UI.

Близкие конкуренты по кускам:
| Проект | Что делает | Чего нет |
|--------|-----------|----------|
| OpenWiki | CLI, incremental wiki | Daemon, web UI, graph |
| CodeWiki | Генерация wiki, Docker | Watch service, dashboard |
| repowise | Self-host, MCP, code intelligence | Grafana-like UI для lore |
| knowing, obs-code | Code graph, MCP | Living docs sidecar |
| Backstage | Service catalog | Repo-level living knowledge |

**Ниша Loreport:** sidecar + web UI + lore-фрейминг + living sync.

---

## Архитектурное видение (полное)

```
Git Repository
       │
       ▼
   Indexer
       │
       ├── AST                    (v1.0+)
       ├── Git history            (v0.1)
       ├── Comments               (v0.5+)
       ├── ADR / Markdown         (v0.1)
       ├── OpenAPI                (v0.3)
       ├── Docker / CI/CD         (v0.3)
       ├── Kubernetes             (v0.5+)
       └── Dependencies           (v0.3)
       │
       ▼
 Knowledge Graph                (v1.0)
       │
       ▼
      Loreport
       │
       ├── Documentation          (v0.1)
       ├── Architecture           (v0.1)
       ├── Dependency Graph       (v0.3)
       ├── API Map                (v0.3)
       ├── Doc Drift              (v0.5)
       ├── Dead Code              (v1.0+)
       ├── Vulnerabilities        (v1.0+)
       ├── Technical Debt         (v1.0+)
       ├── Ownership              (v1.0+)
       └── Impact Analysis        (v1.0+)
```

### Двунаправленность (важная идея)

- **Code → Lore** — агент анализирует репо, синтезирует знания
- **Lore → Code** — команда дописывает lore через UI («этот endpoint нельзя трогать, клиент X»)

Это отличает от чистого doc generator: персистентная память команды, не только AI-readonly.

### Принцип построения графа

- Детерминированные edges: imports, HTTP routes, package.json, OpenAPI paths
- LLM — для synthesis и gap-filling, не для всех связей
- Confidence score на утверждениях (чтобы не было галлюцинаций с красивым UI)

---

## Решение по репозиторию

**Отдельный репозиторий `loreport`**, не форк openwiki.

Причины:
- `langchain-ai/openwiki` — чужой продукт (CLI, бренд LangChain)
- Loreport — другой продукт, архитектура, позиционирование
- MIT-лицензия OpenWiki позволяет переиспользовать agent core с attribution

```
github.com/<org>/loreport     ← разработка
github.com/langchain-ai/openwiki  ← reference + agent core source
```

---

## Что переиспользовать из OpenWiki

OpenWiki — TypeScript CLI. Loreport backend — **Python**. Переносим **логику и промпты**, не копируем файлы.

| Модуль OpenWiki (TS) | Куда в Loreport (Python) | Действие |
|----------------------|--------------------------|----------|
| `src/agent/index.ts` | `backend/loreport_core/agent/` | Порт `run_loreport_agent`, убрать CLI |
| `src/agent/prompt.ts` | `backend/loreport_core/prompts/` | Переименовать openwiki → loreport paths |
| `src/agent/utils.ts` | `backend/loreport_core/git/`, `snapshot/` | Git evidence + snapshot |
| `src/agent/types.ts` | `backend/loreport_core/types.py` | Расширить для jobs/API |
| `src/constants.ts` | `backend/loreport_core/constants.py` | Providers, models |
| `src/env.ts` | `backend/loreport_server/config.py` | Env vars контейнера |
| `src/cli.tsx` | — | Не переносить |
| `src/credentials.tsx` | `web/` Settings page | Заменить web UI |

---

## MVP — что ship первым

**Не весь knowledge graph.** Только:

1. Sidecar: FastAPI + in-process worker + SQLite
2. Web UI: dashboard (sync status) + docs browser (React)
3. Git webhook + HEAD polling (not yet)
4. Agent `init` / `update` (порт из OpenWiki → Python deepagents)
5. Snapshot skip для пустых обновлений
6. Docker single-container sidecar

**Definition of Done v0.1:**
- `docker compose up` → UI на `:3080`
- Push в репо → через N минут обновлённая lore
- Dashboard показывает историю sync
- Пустой update не создаёт ложный success

---

## Риски

| Риск | Митигация |
|------|-----------|
| Слишком широкое видение | Ship L0, продавать полную картину в roadmap |
| LLM costs | Sync только при изменении HEAD + snapshot skip |
| Knowledge graph hallucinations | Детерминированные edges + confidence |
| Конкуренция с doc generators | Позиционирование «lore platform», не «doc tool» |
| Gaming-ассоциация «lore» | Tagline приземляет: *engineering knowledge* |

---

## Технический стек

| Слой | Выбор |
|------|-------|
| Backend | Python 3.11+ |
| API | FastAPI + uvicorn |
| DB | PostgreSQL + SQLAlchemy 2.0 + Alembic |
| Queue | in-process asyncio.Queue |
| UI | React + Vite + shadcn (pnpm) |
| Agent | deepagents + langchain (Python) |
| Backend tooling | uv, ruff |
| Deploy | Docker multi-stage (api + worker) |

---

## API (MVP)

```
GET  /api/health
GET  /api/sync/status
POST /api/sync/trigger
GET  /api/sync/history
GET  /api/docs/tree
GET  /api/docs/content?path=
POST /webhooks/git
GET  /api/settings
PUT  /api/settings
```

---

## Статус

- [x] Идея и позиционирование
- [x] Название: Loreport
- [x] Решение: отдельный репозиторий
- [x] Стартовая документация
- [ ] Scaffold backend + web
- [ ] Port agent core from OpenWiki (Python)
- [ ] API + worker MVP
- [ ] Web UI MVP
- [x] Docker single-container sidecar

---

## Ссылки

- OpenWiki (reference): https://github.com/langchain-ai/openwiki
- Локальный клон для reference: `/Users/aleksejhodakov/openwiki`
- Новый репозиторий: `/Users/aleksejhodakov/loreport`
