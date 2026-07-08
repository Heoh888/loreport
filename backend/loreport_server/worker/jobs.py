import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from loreport_core.agent import run_loreport_agent
from loreport_core.constants import resolve_model_id, resolve_provider
from loreport_core.git import get_head
from loreport_core.snapshot import create_loreport_content_snapshot
from loreport_core.types import SyncJobPayload
from loreport_server.config import get_settings
from loreport_server.db.models import SyncJob
from loreport_server.db.session import _ensure_engine

logger = logging.getLogger(__name__)


async def process_job(payload: SyncJobPayload) -> None:
    settings = get_settings()
    repo_path = Path(payload.repo_path)
    job_id = uuid.UUID(payload.id)
    resolved_provider = resolve_provider(settings.loreport_provider)
    resolved_model = resolve_model_id(settings.loreport_model_id, resolved_provider)

    session_factory = _ensure_engine()
    async with session_factory() as session:
        result = await session.execute(select(SyncJob).where(SyncJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            logger.error("Job %s not found", job_id)
            return

        job.status = "running"
        job.snapshot_before = create_loreport_content_snapshot(repo_path, settings.loreport_dir)
        try:
            job.git_head = await get_head(repo_path)
        except RuntimeError:
            job.git_head = None
        await session.commit()

    changed = False
    error: str | None = None
    status = "done"
    try:
        logger.info("Agent started job=%s command=%s repo=%s", job_id, payload.command, repo_path)
        changed = await run_loreport_agent(
            payload.command,
            repo_path,
            loreport_dir=settings.loreport_dir,
            model_id=settings.loreport_model_id,
            provider=settings.loreport_provider,
            language=payload.language or settings.loreport_language,
            workflow_enabled=settings.loreport_workflow_enabled,
            dynamic_workflow_enabled=settings.loreport_dynamic_workflow_enabled,
            max_parallel_subagents=settings.loreport_max_parallel_subagents,
            subagent_model_id=settings.loreport_subagent_model_id,
            update_max_passes=settings.loreport_update_max_passes,
            verification_convergence_passes=settings.loreport_verification_convergence_passes,
        )
        logger.info("Agent finished job=%s changed=%s", job_id, changed)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed", job_id)
        status = "failed"
        error = str(exc)

    async with session_factory() as session:
        result = await session.execute(select(SyncJob).where(SyncJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return
        job.status = status
        job.changed = changed if status == "done" else None
        job.model = resolved_model if status == "done" else job.model
        job.snapshot_after = (
            create_loreport_content_snapshot(repo_path, settings.loreport_dir)
            if status == "done"
            else job.snapshot_after
        )
        job.error = error
        job.finished_at = datetime.now(UTC)
        await session.commit()
