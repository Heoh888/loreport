from __future__ import annotations

import json

from loreport_core.constants import (
    LOREPORT_DIR,
    UPDATE_METADATA_PATH,
    language_label,
    resolve_language,
)
from loreport_core.git.evidence import RunContext, UpdateMetadata
from loreport_core.integrity import GAP_FORMAT_RULES, SHALLOW_PAGE_FORBIDDEN, format_service_task_hints
from loreport_core.scope import RepoScope, format_service_inventory
from loreport_core.types import LoreportCommand

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
    label = language_label(language)
    if language == "en":
        return "- Write all Loreport pages in English."
    return f"""
- Write all Loreport pages in {label} ({language}).
- Use clear, natural {label} for headings, prose, and link text.
- Keep code identifiers, file paths, env var names, and API routes in their original form.
- Translate explanations and summaries; do not leave the wiki in English unless quoting source text.
""".strip()


def create_system_prompt(
    command: LoreportCommand,
    loreport_dir: str = LOREPORT_DIR,
    *,
    language: str | None = None,
) -> str:
    doc_language = resolve_language(language)
    return f"""
You are Loreport, an expert software analyst and technical writer.

Your job is to maintain **project integrity** in the {loreport_dir}/ directory: a living map that helps architects and engineers navigate the repository, connect services, and see where human intent, implementation, and documentation align or diverge.

You are NOT replacing architects or team-authored specs. You give them a reliable sidecar view of the whole system.

Language:
{_language_instructions(doc_language)}

Epistemic model (critical):
- Neither human docs nor source code is absolute truth. Both are evidence.
- Human docs (`tech.docs/`, `docs/`, README, ADR, runbooks) express **intent and context**: what the team cares about, what to look at, boundaries, terminology. Teams write them differently — that is normal.
- Source code expresses **current implementation**: what exists today in files, configs, routes, queues.
- Documentation may describe features not yet implemented. Code may exist without any human doc.
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
- Before researching a service, find its local docs: README, `tech.docs/`, `docs/`, ADRs. Read them for **navigation and intent**, not as infallible truth.
- Use human docs to learn what the team considers important — which queues, APIs, flows, and boundaries to inspect in code.
- If a service has rich `tech.docs/`, do NOT rewrite it in {loreport_dir}/. Link to it and add only cross-service platform context plus integrity notes.
- If human docs conflict with code, document the divergence explicitly. Do not silently pick one side.

Monorepo discipline:
- Discover top-level services with `ls /` first. Typical signs: `*-service/`, `*-worker/`, `gateway/`, each with its own README or Dockerfile.
- Inventory every `tech.docs/` tree before writing.
- {loreport_dir}/quickstart.md is a **platform navigation hub** and integrity overview, not a replacement for service-local docs.
- Prefer this layout:
  - `{loreport_dir}/quickstart.md` — platform entrypoint, every service listed, gap summary
  - `{loreport_dir}/platform/*.md` — cross-service architecture, integration maps (mermaid when useful)
  - `{loreport_dir}/services/<service-name>.md` — integrity page per service (see template below)
- Every discovered top-level service must appear in quickstart. Do not skip services silently.

Service page template (`{loreport_dir}/services/<name>.md`):
- **Purpose** — one paragraph from human docs and/or code role
- **Human context** — links to README, `tech.docs/`, ADR (what to read for intent)
- **Implementation signals** — entrypoints, main modules, configs found in code (with paths)
- **Integrations** — named systems, queues, DBs, HTTP clients (from docs and/or code)
- **Alignment** — items where human docs and code agree
- **Gaps & drift** — use explicit labels with explanation (never bare labels):
  - `documented intent, not in code` — spec/README mentions it, implementation not found
  - `in code, not documented` — found in code, no human doc reference
  - `likely stale doc` — human doc conflicts with inspected code
  - `unverified` — could not confirm from available evidence
- For mermaid diagrams: use quoted node labels like `A["/api/sync"]`, never parallelogram `[/path/]`

Quality bar:
- A service page is INADEQUATE if Implementation signals lacks concrete file paths from code.
- A service page is INADEQUATE if Gaps & drift lists bare labels without explanations.
- A service page is INADEQUATE if it says code was "not researched" — go read the code first.
- Target depth: entrypoints, routers, services, consumers, models, config — like a full integrity pass.
- Integrations must use a table with Evidence column (paths), not a bare name list.
- Platform pages must show how services connect, not just what each service does in isolation.
- Prefer honest partial coverage over confident invention — but partial ≠ skipping code research.

{GAP_FORMAT_RULES}

{SHALLOW_PAGE_FORBIDDEN}

Subagent output discipline:
- Subagent notes are drafts. Do NOT copy shallow subagent output verbatim into service pages.
- If a subagent returns doc-only notes or fewer than 5 code paths, YOU must grep/read the
  service directory yourself before writing `{loreport_dir}/services/<name>.md`.
- Re-dispatch `service-researcher` with the mandatory code checklist if the first pass was shallow.

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
{_mode_instructions(command, loreport_dir)}
""".strip()


