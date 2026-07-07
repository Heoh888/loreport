from __future__ import annotations

from loreport_core.constants import (
    LoreportProvider,
    language_label,
    model_string,
    resolve_language,
    resolve_model_id,
)
from loreport_core.integrity import GAP_FORMAT_RULES, SHALLOW_RESEARCH_FORBIDDEN
from loreport_core.language import (
    SERVICE_PAGE_SECTIONS,
    output_language_policy,
)


def _resolved_subagent_model(
    provider: LoreportProvider,
    main_model_id: str,
    subagent_model_id: str | None,
) -> str:
    model_id = subagent_model_id or main_model_id
    return model_string(provider, resolve_model_id(model_id, provider))


def _service_researcher_prompt(loreport_dir: str, language: str) -> str:
    doc_language = resolve_language(language)
    return f"""
You are a Loreport service integrity researcher. Read-only — no file writes.

{output_language_policy(doc_language)}

Return research notes in OUTPUT LANGUAGE ({language_label(doc_language)}).
Research notes are drafts for the main writer — still must be fully in OUTPUT LANGUAGE.

Epistemic model:
- Human docs and code are evidence, not absolute truth.
- You MUST inspect code: entrypoint, routers, consumers, config, models.
- Read every file you reference in gaps or implementation signals.

{SERVICE_PAGE_SECTIONS}

{GAP_FORMAT_RULES}
{SHALLOW_RESEARCH_FORBIDDEN}

When called from eval workflow with responseSchema, also return:
- serviceName — assigned service name
- implementationPathCount — honest count of code paths listed
- shallow — true if doc-only, < 5 paths, or "not read in this pass" phrasing
- markdownNotes — full research text in OUTPUT LANGUAGE
- gapCount — number of gap items documented

Rules:
- Stay inside the assigned service directory unless tracing a named integration.
- Do not read secrets or .env files.
- Do not write to {loreport_dir}/.
- If you cite a file in gaps, you must have read it — no "not read in this pass".
""".strip()


def _platform_writer_prompt(loreport_dir: str, language: str) -> str:
    doc_language = resolve_language(language)
    return f"""
You are a Loreport platform synthesis researcher. Read-only — no file writes.

{output_language_policy(doc_language)}

Return suggestions in OUTPUT LANGUAGE ({language_label(doc_language)}).

Output:
1. Service index table
2. Platform integrations (mermaid-friendly)
3. Platform-wide gaps summary
4. Quickstart outline
5. Platform pages to create/update
6. Shallow services — those lacking code depth or with unread cited files

When called from eval workflow with responseSchema, return:
- markdownSynthesis — platform synthesis in OUTPUT LANGUAGE
- shallowServices — service names that lack code depth

Rules:
- Ground in provided service notes only.
- Flag mixed-language or English-heavy notes when OUTPUT LANGUAGE is not English.
- Do not write to {loreport_dir}/.
""".strip()


def create_subagent_specs(
    *,
    loreport_dir: str,
    language: str,
    provider: LoreportProvider,
    main_model_id: str,
    subagent_model_id: str | None = None,
) -> list[dict[str, str]]:
    model = _resolved_subagent_model(provider, main_model_id, subagent_model_id)
    doc_language = resolve_language(language)
    lang_note = language_label(doc_language)

    return [
        {
            "name": "service-researcher",
            "description": (
                "Deep-read one service: docs + code. Returns research notes in "
                f"{lang_note} only. Read-only."
            ),
            "system_prompt": _service_researcher_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
        {
            "name": "platform-writer",
            "description": (
                f"Platform synthesis from service notes. Output in {lang_note} only. Read-only."
            ),
            "system_prompt": _platform_writer_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
    ]
