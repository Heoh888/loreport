# План: Integrity Engine + Workflow для Loreport

## Epistemic model (зачем Loreport)

Loreport **не заменяет архитектора** и не выбирает между docs и code как «истиной».

| Слой | Роль | Что даёт |
|------|------|----------|
| Human docs (`tech.docs/`, README, ADR) | **Intent & context** | Куда смотреть, зачем сервис, границы. Каждая команда пишет по-своему — это норма |
| Source code | **Implementation** | Что реально есть сейчас: роуты, конфиги, deps |
| Git | **Change** | Что изменилось |
| `loreport/` | **Integrity** | Как всё складывается в целое + явные gaps |

**Ни docs, ни code не absolute truth:**
- docs могут описывать то, что ещё не написано в коде
- code может существовать без human doc
- расхождения — норма, не баг Loreport

**Задача Loreport:** поддерживать **целостность проекта** — навигация, связи между сервисами, radar gaps/drift.

---

## Формат страницы сервиса

Каждый `{loreport_dir}/services/<name>.md`:

```markdown
# rag-service

## Purpose
Кратко: роль сервиса (из human docs и/или кода).

## Human context
- rag-service/tech.docs/technical-specification.md — intent, flows
- rag-service/README.md

## Implementation signals
- Entrypoints: api/routes/rag.py, worker/consumer.py
- Config: docker-compose env RABBITMQ_URL

## Integrations
| System | Evidence | Role |
|--------|----------|------|
| RabbitMQ | config.py + tech.docs | job queue |

## Alignment
- Queue name `rag.jobs` — совпадает в spec и config

## Gaps & drift
- `documented intent, not in code` — endpoint /reindex в spec, роут не найден
- `in code, not documented` — healthcheck /internal/ping без упоминания в docs
- `likely stale doc` — spec ссылается на Postgres, код использует SQLite
- `unverified` — не удалось подтвердить auth flow
```

**Platform quickstart** заканчивается секцией **Platform gaps** — сводка по всем сервисам.

Промпты: `backend/loreport_core/prompts.py` (обновлено).

---

## Dynamic Subagents + Workflow

