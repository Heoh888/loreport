import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from loreport_server.api.routes import docs, health, settings, sync, webhooks
from loreport_server.config import get_settings
from loreport_server.db.session import init_db
from loreport_server.queue.local import run_standalone_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    await init_db()
    from loreport_server.worker.recovery import recover_stale_jobs

    await recover_stale_jobs()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(run_standalone_worker(stop_event))
    logger.info("Loreport started: api + in-process worker")

    yield

    stop_event.set()
    await worker_task


app = FastAPI(title="Loreport", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(sync.router)
app.include_router(docs.router)
app.include_router(webhooks.router)
app.include_router(settings.router)

settings = get_settings()
static_dir = Path(settings.static_dir) if settings.static_dir else None
INDEX_HEADERS = {"Cache-Control": "no-cache"}

if static_dir and static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/")
    async def spa_index() -> FileResponse:
        return FileResponse(static_dir / "index.html", headers=INDEX_HEADERS)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        index = static_dir / "index.html"
        if full_path.startswith("api/") or full_path.startswith("webhooks/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404)
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(index, headers=INDEX_HEADERS)
