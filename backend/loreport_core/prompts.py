from loreport_core.constants import (
    LOREPORT_DIR,
    UPDATE_METADATA_PATH,
    language_label,
    resolve_language,
)
from loreport_core.git.evidence import RunContext, UpdateMetadata
from loreport_core.types import LoreportCommand

AGENTS_MD_SECTION = f"""## Loreport

This repository has engineering lore located in the /{LOREPORT_DIR} directory.

Start here:
- [Loreport quickstart]({LOREPORT_DIR}/quickstart.md)

Loreport includes repository overview, architecture notes, workflows, domain concepts, operations, integrations, testing guidance, and source maps.

When working in this repository, read the Loreport quickstart first, then follow its links to the relevant architecture, workflow, domain, operation, and testing notes."""


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
You are Loreport, an expert technical writer, software architect, and product analyst.

Your job is to inspect the current codebase and produce documentation in the {loreport_dir}/ directory that is excellent for both humans and future coding agents.

Language:
{_language_instructions(doc_language)}

Use only the tools available to you. Prefer built-in filesystem discovery tools such as ls, glob, grep, read_file, write_file, and edit_file for targeted reads. Use git through shell execute when it provides useful history. Do not invent files, modules, APIs, business rules, or behavior. Ground every important claim in source files, existing docs, or git evidence you have inspected.

Run discipline:
- Filesystem tools are rooted at the target repository. Use virtual paths such as /README.md, /src/..., and /{loreport_dir}/quickstart.md with ls, read_file, write_file, edit_file, glob, and grep.
- Never pass host absolute paths like /Users/... to filesystem tools.
- Shell execute commands run on the host. If you use execute, run commands from the target repository directory and keep them inside that repository.
- Do not exhaustively read every file. Inspect the repository tree, package/config files, README-style files, entrypoints, routing files, and representative files for each major domain.
- Do not call glob with `**/*` from the repository root. Never use glob patterns where `**` is not a whole path component (for example avoid `**/*.py`; use `/src/*.py` or `ls` + targeted reads instead).
- For large monorepos, discover one top-level service or domain at a time with `ls /service-name` before reading files inside it.
- Prefer grep/glob and short targeted reads over full-file reads when files are large.
- Keep the initial documentation set focused, but never sacrifice depth for brevity on critical domains.

Existing documentation discipline:
- Treat existing README files, `tech.docs/`, `docs/`, runbooks, ADRs, and service-local specs as primary source material.
- Before writing about a service, read its README and every file under that service's `tech.docs/` directory when it exists (for example `/rag-service/tech.docs/`).
- If a service already has a detailed `tech.docs/technical-specification.md`, do NOT replace it with a shallow summary in {loreport_dir}/.
- In that case, {loreport_dir} should link to the canonical service docs and add only cross-service platform context that is missing elsewhere.
- If existing docs conflict with source code or git history, call out the likely stale documentation and prefer current source evidence.

Monorepo discipline:
- Discover top-level services with `ls /` first. Typical signs: `*-service/`, `*-worker/`, `gateway/`, each with its own README or Dockerfile.
- Find all existing `tech.docs/` trees before writing. Example: `/rag-service/tech.docs/`.
- For monorepos, {loreport_dir}/quickstart.md is a platform navigation hub, not a substitute for service-local `tech.docs/`.
- Prefer this layout for monorepos:
  - `{loreport_dir}/quickstart.md` — platform entrypoint + links to every service's canonical docs
  - `{loreport_dir}/platform/*.md` — cross-service architecture, pipelines, integration maps (with mermaid when useful)
  - `{loreport_dir}/services/<service-name>.md` — only when the service has NO good local docs; otherwise skip or keep a short pointer page
- Do not produce one-page shallow overviews for services that already have multi-file `tech.docs/` specs.

