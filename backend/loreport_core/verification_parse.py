from __future__ import annotations

import re
from dataclasses import dataclass

from loreport_core.claim_extract import (
    has_concrete_claim_shape,
    is_pending_verification_status,
    is_shallow_verification_claim,
)
from loreport_core.compile_markers import (
    TABLE_COL_CLAIM,
    TABLE_COL_CODE,
    TABLE_COL_STATUS,
    VERIFICATION_BEGIN,
    VERIFICATION_END,
)

_VERIFICATION_ROW_RE = re.compile(
    r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class VerificationRow:
    claim: str
    code_ref: str
    status: str

    @property
    def is_pending(self) -> bool:
        return is_pending_verification_status(self.status)

    @property
    def is_shallow(self) -> bool:
        if is_shallow_verification_claim(self.claim):
            return True
        if self.code_ref and not has_concrete_claim_shape(self.claim):
            return bool(re.search(r"\.(py|ts|tsx|go|rs|java)\b", self.code_ref, re.I))
        return False


def _is_table_meta_row(claim: str, code_ref: str, status: str) -> bool:
    """Skip header/separator rows — language-agnostic via loreport: status protocol."""
    claim_cell = claim.strip()
    if set(claim_cell) <= set("-: "):
        return True
    claim_key = claim_cell.strip("- ").lower()
    if claim_key in {TABLE_COL_CLAIM, "claim"}:
        return True
    if code_cell := code_ref.strip():
        if code_cell.lower() in {TABLE_COL_CODE, "code"} and not status.strip():
            return True
    status_cell = status.strip()
    # Data rows use loreport:* tokens; localized column headers and | --- | fail here.
    if status_cell and not status_cell.startswith("loreport:"):
        return True
    if status_cell.lower() in {TABLE_COL_STATUS, "status"}:
        return True
    return False


def parse_verification_rows(content: str) -> list[VerificationRow]:
    block_match = re.search(
        rf"{re.escape(VERIFICATION_BEGIN)}(.*?){re.escape(VERIFICATION_END)}",
        content,
        re.DOTALL,
    )
    block = block_match.group(1) if block_match else content

    rows: list[VerificationRow] = []
    for match in _VERIFICATION_ROW_RE.finditer(block):
        claim, code_ref, status = match.group(1), match.group(2), match.group(3)
        if _is_table_meta_row(claim, code_ref, status):
            continue
        rows.append(
            VerificationRow(
                claim=claim.strip(),
                code_ref=code_ref.strip(),
                status=status.strip(),
            )
        )
    return rows
