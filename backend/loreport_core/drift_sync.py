from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loreport_core.claim_extract import (
    drift_severity_for_status,
    is_match_verification_status,
    is_pending_verification_status,
)
from loreport_core.compile_markers import (
    DRIFT_NONE,
    SECTION_DRIFT_CRITICAL,
    SECTION_DRIFT_INFO,
    SECTION_DRIFT_TITLE,
    SECTION_DRIFT_WARNING,
    section_heading,
)
from loreport_core.constants import LOREPORT_DIR
from loreport_core.doc_pattern import DRIFT_FILE, ServiceDocPattern
from loreport_core.verification_parse import parse_verification_rows


@dataclass(frozen=True, slots=True)
class DriftEntry:
    source_file: str
    claim: str
    code_ref: str
    status: str


def _collect_drift_entries(
    service_dir: Path,
    pattern: ServiceDocPattern,
) -> list[DriftEntry]:
    entries: list[DriftEntry] = []
    for aspect in pattern.aspects:
        page_path = service_dir / aspect.loreport_file
        if not page_path.is_file():
            continue
        try:
            content = page_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for row in parse_verification_rows(content):
            if is_pending_verification_status(row.status):
                continue
            if is_match_verification_status(row.status):
                continue
            if drift_severity_for_status(row.status) is None:
                continue
            entries.append(
                DriftEntry(
                    source_file=aspect.loreport_file,
                    claim=row.claim,
                    code_ref=row.code_ref,
                    status=row.status,
                )
            )
    return entries


def _render_section(items: list[DriftEntry]) -> str:
    if not items:
        return DRIFT_NONE
    lines: list[str] = []
    for item in items:
        code_ref = f"`{item.code_ref}`" if item.code_ref else "—"
        lines.append(
            f"- `{item.source_file}` | {item.claim} | {code_ref} | `{item.status}`"
        )
    return "\n".join(lines)


def render_drift_file(entries: list[DriftEntry]) -> str:
    critical: list[DriftEntry] = []
    warning: list[DriftEntry] = []
    info: list[DriftEntry] = []
    for entry in entries:
        severity = drift_severity_for_status(entry.status)
        if severity == "critical":
            critical.append(entry)
        elif severity == "warning":
            warning.append(entry)
        else:
            info.append(entry)

    if not entries:
        critical_body = DRIFT_NONE
    else:
        critical_body = _render_section(critical) if critical else DRIFT_NONE

    warning_body = _render_section(warning) if warning else ""
    info_body = _render_section(info) if info else ""

    return "\n\n".join(
        [
            section_heading(SECTION_DRIFT_TITLE, level=1),
            section_heading(SECTION_DRIFT_CRITICAL),
            critical_body,
            section_heading(SECTION_DRIFT_WARNING),
            warning_body,
            section_heading(SECTION_DRIFT_INFO),
            info_body,
        ]
    ) + "\n"


def sync_service_drift(
    repo_path: Path,
    pattern: ServiceDocPattern,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> bool:
    service_dir = repo_path / loreport_dir / "services" / pattern.service_name
    if not service_dir.is_dir():
        return False
    entries = _collect_drift_entries(service_dir, pattern)
    drift_path = service_dir / DRIFT_FILE
    drift_path.write_text(render_drift_file(entries), encoding="utf-8")
    return True


def sync_repo_drift(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> int:
    synced = 0
    for pattern in patterns.values():
        if sync_service_drift(repo_path, pattern, loreport_dir=loreport_dir):
            synced += 1
    return synced
