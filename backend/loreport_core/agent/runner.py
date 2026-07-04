from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from loreport_core.constants import (
    LOREPORT_DIR,
    LoreportProvider,
    ensure_provider_key,
    model_string,
    resolve_language,
    resolve_model_id,
    resolve_provider,
)
from loreport_core.git import create_run_context, write_last_update_metadata
from loreport_core.prompts import create_run_user_message, create_system_prompt
from loreport_core.snapshot import create_loreport_content_snapshot
from loreport_core.types import LoreportCommand

logger = logging.getLogger(__name__)


def _create_thread_id(repo_path: Path) -> str:
    digest = hashlib.sha256(str(repo_path.resolve()).encode()).hexdigest()[:32]
    return f"loreport-{digest}-{int(time.time()):x}"


def _run_agent_sync(
    *,
    command: LoreportCommand,
    repo_path: Path,
    loreport_dir: str,
    provider: LoreportProvider,
    model_id: str,
    user_message: str,
    language: str,
) -> None:
    ensure_provider_key(provider)

    backend = LocalShellBackend(
        root_dir=str(repo_path),
        virtual_mode=True,
        timeout=120,
        max_output_bytes=100_000,
    )

    agent = create_deep_agent(
        model=model_string(provider, model_id),
        tools=[],
        backend=backend,
        system_prompt=create_system_prompt(command, loreport_dir, language=language),
    )

    logger.info(
        "Running Loreport agent command=%s model=%s language=%s",
        command,
        model_id,
        language,
    )
    agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": _create_thread_id(repo_path)}},
    )


async def run_loreport_agent(
    command: LoreportCommand,
    repo_path: Path,
    *,
    loreport_dir: str = LOREPORT_DIR,
    model_id: str | None = None,
    provider: str | None = None,
    language: str | None = None,
) -> bool:
    """Run init/update agent. Returns True if lore content changed."""
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise FileNotFoundError(f"Repository path not found: {repo_path}")

    resolved_provider = resolve_provider(provider)
    resolved_model = resolve_model_id(model_id, resolved_provider)
    resolved_language = resolve_language(language)

    context = await create_run_context(command, repo_path, loreport_dir=loreport_dir)
    user_message = create_run_user_message(
        command,
        str(repo_path),
        context,
        loreport_dir=loreport_dir,
        language=resolved_language,
    )

    before = create_loreport_content_snapshot(repo_path, loreport_dir)

    await asyncio.to_thread(
        _run_agent_sync,
        command=command,
        repo_path=repo_path,
        loreport_dir=loreport_dir,
        provider=resolved_provider,
        model_id=resolved_model,
        user_message=user_message,
        language=resolved_language,
    )

    after = create_loreport_content_snapshot(repo_path, loreport_dir)
    changed = before != after
    if changed:
        await write_last_update_metadata(repo_path, command, resolved_model, loreport_dir)
        logger.info("Loreport content changed for %s", repo_path)
    else:
        logger.info("Loreport content unchanged for %s", repo_path)
    return changed
