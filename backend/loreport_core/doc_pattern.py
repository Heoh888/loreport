from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from loreport_core.constants import LOREPORT_DIR
from loreport_core.scope import HUMAN_DOC_DIR_NAMES

ASPECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "messaging": ("events", "rabbitmq", "kafka", "queue", "amqp", "mq", "nats", "pubsub"),
    "api": ("curl", "api", "openapi", "swagger", "rest", "grpc", "endpoint", "http"),
    "data-model": ("er-", "er_", "diagram", "schema", "entity", "database", "db-", "model"),
    "specification": ("spec", "technical", "architecture", "design", "requirement"),
    "operations": ("deploy", "runbook", "ops", "docker", "k8s", "helm", "infra"),
    "testing": ("test", "e2e", "qa"),
}

ASPECT_LOREPORT_FILES: dict[str, str] = {
    "overview": "index.md",
    "messaging": "messaging.md",
    "api": "api-surface.md",
    "data-model": "data-model.md",
    "specification": "specification.md",
    "operations": "operations.md",
    "testing": "testing.md",
    "general": "general.md",
}

DRIFT_FILE = "drift.md"
PATTERN_FILE = "_pattern.json"


ASPECT_CONTENT_HINTS: dict[str, str] = {
    "api": "Extract endpoints from human doc into Intent table; verify each in routers.",
    "messaging": "Extract queues/events/payloads from human doc; verify in consumer/schemas.",
    "data-model": "Extract entities/relations from ER/spec; verify in models.",
    "specification": "Extract architecture boundaries from spec; verify in entrypoint/modules.",
    "operations": "Extract deploy/run steps; verify in Dockerfile/compose/config.",
    "testing": "Extract test scenarios; verify in test files.",
    "general": "Extract flows from plan docs; verify in named modules.",
    "overview": "Short hub only — link to aspect pages, no file dump.",
}


class IncompleteLoreportError(RuntimeError):
    """Raised when service folders lack required compiled markdown files."""


@dataclass(frozen=True, slots=True)
class DocAspect:
    id: str
    label: str
    human_files: tuple[str, ...]
    loreport_file: str


@dataclass(frozen=True, slots=True)
class ServiceDocPattern:
    service_name: str
    human_doc_root: str | None
    readme_path: str | None
    aspects: tuple[DocAspect, ...] = field(default_factory=tuple)

    @property
    def loreport_dir(self) -> str:
        return f"services/{self.service_name}"

    def to_dict(self) -> dict[str, object]:
        return {
            "serviceName": self.service_name,
            "humanDocRoot": self.human_doc_root,
            "readmePath": self.readme_path,
            "aspects": [
                {
                    "id": aspect.id,
                    "label": aspect.label,
                    "humanFiles": list(aspect.human_files),
                    "loreportFile": aspect.loreport_file,
                }
                for aspect in self.aspects
            ],
            "driftFile": DRIFT_FILE,
        }


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _score_aspect(filename: str) -> tuple[str, int]:
    stem = Path(filename).stem.lower()
    best_id = "general"
    best_score = 0
    for aspect_id, keywords in ASPECT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in stem)
        if score > best_score:
            best_id = aspect_id
            best_score = score
    return best_id, best_score


def _human_doc_root(service_path: Path) -> Path | None:
    for dirname in HUMAN_DOC_DIR_NAMES:
        doc_dir = service_path / dirname
        if doc_dir.is_dir():
            try:
                if any(doc_dir.rglob("*.md")):
                    return doc_dir
            except OSError:
                continue
    return None


def _collect_human_markdown(service_path: Path, doc_root: Path | None) -> list[str]:
    files: list[str] = []
    if doc_root is not None:
        for path in sorted(doc_root.rglob("*.md")):
            if path.is_file():
                files.append(path.relative_to(service_path).as_posix())
    readme = service_path / "README.md"
    if readme.is_file():
        files.append("README.md")
    return files


