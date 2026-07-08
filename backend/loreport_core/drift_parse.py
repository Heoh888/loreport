from __future__ import annotations

import re
from dataclasses import dataclass

from loreport_core.compile_markers import (
    DRIFT_NONE,
    DRIFT_PENDING,
    DRIFT_SEVERITY_SLUGS,
    SECTION_DRIFT_BLOCKER,
    SECTION_DRIFT_FIX_DOC,
    SECTION_DRIFT_RESPOND,
    section_marker,
)

_TABLE_ROW_RE = re.compile(
    r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
    re.MULTILINE,
)

_LEGACY_SEVERITY_MAP = {
    "critical": SECTION_DRIFT_BLOCKER,
    "high": SECTION_DRIFT_BLOCKER,
    "warning": SECTION_DRIFT_RESPOND,
    "info": SECTION_DRIFT_FIX_DOC,
    "low": SECTION_DRIFT_FIX_DOC,
}


@dataclass(frozen=True, slots=True)
class DriftItem:
    aspect: str
    human_doc: str
    code: str
    issue: str
    severity: str


def _is_table_meta_row(cells: tuple[str, str, str, str]) -> bool:
    first = cells[0].strip("- :").lower()
    if set(cells[0].strip()) <= set("-: "):
        return True
    if first in {"aspect", "human-doc", "human", "code", "issue", "claim"}:
        return True
    return False


def _extract_section_block(content: str, slug: str) -> str:
    marker = re.escape(section_marker(slug))
    match = re.search(
        rf"{marker}\n#[^\n]*\n(.*?)(?=\n<!-- loreport:section:|\Z)",
        content,
        re.DOTALL,
    )
    return match.group(1) if match else ""


def _parse_section_items(block: str, severity: str) -> list[DriftItem]:
    if DRIFT_NONE in block:
        return []
    items: list[DriftItem] = []
    for match in _TABLE_ROW_RE.finditer(block):
        cells = (
            match.group(1).strip(),
            match.group(2).strip(),
            match.group(3).strip(),
            match.group(4).strip(),
        )
        if _is_table_meta_row(cells):
            continue
        items.append(
            DriftItem(
                aspect=cells[0],
                human_doc=cells[1],
                code=cells[2],
                issue=cells[3],
                severity=severity,
            )
        )
    return items


def parse_drift_items(content: str) -> list[DriftItem]:
    items: list[DriftItem] = []
    seen_slugs: set[str] = set()
    for slug in DRIFT_SEVERITY_SLUGS:
        seen_slugs.add(slug)
        items.extend(_parse_section_items(_extract_section_block(content, slug), slug))
    for legacy, mapped in _LEGACY_SEVERITY_MAP.items():
        if legacy in seen_slugs:
            continue
        items.extend(_parse_section_items(_extract_section_block(content, legacy), mapped))
    return items


def drift_is_pending(content: str) -> bool:
    if DRIFT_PENDING in content:
        return True
    if DRIFT_NONE in content:
        return False
    return not parse_drift_items(content)