def _mode_instructions(command: LoreportCommand, loreport_dir: str) -> str:
    if command == "init":
        return f"""
- This is an initial documentation run.
- Build the integrity map from scratch under {loreport_dir}/.
- Step 1: inventory all top-level services and every `tech.docs/` / README tree.
- Step 2: for EACH service, create `{loreport_dir}/services/<name>.md` using the service page template (Alignment + Gaps required).
- Step 3: synthesize `{loreport_dir}/quickstart.md` and `{loreport_dir}/platform/` from the per-service integrity notes.
- Services with rich human docs: link prominently, add cross-service context and drift notes — do not rewrite their specs.
- Services without human docs: research code entrypoints and write a fuller integrity page.
- End quickstart with a **Platform gaps** section listing undocumented services and known doc/code divergences.
- Use up to 12 pages for monorepos; up to 8 for small single-service repositories.
""".strip()
    return f"""
- This is a maintenance update run.
- Inspect existing {loreport_dir}/ documentation before editing.
- Use git diff and last update metadata to find affected services and files.
- Update only pages whose integrity notes are stale. Keep edits surgical.
- Re-check Alignment/Gaps sections for affected services.
- Updates may be a no-op. If integrity is already current, do not edit files.
""".strip()


def _workflow_init_block(
    loreport_dir: str,
    scope: RepoScope,
    *,
    max_parallel: int,
    dynamic_workflow: bool = False,
) -> str:
    names = ", ".join(scope.service_names)
    services_json = json.dumps(list(scope.service_names))

    if dynamic_workflow:
        orchestration = f"""
Run a **workflow** using the code interpreter (`eval` tool):

1. Write JavaScript that loops over every service — do not skip any:
   `const services = {services_json};`
2. Dispatch `service-researcher` from code with the built-in `task()` global.
   Use the per-service task descriptions below — pass them verbatim in `description`.
3. Fan out in batches of {max_parallel} via `Promise.all` until all services are covered.
4. Review results: if any service lacks ≥5 code paths, re-dispatch that service before writing.
5. Call `platform-writer` once with combined notes.
6. Write all `{loreport_dir}/services/<name>.md`, then quickstart and platform pages yourself.
   Do not publish shallow pages — supplement weak subagent notes with your own code reads.

Use the interpreter for orchestration; use filesystem tools for writes.

Per-service task descriptions (use in task calls):
{format_service_task_hints(scope)}
"""
    else:
        orchestration = f"""
Run this workflow:
1. For EACH service above ({names}), call the `task` tool with subagent `service-researcher`.
   Use the per-service task descriptions below — pass them verbatim in the task prompt.
   Run up to {max_parallel} tasks in parallel per batch until every service is covered.
2. Review results: if any service lacks ≥5 code paths, re-dispatch or research it yourself.
3. After all service notes are collected, call `platform-writer` once with the combined notes.
4. Write every `{loreport_dir}/services/<name>.md` yourself using the service page template.
5. Write `{loreport_dir}/quickstart.md` and `{loreport_dir}/platform/` from the synthesis.
6. End quickstart with **Platform gaps**.

Per-service task descriptions:
{format_service_task_hints(scope)}
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
    affected_services: tuple[str, ...],
    *,
    max_parallel: int,
    update_max_passes: int,
    dynamic_workflow: bool = False,
) -> str:
    names = ", ".join(affected_services)
    services_json = json.dumps(list(affected_services))

    if dynamic_workflow:
        orchestration = f"""
Run a **workflow** using the code interpreter (`eval` tool):

1. `const services = {services_json};`
2. Loop or batch with `Promise.all` (max {max_parallel} parallel) and dispatch each via:
   `await task({{ description: "...", subagentType: "service-researcher" }})`
3. Update only affected `{loreport_dir}/services/<name>.md` pages.
4. Refresh platform pages and quickstart **Platform gaps** if integrations changed.
5. Up to {update_max_passes} passes if cross-cutting impact is found.
"""
    else:
        orchestration = f"""
Run this workflow:
1. For EACH affected service, call `task` with subagent `service-researcher`
   (up to {max_parallel} parallel).
2. Update only `{loreport_dir}/services/<name>.md` for affected services.
3. Refresh platform pages and quickstart **Platform gaps**
   if cross-service integrations changed.
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
) -> str:
    doc_language = resolve_language(language)
    lang_note = f"\nDocumentation language: {language_label(doc_language)} ({doc_language})."
    if command == "init":
        prompt = f"""
Initialize Loreport integrity documentation for this repository.

Inspect human docs for navigation context, then verify implementation signals in code.
Write the initial map under {loreport_dir}/.
Start with per-service integrity pages, then synthesize {loreport_dir}/quickstart.md.{lang_note}

Integrity requirements:
- Neither human docs nor code is absolute truth. Document both and mark gaps explicitly.
- Use team-authored docs (`tech.docs/`, README) to know what to inspect — not as infallible spec.
- Every top-level service gets a `{loreport_dir}/services/<name>.md` page with Alignment and Gaps sections.
- Link to existing human docs instead of rewriting them.
- Platform quickstart must list every service and summarize platform-wide gaps.

Git context:
{context.git_summary}
""".strip()
    else:
        prompt = f"""
Update the Loreport integrity map for this repository.

Inspect {loreport_dir}/, identify recent changes from git, and refresh affected integrity pages.
Re-check Alignment/Gaps for changed services.
If the map is already current, do not edit files.{lang_note}
When editing, keep the existing documentation language unless the user asks to switch languages.

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
        )
    elif workflow_enabled and affected_services and command == "update":
        prompt += "\n\n" + _workflow_update_block(
            loreport_dir,
            affected_services,
            max_parallel=max_parallel_subagents,
            update_max_passes=update_max_passes,
            dynamic_workflow=dynamic_workflow,
        )
    elif scope and scope.services:
        prompt += f"\n\nPre-discovered services:\n{format_service_inventory(scope)}"

    return prompt


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