def discover_service_doc_pattern(repo_path: Path, service_name: str) -> ServiceDocPattern:
    service_path = repo_path / service_name
    if not service_path.is_dir():
        return ServiceDocPattern(service_name=service_name, human_doc_root=None, readme_path=None)

    doc_root = _human_doc_root(service_path)
    human_doc_root = doc_root.relative_to(service_path).as_posix() if doc_root else None
    readme_path = "README.md" if (service_path / "README.md").is_file() else None
    human_files = _collect_human_markdown(service_path, doc_root)

    grouped: dict[str, list[str]] = {}
    for human_file in human_files:
        if human_file == "README.md":
            grouped.setdefault("overview", []).append(human_file)
            continue
        aspect_id, _ = _score_aspect(human_file)
        grouped.setdefault(aspect_id, []).append(human_file)

    aspects: list[DocAspect] = []
    if "overview" in grouped or readme_path:
        overview_files = tuple(grouped.get("overview", ()))
        if readme_path and readme_path not in overview_files:
            overview_files = (readme_path,) + overview_files
        aspects.append(
            DocAspect(
                id="overview",
                label="Overview",
                human_files=overview_files or ((readme_path,) if readme_path else ()),
                loreport_file=ASPECT_LOREPORT_FILES["overview"],
            )
        )

    for aspect_id in sorted(grouped):
        if aspect_id == "overview":
            continue
        files = tuple(sorted(grouped[aspect_id]))
        label = aspect_id.replace("-", " ").title()
        loreport_file = ASPECT_LOREPORT_FILES.get(aspect_id, f"{_normalize_name(aspect_id)}.md")
        aspects.append(
            DocAspect(
                id=aspect_id,
                label=label,
                human_files=files,
                loreport_file=loreport_file,
            )
        )

    if not aspects:
        aspects = (
            DocAspect(
                id="overview",
                label="Overview",
                human_files=(),
                loreport_file=ASPECT_LOREPORT_FILES["overview"],
            ),
        )

    return ServiceDocPattern(
        service_name=service_name,
        human_doc_root=human_doc_root,
        readme_path=readme_path,
        aspects=tuple(aspects),
    )


def discover_repo_doc_patterns(
    repo_path: Path,
    service_names: tuple[str, ...],
) -> dict[str, ServiceDocPattern]:
    return {
        name: discover_service_doc_pattern(repo_path, name)
        for name in service_names
    }


