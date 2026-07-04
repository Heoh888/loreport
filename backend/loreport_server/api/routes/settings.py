from fastapi import APIRouter, Depends
from pydantic import BaseModel

from loreport_core.constants import SUPPORTED_LANGUAGES, resolve_language
from loreport_server.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LanguageOption(BaseModel):
    code: str
    label: str


class SettingsResponse(BaseModel):
    provider: str
    model_id: str | None
    language: str
    languages: list[LanguageOption]


@router.get("", response_model=SettingsResponse)
async def read_settings(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    language = resolve_language(settings.loreport_language)
    return SettingsResponse(
        provider=settings.loreport_provider,
        model_id=settings.loreport_model_id,
        language=language,
        languages=[
            LanguageOption(code=code, label=label)
            for code, label in SUPPORTED_LANGUAGES.items()
        ],
    )
