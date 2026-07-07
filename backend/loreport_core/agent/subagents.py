from __future__ import annotations

from loreport_core.constants import (
    LoreportProvider,
    language_label,
    model_string,
    resolve_language,
    resolve_model_id,
)
from loreport_core.integrity import GAP_FORMAT_RULES, SHALLOW_RESEARCH_FORBIDDEN
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

Your job: deeply inspect ONE assigned top-level service directory and return
structured integrity notes grounded in BOTH human docs AND code.
You do NOT write files. You only read and summarize.

Language for your response:
{_language_instructions(doc_language)}

Epistemic model:
- Human docs and code are both evidence, not absolute truth.
- Human docs (`tech.docs/`, `docs/`, README) = intent and navigation context.
- Code = current implementation signals — you MUST inspect code, not skip it.
- Document alignment and gaps explicitly.

Required research order:
1. Human docs: README, `tech.docs/`, `docs/`, ADR — learn what to verify in code.
2. Code (mandatory): entrypoint, routers/handlers, services, messaging consumers,
   models, config. Use ls, grep, read_file inside the service directory only.
3. Cross-check: for each integration named in docs, find code evidence (config,
   client, queue name, env var).

Return markdown with these sections (all required):
- **Purpose** — one paragraph from docs and/or code role
- **Human context** — links with virtual paths
- **Implementation signals** — minimum 8 bullet paths with role (if source exists)
- **Integrations** — markdown table: System | Evidence | Role
- **Alignment** — specific agreements between docs and code (with paths)
- **Gaps & drift** — only real findings, proper format (see below)

{GAP_FORMAT_RULES}

{SHALLOW_RESEARCH_FORBIDDEN}

Rules:
- Stay inside the assigned service directory unless tracing a named integration.
- Do not read secrets, .env, or credentials.
- Do not write to {loreport_dir}/ or modify source code.
- If `tech.docs/` is rich, link to it — do not rewrite the spec.
- Prefer grep and targeted reads; avoid `**` glob from repo root.
- Incomplete research is worse than fewer gaps — dig into code before responding.
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
6. **Shallow services** — list any service notes that lack code paths and need rework

Rules:
- Ground suggestions in the provided service notes only.
- Flag services whose Implementation signals section looks shallow or doc-only.
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
                "Deep-read one service directory: human docs + code entrypoints, "
                "routers, consumers, config. Returns integrity notes with "
                f"≥8 implementation paths. Read-only. Response in {lang_note}."
            ),
            "system_prompt": _service_researcher_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
        {
            "name": "platform-writer",
            "description": (
                "Synthesize platform-level integrity overview from per-service notes. "
                f"Returns service index, integrations map, platform gaps, shallow-service "
                f"flags, and page outlines. Read-only. Response in {lang_note}."
            ),
            "system_prompt": _platform_writer_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
    ]