def write_service_patterns(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> None:
    for pattern in patterns.values():
        target = repo_path / loreport_dir / "services" / pattern.service_name / PATTERN_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(pattern.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def format_service_pattern_summary(
    pattern: ServiceDocPattern,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> str:
    lines = [
        f"### `{pattern.service_name}`",
        f"- Loreport folder: `{loreport_dir}/services/{pattern.service_name}/`",
        f"- Human docs root: `{pattern.human_doc_root or 'none'}`",
        "- Required files:",
        f"  - `{pattern.loreport_dir}/{DRIFT_FILE}` — drift registry by severity",
    ]
    for aspect in pattern.aspects:
        human = ", ".join(f"`{path}`" for path in aspect.human_files) or "code-first"
        hint = ASPECT_CONTENT_HINTS.get(aspect.id, "Extract concrete claims from human docs.")
        lines.append(
            f"  - `{pattern.loreport_dir}/{aspect.loreport_file}` — `{aspect.label}` "
            f"(human: {human}). {hint}"
        )
    return "\n".join(lines)


def format_doc_patterns_block(
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> str:
    if not patterns:
        return ""
    blocks = [
        format_service_pattern_summary(pattern, loreport_dir=loreport_dir)
        for pattern in patterns.values()
    ]
    return "\n\n".join(blocks)


def required_lore_files_for_pattern(pattern: ServiceDocPattern) -> tuple[str, ...]:
    files = {DRIFT_FILE}
    for aspect in pattern.aspects:
        files.add(aspect.loreport_file)
    return tuple(sorted(files))


def find_incomplete_service_folders(
    repo_path: Path,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> list[str]:
    services_root = repo_path / loreport_dir / "services"
    if not services_root.is_dir():
        return []

    missing: list[str] = []
    for service_dir in sorted(services_root.iterdir(), key=lambda path: path.name.lower()):
        if not service_dir.is_dir():
            continue
        pattern_path = service_dir / PATTERN_FILE
        if not pattern_path.is_file():
            continue
        try:
            payload = json.loads(pattern_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            missing.append(f"{service_dir.name}/_pattern.json (invalid)")
            continue
        required = {DRIFT_FILE}
        for aspect in payload.get("aspects", []):
            lore_file = aspect.get("loreportFile")
            if isinstance(lore_file, str):
                required.add(lore_file)
        for filename in sorted(required):
            if not (service_dir / filename).is_file():
                missing.append(f"{service_dir.name}/{filename}")
    return missing


def format_incomplete_services_warning(missing: list[str]) -> str:
    if not missing:
        return ""
    preview = ", ".join(missing[:12])
    suffix = f" (+{len(missing) - 12} more)" if len(missing) > 12 else ""
    return f"Incomplete service folders — missing: {preview}{suffix}"


COMPILED_ASPECT_RULES = """
Compiled aspect page (`{loreport_dir}/services/<name>/<aspect>.md`) — full UI doc, NOT a path index.

Write workflow per aspect:
1. read_file every human file listed in _pattern.json for this aspect
2. read_file code files needed to verify claims
3. write compiled page with substance FROM human docs

Required structure (ALL headings in OUTPUT LANGUAGE):
- `> Источник: <human-path>` — provenance only
- ## Замысел — concrete content extracted from human docs:
  - api-surface: table method | path | назначение (from curl/openapi examples)
  - messaging: table queue/event | payload | producer/consumer
  - data-model: entities, fields, relations (from ER/spec)
  - specification: sections: boundaries, modules, flows (from tech spec)
  - Minimum 5 concrete rows/bullets sourced from human doc text
- ## Сверка с кодом — one row per Intent claim (NOT per file):
  | Заявление | Где в коде | Статус |
  Статус: совпадает | расхождение | нет в коде | нет в документации
- ## Детали — optional code-only findings (brief)

FORBIDDEN on aspect pages:
- Page that is mostly paths or "## Открытые файлы" as main body
- Vague one-paragraph Intent without endpoints/queues/entities from human doc
- Marking whole file "совпадает" without checking specific claims
- English headings (# Api, # Messaging) when OUTPUT LANGUAGE is not English
""".strip()

INDEX_FILE_RULES = """
index.md — short service hub (NOT a duplicate of all aspects):
- ## Назначение — one paragraph
- ## Разделы документации — links to sibling aspect .md in same folder
- ## Интеграции — compact cross-service table
- ## Критичные расхождения — top items with link to drift.md
FORBIDDEN on index.md: long file inventories, duplicating aspect Intent tables.
""".strip()

DRIFT_FILE_RULES = """
Drift registry (`{loreport_dir}/services/<name>/drift.md`):
- Sections in OUTPUT LANGUAGE: ## Критично, ## Предупреждение, ## Информация
- Each item: `категория на OUTPUT LANGUAGE` — конкретное расхождение: цитата/тема из human doc +
  конкретное место в коде + что не сходится
- Gap category labels MUST be translated — never English labels in Russian pages
- FORBIDDEN: vague "нужно подтвердить в main.py" when main.py was read; vague navigation-only items
- Code = implementation truth; human docs = intent truth
""".strip()

SERVICE_FOLDER_LAYOUT = """
Service output layout (required for every service):
```
{loreport_dir}/services/<service-name>/
  _pattern.json     # pre-generated manifest — read and follow; update if human docs changed
  index.md          # service overview + integration map + aspect index
  drift.md          # all drifts by severity
  <aspect>.md       # one compiled file per aspect in _pattern.json
```

Legacy flat `{loreport_dir}/services/<name>.md` is deprecated — use folder layout only.
Follow `_pattern.json` aspects — do not invent a different file set per service.
""".strip()