Контекст: [видео LangChain про dynamic subagents](https://docs.langchain.com/oss/python/deepagents/overview).

Цель workflow: **полный integrity pass** по monorepo — каждый сервис получает human context + code signals + Alignment/Gaps, не shallow summary.

---

## Проблема сейчас

`runner.py` — один агент, один контекст:

```python
create_deep_agent(model=..., tools=[], backend=LocalShellBackend, system_prompt=...)
agent.invoke(...)
```

| Симптом | Причина |
|---------|---------|
| Пропуск сервисов в monorepo | Агент «решает в уме», когда остановиться |
| Слабые `services/*.md` vs `tech.docs/` | Нет изолированного research per service |
| Долгий init, непредсказуемый результат | Много tool calls в одном thread |
| Glob `**` errors | Большой repo, один агент лезет везде |

**Snapshot guard** и **git evidence** снаружи — это правильно, не трогаем.

---

## Что дают dynamic subagents (из видео)

| Обычные subagents | Dynamic subagents |
|-------------------|-------------------|
| Main agent вызывает `task` по одному | Агент пишет **код** (цикл, `Promise.all`) |
| Оркестрация в контексте LLM | Оркестрация в **eval sandbox** |
| ~10 задач — ок | 50–500 файлов/сервисов — надёжно |
| Модель забывает items | `for item in items: await task(...)` — полное покрытие |

**Триггер:** слово `workflow` в user prompt → агент пишет код вместо последовательных task calls.

**Инфраструктура:**
- `CodeInterpreterMiddleware` — sandbox, tool `eval`
- `global task` / `await task(...)` — программный запуск subagent из кода
- Dynamic response schema — типизированный результат subagent для циклов

---

## Паттерны — что применить к Loreport

| # | Паттерн | Применение |
|---|---------|------------|
| 1 | Classify & act | Сервис с `tech.docs/` → integrity page с pointer + drift; без docs → полный research |
| 2 | **Map-reduce** | **Основной для init:** N subagents → integrity note per service → platform synthesis |
| 3 | Adversarial verify | Второй subagent проверяет «дока vs код» (update, optional) |
| 4 | Generate & filter | Несколько вариантов architecture → выбрать лучший (optional) |
| 5 | Tournament | Не приоритет |
| 6 | Loop until done | Update: проходы пока git diff не исчерпан |

### Init monorepo (целевой flow)

```
workflow:
  1. ls top-level → список сервисов (исключить node_modules, .git, loreport/)
  2. classify каждый: has tech.docs? has README?
  3. parallel task per service:
     - read human docs for intent/navigation context
     - read code entrypoints for implementation signals
     - output: Alignment + Gaps (four labels)
  4. synthesize: quickstart.md (with Platform gaps), platform/integration-map.md
```

### Update

```
workflow:
  1. git diff since last_update → список затронутых paths
  2. map: затронутые сервисы → subagent update только их страниц
  3. loop (max 3): если subagent нашёл cross-cutting change → ещё один проход
```

---

## Изменения в коде

### 1. Зависимости

- Проверить версию deepagents с `CodeInterpreterMiddleware` (сейчас **0.6.12** — interpreter может быть в более новой версии)
- При необходимости: `deepagents>=0.7` (или актуальная с docs)

### 2. `runner.py`

```python
from deepagents.middleware import CodeInterpreterMiddleware  # когда доступен
from deepagents.middleware.subagents import SubAgent, SubAgentMiddleware

SERVICE_RESEARCHER = SubAgent(
    name="service-researcher",
    description="Read one service directory and write loreport/services/<name>.md",
    system_prompt="...",  # узкий scope, один сервис
)

PLATFORM_WRITER = SubAgent(
    name="platform-writer",
    description="Synthesize platform-level loreport pages from service summaries",
    system_prompt="...",
)

agent = create_deep_agent(
    model=...,
    backend=LocalShellBackend(...),
    middleware=[
        CodeInterpreterMiddleware(),
        SubAgentMiddleware(subagents=[SERVICE_RESEARCHER, PLATFORM_WRITER]),
    ],
    system_prompt=create_system_prompt(...),
)
```

### 3. `prompts.py`

**Init monorepo** — добавить блок:

```markdown
Run a **workflow** for this monorepo init:
- Discover each top-level service with `ls /`
- For EACH service (do not skip any), spawn a subagent via code
- Services with existing `tech.docs/` → pointer page only, link as canonical
- Services without good docs → full-depth page under loreport/services/
- After all complete, synthesize loreport/quickstart.md and loreport/platform/
```

**Update** — добавить `workflow` только если `git diff` затрагивает >3 сервисов.

Ключевые слова из видео: `workflow`, `each`, `every`, `all`, `parallel`, `do not skip`.

### 4. Scope detection (новый модуль)

`loreport_core/scope.py` — до запуска агента:

```python
def detect_monorepo_services(repo_path: Path) -> list[str]:
    """Top-level dirs excluding loreport/, .git, node_modules, ..."""
```

Передавать список в user prompt — агенту не нужно угадывать границы.

### 5. Конфиг

```python
# config.py
init_workflow_enabled: bool = True
init_max_parallel_subagents: int = 5  # лимит cost
init_subagent_model: str | None = None  # cheaper model for map phase
```

### 6. UI / jobs (optional)

- `sync_jobs` — поле `subagents_spawned`, `workflow_mode`
- Логи: парсить structured output или считать eval calls

---

## Оценка cost / time

| Режим | Сервисов | LLM calls (оценка) | Время |
|-------|----------|-------------------|-------|
| Сейчас (1 agent) | 10 | 50–150 tool rounds | 10–30 min |
| Map-reduce (5 parallel) | 10 | 10 subagents + 1 synth ≈ 15–30 | 15–40 min |
| Map-reduce (15 parallel) | 15 | 15 + synth | 20–50 min, $$ |

**Рекомендация:** `init_max_parallel_subagents=3–5`, дешёвая модель для map (`gpt-5.4-mini`), сильная для synthesis.

---

## Этапы внедрения

### Этап 0.5 — Prompt integrity (сделано)

- [x] Epistemic model в `prompts.py`
- [x] Service page template: Alignment + Gaps
- [x] Init flow: per-service integrity pages → platform synthesis

### Этап 0 — Spike (1–2 дня)

- [ ] Обновить deepagents, найти `CodeInterpreterMiddleware` в API
- [ ] Минимальный скрипт: `workflow` + 3 fake «сервиса» на тестовом repo
- [ ] Проверить `global task` / eval в Docker контейнере

### Этап 1 — Init map-reduce (3–5 дней)

- [ ] `scope.py` — detect services
- [ ] Subagents: `service-researcher`, `platform-writer`
- [ ] Промпт init с `workflow` для monorepo (`len(services) > 2`)
- [ ] Флаг `INIT_WORKFLOW_ENABLED` в env

### Этап 2 — Update targeted (2–3 дня)

- [ ] Workflow только для затронутых paths из git diff
- [ ] Loop until done (max 3 passes)

### Этап 3 — Quality (optional)

- [ ] Adversarial verify subagent на update
- [ ] Метрики в SQLite: coverage %, pages written

---

## Что не менять

- `queue/local.py`, `jobs.py` — pipeline тот же
- `snapshot/` — hash guard
- `git/evidence.py` — контекст для промпта
- Standalone SQLite sidecar
- Frontend — только опционально показать «N subagents»

---

## Риски

| Риск | Митигация |
|------|-----------|
| Версия deepagents без interpreter | Pin после spike; fallback на static SubAgentMiddleware |
| Cost explosion | `max_parallel`, cheaper model для map |
| Eval sandbox security | Только in-memory, без network; тот же REPO_PATH |
| Timeout job | Увеличить или chunk services (batch по 5) |
| Subagent пишет не туда | Permissions / prompt: only `loreport/` |

---

## Критерий успеха (forsi dogfooding)

После init на product-forsi:

1. Каждый top-level сервис в `loreport/quickstart.md`
2. У каждого сервиса есть `loreport/services/<name>.md` с секциями Alignment и Gaps
3. Сервисы с `tech.docs/` — ссылки на human docs, без переписывания spec
4. Platform gaps в quickstart перечисляет doc/code divergences
5. Init не пропускает >90% сервисов

---

## Ссылки

- [deepagents overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- Loreport: `backend/loreport_core/agent/runner.py`, `prompts.py`
- OpenWiki reference: `/Users/aleksejhodakov/openwiki`
