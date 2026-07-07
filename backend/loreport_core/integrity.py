from __future__ import annotations

from loreport_core.scope import ServiceScope

GAP_FORMAT_RULES = """
Gaps & drift format (strict):
- Every item MUST be: `- \\`label\\` — concrete explanation with paths or doc references`
- Valid labels only: `documented intent, not in code`, `in code, not documented`,
  `likely stale doc`, `unverified`
- NEVER output a bare label without explanation
- NEVER list all four labels as placeholders
- If no gaps found for a label, omit that label entirely
""".strip()

SHALLOW_PAGE_FORBIDDEN = """
FORBIDDEN on published service pages:
- "not researched", "not verified in this pass", "not explored in detail"
- Implementation signals with fewer than 5 concrete file paths (when source exists)
- Bare gap labels without explanation
- Integrations as a bullet list without Evidence paths
""".strip()

SHALLOW_RESEARCH_FORBIDDEN = """
FORBIDDEN in research output:
- "not researched", "not verified in this pass", "not explored in detail"
- Empty Implementation signals section
- Implementation signals with fewer than 5 concrete file paths (when the service has source code)
- Integrations listed without Evidence column or path references
- Copying human doc titles without reading code entrypoints
""".strip()


def build_service_research_task(service: ServiceScope) -> str:
    doc_hint = (
        "rich tech.docs present — read for intent, then verify in code"
        if service.has_tech_docs
        else "no tech.docs — research code entrypoints thoroughly"
    )
    readme_hint = "README present" if service.has_readme else "no README"
    return f"""
Inspect service `{service.name}` at virtual path `/{service.name}/`.

Context: {doc_hint}; {readme_hint}.

Mandatory code research (do all before responding):
1. `ls /{service.name}/` — map top-level layout
2. Find entrypoint: main.py, app/main.py, src/index.ts, or equivalent
3. `grep` for routers/routes/handlers/consumers in `/{service.name}/`
4. Read config module (config.py, settings.py, .env.example if present)
5. Read messaging layer if exists (messaging/, consumers/, queues/)
6. Read models/schemas if exists

Return full integrity notes with ALL sections. Implementation signals must list
at least 8 concrete paths with one-line role each (routers, services, consumers,
models, config). Integrations table must have Evidence column with paths.

{GAP_FORMAT_RULES}

{SHALLOW_RESEARCH_FORBIDDEN}
""".strip()


def format_service_task_hints(scope: RepoScope, *, compact_threshold: int = 8) -> str:
    if not scope.services:
        return ""
    if len(scope.services) <= compact_threshold:
        blocks = [build_service_research_task(service) for service in scope.services]
        return "\n\n---\n\n".join(blocks)

    lines = [
        "Large monorepo — pass this checklist in every service-researcher task:",
        "",
        *[
            f"- `{service.name}` at `/{service.name}/`"
            + (" (tech.docs)" if service.has_tech_docs else " (code-first)")
            for service in scope.services
        ],
        "",
        "Each task must require: ls, entrypoint, grep routers/consumers, config, messaging, models.",
        "Each result must have ≥8 implementation paths and Integrations table with Evidence.",
        "",
        GAP_FORMAT_RULES,
        "",
        SHALLOW_RESEARCH_FORBIDDEN,
    ]
    return "\n".join(lines)
