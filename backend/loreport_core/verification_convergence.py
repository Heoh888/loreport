from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loreport_core.claim_extract import (
    has_concrete_claim_shape,
    is_pending_verification_status,
    is_shallow_verification_claim,
)
from loreport_core.compile_markers import (
    DRIFT_PENDING,
    INTEGRATIONS_PENDING,
    VERIFICATION_BEGIN,
    VERIFICATION_END,
)
from loreport_core.constants import LOREPORT_DIR
from loreport_core.doc_pattern import DRIFT_FILE, ServiceDocPattern

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


@dataclass(frozen=True, slots=True)
class PendingVerificationTarget:
    service_name: str
    loreport_file: str
    aspect_id: str
    pending_claims: tuple[str, ...]
    shallow_claims: tuple[str, ...]
    has_placeholder: bool
    integrations_pending: bool = False
    drift_pending: bool = False


def _parse_verification_rows(content: str) -> list[VerificationRow]:
    block_match = re.search(
        rf"{re.escape(VERIFICATION_BEGIN)}(.*?){re.escape(VERIFICATION_END)}",
        content,
        re.DOTALL,
    )
    block = block_match.group(1) if block_match else content

    rows: list[VerificationRow] = []
    for match in _VERIFICATION_ROW_RE.finditer(block):
        claim, code_ref, status = match.group(1), match.group(2), match.group(3)
        if claim.strip("- ").lower() in {"claim", "---"}:
            continue
        rows.append(
            VerificationRow(
                claim=claim.strip(),
                code_ref=code_ref.strip(),
                status=status.strip(),
            )
        )
    return rows


def _aspect_id_for_file(pattern: ServiceDocPattern, loreport_file: str) -> str:
    for aspect in pattern.aspects:
        if aspect.loreport_file == loreport_file:
            return aspect.id
    return "general"


def _integrations_pending(content: str) -> bool:
    return INTEGRATIONS_PENDING in content


def _drift_pending(
    repo_path: Path,
    service_name: str,
    loreport_dir: str,
) -> bool:
    drift_path = repo_path / loreport_dir / "services" / service_name / DRIFT_FILE
    if not drift_path.is_file():
        return True
    try:
        content = drift_path.read_text(encoding="utf-8")
    except OSError:
        return True
    return DRIFT_PENDING in content


def analyze_service_page(
    *,
    service_name: str,
    loreport_file: str,
    aspect_id: str,
    content: str,
    language: str | None = None,
    drift_pending: bool = False,
) -> PendingVerificationTarget | None:
    rows = _parse_verification_rows(content)
    has_placeholder = not rows or all(row.is_pending for row in rows)
    pending = tuple(row.claim for row in rows if row.is_pending)
    shallow = tuple(row.claim for row in rows if row.is_shallow)
    integrations_pending = aspect_id == "overview" and _integrations_pending(content)

    if not pending and not shallow and not integrations_pending and not drift_pending:
        return None

    return PendingVerificationTarget(
        service_name=service_name,
        loreport_file=loreport_file,
        aspect_id=aspect_id,
        pending_claims=pending,
        shallow_claims=shallow,
        has_placeholder=has_placeholder,
        integrations_pending=integrations_pending,
        drift_pending=drift_pending,
    )


def find_pending_verification_targets(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
) -> list[PendingVerificationTarget]:
    targets: list[PendingVerificationTarget] = []
    services_root = repo_path / loreport_dir / "services"
    if not services_root.is_dir():
        return targets

    for service_dir in sorted(services_root.iterdir(), key=lambda path: path.name.lower()):
        if not service_dir.is_dir():
            continue
        pattern = patterns.get(service_dir.name)
        if pattern is None:
            continue

        drift_pending = _drift_pending(repo_path, service_dir.name, loreport_dir)

        for aspect in pattern.aspects:
            page_path = service_dir / aspect.loreport_file
            if not page_path.is_file():
                continue
            try:
                content = page_path.read_text(encoding="utf-8")
            except OSError:
                continue

            target = analyze_service_page(
                service_name=service_dir.name,
                loreport_file=aspect.loreport_file,
                aspect_id=aspect.id,
                content=content,
                language=language,
                drift_pending=drift_pending and aspect.id == "overview",
            )
            if target is not None:
                targets.append(target)

        if drift_pending:
            drift_target = PendingVerificationTarget(
                service_name=service_dir.name,
                loreport_file=DRIFT_FILE,
                aspect_id="drift",
                pending_claims=(),
                shallow_claims=(),
                has_placeholder=True,
                drift_pending=True,
            )
            if not any(
                t.service_name == drift_target.service_name and t.loreport_file == DRIFT_FILE
                for t in targets
            ):
                targets.append(drift_target)

    return targets


def verification_progress_snapshot(targets: list[PendingVerificationTarget]) -> frozenset[str]:
    tokens: list[str] = []
    for target in sorted(targets, key=lambda item: (item.service_name, item.loreport_file)):
        tokens.append(target.service_name)
        tokens.append(target.loreport_file)
        tokens.extend(target.pending_claims)
        tokens.extend(target.shallow_claims)
        if target.integrations_pending:
            tokens.append("integrations:pending")
        if target.drift_pending:
            tokens.append("drift:pending")
    return frozenset(tokens)


def count_open_verification_items(targets: list[PendingVerificationTarget]) -> int:
    total = 0
    for target in targets:
        total += len(target.pending_claims)
        total += len(target.shallow_claims)
        if target.integrations_pending:
            total += 1
        if target.drift_pending:
            total += 1
    return total


def format_convergence_targets_block(
    targets: list[PendingVerificationTarget],
    *,
    loreport_dir: str = LOREPORT_DIR,
) -> str:
    blocks: list[str] = []
    for target in targets:
        rel_path = (
            f"{loreport_dir}/services/{target.service_name}/{target.loreport_file}"
        )
        lines = [f"### `{target.service_name}` → `{rel_path}`"]
        if target.pending_claims:
            lines.append("- Pending claims:")
            for claim in target.pending_claims:
                lines.append(f"  - {claim}")
        if target.shallow_claims:
            lines.append("- Shallow rows (replace with specific claims from human doc):")
            for claim in target.shallow_claims:
                lines.append(f"  - {claim}")
        if target.integrations_pending:
            lines.append(
                "- Fill integrations section "
                "(`<!-- loreport:section:integrations:pending -->`)"
            )
        if target.drift_pending:
            lines.append("- Fill drift.md from verification results")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
