from __future__ import annotations

import asyncio
import logging

from loreport_core.types import SyncJobPayload
from loreport_server.worker.jobs import process_job

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[SyncJobPayload] | None = None


def get_queue() -> asyncio.Queue[SyncJobPayload]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def enqueue(payload: SyncJobPayload) -> None:
    await get_queue().put(payload)


async def run_standalone_worker(stop_event: asyncio.Event) -> None:
    queue = get_queue()
    logger.info("Standalone worker started")
    while not stop_event.is_set():
        try:
            payload = await asyncio.wait_for(queue.get(), timeout=1.0)
        except TimeoutError:
            continue
        logger.info("Processing job %s command=%s", payload.id, payload.command)
        try:
            await process_job(payload)
        finally:
            queue.task_done()
    logger.info("Standalone worker stopped")
