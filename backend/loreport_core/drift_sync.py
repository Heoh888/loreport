from __future__ import annotations

import re
from pathlib import Path

from loreport_core.compile_markers import (
    DRIFT_NONE,
    SECTION_DRIFT_BLOCKER,
    SECTION_DRIFT_FIX_CODE,
    SECTION_DRIFT_FIX_DOC,
    SECTION_DRIFT_RESPOND,
    SECTION_DRIFT_SUMMARY,
    section_marker,
)
from loreport_core.constants import LOREPORT_DIR
from loreport_core.doc_pattern import DRIFT_FILE, ServiceDocPattern
from loreport_core.drift_parse import DriftItem, parse_drift_items

_SEVERITY_ICON = {
    SECTION_DRIFT_BLOCKER: "🔴",
    SECTION_DRIFT_RESPOND: "🟠",
    SECTION_DRIFT_FIX_DOC: "🟡",
    SECTION_DRIFT_FIX_CODE: "🟢",
}


def _render_drift_summary(items: list[DriftItem]) -> str:
    lines = ["[drift.md](drift.md)", ""]
    if not items:
        lines.append(DRIFT_NONE)
        return "\n".join(lines)
    for item in items[:3]:
        icon = _SEVERITY_ICON.get(item.severity, "•")
        lines.append(f"- {icon} `{item.aspect}` — {item.issue}")
    if len(items) > 3:
        lines.append(f"- … +{len(items) - 3} more in [drift.md](drift.md)")
    return "\n".join(lines)


def _replace_marked_section_body(content: str, slug: str, body: str) -> str:
    marker = re.escape(section_marker(slug))
    pattern = re.compile(
        rf"({marker}\n#[^\n]*\n)(.*?)(?=\n<!-- loreport:section:|\Z)",
        re.DOTALL,
    )
    if not pattern.search(content):
        return content
    return pattern.sub(rf"\1{body}", content, count=1)


def _patch_index_drift_summary(service_dir: Path, items: list[DriftItem]) -> None:
    index_path = service_dir / "index.md"
    if not index_path.is_file():
        return
    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError:
        return
    summary = _render_drift_summary(items)
    patched = _replace_marked_section_body(content, SECTION_DRIFT_SUMMARY, summary)
    if patched != content:
        index_path.write_text(patched, encoding="utf-8")


def sync_service_drift_summary(
    repo_path: Path,
    pattern: ServiceDocPattern,
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> bool:
    """Sync index.md drift-summary from agent-written drift.md."""
    service_dir = repo_path / loreport_dir / "services" / pattern.service_name
    drift_path = service_dir / DRIFT_FILE
    if not service_dir.is_dir() or not drift_path.is_file():
        return False
    try:
        content = drift_path.read_text(encoding="utf-8")
    except OSError:
        return False
    items = parse_drift_items(content)
    _patch_index_drift_summary(service_dir, items)
    return True


def sync_repo_drift_summaries(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> int:
    synced = 0
    for pattern in patterns.values():
        if sync_service_drift_summary(repo_path, pattern, loreport_dir=loreport_dir):
            synced += 1
    return synced
