import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from loreport_core.constants import LOREPORT_DIR, UPDATE_METADATA_FILE
from loreport_core.git.evidence import RunContext, create_run_context, read_last_update

__all__ = [
    "RunContext",
    "create_run_context",
    "get_head",
    "read_last_update",
    "run_git",
    "write_last_update_metadata",
]


async def run_git(repo_path: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git",
        "--no-pager",
        *args,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    parts = [stdout.decode().strip(), stderr.decode().strip()]
    return "\n".join(part for part in parts if part)


async def get_head(repo_path: Path) -> str:
    head = await run_git(repo_path, "rev-parse", "HEAD")
    return head.splitlines()[0] if head else ""


async def write_last_update_metadata(
    repo_path: Path,
    command: str,
    model_id: str,
    loreport_dir: str = LOREPORT_DIR,
) -> None:
    lore_dir = repo_path / loreport_dir
    lore_dir.mkdir(parents=True, exist_ok=True)
    head = await get_head(repo_path)
    payload = {
        "command": command,
        "updatedAt": datetime.now(UTC).isoformat(),
        "gitHead": head or None,
        "model": model_id,
    }
    meta_path = lore_dir / UPDATE_METADATA_FILE
    meta_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
