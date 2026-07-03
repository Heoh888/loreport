from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from loreport_server.config import Settings, get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class GitWebhookBody(BaseModel):
    ref: str | None = None
    after: str | None = None


@router.post("/git")
async def git_webhook(
    body: GitWebhookBody,
    settings: Settings = Depends(get_settings),
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, str]:
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    # TODO: debounce + publish sync job when ref matches default branch
    _ = body
    return {"status": "accepted"}
