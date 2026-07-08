from __future__ import annotations

from loreport_core.constants import (
    LOREPORT_DIR,
    UPDATE_METADATA_PATH,
    language_label,
    resolve_language,
)
from loreport_core.doc_pattern import (
    COMPILED_ASPECT_RULES,
    DRIFT_FILE_RULES,
    INDEX_FILE_RULES,
    SERVICE_FOLDER_LAYOUT,
    ServiceDocPattern,
    format_service_completion_block,
)
from loreport_core.git.evidence import RunContext, UpdateMetadata
from loreport_core.integrity import (
    GAP_FORMAT_RULES,
    INCOMPLETE_DOCS_CODE_DISCIPLINE,
    SHALLOW_PAGE_FORBIDDEN,
    format_service_task_hints,
)
from loreport_core.language import (
    SERVICE_PAGE_SECTIONS,
    output_language_policy,
    writer_language_discipline,
)
from loreport_core.scope import RepoScope, format_service_inventory
from loreport_core.types import LoreportCommand
from loreport_core.workflow import (
    build_map_reduce_init_script,
    build_map_reduce_update_script,
    format_eval_workflow_block,
)

AGENTS_MD_SECTION = f"""## Loreport

This repository has engineering lore located in the /{LOREPORT_DIR} directory.

Start here:
- [Loreport quickstart]({LOREPORT_DIR}/quickstart.md)

Loreport maintains project integrity: navigation across services, links to human-authored docs, and explicit gaps between intent and implementation.

When working in this repository, read the Loreport quickstart first, then follow its links to architecture, workflows, domain, operations, and testing notes."""


def _format_last_update(last_update: UpdateMetadata | None) -> str:
    if last_update is None:
        return "No previous Loreport update metadata was found."
    return (
        f'{{"updatedAt": "{last_update.updated_at}", '
        f'"command": "{last_update.command}", '
        f'"gitHead": "{last_update.git_head or ""}", '
        f'"model": "{last_update.model}"}}'
    )


def _language_instructions(language: str) -> str:
    return output_language_policy(language)


