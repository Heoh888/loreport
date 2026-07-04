from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loreport_core.git import get_head
from loreport_core.snapshot import create_loreport_content_snapshot
from loreport_core.constants import resolve_language
from loreport_core.types import LoreportCommand
from loreport_server.config import Settings, get_settings
from loreport_server.db.models import SyncJob
from loreport_server.db.session import get_session
from loreport_server.queue.local import publish_sync_job

router = APIRouter(prefix="/api/sync", tags=["sync"])


class TriggerRequest(BaseModel):
    command: LoreportCommand = "update"
    language: str | None = None


class TriggerResponse(BaseModel):
    command: LoreportCommand
    job_id: str


class SyncStatusResponse(BaseModel):
    state: str
    last_run: datetime | None = None
    head: str | None = None
    changed: bool | None = None
    error: str | None = None


class SyncHistoryItem(BaseModel):
    id: str
    command: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    changed: bool | None
    model: str | None
    error: str | None


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_sync(
    body: TriggerRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TriggerResponse:
    repo_path = Path(settings.repo_path)
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail=f"REPO_PATH not found: {repo_path}")

    job = SyncJob(command=body.command, status="pending")
    session.add(job)
    await session.commit()
    await session.refresh(job)

    await publish_sync_job(
        job_id=job.id,
        command=body.command,
        repo_path=str(repo_path),
        language=resolve_language(body.language or settings.loreport_language),
    )
    return TriggerResponse(command=body.command, job_id=str(job.id))


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SyncStatusResponse:
    result = await session.execute(
        select(SyncJob).order_by(SyncJob.started_at.desc()).limit(1)
    )
    job = result.scalar_one_or_none()
    head = None
    repo_path = Path(settings.repo_path)
    if repo_path.is_dir():
        try:
            head = await get_head(repo_path)
        except RuntimeError:
            head = None

    if job is None:
        return SyncStatusResponse(state="idle", head=head)

    state = "running" if job.status in {"pending", "running"} else job.status
    if job.status == "done":
        state = "idle"
    if job.status == "failed":
        state = "error"

    return SyncStatusResponse(
        state=state,
        last_run=job.finished_at or job.started_at,
        head=head or job.git_head,
        changed=job.changed,
        error=job.error,
    )


@router.get("/history", response_model=list[SyncHistoryItem])
async def sync_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[SyncHistoryItem]:
    result = await session.execute(
        select(SyncJob).order_by(SyncJob.started_at.desc()).limit(limit)
    )
    jobs = result.scalars().all()
    return [
        SyncHistoryItem(
            id=str(job.id),
            command=job.command,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            changed=job.changed,
            model=job.model,
            error=job.error,
        )
        for job in jobs
    ]


@router.get("/snapshot")
async def current_snapshot(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    repo_path = Path(settings.repo_path)
    snapshot = create_loreport_content_snapshot(repo_path, settings.loreport_dir)
    return {"snapshot": snapshot}
