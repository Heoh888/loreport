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
- Every local path named in a gap MUST also appear in Implementation signals
- NEVER use a gap to record that a local file was skipped — read it or omit the gap
- Category "could not verify" is ONLY for external/uninspectable systems —
  never for local source files
""".strip()

SHALLOW_PAGE_FORBIDDEN = """
FORBIDDEN on published service pages:
- Gaps naming local paths absent from Implementation signals
- Gaps whose purpose is to excuse missing code inspection instead of stating a finding
- Implementation signals with fewer than 5 concrete file paths (when source exists)
- Bare gap labels without explanation
- Integrations as bullets without evidence paths
- Prose in a language other than OUTPUT LANGUAGE
""".strip()

SHALLOW_RESEARCH_FORBIDDEN = """
FORBIDDEN in research output:
- citedPathsInGaps containing paths not listed in readPathsInImplementation
- Empty Implementation signals section
- Fewer than 5 code paths when the service has source code
- Doc-only research when source code exists
""".strip()


def normalize_repo_path(path: str) -> str:
    return path.strip().strip("`").lstrip("/").lower()


def has_unread_gap_citations(
    read_paths: list[str],
    cited_paths: list[str],
) -> bool:
    read_set = {normalize_repo_path(path) for path in read_paths if path.strip()}
    for cited in cited_paths:
        norm = normalize_repo_path(cited)
        if not norm:
            continue
        if norm in read_set:
            continue
        if any(read_path.startswith(norm) or norm.startswith(read_path) for read_path in read_set):
            continue
        return True
    return False


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
6. models/schemas — open every file you cite in gaps

Return research notes with all six sections from the service page structure.
Min 8 implementation paths. Integrations table with evidence paths.
Every path in Gaps & drift must also be in Implementation signals.

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
        "Min 8 code paths. citedPathsInGaps must be subset of readPathsInImplementation.",
        "",
        GAP_FORMAT_RULES,
        SHALLOW_RESEARCH_FORBIDDEN,
        SERVICE_PAGE_SECTIONS,
    ]
    return "\n".join(lines)
