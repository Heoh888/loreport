from __future__ import annotations

from loreport_core.language import SERVICE_PAGE_SECTIONS, output_language_policy
from loreport_core.scope import RepoScope, ServiceScope

MIN_SOURCE_FILE_PATHS = 5
MIN_SOURCE_FILE_PATHS_TARGET = 8

INCOMPLETE_DOCS_CODE_DISCIPLINE = """
Incomplete human docs discipline:
- Thin README or missing tech.docs does NOT reduce the need for code research — it increases it.
- Read code to discover what exists: entrypoint, routes, handlers, pages, consumers, models.
- Then compare with human docs and record concrete gaps:
  specific feature X in file Y, absent from README.
- NEVER stop at directory inventory (src/, pages/) — open and list actual files you read.
- Gap "found in code, not in human docs" requires evidence from opened files, not ls alone.
""".strip()

GAP_FORMAT_RULES = """
Gaps & drift format (strict):
- Every item: `- \\`category in OUTPUT LANGUAGE\\` — explanation with paths`
- NEVER bare labels without explanation
- NEVER placeholder lists of all categories
- Omit categories with no real finding
- Gap explanations must be in OUTPUT LANGUAGE
- Every local path named in a gap MUST be an opened file in Implementation signals
- NEVER use a gap to record that a local file was skipped — read it or omit the gap
- Category "could not verify" is ONLY for external/uninspectable systems —
  never for local source files
""".strip()

SHALLOW_PAGE_FORBIDDEN = """
FORBIDDEN on published service pages:
- Implementation signals listing directories without opened files (src/, pages/, app/)
- Gaps naming local paths absent from Implementation signals
- Gaps whose purpose is to excuse missing code inspection instead of stating a finding
- Implementation signals with fewer than 5 opened files (when source exists)
- Bare gap labels without explanation
- Integrations as bullets without evidence paths
- Prose in a language other than OUTPUT LANGUAGE
""".strip()

SHALLOW_RESEARCH_FORBIDDEN = """
FORBIDDEN in research output:
- readPathsInImplementation containing only directories — must list opened files
- citedPathsInGaps with paths not covered by opened files in readPathsInImplementation
- Empty Implementation signals section
- Fewer than 5 opened source files when the service has source code
- Doc-only or ls-only research when source code exists
""".strip()


def normalize_repo_path(path: str) -> str:
    return path.strip().strip("`").lstrip("/").lower().rstrip("/")


def is_repo_file_path(path: str) -> bool:
    norm = normalize_repo_path(path)
    if not norm:
        return False
    basename = norm.rsplit("/", 1)[-1]
    return "." in basename


def filter_source_file_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if is_repo_file_path(path)]


def citation_is_covered(cited: str, read_paths: list[str]) -> bool:
    cited_norm = normalize_repo_path(cited)
    if not cited_norm:
        return True
    read_files = [normalize_repo_path(path) for path in read_paths if is_repo_file_path(path)]
    if is_repo_file_path(cited):
        return cited_norm in read_files
    dir_prefix = f"{cited_norm}/"
    return any(read_file.startswith(dir_prefix) for read_file in read_files)


def has_unread_gap_citations(
    read_paths: list[str],
    cited_paths: list[str],
) -> bool:
    for cited in cited_paths:
        if cited.strip() and not citation_is_covered(cited, read_paths):
            return True
    return False


def count_opened_files(read_paths: list[str]) -> int:
    return len(filter_source_file_paths(read_paths))


def research_is_shallow(
    read_paths: list[str],
    cited_paths: list[str],
    *,
    min_files: int = MIN_SOURCE_FILE_PATHS,
    shallow_flag: bool = False,
) -> bool:
    if shallow_flag:
        return True
    if count_opened_files(read_paths) < min_files:
        return True
    return has_unread_gap_citations(read_paths, cited_paths)


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

{INCOMPLETE_DOCS_CODE_DISCIPLINE}

Mandatory code research:
1. `ls /{service.name}/` — then open files, do not stop at directories
2. Entrypoint (main.py, main.tsx, app/main.py, etc.) — read_file
3. `grep` routers/handlers/consumers/pages in `/{service.name}/` — read matches
4. Config files (package.json, pyproject.toml, docker-compose) — read_file
5. Messaging layer if present — read consumers/producers
6. Open every file you cite in gaps or Implementation signals

Return compiled research per _pattern.json aspects:
- overview/index, drift by severity, one block per aspect loreport file
- Intent summary from human docs + implementation status with opened files
- Min {MIN_SOURCE_FILE_PATHS_TARGET} opened files; citedPathsInGaps covered by files

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
        "Require: ls then read_file on entrypoint, routes, handlers, key modules.",
        f"Min {MIN_SOURCE_FILE_PATHS_TARGET} opened files in readPathsInImplementation.",
        "citedPathsInGaps must be covered by opened files, not directories.",
        "",
        GAP_FORMAT_RULES,
        SHALLOW_RESEARCH_FORBIDDEN,
        SERVICE_PAGE_SECTIONS,
    ]
    return "\n".join(lines)
