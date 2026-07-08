from __future__ import annotations

from pathlib import Path

from loreport_core.compile_markers import (
    DETAILS_PENDING,
    DRIFT_PENDING,
    DRIFT_TRAFFIC_LEGEND,
    HUMAN_DOC_BEGIN,
    HUMAN_DOC_END,
    INTEGRATIONS_PENDING,
    SECTION_DETAILS,
    SECTION_DRIFT_BLOCKER,
    SECTION_DRIFT_FIX_CODE,
    SECTION_DRIFT_FIX_DOC,
    SECTION_DRIFT_RESPOND,
    SECTION_DRIFT_SUMMARY,
    SECTION_DRIFT_TITLE,
    SECTION_HUMAN_DOC,
    SECTION_INDEX_SECTIONS,
    SECTION_INTEGRATIONS,
    aspect_link_label,
    drift_severity_table_header,
    section_heading,
)
from loreport_core.constants import LOREPORT_DIR
from loreport_core.doc_pattern import (
    DRIFT_FILE,
    DocAspect,
    ServiceDocPattern,
)


def _read_service_markdown(
    repo_path: Path,
    service_name: str,
    relative_path: str,
) -> str | None:
    target = repo_path / service_name / relative_path
    if not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _format_sources(service_name: str, human_files: tuple[str, ...]) -> str:
    if not human_files:
        return f"> source: `/{service_name}/` (code-first)"
    paths = ", ".join(f"`/{service_name}/{path}`" for path in human_files)
    return f"> source: {paths}"


def _format_human_doc_body(
    repo_path: Path,
    service_name: str,
    human_files: tuple[str, ...],
) -> str:
    if not human_files:
        return "<!-- loreport:code-first -->"

    blocks: list[str] = []
    for human_file in human_files:
        content = _read_service_markdown(repo_path, service_name, human_file)
        if content is None:
            blocks.append(f"### `{human_file}`\n\n<!-- loreport:missing-file -->")
            continue
        if len(human_files) > 1:
            blocks.append(f"### `{human_file}`\n\n{content}")
        else:
            blocks.append(content)
    return "\n\n".join(blocks)


def compile_aspect_draft(
    pattern: ServiceDocPattern,
    aspect: DocAspect,
    repo_path: Path,
    *,
    language: str | None = None,
) -> str:
    del language
    human_body = _format_human_doc_body(repo_path, pattern.service_name, aspect.human_files)
    return "\n\n".join(
        [
            _format_sources(pattern.service_name, aspect.human_files),
            section_heading(SECTION_HUMAN_DOC),
            HUMAN_DOC_BEGIN,
            human_body,
            HUMAN_DOC_END,
            section_heading(SECTION_DETAILS),
            DETAILS_PENDING,
        ]
    )


def compile_index_draft(
    pattern: ServiceDocPattern,
    repo_path: Path,
    *,
    language: str | None = None,
) -> str:
    del language
    overview_aspect = next(
        (aspect for aspect in pattern.aspects if aspect.id == "overview"),
        None,
    )
    human_files = overview_aspect.human_files if overview_aspect else ()
    human_body = _format_human_doc_body(repo_path, pattern.service_name, human_files)

    section_links: list[str] = []
    for aspect in pattern.aspects:
        if aspect.id == "overview":
            continue
        label = aspect_link_label(aspect.id)
        section_links.append(f"- [{label}]({aspect.loreport_file})")

    sections_block = "\n".join(section_links) if section_links else "<!-- loreport:no-aspects -->"

    return "\n\n".join(
        [
            _format_sources(pattern.service_name, human_files),
            section_heading(SECTION_HUMAN_DOC),
            HUMAN_DOC_BEGIN,
            human_body,
            HUMAN_DOC_END,
            section_heading(SECTION_INDEX_SECTIONS),
            sections_block,
            section_heading(SECTION_INTEGRATIONS),
            INTEGRATIONS_PENDING,
            section_heading(SECTION_DRIFT_SUMMARY),
            "[drift.md](drift.md)",
        ]
    )


def compile_drift_draft(*, language: str | None = None) -> str:
    del language
    empty_table = drift_severity_table_header()
    return "\n\n".join(
        [
            section_heading(SECTION_DRIFT_TITLE, level=1),
            DRIFT_TRAFFIC_LEGEND,
            DRIFT_PENDING,
            section_heading(SECTION_DRIFT_BLOCKER, label="🔴 blocker"),
            empty_table,
            section_heading(SECTION_DRIFT_RESPOND, label="🟠 respond"),
            empty_table,
            section_heading(SECTION_DRIFT_FIX_DOC, label="🟡 fix-doc"),
            empty_table,
            section_heading(SECTION_DRIFT_FIX_CODE, label="🟢 fix-code"),
            empty_table,
        ]
    ) + "\n"


def write_compiled_drafts(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
    only_missing: bool = False,
) -> int:
    """Pre-compile human docs into service aspect pages. Returns files written."""
    written = 0
    for pattern in patterns.values():
        service_dir = repo_path / loreport_dir / "services" / pattern.service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        for aspect in pattern.aspects:
            if aspect.id == "overview":
                content = compile_index_draft(pattern, repo_path, language=language)
            else:
                content = compile_aspect_draft(
                    pattern,
                    aspect,
                    repo_path,
                    language=language,
                )
            target = service_dir / aspect.loreport_file
            if only_missing and target.is_file():
                continue
            target.write_text(content + "\n", encoding="utf-8")
            written += 1

        drift_target = service_dir / DRIFT_FILE
        if not only_missing or not drift_target.is_file():
            drift_target.write_text(compile_drift_draft(language=language), encoding="utf-8")
            written += 1

    return written
