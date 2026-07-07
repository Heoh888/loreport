from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from loreport_core.constants import LOREPORT_DIR
from loreport_core.git.evidence import UpdateMetadata
from loreport_core.types import LoreportCommand

EXCLUDED_TOP_LEVEL = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "target",
        ".idea",
        ".vscode",
        ".cursor",
        ".github",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
    }
)

HUMAN_DOC_DIR_NAMES = ("tech.docs", "docs")


@dataclass(frozen=True, slots=True)
class ServiceScope:
    name: str
    has_tech_docs: bool
    has_readme: bool

    @property
    def has_human_docs(self) -> bool:
        return self.has_tech_docs or self.has_readme


@dataclass(frozen=True, slots=True)
class RepoScope:
    services: tuple[ServiceScope, ...]

    @property
    def is_monorepo(self) -> bool:
        return len(self.services) > 2

    @property
    def service_names(self) -> tuple[str, ...]:
        return tuple(service.name for service in self.services)


def detect_monorepo_services(
    repo_path: Path,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> RepoScope:
    repo_path = repo_path.resolve()
    excluded = EXCLUDED_TOP_LEVEL | {loreport_dir}
    services: list[ServiceScope] = []

    try:
        entries = sorted(repo_path.iterdir(), key=lambda path: path.name.lower())
    except OSError:
        return RepoScope(services=())

    for entry in entries:
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name in excluded:
            continue
        services.append(
            ServiceScope(
                name=name,
                has_tech_docs=_has_human_doc_dir(entry),
                has_readme=(entry / "README.md").is_file(),
            )
        )

    return RepoScope(services=tuple(services))


def _has_human_doc_dir(service_path: Path) -> bool:
    for dirname in HUMAN_DOC_DIR_NAMES:
        doc_dir = service_path / dirname
        if doc_dir.is_dir():
            try:
                if any(doc_dir.iterdir()):
                    return True
            except OSError:
                continue
    return False


def format_service_inventory(scope: RepoScope) -> str:
    if not scope.services:
        return "No top-level service directories were detected."
    lines: list[str] = []
    for service in scope.services:
        flags: list[str] = []
        if service.has_tech_docs:
            flags.append("tech.docs")
        if service.has_readme:
            flags.append("README")
        if not flags:
            flags.append("no human docs")
        lines.append(f"- {service.name} ({', '.join(flags)})")
    return "\n".join(lines)


def affected_services_from_paths(
    paths: Iterable[str],
    scope: RepoScope,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> tuple[str, ...]:
    known = set(scope.service_names)
    affected: set[str] = set()
    for raw in paths:
        path = raw.strip().strip('"').lstrip("./")
        if not path or path.startswith(f"{loreport_dir}/"):
            continue
        top = path.split("/", 1)[0]
        if top in known:
            affected.add(top)
    return tuple(sorted(affected))


async def collect_changed_paths(
    repo_path: Path,
    *,
    command: LoreportCommand,
    last_update: UpdateMetadata | None,
) -> list[str]:
    from loreport_core.git import run_git

    paths: set[str] = set()

    unstaged = await run_git(repo_path, "diff", "--name-only", "HEAD")
    for line in unstaged.splitlines():
        stripped = line.strip()
        if stripped:
            paths.add(stripped)

    if command == "update" and last_update and last_update.git_head:
        since_head = await run_git(
            repo_path,
            "diff",
            "--name-only",
            f"{last_update.git_head}..HEAD",
        )
        for line in since_head.splitlines():
            stripped = line.strip()
            if stripped:
                paths.add(stripped)

    return sorted(paths)
