from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loreport_core.compile_markers import INTEGRATIONS_PENDING
from loreport_core.constants import LOREPORT_DIR
from loreport_core.doc_pattern import DRIFT_FILE, ServiceDocPattern
from loreport_core.drift_parse import drift_is_pending


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


def _integrations_pending(content: str) -> bool:
    return INTEGRATIONS_PENDING in content


def find_pending_verification_targets(
    repo_path: Path,
    patterns: dict[str, ServiceDocPattern],
    *,
    loreport_dir: str = LOREPORT_DIR,
    language: str | None = None,
) -> list[PendingVerificationTarget]:
    del language
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

        index_path = service_dir / "index.md"
        if index_path.is_file():
            try:
                index_content = index_path.read_text(encoding="utf-8")
            except OSError:
                index_content = ""
            if _integrations_pending(index_content):
                targets.append(
                    PendingVerificationTarget(
                        service_name=service_dir.name,
                        loreport_file="index.md",
                        aspect_id="overview",
                        pending_claims=(),
                        shallow_claims=(),
                        has_placeholder=False,
                        integrations_pending=True,
                    )
                )

        drift_path = service_dir / DRIFT_FILE
        if not drift_path.is_file():
            targets.append(
                PendingVerificationTarget(
                    service_name=service_dir.name,
                    loreport_file=DRIFT_FILE,
                    aspect_id="drift",
                    pending_claims=(),
                    shallow_claims=(),
                    has_placeholder=True,
                    drift_pending=True,
                )
            )
            continue

        try:
            drift_content = drift_path.read_text(encoding="utf-8")
        except OSError:
            drift_content = ""

        if drift_is_pending(drift_content):
            targets.append(
                PendingVerificationTarget(
                    service_name=service_dir.name,
                    loreport_file=DRIFT_FILE,
                    aspect_id="drift",
                    pending_claims=(),
                    shallow_claims=(),
                    has_placeholder=True,
                    drift_pending=True,
                )
            )

    return targets


def verification_progress_snapshot(targets: list[PendingVerificationTarget]) -> frozenset[str]:
    tokens: list[str] = []
    for target in sorted(targets, key=lambda item: (item.service_name, item.loreport_file)):
        tokens.append(target.service_name)
        tokens.append(target.loreport_file)
        if target.integrations_pending:
            tokens.append("integrations:pending")
        if target.drift_pending:
            tokens.append("drift:pending")
    return frozenset(tokens)


def count_open_verification_items(targets: list[PendingVerificationTarget]) -> int:
    total = 0
    for target in targets:
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
        if target.integrations_pending:
            lines.append(
                "- Fill integrations section "
                "(`<!-- loreport:section:integrations:pending -->`)"
            )
        if target.drift_pending:
            lines.append(
                "- Fill drift.md (🔴 blocker / 🟠 respond / 🟡 fix-doc / 🟢 fix-code); "
                "use drift-classifier + drift-verifier; remove drift:pending or set drift:none"
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
