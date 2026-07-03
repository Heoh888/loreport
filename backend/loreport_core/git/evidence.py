from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from loreport_core.constants import LOREPORT_DIR, UPDATE_METADATA_FILE
from loreport_core.types import LoreportCommand


@dataclass
class UpdateMetadata:
    updated_at: str
    command: str
    model: str
    git_head: str | None = None


@dataclass
class RunContext:
    last_update: UpdateMetadata | None
    git_summary: str


async def create_run_context(
    command: LoreportCommand,
    repo_path: Path,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> RunContext:
    last_update = await read_last_update(repo_path, loreport_dir)
    if command == "chat":
        return RunContext(last_update=last_update, git_summary="Not applicable for chat.")
    git_summary = await create_git_summary(command, repo_path, last_update, loreport_dir)
    return RunContext(last_update=last_update, git_summary=git_summary)


async def read_last_update(repo_path: Path, loreport_dir: str = LOREPORT_DIR) -> UpdateMetadata | None:
    meta_path = repo_path / loreport_dir / UPDATE_METADATA_FILE
    if not meta_path.is_file():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    updated_at = raw.get("updatedAt") or raw.get("updated_at")
    model = raw.get("model") or raw.get("modelId")
    command = raw.get("command")
    if not isinstance(updated_at, str) or not isinstance(model, str) or not isinstance(command, str):
        return None

    git_head = raw.get("gitHead") or raw.get("git_head")
    return UpdateMetadata(
        updated_at=updated_at,
        command="init" if command == "init" else "update",
        model=model,
        git_head=git_head if isinstance(git_head, str) else None,
    )


async def create_git_summary(
    command: LoreportCommand,
    repo_path: Path,
    last_update: UpdateMetadata | None,
    loreport_dir: str,
) -> str:
    from loreport_core.git import run_git

    sections: list[str] = []
    status = await run_git(repo_path, "status", "--short")
    head = await run_git(repo_path, "rev-parse", "HEAD")
    sections.append(_format_section("git status --short", status))
    sections.append(_format_section("git rev-parse HEAD", head or "(unknown)"))

    if command == "update" and last_update and last_update.git_head:
        log = await run_git(
            repo_path,
            "log",
            f"{last_update.git_head}..HEAD",
            "--name-status",
            "--oneline",
        )
        sections.append(
            _format_section(
                f"git log {last_update.git_head}..HEAD --name-status --oneline",
                log,
            )
        )
    elif command == "update" and last_update:
        log = await run_git(
            repo_path,
            "log",
            "--since",
            last_update.updated_at,
            "--name-status",
            "--oneline",
        )
        sections.append(
            _format_section(
                f"git log --since {last_update.updated_at} --name-status --oneline",
                log,
            )
        )
    else:
        if command == "update":
            sections.append("No prior Loreport update metadata was found.")
        log = await run_git(
            repo_path,
            "log",
            "--max-count=20",
            "--name-status",
            "--oneline",
        )
        sections.append(
            _format_section("git log --max-count=20 --name-status --oneline", log)
        )

    diff = await run_git(repo_path, "diff", "--name-status", "HEAD")
    sections.append(_format_section("git diff --name-status HEAD", diff))
    _ = loreport_dir
    return "\n\n".join(sections)


def _format_section(command: str, output: str) -> str:
    body = output if output else "(no output)"
    return f"$ {command}\n{body}"