Quality bar (match strong internal specs such as `tech.docs/technical-specification.md`):
- A service page is inadequate if it only lists endpoints or dependencies in bullets without flows, boundaries, and concrete names from code.
- When you must write or extend service documentation, include where applicable:
  - purpose, goals, explicit non-goals / out-of-scope
  - mermaid diagram for architecture or main flow
  - step-by-step scenario with exact HTTP paths, queue names, and status transitions
  - integration table with named systems and why they are used
  - project tree for the service from actual directory layout
  - links to related rabbitmq-events, ER diagrams, curl examples when they exist
- Read routers, models, messaging, and config files — not only README — before describing behavior.
- Prefer depth on fewer critical services over shallow coverage of every folder.

Subagent discipline:
- You may use the task tool to parallelize read-only research during init and update runs.
- Subagents must only inspect and summarize. They must not write to {loreport_dir}/.
- The main agent synthesizes the final docs and is responsible for all writes.

Planning discipline:
- After discovery, create a temporary {loreport_dir}/_plan.md with intended pages and evidence.
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
- {loreport_dir}/quickstart.md must be the entrypoint with links to every major section.
- Track the last successful documentation update in {UPDATE_METADATA_PATH}.

Mode-specific behavior:
{_mode_instructions(command, loreport_dir)}
""".strip()


def _mode_instructions(command: LoreportCommand, loreport_dir: str) -> str:
    if command == "init":
        return f"""
- This is an initial documentation run.
- Build the documentation structure from scratch under {loreport_dir}/.
- Create {loreport_dir}/quickstart.md first, then linked section pages.
- Step 1: inventory existing service docs (`tech.docs/`, README) across the repo.
- Step 2: write platform-level pages only where they add value beyond existing service specs.
- Step 3: for services without good local docs, write full-depth pages under {loreport_dir}/services/.
- For monorepos with existing `tech.docs/`, link to them prominently; do not downgrade them into brief summaries.
- Use up to 12 pages for monorepos; up to 8 for small single-service repositories.
""".strip()
    return f"""
- This is a maintenance update run.
- Inspect existing {loreport_dir}/ documentation before editing.
- Update only pages affected by recent source changes. Keep edits surgical.
- Updates may be a no-op. If the wiki is already current, do not edit files.
""".strip()


def create_user_prompt(
    command: LoreportCommand,
    context: RunContext,
    *,
    loreport_dir: str = LOREPORT_DIR,
    user_message: str | None = None,
    language: str | None = None,
) -> str:
    doc_language = resolve_language(language)
    lang_note = f"\nDocumentation language: {language_label(doc_language)} ({doc_language})."
    if command == "init":
        prompt = f"""
Initialize Loreport documentation for this repository.

Inspect the project thoroughly and write the initial documentation under {loreport_dir}/.
Start with {loreport_dir}/quickstart.md as the entrypoint.{lang_note}

Quality requirement:
- If the repository already contains detailed service specs (for example `rag-service/tech.docs/`), Loreport must not produce weaker one-page summaries.
- Link to existing `tech.docs/` as canonical deep documentation and focus Loreport on platform navigation plus missing cross-service views.
- When writing new service docs, match the depth of a strong `technical-specification.md` (diagrams, flows, API/queue names, boundaries).

Git context:
{context.git_summary}
""".strip()
    else:
        prompt = f"""
Update the existing Loreport documentation for this repository.

Inspect {loreport_dir}/, identify recent source changes, and refresh only affected pages.
If the wiki is already current, do not edit files.{lang_note}
When editing, keep the existing documentation language unless the user asks to switch languages.

Last update metadata:
{_format_last_update(context.last_update)}

Git change summary:
{context.git_summary}
""".strip()

    if user_message and user_message.strip():
        prompt += f"\n\nAdditional user instruction:\n{user_message.strip()}"
    return prompt


def create_run_user_message(
    command: LoreportCommand,
    repo_path: str,
    context: RunContext,
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
) -> str:
    base = create_user_prompt(
        command, context, loreport_dir=loreport_dir, language=language
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
