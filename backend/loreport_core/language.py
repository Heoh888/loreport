from __future__ import annotations

from loreport_core.constants import language_label, resolve_language

SERVICE_PAGE_SECTIONS = """
Service page structure (translate ALL headings and prose into OUTPUT LANGUAGE):
1. Purpose — one paragraph on service role
2. Human context — links to README, tech.docs/, ADR
3. Implementation signals — opened files with one-line roles (min 8 files; not directories)
4. Integrations — table: system, evidence file paths, role
5. Alignment — where human docs and code agree (concrete topics, not vague)
6. Gaps — concrete findings only; full drift registry lives in drift.md

Gap categories (translate labels into OUTPUT LANGUAGE, keep semantic meaning):
- documented intent exists but not found in inspected code
- found in code but not referenced in human docs
- human doc likely conflicts with inspected code
- could not verify from available evidence — ONLY external/uninspectable systems;
  NEVER for local files you can read with tools
""".strip()


def output_language_policy(language: str | None = None) -> str:
    code = resolve_language(language)
    label = language_label(code)
    return f"""
OUTPUT LANGUAGE: {label} ({code}) — highest priority rule.

Everything written to loreport/*.md must be entirely in {label}:
section headings, table headers, table body, gap labels, gap explanations, bullets, prose.

Only keep as-is: file paths, directory names, env vars, API route strings, code identifiers,
HTML loreport markers (`<!-- loreport:... -->`), slug headings until you translate them,
and short literal quotes from source files.

Pre-compiled pages use slug headings (`human-doc`, `code-verification`,
table cols `claim|code|status`).
Translate slugs to {label} when you edit_file — keep markers unchanged.

Forbidden in loreport/*.md:
- Prose in a language other than OUTPUT LANGUAGE ({code})
- Mixed-language pages
- Copying subagent/task research notes verbatim — rewrite into {label} first
- English headings (# Api, # Messaging) or English gap labels in non-English pages
- Pages where >40% of lines are file paths
""".strip()


def writer_language_discipline(language: str | None = None) -> str:
    code = resolve_language(language)
    label = language_label(code)
    return f"""
Writer discipline:
- You are the ONLY agent that writes loreport/*.md files.
- Subagent and task outputs are raw research — often English. Never paste them directly.
- Before each write_file/edit_file to loreport/, rewrite the full page in {label}.
- On update: read the existing .md page first, then rewrite changed sections in {label}.
- If an existing page uses the wrong language, translate the whole page to {label}.
""".strip()
