from __future__ import annotations

from loreport_core.constants import (
    LoreportProvider,
    language_label,
    model_string,
    resolve_language,
    resolve_model_id,
)
from loreport_core.drift_classify import DRIFT_CLASSIFY_RULES
from loreport_core.integrity import (
    GAP_FORMAT_RULES,
    INCOMPLETE_DOCS_CODE_DISCIPLINE,
    SHALLOW_RESEARCH_FORBIDDEN,
)
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
- Thin human docs mean read MORE code, not less — compare and find concrete gaps.
- Compile aspect pages for UI completeness; human files remain canonical sources.
- read_file human docs and extract endpoints, queues, entities — not just list paths.
- You MUST inspect code: entrypoint, routers, pages, consumers, config, models.

{INCOMPLETE_DOCS_CODE_DISCIPLINE}

{SERVICE_PAGE_SECTIONS}

{GAP_FORMAT_RULES}
{SHALLOW_RESEARCH_FORBIDDEN}

When called from eval workflow with responseSchema, also return:
- serviceName — assigned service name
- implementationPathCount — count of opened files in readPathsInImplementation (not dirs)
- readPathsInImplementation — repo-relative files opened with read_file
- citedPathsInGaps — repo-relative paths named in gap items
- shallow — true if too few opened files or citedPaths not covered by opened files
- markdownNotes — full research text in OUTPUT LANGUAGE
- gapCount — number of gap items documented

Rules:
- Stay inside the assigned service directory unless tracing a named integration.
- Do not read secrets or .env files.
- Do not write to {loreport_dir}/.
- readPathsInImplementation must list opened files; directories alone are invalid.
- citedPathsInGaps must be covered by opened files in readPathsInImplementation.
""".strip()


def _drift_classifier_prompt(loreport_dir: str, language: str) -> str:
    doc_language = resolve_language(language)
    return f"""
You are a Loreport drift classifier (Classify & Act pattern). Read-only — no file writes.

{output_language_policy(doc_language)}

Input: service research notes + human-doc context. Output: classified drift candidates ONLY.

{DRIFT_CLASSIFY_RULES}

For each candidate return:
- aspect — aspect id or topic slug
- humanDoc — what human doc says (quote/topic, OUTPUT LANGUAGE)
- code — repo-relative paths inspected
- issue — what diverges (OUTPUT LANGUAGE prose)
- driftClass — one of: match | stub-ok | doc-lies | doc-gap | code-gap | ambiguous
- signal — ALWAYS English slug:
  aligned | silence | contradiction | doc-ahead | code-missing | stub | unclear

Rules:
- Prefer match/stub-ok when doc and code agree or doc correctly says stub/not wired.
- doc-lies ONLY with signal `contradiction`; silence/omission = signal `silence` + doc-gap.
- Code exists, docs should mention it = signal `doc-ahead` + doc-gap, never code-gap.
- Route exists without publish/enqueue/persist = signal `stub` + stub-ok when doc silent.
- API endpoint without UI = doc-gap or ambiguous, NOT doc-lies.
- Do not write to {loreport_dir}/.
""".strip()


def _drift_verifier_prompt(loreport_dir: str, language: str) -> str:
    doc_language = resolve_language(language)
    return f"""
You are a Loreport drift verifier (Adversarial verify). Read-only — no file writes.

{output_language_policy(doc_language)}

You receive ONE classified drift candidate. Re-read cited code paths. Be skeptical.

Confirm ONLY if:
- driftClass is correct after re-inspection
- human doc and code evidence support the issue
- NOT a false positive (stub treated as full feature, API treated as UI)

Reject (confirmed=false) when:
- doc and code actually agree
- doc correctly describes stub/backlog and code matches
- claim is "endpoint exists" but doc never claimed full feature
- driftClass is doc-lies but signal is silence, doc-ahead, or stub
- driftClass is code-gap but signal is doc-ahead (code already implements the feature)

Return: confirmed (boolean), reason (OUTPUT LANGUAGE, one sentence).

Do not write to {loreport_dir}/.
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
            "name": "drift-classifier",
            "description": (
                "Classify doc↔code drift candidates into structural classes "
                f"(match/stub-ok/doc-lies/...). Output in {lang_note}. Read-only."
            ),
            "system_prompt": _drift_classifier_prompt(loreport_dir, language),
            "model": model,
            "tools": [],
        },
        {
            "name": "drift-verifier",
            "description": (
                "Skeptically verify one drift candidate (adversarial pass). "
                f"Output in {lang_note}. Read-only."
            ),
            "system_prompt": _drift_verifier_prompt(loreport_dir, language),
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
