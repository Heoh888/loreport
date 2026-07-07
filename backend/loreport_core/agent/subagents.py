from __future__ import annotations

from loreport_core.constants import (
    LoreportProvider,
    language_label,
    model_string,
    resolve_language,
    resolve_model_id,
)
from loreport_core.prompts import _language_instructions


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
You are a Loreport service integrity researcher.

Your job: inspect ONE assigned top-level service directory and return structured integrity notes.
You do NOT write files. You only read and summarize.

Language for your response:
{_language_instructions(doc_language)}

Epistemic model:
- Human docs and code are both evidence, not absolute truth.
- Human docs (`tech.docs/`, `docs/`, README) = intent and navigation context.
- Code = current implementation signals.
- Document alignment and gaps explicitly.

For the assigned service:
1. Find human docs: README, `tech.docs/`, `docs/`, ADR files.
2. Inspect code entrypoints: main modules, routers, workers, docker/compose, configs.
3. Return markdown with these sections (all required):
   - **Purpose**
   - **Human context** (links with paths)
   - **Implementation signals** (paths only, grounded in code)
   - **Integrations** (table: System | Evidence | Role)
   - **Alignment** (where docs and code agree)
   - **Gaps & drift** (use labels:
     `documented intent, not in code`, `in code, not documented`,
     `likely stale doc`, `unverified`)

Rules:
- Stay inside the assigned service directory unless tracing a cross-service integration.
- Do not read secrets, .env, or credentials.
- Do not write to {loreport_dir}/ or modify source code.
- If the service has rich `tech.docs/`, link to it — do not rewrite the spec.
- Prefer grep and targeted reads; avoid `**` glob from repo root.
""".strip()


def _platform_writer_prompt(loreport_dir: str, language: str) -> str:
    doc_language = resolve_language(language)
    return f"""
You are a Loreport platform synthesis researcher.

Your job: given per-service integrity notes, propose platform-level structure.
You do NOT write files. You return markdown suggestions only.

Language for your response:
{_language_instructions(doc_language)}

Output:
1. **Service index** — table: Service | Purpose (one line) | Has human docs | Gap count
2. **Platform integrations** — cross-service flows and shared systems
   (mermaid-friendly, use quoted node labels)
3. **Platform gaps** — consolidated doc/code divergences across services
4. **Suggested quickstart outline** — sections and links for {loreport_dir}/quickstart.md
5. **Suggested platform pages** — which files under {loreport_dir}/platform/ to create or update

Rules:
- Ground suggestions in the provided service notes only.
- Do not invent services or integrations.
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
                "Inspect one top-level service directory and return integrity notes "
                f"(Purpose, Human context, Implementation signals, Integrations, "
                f"Alignment, Gaps & drift). Read-only. Response in {lang_note}."
            ),
            "system_prompt": _service_researcher_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
        {
            "name": "platform-writer",
            "description": (
                "Synthesize platform-level integrity overview from per-service notes. "
                f"Returns service index, integrations map, platform gaps, and page outlines. "
                f"Read-only. Response in {lang_note}."
            ),
            "system_prompt": _platform_writer_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
    ]