def create_system_prompt(
    command: LoreportCommand,
    loreport_dir: str = LOREPORT_DIR,
    *,
    language: str | None = None,
) -> str:
    doc_language = resolve_language(language)
    lang_policy = output_language_policy(doc_language)
    writer_rules = writer_language_discipline(doc_language)
    return f"""
You are Loreport, an expert software analyst and technical writer.

{lang_policy}

{writer_rules}

Your job is to maintain **project integrity** in the {loreport_dir}/ directory: a living map that helps architects and engineers navigate the repository, connect services, and see where human intent, implementation, and documentation align or diverge.

You are NOT replacing architects or team-authored specs. You give them a reliable sidecar view of the whole system.

Epistemic model (critical):
- Neither human docs nor source code is absolute truth. Both are evidence.
- Human docs (`tech.docs/`, `docs/`, README, ADR, runbooks) express **intent and context**: what the team cares about, what to look at, boundaries, terminology. Teams write them differently — that is normal.
- Source code expresses **current implementation**: what exists today in files, configs, routes, queues.
- Documentation may describe features not yet implemented. Code may exist without any human doc.
- **Incomplete human docs require deeper code research** — read code to map reality, then compare.
- Loreport does not excuse thin README with directory inventory; open entrypoints and source files.
- Loreport synthesizes both: what is documented, what is implemented, what aligns, what diverges, what is missing.
- Do not invent files, modules, APIs, or behavior. Ground claims in inspected docs, code, or git evidence.
- Do not declare "this is how it works" without code evidence. Do not declare "this is the design" without a human-doc reference.
- When uncertain, say so explicitly and mark the item as unverified.

Use only the tools available to you. Prefer ls, glob, grep, read_file, write_file, and edit_file. Use git through shell execute when history helps.

Run discipline:
- Filesystem tools are rooted at the target repository. Use virtual paths such as /README.md, /src/..., and /{loreport_dir}/quickstart.md.
- Never pass host absolute paths like /Users/... to filesystem tools.
- Shell execute runs on the host. Keep commands inside the target repository.
- Do not exhaustively read every file. Use human docs to decide **what matters**, then verify in code entrypoints, routers, configs, and compose files.
- Do not call glob with `**/*` from the repository root. Avoid `**` patterns that are not whole path components.
- For large monorepos, discover one top-level service at a time with `ls /service-name` before reading inside it.
- Prefer grep and short targeted reads over full-file reads when files are large.

Human documentation discipline:
- Before researching a service, find its local docs: README, `tech.docs/`, `docs/`, ADRs.
- Human docs are navigation hints — if they are thin, read more code, not less.
- Use human docs to learn what the team considers important, then verify in source files.
- If a service has rich `tech.docs/`, pages are pre-compiled with full human doc text in UI.
- If human docs conflict with code, set verification status to `loreport:drift` (drift.md syncs automatically).
- Gap "found in code, not in human docs" requires naming specific features from opened files.

{INCOMPLETE_DOCS_CODE_DISCIPLINE}

{SERVICE_FOLDER_LAYOUT.format(loreport_dir=loreport_dir)}

{COMPILED_ASPECT_RULES}

{INDEX_FILE_RULES.format(loreport_dir=loreport_dir)}

{DRIFT_FILE_RULES.format(loreport_dir=loreport_dir)}

Monorepo discipline:
- Discover top-level services with `ls /` first. Typical signs: `*-service/`, `*-worker/`, `gateway/`.
- Read each service `_pattern.json` before writing — follow discovered human-doc aspects.
- {loreport_dir}/quickstart.md is platform navigation hub with links to every `services/<name>/index.md`.
- Prefer this layout:
  - `{loreport_dir}/quickstart.md` — platform entrypoint, every service listed, drift summary
  - `{loreport_dir}/platform/*.md` — cross-service architecture, integration maps
  - `{loreport_dir}/services/<service-name>/` — folder per service (index, drift, aspect files)
- Every discovered top-level service must appear in quickstart. Do not skip services silently.

Compiled page quality (reference):
{SERVICE_PAGE_SECTIONS}
- For mermaid diagrams: use quoted node labels like `A["/api/sync"]`, never parallelogram `[/path/]`

Quality bar:
- INADEQUATE: rewriting or shortening human-doc section (between human-doc markers)
- INADEQUATE: verification rows checking file existence instead of specific claims
- INADEQUATE: index.md with one-paragraph summary instead of full README transclusion
- INADEQUATE: drift.md with vague confirmation gaps when cited files were read
- REQUIRED: keep human doc body intact; fill code-verification table with claims from human doc
- REQUIRED: api-surface verifies each endpoint from human doc; messaging each queue/event
- Prose in verification/drift sections entirely in OUTPUT LANGUAGE

{GAP_FORMAT_RULES}

{SHALLOW_PAGE_FORBIDDEN}

Subagent output discipline:
- Subagent notes are raw research. Rewrite every sentence into OUTPUT LANGUAGE before write_file.
- If stillShallow=true or citedPathsInGaps has unread paths: read those paths yourself, then write.
- Never publish gaps naming local paths missing from Implementation signals.
- Never publish Alignment/Gaps paragraphs copied from subagent output in the wrong language.

Planning discipline:
- After discovery, create a temporary {loreport_dir}/_plan.md with intended pages, services inventory, and known gaps.
- Before completing the run, delete {loreport_dir}/_plan.md.

Git discipline:
- During init, inspect recent commit history on important files.
- During update, inspect commits since the previous successful Loreport run using gitHead from {UPDATE_METADATA_PATH} when available.
- Use git status and git diff for uncommitted changes.

Root agent instruction files:
- Unless the user explicitly asks you not to, ensure top-level /AGENTS.md and /CLAUDE.md reference the Loreport quickstart.
- Use this section structure:

```markdown
{AGENTS_MD_SECTION}
```

Security rules:
- Do not read or document secrets, credentials, private keys, tokens, or .env files.
- Keep all documentation under {loreport_dir}/.
- Do not modify source code outside {loreport_dir}/ except top-level /AGENTS.md and /CLAUDE.md for the Loreport reference section.

Required structure:
- {loreport_dir}/quickstart.md must be the entrypoint with links to every major section and a platform gap summary.
- Track the last successful documentation update in {UPDATE_METADATA_PATH}.

Mode-specific behavior:
{_mode_instructions(command, loreport_dir, doc_language)}
""".strip()


