from typing import Literal

from pydantic import BaseModel

LoreportCommand = Literal["init", "update", "chat"]
SyncJobStatus = Literal["pending", "running", "done", "failed"]


class SyncJobPayload(BaseModel):
    id: str
    command: LoreportCommand
    repo_path: str
    language: str | None = None
