from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from loreport_core.agent.subagents import create_subagent_specs
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
from loreport_core.scope import (
    RepoScope,
    affected_services_from_paths,
    collect_changed_paths,
    detect_monorepo_services,
)
from loreport_core.snapshot import create_loreport_content_snapshot
from loreport_core.types import LoreportCommand

if TYPE_CHECKING:
    from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)

DEFAULT_MAX_PARALLEL_SUBAGENTS = 5
DEFAULT_UPDATE_MAX_PASSES = 3
UPDATE_WORKFLOW_SERVICE_THRESHOLD = 3


def _create_thread_id(repo_path: Path) -> str:
    digest = hashlib.sha256(str(repo_path.resolve()).encode()).hexdigest()[:32]
    return f"loreport-{digest}-{int(time.time()):x}"


def _should_use_workflow(
    command: LoreportCommand,
    *,
    workflow_enabled: bool,
    scope: RepoScope,
    affected_services: tuple[str, ...],
) -> bool:
    if not workflow_enabled:
        return False
    if command == "init":
        return scope.is_monorepo
    return len(affected_services) > UPDATE_WORKFLOW_SERVICE_THRESHOLD


def _build_interpreter_middleware(
    *,
    dynamic_workflow_enabled: bool,
) -> list[AgentMiddleware]:
    if not dynamic_workflow_enabled:
        return []
    try:
        from langchain_quickjs import CodeInterpreterMiddleware
    except ImportError:
        logger.warning(
            "langchain-quickjs is not installed; falling back to static subagents via task tool"
        )
        return []

    return [CodeInterpreterMiddleware(subagents=True)]


def _run_agent_sync(
    *,
    command: LoreportCommand,
    repo_path: Path,
    loreport_dir: str,
    provider: LoreportProvider,
    model_id: str,
    user_message: str,
    language: str,
    scope: RepoScope,
    use_workflow: bool,
    dynamic_workflow: bool,
    subagent_model_id: str | None,
) -> None:
    ensure_provider_key(provider)

    backend = LocalShellBackend(
        root_dir=str(repo_path),
        virtual_mode=True,
        timeout=120,
        max_output_bytes=100_000,
    )

    subagents = (
        create_subagent_specs(
            loreport_dir=loreport_dir,
            language=language,
            provider=provider,
            main_model_id=model_id,
            subagent_model_id=subagent_model_id,
        )
        if use_workflow
        else None
    )

    middleware = _build_interpreter_middleware(
        dynamic_workflow_enabled=use_workflow and dynamic_workflow,
    )
    use_dynamic = bool(middleware)

    agent = create_deep_agent(
        model=model_string(provider, model_id),
        tools=[],
        backend=backend,
        middleware=middleware,
        system_prompt=create_system_prompt(command, loreport_dir, language=language),
        subagents=subagents,
    )

    logger.info(
        "Running Loreport agent command=%s model=%s language=%s workflow=%s dynamic=%s services=%d",
        command,
        model_id,
        language,
        use_workflow,
        use_dynamic,
        len(scope.services),
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
    workflow_enabled: bool = True,
    dynamic_workflow_enabled: bool = True,
    max_parallel_subagents: int = DEFAULT_MAX_PARALLEL_SUBAGENTS,
    subagent_model_id: str | None = None,
    update_max_passes: int = DEFAULT_UPDATE_MAX_PASSES,
) -> bool:
    """Run init/update agent. Returns True if lore content changed."""
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise FileNotFoundError(f"Repository path not found: {repo_path}")

    resolved_provider = resolve_provider(provider)
    resolved_model = resolve_model_id(model_id, resolved_provider)
    resolved_language = resolve_language(language)

    scope = detect_monorepo_services(repo_path, loreport_dir=loreport_dir)
    context = await create_run_context(command, repo_path, loreport_dir=loreport_dir)

    changed_paths = await collect_changed_paths(
        repo_path,
        command=command,
        last_update=context.last_update,
    )
    affected_services = affected_services_from_paths(
        changed_paths,
        scope,
        loreport_dir=loreport_dir,
    )
    use_workflow = _should_use_workflow(
        command,
        workflow_enabled=workflow_enabled,
        scope=scope,
        affected_services=affected_services,
    )
    use_dynamic = use_workflow and dynamic_workflow_enabled

    user_message = create_run_user_message(
        command,
        str(repo_path),
        context,
        loreport_dir=loreport_dir,
        language=resolved_language,
        scope=scope,
        workflow_enabled=use_workflow,
        dynamic_workflow=use_dynamic,
        affected_services=affected_services,
        max_parallel_subagents=max_parallel_subagents,
        update_max_passes=update_max_passes,
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
        scope=scope,
        use_workflow=use_workflow,
        dynamic_workflow=use_dynamic,
        subagent_model_id=subagent_model_id,
    )

    after = create_loreport_content_snapshot(repo_path, loreport_dir)
    changed = before != after
    if changed:
        await write_last_update_metadata(repo_path, command, resolved_model, loreport_dir)
        logger.info("Loreport content changed for %s", repo_path)
    else:
        logger.info("Loreport content unchanged for %s", repo_path)
    return changed