def _mode_instructions(command: LoreportCommand, loreport_dir: str, language: str) -> str:
    label = language_label(resolve_language(language))
    if command == "init":
        return f"""
- This is an initial documentation run.
- Human docs are PRE-COMPILED into `{loreport_dir}/services/<name>/*.md` before you start.
- Step 1: for EACH service, read pre-compiled aspect pages — human-doc section is canonical.
- Step 2: read code and edit_file ONLY verification/drift/integrations sections — do NOT rewrite human doc body.
- Step 3: synthesize `{loreport_dir}/quickstart.md` and `{loreport_dir}/platform/`.
- End quickstart with a platform-wide gaps section (heading in {label}).
""".strip()
    return f"""
- This is a maintenance update run.
- Read existing `{loreport_dir}/services/<name>/` folders before editing.
- Use git diff and last update metadata to find affected services and files.
- Rewrite edited pages entirely in {label} — fix mixed-language pages you touch.
- If a page mixes languages, translate the full page to {label}, not only changed lines.
- Updates may be a no-op. If integrity is already current, do not edit files.
""".strip()


def _workflow_init_block(
    loreport_dir: str,
    scope: RepoScope,
    *,
    max_parallel: int,
    dynamic_workflow: bool = False,
    language: str | None = None,
) -> str:
    names = ", ".join(scope.service_names)
    task_hints = format_service_task_hints(scope, language=language)

    if dynamic_workflow:
        script = build_map_reduce_init_script(
            scope,
            language=language,
            max_parallel=max_parallel,
        )
        orchestration = format_eval_workflow_block(
            command="init",
            script=script,
            loreport_dir=loreport_dir,
            language=language,
        )
    else:
        orchestration = f"""
Run this workflow:
1. For EACH service above ({names}), call the `task` tool with subagent `service-researcher`.
   Use the per-service task descriptions below — pass them verbatim in the task prompt.
   Run up to {max_parallel} tasks in parallel per batch until every service is covered.
2. Review results: if any service lacks ≥5 code paths, re-dispatch or research it yourself.
3. After all service notes are collected, call `platform-writer` once with the combined notes.
4. For EACH service: read pre-compiled `{loreport_dir}/services/<name>/*.md` pages.
   edit_file ONLY code-verification, details, drift.md, integrations — keep human-doc section intact.
5. Write `{loreport_dir}/quickstart.md` and `{loreport_dir}/platform/` from the synthesis.

Per-service task descriptions:
{task_hints}
"""

    return f"""
Workflow mode (map-reduce init):

Pre-discovered top-level services — do not skip any:
{format_service_inventory(scope)}
{orchestration}
Subagents are read-only researchers. You own all writes to {loreport_dir}/.
""".strip()


