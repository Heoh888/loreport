import os
from typing import Literal

LoreportProvider = Literal["openrouter", "anthropic", "openai", "baseten", "fireworks"]

LOREPORT_DIR = "loreport"
UPDATE_METADATA_FILE = ".last-update.json"
UPDATE_METADATA_PATH = f"{LOREPORT_DIR}/{UPDATE_METADATA_FILE}"

DEFAULT_PROVIDER: LoreportProvider = "openai"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

OPENROUTER_API_KEY_ENV_KEY = "OPENROUTER_API_KEY"
ANTHROPIC_API_KEY_ENV_KEY = "ANTHROPIC_API_KEY"
OPENAI_API_KEY_ENV_KEY = "OPENAI_API_KEY"
BASETEN_API_KEY_ENV_KEY = "BASETEN_API_KEY"
FIREWORKS_API_KEY_ENV_KEY = "FIREWORKS_API_KEY"

LOREPORT_PROVIDER_ENV_KEY = "LOREPORT_PROVIDER"
LOREPORT_MODEL_ID_ENV_KEY = "LOREPORT_MODEL_ID"
LOREPORT_LANGUAGE_ENV_KEY = "LOREPORT_LANGUAGE"
DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "zh": "中文",
    "ja": "日本語",
}

PROVIDER_API_KEY_ENV: dict[LoreportProvider, str] = {
    "openrouter": OPENROUTER_API_KEY_ENV_KEY,
    "anthropic": ANTHROPIC_API_KEY_ENV_KEY,
    "openai": OPENAI_API_KEY_ENV_KEY,
    "baseten": BASETEN_API_KEY_ENV_KEY,
    "fireworks": FIREWORKS_API_KEY_ENV_KEY,
}

PROVIDER_DEFAULT_MODEL: dict[LoreportProvider, str] = {
    "openrouter": "z-ai/glm-5.2",
    "anthropic": "claude-haiku-4-5",
    "openai": "gpt-5.4-mini",
    "baseten": "zai-org/GLM-5.2",
    "fireworks": "accounts/fireworks/models/glm-5p2",
}


def resolve_provider(provider: str | None = None) -> LoreportProvider:
    raw = (provider or os.environ.get(LOREPORT_PROVIDER_ENV_KEY) or "").strip().lower()
    if raw in PROVIDER_API_KEY_ENV:
        return raw  # type: ignore[return-value]
    if os.environ.get(OPENAI_API_KEY_ENV_KEY):
        return "openai"
    if os.environ.get(OPENROUTER_API_KEY_ENV_KEY):
        return "openrouter"
    if os.environ.get(ANTHROPIC_API_KEY_ENV_KEY):
        return "anthropic"
    return DEFAULT_PROVIDER


def resolve_model_id(model_id: str | None, provider: LoreportProvider) -> str:
    return (model_id or os.environ.get(LOREPORT_MODEL_ID_ENV_KEY) or PROVIDER_DEFAULT_MODEL[provider]).strip()


def resolve_language(language: str | None = None) -> str:
    raw = (language or os.environ.get(LOREPORT_LANGUAGE_ENV_KEY) or DEFAULT_LANGUAGE).strip().lower()
    if raw in SUPPORTED_LANGUAGES:
        return raw
    return DEFAULT_LANGUAGE


def language_label(language: str) -> str:
    return SUPPORTED_LANGUAGES.get(language, language)


def model_string(provider: LoreportProvider, model_id: str) -> str:
    if provider == "openrouter":
        return f"openrouter:{model_id}"
    if provider == "anthropic":
        return f"anthropic:{model_id}"
    if provider == "openai":
        return f"openai:{model_id}"
    if provider == "baseten":
        return f"baseten:{model_id}"
    return f"fireworks:{model_id}"


def ensure_provider_key(provider: LoreportProvider) -> None:
    env_key = PROVIDER_API_KEY_ENV[provider]
    if not os.environ.get(env_key):
        raise RuntimeError(f"{env_key} is required to run Loreport with {provider}.")
