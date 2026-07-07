from __future__ import annotations

from loreport_core.language import SERVICE_PAGE_SECTIONS, output_language_policy
from loreport_core.scope import RepoScope, ServiceScope

GAP_FORMAT_RULES = """
Gaps & drift format (strict):
- Every item: `- \\`category in OUTPUT LANGUAGE\\` — explanation with paths`
- NEVER bare labels without explanation
- NEVER placeholder lists of all categories
- Omit categories with no real finding
- Gap explanations must be in OUTPUT LANGUAGE
""".strip()

SHALLOW_PAGE_FORBIDDEN = """
FORBIDDEN on published service pages:
- "not researched", "not verified in this pass", "not read in this pass", "not explored"
- "inferred mostly from", "partially grounded", "only partially"
- Implementation signals with fewer than 5 concrete file paths (when source exists)
- Bare gap labels without explanation
- Integrations as bullets without evidence paths
- Any English prose when OUTPUT LANGUAGE is not English
""".strip()

SHALLOW_RESEARCH_FORBIDDEN = """
FORBIDDEN in research output:
- "not researched", "not verified in this pass", "not read in this pass"
- "inferred mostly from", "partially grounded"
- Empty Implementation signals section
- Fewer than 5 code paths when the service has source code
- Listing files in Implementation signals without having read routers/models when claiming gaps about them
""".strip()


def build_service_research_task(service: ServiceScope, *, language: str | None = None) -> str:
    lang_policy = output_language_policy(language)
    doc_hint = (
        "has tech.docs — read for intent, verify in code"
        if service.has_tech_docs
        else "no tech.docs — code-first research"
    )
    readme_hint = "has README" if service.has_readme else "no README"
    return f"""
Inspect service `{service.name}` at `/{service.name}/`. {doc_hint}; {readme_hint}.

{lang_policy}

Mandatory code research:
1. `ls /{service.name}/`
2. Entrypoint (main.py, app/main.py, etc.)
3. `grep` routers/handlers/consumers in `/{service.name}/`
4. Config module
5. Messaging layer if present
6. models/schemas — READ files you cite in gaps (do not list paths you did not open)

Return research notes with all six sections from the service page structure.
Min 8 implementation paths. Integrations table with evidence paths.

{GAP_FORMAT_RULES}
{SHALLOW_RESEARCH_FORBIDDEN}
{SERVICE_PAGE_SECTIONS}
""".strip()


def format_service_task_hints(
    scope: RepoScope,
    *,
    language: str | None = None,
    compact_threshold: int = 8,
) -> str:
    if not scope.services:
        return ""
    lang_policy = output_language_policy(language)

    if len(scope.services) <= compact_threshold:
        blocks = [
            build_service_research_task(service, language=language) for service in scope.services
        ]
        return "\n\n---\n\n".join(blocks)

    lines = [
        lang_policy,
        "",
        "Large monorepo — per service-researcher task:",
        "",
        *[
            f"- `{service.name}` at `/{service.name}/`"
            + (" (tech.docs)" if service.has_tech_docs else " (code-first)")
            for service in scope.services
        ],
        "",
        "Require: ls, entrypoint, grep, config, messaging, read models if cited.",
        "Min 8 code paths. Read every file mentioned in gaps.",
        "",
        GAP_FORMAT_RULES,
        SHALLOW_RESEARCH_FORBIDDEN,
        SERVICE_PAGE_SECTIONS,
    ]
    return "\n".join(lines)