def _workflow_update_block(
    loreport_dir: str,
    scope: RepoScope,
    affected_services: tuple[str, ...],
    *,
    max_parallel: int,
    update_max_passes: int,
    dynamic_workflow: bool = False,
    language: str | None = None,
) -> str:
    names = ", ".join(affected_services)

    if dynamic_workflow:
        script = build_map_reduce_update_script(
            scope,
            affected_services,
            language=language,
            max_parallel=max_parallel,
            max_passes=update_max_passes,
        )
        orchestration = format_eval_workflow_block(
            command="update",
            script=script,
            loreport_dir=loreport_dir,
            language=language,
        )
    else:
        orchestration = f"""
Run this workflow:
1. For EACH affected service, call `task` with subagent `service-researcher`
   (up to {max_parallel} parallel).
2. Update only `{loreport_dir}/services/<name>/` folders for affected services.
3. Refresh platform pages and quickstart gaps section if cross-service integrations changed.
4. Loop up to {update_max_passes} passes if a subagent reports cross-cutting impact
   beyond the initial list.
"""

    return f"""
Workflow mode (targeted update):

Git changes affect these services: {names}
{orchestration}
Subagents are read-only. You own all writes to {loreport_dir}/.
""".strip()


def create_user_prompt(
    command: LoreportCommand,
    context: RunContext,
    *,
    loreport_dir: str = LOREPORT_DIR,
    user_message: str | None = None,
    language: str | None = None,
    scope: RepoScope | None = None,
    workflow_enabled: bool = False,
    dynamic_workflow: bool = False,
    affected_services: tuple[str, ...] = (),
    max_parallel_subagents: int = 5,
    update_max_passes: int = 3,
    doc_patterns_block: str = "",
) -> str:
    doc_language = resolve_language(language)
    lang_policy = output_language_policy(doc_language)
    lang_note = (
        f"\n{lang_policy}"
        f"\n{writer_language_discipline(doc_language)}"
    )
    if command == "init":
        prompt = f"""
Initialize Loreport integrity documentation for this repository.

Human docs from `tech.docs/` and README are ALREADY transcluded into
`{loreport_dir}/services/<name>/*.md` under `<!-- loreport:section:human-doc -->`.
Your job: verify claims in code and fill verification/drift sections — NOT rewrite human docs.{lang_note}

Integrity requirements:
- human-doc section is canonical team text — preserve it verbatim.
- Read claims from that section, verify each in code, fill code-verification table.
- Record drifts in `drift.md` by severity with concrete paths.
- Write `{loreport_dir}/quickstart.md` and `{loreport_dir}/platform/` after service verification.

INIT COMPLETION (mandatory):
- Every service folder must have index.md, drift.md, and all aspect files from _pattern.json.
- Missing files may be re-generated from human docs — fill their verification sections.
- Do NOT replace full human doc bodies with summaries.

Git context:
{context.git_summary}
""".strip()
    else:
        prompt = f"""
Update the Loreport integrity map for this repository.

Read each affected `{loreport_dir}/services/<name>/` folder with read_file before editing.
Identify recent changes from git and refresh affected integrity pages.
Fix mixed-language pages you touch — rewrite the full page in OUTPUT LANGUAGE.
If the map is already current, do not edit files.{lang_note}

Last update metadata:
{_format_last_update(context.last_update)}

Git change summary:
{context.git_summary}
""".strip()

    if user_message and user_message.strip():
        prompt += f"\n\nAdditional user instruction:\n{user_message.strip()}"

    if workflow_enabled and scope and command == "init" and scope.is_monorepo:
        prompt += "\n\n" + _workflow_init_block(
            loreport_dir,
            scope,
            max_parallel=max_parallel_subagents,
            dynamic_workflow=dynamic_workflow,
            language=doc_language,
        )
    elif workflow_enabled and scope and affected_services and command == "update":
        prompt += "\n\n" + _workflow_update_block(
            loreport_dir,
            scope,
            affected_services,
            max_parallel=max_parallel_subagents,
            update_max_passes=update_max_passes,
            dynamic_workflow=dynamic_workflow,
            language=doc_language,
        )
    elif scope and scope.services:
        prompt += f"\n\nPre-discovered services:\n{format_service_inventory(scope)}"

    if doc_patterns_block:
        prompt += f"\n\nDiscovered human-doc patterns (follow exactly):\n{doc_patterns_block}"

    return prompt


