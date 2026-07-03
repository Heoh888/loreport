import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from loreport_server.db.models import SyncJob
from loreport_server.db.session import _ensure_engine

logger = logging.getLogger(__name__)

STALE_JOB_AFTER = timedelta(hours=2)


async def recover_stale_jobs() -> None:
    """Mark orphaned running jobs as failed after restart or crash."""
    session_factory = _ensure_engine()
    cutoff = datetime.now(UTC) - STALE_JOB_AFTER
    async with session_factory() as session:
        result = await session.execute(
            select(SyncJob).where(
                SyncJob.status.in_(("pending", "running")),
                SyncJob.started_at < cutoff,
            )
        )
        stale_jobs = result.scalars().all()
        if not stale_jobs:
            return
        for job in stale_jobs:
            job.status = "failed"
            job.error = "Job interrupted or timed out. Trigger sync again."
            job.finished_at = datetime.now(UTC)
            logger.warning("Recovered stale job %s", job.id)
        await session.commit()