def create_completion_user_message(
    repo_path: str,
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
    missing_by_service: dict[str, list[str]],
    patterns: dict[str, ServiceDocPattern],
    pass_number: int,
    max_passes: int,
) -> str:
    doc_language = resolve_language(language)
    lang_policy = output_language_policy(doc_language)
    blocks = [
        format_service_completion_block(
            service_name,
            missing_files,
            patterns.get(service_name),
            loreport_dir=loreport_dir,
        )
        for service_name, missing_files in missing_by_service.items()
    ]
    service_list = ", ".join(missing_by_service)
    return f"""
Completion pass {pass_number}/{max_passes} — required markdown still missing.

Missing files were re-generated from human docs where possible.
Your job: ensure files exist AND fill code-verification / drift.md.
Do NOT rewrite human-doc section — it contains full team documentation.

Services to complete: {service_list}
{lang_policy}

{chr(10).join(blocks)}

Repository root:
{repo_path}

Runtime note:
- Pre-compiled pages use virtual paths under /{loreport_dir}/services/<name>/.
- edit_file verification sections; preserve human-doc markers.
- Do not stop until every missing file above exists on disk.
""".strip()


def create_convergence_user_message(
    repo_path: str,
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
    targets_block: str,
    pass_number: int,
    max_passes: int,
    open_items: int,
    stalled: bool,
) -> str:
    doc_language = resolve_language(language)
    lang_policy = output_language_policy(doc_language)
    stall_note = (
        "Previous pass made no progress — read deeper in code and close remaining items."
        if stalled
        else "Each pass closes only items listed below — do not re-verify completed rows."
    )
    return f"""
Verification convergence pass {pass_number}/{max_passes} — iterate-until-convergence.

Open verification items: {open_items}
{stall_note}

Workflow:
1. read_file only the listed service pages
2. read_file code for pending claims
3. edit_file ONLY `<!-- loreport:verification:pending -->` block (drift.md is synced from verification)
4. Do NOT touch `<!-- loreport:human-doc:do-not-edit -->`
5. Replace shallow rows (file-existence checks) with specific claims from human doc
6. Status tokens: `loreport:match` | `loreport:drift` | `loreport:missing-code` | `loreport:missing-doc`

{lang_policy}

{targets_block}

Repository root:
{repo_path}

Runtime note:
- Do not run map-reduce workflow on this pass.
- Verify only pending claims from the list above.
- Run stops automatically when no `loreport:pending` statuses remain.
""".strip()


def create_run_user_message(
    command: LoreportCommand,
    repo_path: str,
    context: RunContext,
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
    scope: RepoScope | None = None,
    workflow_enabled: bool = False,
    dynamic_workflow: bool = False,
    affected_services: tuple[str, ...] = (),
    max_parallel_subagents: int = 5,
    update_max_passes: int = 3,
    doc_patterns_block: str = "",
) -> str:
    base = create_user_prompt(
        command,
        context,
        loreport_dir=loreport_dir,
        language=language,
        scope=scope,
        workflow_enabled=workflow_enabled,
        dynamic_workflow=dynamic_workflow,
        affected_services=affected_services,
        max_parallel_subagents=max_parallel_subagents,
        update_max_passes=update_max_passes,
        doc_patterns_block=doc_patterns_block,
    )
    return f"""
{base}

Repository root:
{repo_path}

Runtime note:
- Treat the repository root above as the only project you are documenting.
- Filesystem tools use a virtual root: / means {repo_path}.
- For ls, read_file, write_file, edit_file, glob, and grep, use virtual paths such as /README.md and /{loreport_dir}/quickstart.md.
- Do not pass host absolute paths to filesystem tools.
- For execute, use cd {repo_path} before repository commands.
""".strip()
